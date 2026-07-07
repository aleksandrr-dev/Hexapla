package com.aleks.hexapla

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.media.MediaPlayer
import android.os.Build
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.support.v4.media.MediaMetadataCompat
import android.support.v4.media.session.MediaSessionCompat
import android.support.v4.media.session.PlaybackStateCompat
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

/** Cross-screen playback state, written by [ReadingService], observed by the UI. */
object Playback {
    val active = mutableStateOf(false)      // service alive (playing or paused)
    val playing = mutableStateOf(false)     // actually speaking right now
    val book = mutableIntStateOf(-1)
    val chapter = mutableIntStateOf(-1)
    val verse = mutableIntStateOf(-1)
    val sleepMinutes = mutableIntStateOf(0) // 0 = off, -1 = end of chapter
    // Character range of the word currently being spoken within the verse text
    // (engine-dependent; Google's local voices report it, some engines don't).
    val wordStart = mutableIntStateOf(-1)
    val wordEnd = mutableIntStateOf(-1)
}

/**
 * Foreground media service that reads chapters aloud with the device TTS engine.
 * Keeps playing with the screen off or the app minimized; exposes controls via a
 * media-style notification and MediaSession (headset buttons, lockscreen).
 * TTS cannot pause mid-utterance, so pause stops speech and resume restarts
 * from the verse that was being read.
 */
class ReadingService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private var tts: TextToSpeech? = null
    private var ttsReady = false

    private var books: List<Book> = emptyList()
    private var bookIdx = 0
    private var chapterIdx = 0
    private var verseIdx = 0
    private var translationId = ""
    private var settings = AppSettings()
    private var voicePrefs: Map<String, String> = emptyMap()

    private var sleepJob: Job? = null
    private var rateJob: Job? = null
    private var session: MediaSessionCompat? = null
    private var focusRequest: AudioFocusRequest? = null

    // Optional instrumental bed under the reading (opt-in in Settings).
    private var musicPlayer: MediaPlayer? = null

    // Narrated audio (LibriVox) mode; when null/false, TTS is used.
    private var player: MediaPlayer? = null
    private var narrating = false
    private var currentSection: AudioRepo.Section? = null
    private var audioSections: Map<Int, List<AudioRepo.Section>> = emptyMap()
    private var downloadPercent = -1

    override fun onBind(intent: Intent?) = null

    override fun onCreate() {
        super.onCreate()
        // Settings changes apply to live playback: music volume/toggle
        // immediately, speech rate from the next verse (TTS) or instantly
        // (narrated player).
        scope.launch {
            Store.settings(this@ReadingService).collect { s ->
                val old = settings
                settings = s
                if (s.musicEnabled != old.musicEnabled) {
                    if (!s.musicEnabled) releaseMusic()
                    else if (Playback.playing.value) startMusic()
                } else if (s.musicVolume != old.musicVolume) {
                    val v = s.musicVolume.coerceIn(0f, 1f)
                    try { musicPlayer?.setVolume(v, v) } catch (_: Exception) { }
                }
                if (s.speechRate != old.speechRate) {
                    try { tts?.setSpeechRate(s.speechRate) } catch (_: Exception) { }
                    if (narrating) {
                        try {
                            player?.let {
                                if (it.isPlaying) it.playbackParams =
                                    it.playbackParams.setSpeed(s.speechRate)
                            }
                        } catch (_: Exception) { }
                    } else if (Playback.playing.value) {
                        // TTS can't change rate mid-utterance: once the slider
                        // settles, restart the current verse at the new speed.
                        rateJob?.cancel()
                        rateJob = scope.launch {
                            delay(700)
                            if (!narrating && Playback.playing.value) speakVerse(verseIdx)
                        }
                    }
                }
            }
        }
        session = MediaSessionCompat(this, "hexapla-reading").apply {
            setCallback(object : MediaSessionCompat.Callback() {
                override fun onPlay() = resume()
                override fun onPause() = pause()
                override fun onStop() = stopEverything()
                override fun onSkipToNext() = skipChapter(+1)
                override fun onSkipToPrevious() = skipChapter(-1)
                override fun onSeekTo(pos: Long) {
                    if (narrating) {
                        try { player?.seekTo(pos.toInt()) } catch (_: Exception) { }
                    } else {
                        // TTS timeline is virtual: one verse per VERSE_MS slot.
                        val v = (pos / VERSE_MS).toInt()
                            .coerceIn(0, (chapterVerses.size - 1).coerceAtLeast(0))
                        verseIdx = v
                        Playback.verse.intValue = v
                        if (Playback.playing.value) speakVerse(v)
                    }
                    updateSessionState(Playback.playing.value)
                    updateNotification()
                }
            })
        }
        tts = TextToSpeech(this) { status ->
            ttsReady = status == TextToSpeech.SUCCESS
            if (ttsReady) {
                // Engine callbacks arrive on a binder thread; hop to main where
                // the session, notifications and our state live.
                tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(utteranceId: String?) {
                        val v = utteranceId?.substringAfter(':')?.toIntOrNull() ?: return
                        scope.launch {
                            verseIdx = v
                            Playback.verse.intValue = v
                            Playback.wordStart.intValue = -1
                            Playback.wordEnd.intValue = -1
                            updateSessionState(Playback.playing.value)
                            updateNotification()
                        }
                    }

                    override fun onRangeStart(utteranceId: String?, start: Int, end: Int, frame: Int) {
                        Playback.wordStart.intValue = start
                        Playback.wordEnd.intValue = end
                    }

                    override fun onDone(utteranceId: String?) {
                        // Verses are fed one at a time: pre-queueing a whole
                        // chapter loses utterances while the engine is still
                        // loading a newly-selected language's voice data.
                        val v = utteranceId?.substringAfter(':')?.toIntOrNull() ?: return
                        scope.launch {
                            if (!narrating && Playback.playing.value) speakVerse(v + 1)
                        }
                    }

                    @Deprecated("Deprecated in Java")
                    override fun onError(utteranceId: String?) {
                        scope.launch { stopEverything() }
                    }
                })
                pendingStart?.invoke()
                pendingStart = null
            }
        }
    }

    private var pendingStart: (() -> Unit)? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_PLAY -> {
                val b = intent.getIntExtra(EXTRA_BOOK, 0)
                val c = intent.getIntExtra(EXTRA_CHAPTER, 0)
                val v = intent.getIntExtra(EXTRA_VERSE, 0)
                startForeground(NOTIF_ID, buildNotification())
                scope.launch {
                    settings = Store.currentSettings(this@ReadingService)
                    voicePrefs = Store.voicePrefs(this@ReadingService).first()
                    translationId = settings.primaryId
                    books = BibleRepo.load(this@ReadingService, translationId)
                    audioSections = if (settings.audioNarration && translationId == "kjv")
                        try { AudioRepo.index(this@ReadingService) } catch (_: Exception) { emptyMap() }
                    else emptyMap()
                    bookIdx = b; chapterIdx = c; verseIdx = v
                    if (ttsReady || sectionForCurrent() != null) startChapter(fromVerse = v)
                    else pendingStart = { startChapter(fromVerse = v) }
                }
            }
            ACTION_PAUSE -> pause()
            ACTION_RESUME -> resume()
            ACTION_STOP -> stopEverything()
            ACTION_NEXT -> skipChapter(+1)
            ACTION_PREV -> skipChapter(-1)
            ACTION_TIMER -> setSleepTimer(intent.getIntExtra(EXTRA_MINUTES, 0))
        }
        return START_NOT_STICKY
    }

    private fun sectionForCurrent(): AudioRepo.Section? =
        AudioRepo.sectionFor(audioSections[bookIdx], chapterIdx)

    /** Entry point for playing the current chapter in whichever mode applies. */
    private fun startChapter(fromVerse: Int = 0) {
        val sec = sectionForCurrent()
        if (sec != null) playSection(sec, sectionFraction(sec, chapterIdx, fromVerse))
        else speakCurrentChapter(fromVerse)
    }

    /**
     * Approximate position of (chapter, verse) inside a multi-chapter section,
     * as a fraction of its verse count — recordings have no verse timestamps,
     * so verse count is the best proxy for elapsed time.
     */
    private fun sectionFraction(sec: AudioRepo.Section, chapter: Int, verse: Int): Float {
        val chapters = books.getOrNull(bookIdx)?.chapters ?: return 0f
        var before = 0
        var total = 0
        for (c in (sec.first - 1) until sec.last) {
            val n = chapters.getOrNull(c)?.size ?: 0
            when {
                c < chapter -> before += n
                c == chapter -> before += verse.coerceIn(0, n)
            }
            total += n
        }
        return if (total > 0) before.toFloat() / total else 0f
    }

    private fun playSection(sec: AudioRepo.Section, fraction: Float = 0f) {
        tts?.stop()
        releasePlayer()
        if (!requestFocus()) { stopEverything(); return }
        narrating = true
        currentSection = sec
        downloadPercent = 0
        startMusic()
        Playback.active.value = true
        Playback.playing.value = true
        Playback.book.intValue = bookIdx
        Playback.chapter.intValue = chapterIdx
        Playback.verse.intValue = -1
        Playback.wordStart.intValue = -1
        Playback.wordEnd.intValue = -1
        updateSessionState(playing = true)
        updateNotification()
        scope.launch { Store.setLastPosition(this@ReadingService, bookIdx, chapterIdx) }
        scope.launch {
            var lastShown = -10
            val file = AudioRepo.ensureDownloaded(this@ReadingService, sec.url) { pct ->
                if (pct >= lastShown + 10) {
                    lastShown = pct
                    downloadPercent = pct
                    scope.launch { updateNotification() }
                }
            }
            downloadPercent = -1
            if (currentSection != sec) return@launch  // user moved on meanwhile
            if (file == null) {
                // Download failed (offline?) — fall back to TTS for this chapter.
                narrating = false
                speakCurrentChapter(fromVerse = 0)
                return@launch
            }
            player = MediaPlayer().apply {
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .build()
                )
                setDataSource(file.path)
                setOnPreparedListener { mp ->
                    // Land a few seconds early so the target verse isn't clipped.
                    val skipMs = (mp.duration * fraction).toInt() - 4000
                    if (skipMs > 1000) mp.seekTo(skipMs)
                    try {
                        mp.playbackParams = mp.playbackParams.setSpeed(settings.speechRate)
                    } catch (_: Exception) { mp.start() }
                    updateSessionState(playing = true)
                    updateNotification()
                }
                setOnCompletionListener { onSectionFinished(sec) }
                setOnErrorListener { _, _, _ -> stopEverything(); true }
                prepareAsync()
            }
        }
    }

    private fun onSectionFinished(sec: AudioRepo.Section) {
        val endOfChapterTimer = Playback.sleepMinutes.intValue == -1
        if (!settings.autoContinue || endOfChapterTimer) { stopEverything(); return }
        // Next chapter after the section (sec.last is 1-based inclusive).
        var b = bookIdx
        var c = sec.last  // 0-based index of the chapter after the section
        while (b < books.size && c >= books[b].chapters.size) { b++; c = 0 }
        if (b >= books.size) { stopEverything(); return }
        bookIdx = b; chapterIdx = c
        startChapter(fromVerse = 0)
    }

    private fun releasePlayer() {
        player?.let { try { it.stop() } catch (_: Exception) {}; it.release() }
        player = null
        narrating = false
        currentSection = null
        downloadPercent = -1
    }

    /* ---- Background music bed: rotates softly through the bundled tracks
       (piano, orchestral, strings, ambient) while the reading plays. ---- */

    private val musicTracks: List<String> by lazy {
        try {
            (assets.list("music") ?: emptyArray()).map { "music/$it" }.shuffled()
        } catch (_: Exception) { emptyList() }
    }
    private var musicIndex = 0

    private fun startMusic() {
        if (!settings.musicEnabled || musicTracks.isEmpty()) return
        val vol = settings.musicVolume.coerceIn(0f, 1f)
        musicPlayer?.let {
            try { it.setVolume(vol, vol); if (!it.isPlaying) it.start() } catch (_: Exception) { }
            return
        }
        playMusicTrack(musicIndex)
    }

    private fun playMusicTrack(index: Int) {
        val vol = settings.musicVolume.coerceIn(0f, 1f)
        try {
            val afd = assets.openFd(musicTracks[index % musicTracks.size])
            musicPlayer = MediaPlayer().apply {
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                        .build()
                )
                setDataSource(afd.fileDescriptor, afd.startOffset, afd.length)
                afd.close()
                setVolume(vol, vol)
                setOnPreparedListener { if (Playback.playing.value) it.start() }
                setOnCompletionListener {
                    // Rotate to the next track so long sessions don't go stale.
                    musicIndex = (index + 1) % musicTracks.size
                    releaseMusic()
                    if (Playback.playing.value && settings.musicEnabled) {
                        playMusicTrack(musicIndex)
                    }
                }
                prepareAsync()
            }
        } catch (_: Exception) {
            musicPlayer = null
        }
    }

    private fun pauseMusic() {
        try { musicPlayer?.pause() } catch (_: Exception) { }
    }

    private fun releaseMusic() {
        musicPlayer?.let { try { it.stop() } catch (_: Exception) {}; it.release() }
        musicPlayer = null
    }

    private var chapterVerses: List<String> = emptyList()

    private fun speakVerse(i: Int) {
        val engine = tts ?: return
        if (i >= chapterVerses.size) { onChapterFinished(); return }
        verseIdx = i
        engine.speak(chapterVerses[i], TextToSpeech.QUEUE_FLUSH, null, "v:$i")
    }

    private fun speakCurrentChapter(fromVerse: Int = 0) {
        releasePlayer()
        val engine = tts ?: return
        val verses = books.getOrNull(bookIdx)?.chapters?.getOrNull(chapterIdx) ?: return
        chapterVerses = verses
        val locale = BibleRepo.translation(translationId).locale
        val result = engine.setLanguage(locale)
        if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
            stopEverything(); return
        }
        voicePrefs[locale.language]?.let { name ->
            try {
                engine.voices?.firstOrNull { it.name == name }?.let { engine.voice = it }
            } catch (_: Exception) { }
        }
        engine.setSpeechRate(settings.speechRate)
        if (!requestFocus()) { stopEverything(); return }

        engine.stop()
        startMusic()
        val start = fromVerse.coerceIn(0, verses.size - 1)
        Playback.active.value = true
        Playback.playing.value = true
        Playback.book.intValue = bookIdx
        Playback.chapter.intValue = chapterIdx
        Playback.verse.intValue = start
        updateSessionState(playing = true)
        updateNotification()
        scope.launch { Store.setLastPosition(this@ReadingService, bookIdx, chapterIdx) }
        speakVerse(start)
    }

    private fun onChapterFinished() {
        val endOfChapterTimer = Playback.sleepMinutes.intValue == -1
        if (!settings.autoContinue || endOfChapterTimer) {
            stopEverything(); return
        }
        // Advance to the next non-empty chapter, or stop at the end of the Bible.
        var b = bookIdx
        var c = chapterIdx + 1
        while (b < books.size && c >= books[b].chapters.size) { b++; c = 0 }
        if (b >= books.size) { stopEverything(); return }
        bookIdx = b; chapterIdx = c
        startChapter(fromVerse = 0)
    }

    private fun skipChapter(delta: Int) {
        if (books.isEmpty()) return
        var b = bookIdx
        // In narrated mode skip whole sections, else single chapters.
        val sec = if (narrating) currentSection else null
        var c = when {
            sec != null && delta > 0 -> sec.last
            sec != null && delta < 0 -> sec.first - 2
            else -> chapterIdx + delta
        }
        if (delta > 0) {
            while (b < books.size && c >= books[b].chapters.size) { b++; c = 0 }
            if (b >= books.size) return
        } else if (c < 0) {
            var nb = b - 1
            while (nb >= 0 && books[nb].chapters.isEmpty()) nb--
            if (nb < 0) return
            b = nb; c = books[b].chapters.size - 1
        }
        bookIdx = b; chapterIdx = c
        startChapter(fromVerse = 0)
    }

    private fun pause() {
        if (narrating) {
            try { player?.pause() } catch (_: Exception) {}
        } else {
            tts?.stop()
        }
        pauseMusic()
        Playback.playing.value = false
        updateSessionState(playing = false)
        updateNotification()
    }

    private fun resume() {
        if (books.isEmpty()) return
        if (narrating && player != null) {
            try { player?.start() } catch (_: Exception) { startChapter(fromVerse = 0); return }
            startMusic()
            Playback.playing.value = true
            updateSessionState(playing = true)
            updateNotification()
        } else {
            startChapter(fromVerse = verseIdx)
        }
    }

    private fun setSleepTimer(minutes: Int) {
        sleepJob?.cancel()
        Playback.sleepMinutes.intValue = minutes
        if (minutes > 0) {
            sleepJob = scope.launch {
                delay(minutes * 60_000L)
                stopEverything()
            }
        }
    }

    private fun stopEverything() {
        // Persist the spot so pressing play later resumes here instead of
        // restarting the chapter. Independent scope: ours dies with the service.
        if (books.isNotEmpty()) {
            val b = bookIdx; val c = chapterIdx; val v = verseIdx
            CoroutineScope(Dispatchers.IO).launch {
                Store.setLastPosition(this@ReadingService, b, c)
                Store.setLastVerse(this@ReadingService, v)
            }
        }
        sleepJob?.cancel()
        tts?.stop()
        releasePlayer()
        releaseMusic()
        Playback.active.value = false
        Playback.playing.value = false
        Playback.verse.intValue = -1
        Playback.wordStart.intValue = -1
        Playback.wordEnd.intValue = -1
        Playback.sleepMinutes.intValue = 0
        updateSessionState(playing = false)
        abandonFocus()
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    /* ---- Audio focus: behave like a music app around calls and other media. ---- */

    private val focusListener = AudioManager.OnAudioFocusChangeListener { change ->
        when (change) {
            AudioManager.AUDIOFOCUS_LOSS,
            AudioManager.AUDIOFOCUS_LOSS_TRANSIENT -> pause()
        }
    }

    private fun requestFocus(): Boolean {
        val am = getSystemService(Context.AUDIO_SERVICE) as AudioManager
        val req = focusRequest ?: AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build()
            )
            .setOnAudioFocusChangeListener(focusListener)
            .build()
            .also { focusRequest = it }
        return am.requestAudioFocus(req) == AudioManager.AUDIOFOCUS_REQUEST_GRANTED
    }

    private fun abandonFocus() {
        focusRequest?.let {
            (getSystemService(Context.AUDIO_SERVICE) as AudioManager).abandonAudioFocusRequest(it)
        }
    }

    /* ---- Notification ---- */

    private fun ensureChannel() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (nm.getNotificationChannel(CHANNEL_ID) == null) {
            nm.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_ID,
                    getString(R.string.playback_channel),
                    NotificationManager.IMPORTANCE_LOW
                )
            )
        }
    }

    private fun action(icon: Int, title: Int, act: String): NotificationCompat.Action {
        val pi = PendingIntent.getService(
            this, act.hashCode(),
            Intent(this, ReadingService::class.java).setAction(act),
            PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Action(icon, getString(title), pi)
    }

    private fun buildNotification(): Notification {
        ensureChannel()
        val sec = currentSection
        val title = books.getOrNull(bookIdx)?.let { b ->
            if (narrating && sec != null && sec.last > sec.first)
                "${b.name} ${sec.first}–${sec.last}"
            else "${b.name} ${chapterIdx + 1}"
        } ?: getString(R.string.app_name)
        val contentText = when {
            narrating && downloadPercent >= 0 ->
                getString(R.string.audio_downloading, downloadPercent)
            narrating -> getString(R.string.audio_narrated)
            else -> getString(R.string.playback_verse, verseIdx + 1)
        }
        val playing = Playback.playing.value
        val art = books.getOrNull(bookIdx)?.let { BookArt.forBook(this, bookIdx, it.name) }
        val durationMs = if (narrating) {
            try { player?.duration?.toLong() ?: -1L } catch (_: Exception) { -1L }
        } else chapterVerses.size * VERSE_MS
        session?.setMetadata(
            MediaMetadataCompat.Builder()
                .putString(MediaMetadataCompat.METADATA_KEY_TITLE, title)
                .putString(
                    MediaMetadataCompat.METADATA_KEY_ARTIST,
                    BibleRepo.translation(translationId).label
                )
                .putBitmap(MediaMetadataCompat.METADATA_KEY_ALBUM_ART, art)
                .apply { if (durationMs > 0) putLong(MediaMetadataCompat.METADATA_KEY_DURATION, durationMs) }
                .build()
        )
        val contentPi = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_book)
            .setLargeIcon(art)
            .setContentTitle(title)
            .setContentText(contentText)
            .setContentIntent(contentPi)
            .setOngoing(playing)
            .setOnlyAlertOnce(true)
            .addAction(action(android.R.drawable.ic_media_previous, R.string.prev_chapter, ACTION_PREV))
            .addAction(
                if (playing) action(android.R.drawable.ic_media_pause, R.string.pause_audio, ACTION_PAUSE)
                else action(android.R.drawable.ic_media_play, R.string.play_audio, ACTION_RESUME)
            )
            .addAction(action(android.R.drawable.ic_media_next, R.string.next_chapter, ACTION_NEXT))
            .setStyle(
                androidx.media.app.NotificationCompat.MediaStyle()
                    .setMediaSession(session?.sessionToken)
                    .setShowActionsInCompactView(0, 1, 2)
            )
            .build()
    }

    private fun updateNotification() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.notify(NOTIF_ID, buildNotification())
    }

    private fun updateSessionState(playing: Boolean) {
        // Real position for narrated audio; a virtual verse timeline for TTS
        // (VERSE_MS per verse) so the system seek bar works in both modes.
        val position = if (narrating) {
            try { player?.currentPosition?.toLong() ?: 0L } catch (_: Exception) { 0L }
        } else verseIdx * VERSE_MS
        session?.isActive = playing || Playback.active.value
        session?.setPlaybackState(
            PlaybackStateCompat.Builder()
                .setActions(
                    PlaybackStateCompat.ACTION_PLAY or PlaybackStateCompat.ACTION_PAUSE or
                        PlaybackStateCompat.ACTION_STOP or
                        PlaybackStateCompat.ACTION_SEEK_TO or
                        PlaybackStateCompat.ACTION_SKIP_TO_NEXT or
                        PlaybackStateCompat.ACTION_SKIP_TO_PREVIOUS
                )
                .setState(
                    if (playing) PlaybackStateCompat.STATE_PLAYING else PlaybackStateCompat.STATE_PAUSED,
                    position,
                    if (playing) settings.speechRate else 0f
                )
                .build()
        )
    }

    override fun onDestroy() {
        sleepJob?.cancel()
        releasePlayer()
        releaseMusic()
        tts?.stop(); tts?.shutdown(); tts = null
        session?.release(); session = null
        abandonFocus()
        Playback.active.value = false
        Playback.playing.value = false
        Playback.verse.intValue = -1
        scope.cancel()
        super.onDestroy()
    }

    companion object {
        private const val CHANNEL_ID = "reading_playback"
        private const val NOTIF_ID = 42
        // Virtual milliseconds per verse for the TTS seek bar timeline.
        private const val VERSE_MS = 15_000L

        const val ACTION_PLAY = "com.aleks.hexapla.PLAY"
        const val ACTION_PAUSE = "com.aleks.hexapla.PAUSE"
        const val ACTION_RESUME = "com.aleks.hexapla.RESUME"
        const val ACTION_STOP = "com.aleks.hexapla.STOP"
        const val ACTION_NEXT = "com.aleks.hexapla.NEXT"
        const val ACTION_PREV = "com.aleks.hexapla.PREV"
        const val ACTION_TIMER = "com.aleks.hexapla.TIMER"

        const val EXTRA_BOOK = "book"
        const val EXTRA_CHAPTER = "chapter"
        const val EXTRA_VERSE = "verse"
        const val EXTRA_MINUTES = "minutes"

        fun play(context: Context, book: Int, chapter: Int, verse: Int = 0) {
            val i = Intent(context, ReadingService::class.java)
                .setAction(ACTION_PLAY)
                .putExtra(EXTRA_BOOK, book)
                .putExtra(EXTRA_CHAPTER, chapter)
                .putExtra(EXTRA_VERSE, verse)
            context.startForegroundService(i)
        }

        fun send(context: Context, action: String, minutes: Int = 0) {
            context.startService(
                Intent(context, ReadingService::class.java)
                    .setAction(action)
                    .putExtra(EXTRA_MINUTES, minutes)
            )
        }
    }
}
