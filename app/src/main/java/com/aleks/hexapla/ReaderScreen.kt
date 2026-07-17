package com.aleks.hexapla

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import android.view.WindowManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.gestures.animateScrollBy
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.interaction.collectIsDraggedAsState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.automirrored.filled.VolumeUp
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Timer
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.runtime.withFrameNanos
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.LinkAnnotation
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextLinkStyles
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.style.BaselineShift
import androidx.compose.ui.text.withLink
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.ui.MotionDurationScale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.core.content.ContextCompat
import java.text.Normalizer
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.isActive
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun ReaderScreen(settings: AppSettings) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }
    val clipboard = LocalClipboardManager.current

    var primaryBooks by remember { mutableStateOf<List<Book>?>(null) }
    var secondaryBooks by remember { mutableStateOf<List<Book>?>(null) }

    LaunchedEffect(settings.primaryId) { primaryBooks = BibleRepo.load(context, settings.primaryId) }
    LaunchedEffect(settings.secondaryId, settings.splitEnabled) {
        if (settings.splitEnabled) secondaryBooks = BibleRepo.load(context, settings.secondaryId)
    }
    LaunchedEffect(Unit) {
        if (!AppState.initialized.value) {
            AppState.book.intValue = settings.lastBook
            AppState.chapter.intValue = settings.lastChapter
            if (settings.lastVerse > 0) AppState.scrollToVerse.intValue = settings.lastVerse
            AppState.initialized.value = true
        }
    }

    // Keep-screen-on applies while the reader is visible.
    val activity = context as? Activity
    DisposableEffect(settings.keepScreenOn) {
        if (settings.keepScreenOn)
            activity?.window?.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        onDispose {
            activity?.window?.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
    }

    val allBooks = primaryBooks
    if (allBooks == null) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        return
    }
    // Apocrypha (slots 66+) is opt-in: hidden unless enabled in Settings.
    val books = if (settings.showApocrypha) allBooks else allBooks.take(66)

    var book = AppState.book.intValue.coerceIn(0, books.size - 1)
    if (books[book].chapters.isEmpty()) {
        book = books.indexOfFirst { it.chapters.isNotEmpty() }.coerceAtLeast(0)
    }
    if (AppState.book.intValue != book) {
        // The canon shrank under us (apocrypha toggled off, or a switch to a
        // 66-book translation while reading slot 66+): clamp the shared state
        // too, or navigateChapter will index past the end of the book list.
        AppState.book.intValue = book
        AppState.chapter.intValue = 0
    }
    val chapter = AppState.chapter.intValue
        .coerceIn(0, (books[book].chapters.size - 1).coerceAtLeast(0))
    val verses = books[book].chapters[chapter]
    // Verse-level versification pivot (KJV backbone); identity until loaded.
    var mapsReady by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { VerseMap.load(context); mapsReady = true }
    // Secondary pane rows aligned to the primary through the KJV pivot:
    // (text, secondary's own 1-based chapter/verse for interlinear taps).
    val sBooks = secondaryBooks
    val secondaryAligned: List<Pair<String, Pair<Int, Int>>>? =
        if (settings.splitEnabled && sBooks != null)
            remember(book, chapter, verses, sBooks, settings.primaryId,
                     settings.secondaryId, mapsReady) {
                val chs = sBooks.getOrNull(book)?.chapters
                List(verses.size) { i ->
                    val (kc, kv) = VerseMap.toKjv(settings.primaryId, book, chapter + 1, i + 1)
                    val segs = VerseMap.fromKjv(settings.secondaryId, book, kc, kv)
                    val text = segs.mapNotNull { (c2, v2) ->
                        chs?.getOrNull(c2 - 1)?.getOrNull(v2 - 1)
                    }.filter { it.isNotBlank() }.joinToString(" ")
                    text to (segs.firstOrNull() ?: (chapter + 1 to i + 1))
                }
            }
        else null

    LaunchedEffect(book, chapter) { Store.setLastPosition(context, book, chapter) }

    val bookmarks by Store.bookmarks(context).collectAsState(initial = emptyList())
    // Bookmarks store their SOURCE translation's own (chapter, verse); pivot each
    // through the KJV backbone into the current primary so the highlight lands on
    // the right verse after a translation switch. Same-translation bookmarks skip
    // the round-trip (byte-identical to the pre-pivot behavior).
    val bookmarkedVerses = remember(bookmarks, book, chapter, settings.primaryId, mapsReady) {
        bookmarks.asSequence()
            .filter { it.book == book }
            .mapNotNull { bm ->
                if (bm.translationId == settings.primaryId) {
                    if (bm.chapter == chapter) bm.verse else null
                } else {
                    val (kc, kv) = VerseMap.toKjv(
                        bm.translationId, bm.book, bm.chapter + 1, bm.verse + 1
                    )
                    VerseMap.fromKjv(settings.primaryId, bm.book, kc, kv)
                        .firstOrNull()?.takeIf { it.first == chapter + 1 }
                        ?.let { it.second - 1 }
                }
            }.toSet()
    }
    val notes by Store.notes(context).collectAsState(initial = emptyMap())
    val voicePrefs by Store.voicePrefs(context).collectAsState(initial = emptyMap())
    val highlights by Store.highlights(context).collectAsState(initial = emptyMap())
    // SnapshotStateMap gives per-item observability; taps update it optimistically
    // so the color appears instantly, and the DataStore flow keeps it in sync.
    val liveHighlights = remember { androidx.compose.runtime.mutableStateMapOf<String, Int>() }
    LaunchedEffect(highlights) {
        liveHighlights.clear()
        liveHighlights.putAll(highlights)
    }

    // The media notification needs POST_NOTIFICATIONS on Android 13+; request
    // it the first time the user starts playback.
    val notifPermLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { }
    fun ensureNotificationPermission() {
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) notifPermLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
    }

    // Red letters: verse-level index of the words of Christ.
    var redLetters by remember { mutableStateOf<Map<Int, List<Set<Int>>>?>(null) }
    LaunchedEffect(settings.redLetters) {
        redLetters = if (settings.redLetters) RedLetters.load(context) else null
    }

    // Strong's overlay: tagged KJV text used for display only.
    var strongsBooks by remember { mutableStateOf<List<Book>?>(null) }
    LaunchedEffect(settings.showStrongs, settings.primaryId) {
        strongsBooks = if (settings.showStrongs && settings.primaryId == "kjv")
            StrongsRepo.books(context) else null
    }
    var strongsId by remember { mutableStateOf<String?>(null) }
    var dictWord by remember { mutableStateOf<String?>(null) }
    val dictPrimary = settings.showDictionary &&
        BibleRepo.translation(settings.primaryId).locale.language == "en"
    val dictSecondary = settings.showDictionary &&
        BibleRepo.translation(settings.secondaryId).locale.language == "en"
    // Interlinear: always live on the original-language texts.
    val interPrimary = Interlinear.isOriginal(settings.primaryId)
    val interSecondary = Interlinear.isOriginal(settings.secondaryId)
    var interTap by remember { mutableStateOf<Triple<Int, Int, String>?>(null) } // verse, wordIdx, word

    val listState = rememberLazyListState()

    // Remember the verse the reader is on, so reopening the app lands on it.
    // collectLatest + delay debounces the DataStore write until scrolling pauses.
    LaunchedEffect(book, chapter) {
        snapshotFlow { listState.firstVisibleItemIndex }
            .collectLatest { verse ->
                kotlinx.coroutines.delay(500)
                Store.setLastVerse(context, verse)
            }
    }

    // One collector owns all position scrolling: verse jumps (search, topics,
    // xrefs, deep links) win over the scroll-to-top on chapter change, and the
    // playback follow-scroll lives in the same collector so it can never race
    // them. Split effects raced — the jump landed first, then the chapter
    // effect saw no pending target and reset to the top.
    // Jumps and chapter resets stay instant (animating across a book is
    // janky); only the verse-to-verse playback follow animates. collectLatest
    // makes a new verse event cancel a stale animation instead of queuing.
    val versesNow by rememberUpdatedState(verses)
    val userDragging by listState.interactionSource.collectIsDraggedAsState()
    var lastPosition by remember { mutableStateOf(-1 to -1) }
    var lastSpoken by remember { mutableStateOf(-1) }
    LaunchedEffect(Unit) {
        snapshotFlow {
            // Playback.verse is only read here while the service is reading
            // the chapter on screen, so it only re-emits when following.
            val here = Playback.active.value &&
                Playback.book.intValue == AppState.book.intValue &&
                Playback.chapter.intValue == AppState.chapter.intValue
            listOf(
                AppState.book.intValue, AppState.chapter.intValue,
                AppState.scrollToVerse.intValue,
                if (here) Playback.verse.intValue else -1
            )
        }.collectLatest { (b, c, target, spoken) ->
            val movedChapter = (b to c) != lastPosition
            when {
                target >= 0 -> {
                    // Explicit jump: instant. Let the new chapter's list
                    // compose before scrolling into it.
                    withFrameNanos { }
                    withFrameNanos { }
                    listState.scrollToItem(target.coerceAtLeast(0))
                    AppState.scrollToVerse.intValue = -1
                }
                // Chapter reset: instant; land straight on the spoken verse
                // when playback is already mid-chapter (re-entering the
                // reader, or the service advancing to the next chapter).
                movedChapter -> {
                    listState.scrollToItem(
                        if (spoken in versesNow.indices) spoken else 0
                    )
                }
                spoken >= 0 && spoken != lastSpoken &&
                    spoken in versesNow.indices && !userDragging -> {
                    try {
                        // Follow-scroll is a functional reading aid, not a
                        // decorative transition: run it at 1x even when the
                        // system reports animator duration scale 0 (Developer
                        // options "Animator duration scale: off", accessibility
                        // "Remove animations", some battery savers). Compose's
                        // suspend animations honor MotionDurationScale from the
                        // effect context.
                        withContext(FollowScrollMotion) {
                            // animateScrollToItem is NOT a glide: its internal
                            // animation is the default spring() — critically
                            // damped, StiffnessMedium (1500) — whose settle time
                            // is distance-INDEPENDENT: half the travel lands in
                            // the first ~40ms, ~90% by 100ms, done ~150ms
                            // (verified in foundation 1.7.4 sources,
                            // LazyAnimateScroll.kt + SuspendAnimation.kt). Over
                            // a one-verse hop that reads as a snap at any
                            // animator scale. So for the normal follow case —
                            // target verse already composed on screen — glide
                            // the exact pixel distance with a real tween;
                            // item.offset is precisely what animateScrollToItem
                            // would land (its calculateDistanceTo returns the
                            // visible item's offset). Off-screen targets (user
                            // flung away) keep the fast catch-up spring.
                            val item = listState.layoutInfo.visibleItemsInfo
                                .firstOrNull { it.index == spoken }
                            if (item != null) {
                                // Duration scales with distance (~1ms/px, 500-1200ms)
                                // so short hops stay quick and long ones stay gentle;
                                // LinearOutSlowIn avoids FastOutSlowIn's front-loaded
                                // lurch landing in the busy verse-boundary frames
                                // (highlight repaint + new utterance start).
                                if (item.offset != 0) listState.animateScrollBy(
                                    item.offset.toFloat(),
                                    tween(
                                        durationMillis = kotlin.math.abs(item.offset)
                                            .coerceIn(500, 1200),
                                        easing = LinearOutSlowInEasing
                                    )
                                )
                            } else {
                                listState.animateScrollToItem(spoken)
                            }
                        }
                    } catch (e: CancellationException) {
                        // Rethrow if WE were cancelled (a newer verse event);
                        // swallow if the user's drag stole the scroll mutex —
                        // never fight a finger, resume on the next verse.
                        currentCoroutineContext().ensureActive()
                    }
                }
            }
            // Update AFTER the scroll: if collectLatest cancels us mid-scroll,
            // the next emission re-evaluates and retries instead of losing it.
            lastPosition = b to c
            lastSpoken = spoken
        }
    }
    // Follow the voice into a new chapter: when the service advances past the
    // one on screen, repoint the reader (the collector above then scrolls).
    val playbackHere = Playback.active.value &&
        Playback.book.intValue == book && Playback.chapter.intValue == chapter
    LaunchedEffect(Playback.book.intValue, Playback.chapter.intValue) {
        if (Playback.active.value && Playback.book.intValue >= 0 && !playbackHere) {
            AppState.open(Playback.book.intValue, Playback.chapter.intValue)
        }
    }

    var showPicker by remember { mutableStateOf(false) }
    var showSearch by remember { mutableStateOf(false) }
    var actionVerse by remember { mutableStateOf<Int?>(null) }
    var xrefVerse by remember { mutableStateOf<Int?>(null) }
    var compareVerse by remember { mutableStateOf<Int?>(null) }
    var originalVerse by remember { mutableStateOf<Int?>(null) }
    var notesVerse by remember { mutableStateOf<Int?>(null) }
    var dragTotal by remember { mutableFloatStateOf(0f) }

    val fontFamily = if (settings.serifFont) FontFamily.Serif else FontFamily.SansSerif
    val ttsError = stringResource(R.string.tts_unavailable)
    val copiedMsg = stringResource(R.string.copied)

    Scaffold(snackbarHost = { SnackbarHost(snackbar) }) { pad ->
        Column(Modifier.fillMaxSize().padding(pad)) {

            Row(
                Modifier.fillMaxWidth().padding(horizontal = 4.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(
                    onClick = { navigateChapter(books, -1) },
                    enabled = !(book == 0 && chapter == 0)
                ) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.prev_chapter))
                }
                TextButton(onClick = { showPicker = true }, modifier = Modifier.weight(1f)) {
                    // Shrink instead of ellipsizing: "Cantique des cantiques 8"
                    // must keep its chapter number visible.
                    val title = "${books[book].name} ${chapter + 1}"
                    var titleScale by remember(title) { mutableFloatStateOf(1f) }
                    Text(
                        title,
                        style = MaterialTheme.typography.titleMedium,
                        fontSize = MaterialTheme.typography.titleMedium.fontSize * titleScale,
                        textAlign = TextAlign.Center,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        onTextLayout = {
                            if (it.hasVisualOverflow && titleScale > 0.65f) titleScale *= 0.92f
                        },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
                IconButton(onClick = { showSearch = true }) {
                    Icon(Icons.Filled.Search, stringResource(R.string.search))
                }
                IconButton(onClick = {
                    if (Playback.active.value) ReadingService.send(context, ReadingService.ACTION_STOP)
                    else {
                        ensureNotificationPermission()
                        ReadingService.play(
                            context, book, chapter,
                            // Resume from the saved verse when starting where we left off.
                            if (book == settings.lastBook && chapter == settings.lastChapter)
                                settings.lastVerse else 0
                        )
                    }
                }) {
                    if (Playback.active.value)
                        Icon(Icons.Filled.Stop, stringResource(R.string.stop_audio))
                    else
                        Icon(Icons.AutoMirrored.Filled.VolumeUp, stringResource(R.string.play_audio))
                }
                IconButton(
                    onClick = { navigateChapter(books, +1) },
                    enabled = !(book == books.size - 1 && chapter == books[book].chapters.size - 1)
                ) {
                    Icon(Icons.AutoMirrored.Filled.ArrowForward, stringResource(R.string.next_chapter))
                }
            }
            HorizontalDivider()

            if (Playback.active.value) PlaybackBar(context)

            LazyColumn(
                state = listState,
                modifier = Modifier
                    .weight(1f)
                    .pointerInput(book, chapter) {
                        detectHorizontalDragGestures(
                            onDragStart = { dragTotal = 0f },
                            onHorizontalDrag = { _, amount -> dragTotal += amount },
                            onDragEnd = {
                                if (dragTotal < -160f) navigateChapter(books, +1)
                                else if (dragTotal > 160f) navigateChapter(books, -1)
                            }
                        )
                    }
            ) {
                itemsIndexed(verses) { i, verse ->
                    val highlighted = playbackHere && Playback.verse.intValue == i
                    // Red letters, notes and highlights are all keyed by the
                    // canonical KJV reference; pivot the primary's own
                    // (chapter, verse) once. Reading mapsReady re-runs this
                    // item when versemap.json finishes loading.
                    val (kc, kv) = if (mapsReady)
                        VerseMap.toKjv(settings.primaryId, book, chapter + 1, i + 1)
                    else chapter + 1 to i + 1
                    val canonKey = "$book:${kc - 1}:${kv - 1}"
                    val red = redLetters?.get(book)?.let { chs ->
                        chs.getOrNull(kc - 1)?.contains(kv - 1)
                    } == true
                    val tagged = strongsBooks?.getOrNull(book)?.chapters
                        ?.getOrNull(chapter)?.getOrNull(i)
                    // Word ranges refer to the plain text; skip them when the
                    // Strong's-tagged text is displayed instead.
                    val spoken = if (tagged == null && highlighted && Playback.wordStart.intValue >= 0)
                        Playback.wordStart.intValue..Playback.wordEnd.intValue else null
                    val bookmarked = bookmarkedVerses.contains(i)
                    val noteText = notes[canonKey]
                    val userColor = liveHighlights[canonKey]
                    val bg = when {
                        highlighted -> MaterialTheme.colorScheme.primaryContainer
                        userColor != null -> HighlightColors[userColor % HighlightColors.size]
                        bookmarked -> MaterialTheme.colorScheme.secondaryContainer
                        else -> MaterialTheme.colorScheme.background
                    }
                    Column(
                        Modifier
                            .fillMaxWidth()
                            .background(bg)
                            .combinedClickable(
                                onClick = {},
                                onLongClick = { actionVerse = i }
                            )
                            .padding(horizontal = 16.dp, vertical = 6.dp)
                    ) {
                        if (settings.splitEnabled && secondaryAligned != null) {
                            val (second, secondPos) = secondaryAligned.getOrNull(i)
                                ?: ("" to (chapter + 1 to i + 1))
                            // Interlinear taps need the secondary's OWN verse
                            // index; disabled on the rare cross-chapter rows.
                            val secondTap = if (interSecondary && secondPos.first == chapter + 1)
                                ({ w: Int, t: String -> interTap = Triple(secondPos.second - 1, w, t) })
                            else null
                            if (settings.splitHorizontal) {
                                Row(Modifier.fillMaxWidth()) {
                                    VerseText(i + 1, verse, settings.fontSize, fontFamily, Modifier.weight(1f), spokenRange = spoken, taggedText = tagged, onStrongs = { strongsId = it }, onWord = if (dictPrimary) ({ dictWord = it }) else null, onWordIndexed = if (interPrimary) ({ w, t -> interTap = Triple(i, w, t) }) else null, red = red, showNumber = !settings.hideVerseNumbers, onLongPress = { actionVerse = i })
                                    Spacer(Modifier.width(12.dp))
                                    VerseText(i + 1, second, settings.fontSize, fontFamily, Modifier.weight(1f), onWord = if (dictSecondary) ({ dictWord = it }) else null, onWordIndexed = secondTap, red = red, showNumber = !settings.hideVerseNumbers, onLongPress = { actionVerse = i })
                                }
                            } else {
                                VerseText(i + 1, verse, settings.fontSize, fontFamily, Modifier.fillMaxWidth(), spokenRange = spoken, taggedText = tagged, onStrongs = { strongsId = it }, onWord = if (dictPrimary) ({ dictWord = it }) else null, onWordIndexed = if (interPrimary) ({ w, t -> interTap = Triple(i, w, t) }) else null, red = red, showNumber = !settings.hideVerseNumbers, onLongPress = { actionVerse = i })
                                Spacer(Modifier.height(4.dp))
                                VerseText(
                                    i + 1, second, settings.fontSize, fontFamily,
                                    Modifier.fillMaxWidth(), secondary = true,
                                    onWord = if (dictSecondary) ({ dictWord = it }) else null,
                                    onWordIndexed = secondTap,
                                    red = red, showNumber = !settings.hideVerseNumbers,
                                    onLongPress = { actionVerse = i }
                                )
                            }
                        } else {
                            VerseText(i + 1, verse, settings.fontSize, fontFamily, Modifier.fillMaxWidth(), spokenRange = spoken, taggedText = tagged, onStrongs = { strongsId = it }, onWord = if (dictPrimary) ({ dictWord = it }) else null, onWordIndexed = if (interPrimary) ({ w, t -> interTap = Triple(i, w, t) }) else null, red = red, showNumber = !settings.hideVerseNumbers, onLongPress = { actionVerse = i })
                        }
                        if (noteText != null) {
                            Row(Modifier.padding(top = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    Icons.Filled.Edit, contentDescription = null,
                                    tint = MaterialTheme.colorScheme.secondary,
                                    modifier = Modifier.width(14.dp)
                                )
                                Spacer(Modifier.width(6.dp))
                                Text(
                                    noteText,
                                    fontSize = (settings.fontSize * 0.8f).sp,
                                    fontStyle = FontStyle.Italic,
                                    color = MaterialTheme.colorScheme.secondary
                                )
                            }
                        }
                    }
                    if (settings.splitEnabled) HorizontalDivider(
                        color = MaterialTheme.colorScheme.surfaceVariant
                    )
                }
                item { Spacer(Modifier.height(32.dp)) }
            }
        }
    }

    if (showPicker) {
        BookChapterPicker(
            books = books,
            currentBook = book,
            currentChapter = chapter,
            splitEnabled = settings.splitEnabled,
            primaryId = settings.primaryId,
            secondaryId = settings.secondaryId,
            onDismiss = { showPicker = false },
            onSelect = { b, c -> AppState.open(b, c); showPicker = false }
        )
    }

    if (showSearch) {
        SearchDialog(
            books = books,
            onDismiss = { showSearch = false },
            onSelect = { b, c, v -> AppState.open(b, c, v); showSearch = false }
        )
    }

    actionVerse?.let { v ->
        val verseText = verses.getOrNull(v) ?: ""
        val refLabel = "${books[book].name} ${chapter + 1}:${v + 1}"
        // "Original text" needs a non-empty grc/wlc counterpart (mapped through
        // the KJV pivot). Resolved async: BibleRepo caches, so after the first
        // long-press this is instant; the entry appears once known available.
        val origId = if (book < 39) "wlc" else "grc"
        var originalAvailable by remember(book, chapter, v) { mutableStateOf(false) }
        LaunchedEffect(book, chapter, v) {
            if (settings.primaryId == origId) return@LaunchedEffect
            VerseMap.load(context)
            val (kc, kv) = VerseMap.toKjv(settings.primaryId, book, chapter + 1, v + 1)
            originalAvailable =
                VerseMap.textAt(origId, BibleRepo.load(context, origId), book, kc, kv).isNotBlank()
        }
        // Translator margin notes stripped from the displayed text, if any.
        val verseNotes = BibleRepo.notes(settings.primaryId)["$book:$chapter:$v"]
        // Personal notes/highlights key by the canonical KJV reference (same
        // pivot as the reader list above), so they survive translation switches.
        val (akc, akv) = if (mapsReady)
            VerseMap.toKjv(settings.primaryId, book, chapter + 1, v + 1)
        else chapter + 1 to v + 1
        val canonKey = "$book:${akc - 1}:${akv - 1}"
        VerseActionsDialog(
            refLabel = refLabel,
            bookmarked = bookmarkedVerses.contains(v),
            existingNote = notes[canonKey] ?: "",
            onBookmark = {
                scope.launch {
                    Store.toggleBookmark(context, Bookmark(settings.primaryId, book, chapter, v))
                }
                actionVerse = null
            },
            onCopy = {
                clipboard.setText(AnnotatedString("$verseText — $refLabel"))
                scope.launch { snackbar.showSnackbar(copiedMsg) }
                actionVerse = null
            },
            onShare = {
                val send = Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_TEXT, "$verseText — $refLabel")
                }
                context.startActivity(Intent.createChooser(send, refLabel))
                actionVerse = null
            },
            onSaveNote = { text ->
                scope.launch { Store.setNote(context, book, akc - 1, akv - 1, text) }
                actionVerse = null
            },
            onXrefs = {
                xrefVerse = v
                actionVerse = null
            },
            onCompare = {
                compareVerse = v
                actionVerse = null
            },
            onShowOriginal = if (originalAvailable) ({
                originalVerse = v
                actionVerse = null
            }) else null,
            onNotes = if (!verseNotes.isNullOrEmpty()) ({
                notesVerse = v
                actionVerse = null
            }) else null,
            onListen = {
                ensureNotificationPermission()
                ReadingService.play(context, book, chapter, v)
                actionVerse = null
            },
            onShareImage = {
                ShareImage.share(context, verseText, refLabel)
                actionVerse = null
            },
            currentHighlight = liveHighlights[canonKey],
            onHighlight = { color ->
                if (color == null) liveHighlights.remove(canonKey)
                else liveHighlights[canonKey] = color
                scope.launch { Store.setHighlight(context, book, akc - 1, akv - 1, color) }
                actionVerse = null
            },
            onDismiss = { actionVerse = null }
        )
    }

    strongsId?.let { id ->
        var entry by remember(id) { mutableStateOf<StrongsRepo.Entry?>(null) }
        LaunchedEffect(id) { entry = StrongsRepo.entry(context, id) }
        AlertDialog(
            onDismissRequest = { strongsId = null },
            title = { Text(entry?.let { "$id · ${it.word}" } ?: id) },
            text = {
                val e = entry
                if (e == null) {
                    Box(Modifier.fillMaxWidth().padding(16.dp), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator()
                    }
                } else {
                    Column {
                        Text(
                            listOf(e.translit, e.pos).filter { it.isNotBlank() }.joinToString(" · "),
                            style = MaterialTheme.typography.labelLarge,
                            color = MaterialTheme.colorScheme.primary
                        )
                        Spacer(Modifier.height(8.dp))
                        Text(e.def, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { strongsId = null }) { Text(stringResource(R.string.cancel)) }
            }
        )
    }

    dictWord?.let { word ->
        var result by remember(word) { mutableStateOf<Pair<String, String>?>(null) }
        var loaded by remember(word) { mutableStateOf(false) }
        LaunchedEffect(word) {
            result = Webster1828.lookup(context, word)
            loaded = true
        }
        AlertDialog(
            onDismissRequest = { dictWord = null },
            title = { Text(result?.first ?: word) },
            text = {
                when {
                    !loaded -> Box(Modifier.fillMaxWidth().padding(16.dp), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator()
                    }
                    result == null -> Text(stringResource(R.string.dict_not_found))
                    else -> Column(Modifier.verticalScroll(rememberScrollState())) {
                        Text(
                            stringResource(R.string.dict_source),
                            style = MaterialTheme.typography.labelLarge,
                            color = MaterialTheme.colorScheme.primary
                        )
                        Spacer(Modifier.height(8.dp))
                        Text(result!!.second, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { dictWord = null }) { Text(stringResource(R.string.cancel)) }
            }
        )
    }

    interTap?.let { (v, w, word) ->
        InterlinearWordDialog(
            book = book, chapter = chapter, verse = v, wordIndex = w, word = word,
            onDismiss = { interTap = null }
        )
    }

    compareVerse?.let { v ->
        CompareDialog(
            primaryId = settings.primaryId,
            book = book,
            chapter = chapter,
            verse = v,
            refLabel = "${books[book].name} ${chapter + 1}:${v + 1}",
            enabledIds = settings.compareIds,
            onDismiss = { compareVerse = null }
        )
    }

    originalVerse?.let { v ->
        OriginalDialog(
            primaryId = settings.primaryId,
            book = book,
            chapter = chapter,
            verse = v,
            fontSize = settings.fontSize,
            fontFamily = fontFamily,
            onDismiss = { originalVerse = null }
        )
    }

    notesVerse?.let { v ->
        val noteList = BibleRepo.notes(settings.primaryId)["$book:$chapter:$v"] ?: emptyList()
        AlertDialog(
            onDismissRequest = { notesVerse = null },
            title = { Text("${books[book].name} ${chapter + 1}:${v + 1}") },
            text = {
                Column(Modifier.verticalScroll(rememberScrollState())) {
                    Text(
                        stringResource(R.string.verse_notes),
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.primary
                    )
                    Spacer(Modifier.height(8.dp))
                    noteList.forEach { n ->
                        Text(
                            n,
                            style = MaterialTheme.typography.bodyMedium,
                            modifier = Modifier.padding(vertical = 3.dp)
                        )
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { notesVerse = null }) { Text(stringResource(R.string.cancel)) }
            }
        )
    }

    xrefVerse?.let { v ->
        XrefsDialog(
            primaryId = settings.primaryId,
            books = allBooks,
            book = book,
            chapter = chapter,
            verse = v,
            refLabel = "${books[book].name} ${chapter + 1}:${v + 1}",
            onDismiss = { xrefVerse = null },
            onSelect = { b, c, tv ->
                xrefVerse = null
                AppState.open(b, c, tv)
            }
        )
    }
}

private fun navigateChapter(books: List<Book>, delta: Int) {
    var b = AppState.book.intValue.coerceIn(0, books.size - 1)
    var c = AppState.chapter.intValue
        .coerceIn(0, (books[b].chapters.size - 1).coerceAtLeast(0)) + delta
    if (c < 0) {
        var nb = b - 1
        while (nb >= 0 && books[nb].chapters.isEmpty()) nb--
        if (nb >= 0) { b = nb; c = books[b].chapters.size - 1 } else c = 0
    } else if (c >= books[b].chapters.size) {
        var nb = b + 1
        while (nb < books.size && books[nb].chapters.isEmpty()) nb++
        if (nb < books.size) { b = nb; c = 0 } else c = books[b].chapters.size - 1
    }
    AppState.open(b, c)
}

/** Slim controls shown while audio reading is active: pause/resume + sleep timer. */
@Composable
private fun PlaybackBar(context: android.content.Context) {
    var showTimer by remember { mutableStateOf(false) }
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        IconButton(onClick = {
            ReadingService.send(
                context,
                if (Playback.playing.value) ReadingService.ACTION_PAUSE
                else ReadingService.ACTION_RESUME
            )
        }) {
            if (Playback.playing.value)
                Icon(Icons.Filled.Pause, stringResource(R.string.pause_audio))
            else
                Icon(Icons.Filled.PlayArrow, stringResource(R.string.play_audio))
        }
        IconButton(onClick = { showTimer = true }) {
            Icon(Icons.Filled.Timer, stringResource(R.string.sleep_timer))
        }
        val sleep = Playback.sleepMinutes.intValue
        if (sleep != 0) {
            Text(
                if (sleep == -1) stringResource(R.string.sleep_end_of_chapter)
                else stringResource(R.string.sleep_minutes, sleep),
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
    HorizontalDivider()

    if (showTimer) {
        AlertDialog(
            onDismissRequest = { showTimer = false },
            title = { Text(stringResource(R.string.sleep_timer)) },
            text = {
                Column {
                    listOf(
                        0 to stringResource(R.string.sleep_off),
                        -1 to stringResource(R.string.sleep_end_of_chapter),
                        15 to stringResource(R.string.sleep_minutes, 15),
                        30 to stringResource(R.string.sleep_minutes, 30),
                        60 to stringResource(R.string.sleep_minutes, 60)
                    ).forEach { (minutes, label) ->
                        TextButton(
                            onClick = {
                                ReadingService.send(context, ReadingService.ACTION_TIMER, minutes)
                                showTimer = false
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                (if (Playback.sleepMinutes.intValue == minutes) "✓  " else "") + label
                            )
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showTimer = false }) { Text(stringResource(R.string.cancel)) }
            }
        )
    }
}

/** Forces 1x motion for the playback follow-scroll (see the collector above). */
private val FollowScrollMotion = object : MotionDurationScale {
    override val scaleFactor: Float get() = 1f
}

private val wordRegex = Regex("""[A-Za-z]+(?:['’-][A-Za-z]+)*""")

/** Append [text] wrapping each interlinear token in an invisible link that
 *  reports its word index — tokenization matches tools/build_interlinear.py. */
private fun androidx.compose.ui.text.AnnotatedString.Builder.appendWordsIndexed(
    text: String,
    onWordIndexed: (Int, String) -> Unit
) {
    var pos = 0
    var index = 0
    for (m in Interlinear.token.findAll(text)) {
        append(text.substring(pos, m.range.first))
        val word = m.value
        if (word.any { it.isLetter() }) {
            val i = index++
            withLink(
                LinkAnnotation.Clickable("iw", TextLinkStyles()) { onWordIndexed(i, word) }
            ) { append(word) }
        } else append(word)
        pos = m.range.last + 1
    }
    append(text.substring(pos))
}

/** Append [text], wrapping each word in an invisible link when [onWord] is set. */
private fun androidx.compose.ui.text.AnnotatedString.Builder.appendWords(
    text: String,
    onWord: ((String) -> Unit)?
) {
    if (onWord == null) { append(text); return }
    var pos = 0
    for (m in wordRegex.findAll(text)) {
        append(text.substring(pos, m.range.first))
        val word = m.value
        withLink(
            LinkAnnotation.Clickable("w", TextLinkStyles()) { onWord(word) }
        ) { append(word) }
        pos = m.range.last + 1
    }
    append(text.substring(pos))
}

@Composable
private fun VerseText(
    number: Int,
    text: String,
    fontSize: Float,
    fontFamily: FontFamily,
    modifier: Modifier = Modifier,
    secondary: Boolean = false,
    spokenRange: IntRange? = null,
    taggedText: String? = null,
    onStrongs: ((String) -> Unit)? = null,
    onWord: ((String) -> Unit)? = null,
    onWordIndexed: ((Int, String) -> Unit)? = null,
    red: Boolean = false,
    showNumber: Boolean = true,
    onLongPress: (() -> Unit)? = null
) {
    val annotated = when {
        taggedText != null -> {
            val accent = MaterialTheme.colorScheme.primary
            buildAnnotatedString {
                var pos = 0
                for (m in StrongsRepo.tag.findAll(taggedText)) {
                    appendWords(taggedText.substring(pos, m.range.first), onWord)
                    val id = m.groupValues[1]
                    withLink(
                        LinkAnnotation.Clickable(
                            id,
                            TextLinkStyles(
                                SpanStyle(
                                    color = accent,
                                    fontSize = (fontSize * 0.55f).sp,
                                    baselineShift = BaselineShift.Superscript
                                )
                            )
                        ) { onStrongs?.invoke(id) }
                    ) { append(id.drop(1)) }
                    pos = m.range.last + 1
                }
                appendWords(taggedText.substring(pos), onWord)
            }
        }
        // first <= last guards a recomposition race: wordStart/wordEnd are two
        // separate states, so a frame can pair the new word's start with the
        // old word's end — a reversed range crashes AnnotatedString.
        spokenRange != null && spokenRange.first >= 0 &&
            spokenRange.first <= spokenRange.last && spokenRange.last <= text.length -> {
            val mark = MaterialTheme.colorScheme.primary.copy(alpha = 0.35f)
            buildAnnotatedString {
                append(text)
                addStyle(SpanStyle(background = mark), spokenRange.first, spokenRange.last)
            }
        }
        onWordIndexed != null -> buildAnnotatedString { appendWordsIndexed(text, onWordIndexed) }
        onWord != null -> buildAnnotatedString { appendWords(text, onWord) }
        else -> AnnotatedString(text)
    }
    // Classic red-letter tone, adjusted for theme luminance.
    val redColor = if (MaterialTheme.colorScheme.background.luminance() < 0.5f)
        Color(0xFFEF9A9A) else Color(0xFFB71C1C)
    // Long-press must open the verse action sheet even when the press lands
    // on a word/Strong's LinkAnnotation: the link's own handler consumes the
    // press, so the parent Column's combinedClickable never fires. Watch the
    // raw stream on the Initial pass (delivered to this Row before the link's
    // Main-pass handling can consume anything); on a hold past the long-press
    // timeout, fire the callback and eat the rest of the gesture so the link
    // doesn't also open the dictionary on release. Short taps pass through
    // untouched, so word/Strong's links keep working exactly as before.
    val currentLongPress = rememberUpdatedState(onLongPress)
    val rowModifier = if (onLongPress != null) modifier.pointerInput(Unit) {
        awaitEachGesture {
            val down = awaitFirstDown(pass = PointerEventPass.Initial)
            val cancelled = withTimeoutOrNull(viewConfiguration.longPressTimeoutMillis) {
                var cancel = false
                while (!cancel) {
                    val event = awaitPointerEvent(PointerEventPass.Initial)
                    val change = event.changes.firstOrNull { it.id == down.id }
                    cancel = change == null || !change.pressed ||
                        event.changes.size > 1 ||
                        (change.position - down.position).getDistance() >
                            viewConfiguration.touchSlop
                }
            } != null
            if (!cancelled) {
                currentLongPress.value?.invoke()
                while (true) {
                    val event = awaitPointerEvent(PointerEventPass.Initial)
                    event.changes.forEach { it.consume() }
                    if (event.changes.none { it.pressed }) break
                }
            }
        }
    } else modifier
    Row(rowModifier) {
        if (showNumber) {
            Text(
                "$number",
                fontSize = (fontSize * 0.65f).sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier.padding(end = 6.dp, top = 2.dp)
            )
        }
        Text(
            annotated,
            fontSize = fontSize.sp,
            lineHeight = (fontSize * 1.45f).sp,
            fontFamily = fontFamily,
            color = when {
                red -> redColor
                secondary -> MaterialTheme.colorScheme.onSurfaceVariant
                else -> MaterialTheme.colorScheme.onBackground
            }
        )
    }
}

/** Semi-transparent marker colors that work over light and dark backgrounds. */
private val HighlightColors = listOf(
    Color(0x59FFD54F),  // amber
    Color(0x5981C784),  // green
    Color(0x5964B5F6),  // blue
    Color(0x59F06292)   // pink
)

@Composable
private fun VerseActionsDialog(
    refLabel: String,
    bookmarked: Boolean,
    existingNote: String,
    onBookmark: () -> Unit,
    onCopy: () -> Unit,
    onShare: () -> Unit,
    onSaveNote: (String) -> Unit,
    onXrefs: () -> Unit,
    onCompare: () -> Unit,
    onShowOriginal: (() -> Unit)?,
    onNotes: (() -> Unit)?,
    onListen: () -> Unit,
    onShareImage: () -> Unit,
    currentHighlight: Int?,
    onHighlight: (Int?) -> Unit,
    onDismiss: () -> Unit
) {
    var editingNote by remember { mutableStateOf(false) }
    var noteText by remember { mutableStateOf(existingNote) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(refLabel) },
        text = {
            if (editingNote) {
                OutlinedTextField(
                    value = noteText,
                    onValueChange = { noteText = it },
                    label = { Text(stringResource(R.string.note)) },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 3
                )
            } else {
                Column {
                    // Highlight colors: tap a dot to mark, tap the active dot to clear.
                    Row(
                        Modifier.fillMaxWidth().padding(vertical = 6.dp),
                        horizontalArrangement = Arrangement.spacedBy(14.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        HighlightColors.forEachIndexed { idx, c ->
                            val active = currentHighlight == idx
                            Box(
                                Modifier
                                    .size(32.dp)
                                    .background(c.copy(alpha = 1f), CircleShape)
                                    .border(
                                        width = if (active) 3.dp else 1.dp,
                                        color = if (active) MaterialTheme.colorScheme.primary
                                        else MaterialTheme.colorScheme.outline,
                                        shape = CircleShape
                                    )
                                    .clickable { onHighlight(if (active) null else idx) }
                            )
                        }
                    }
                    TextButton(onClick = onBookmark, modifier = Modifier.fillMaxWidth()) {
                        Text(stringResource(if (bookmarked) R.string.remove_bookmark else R.string.add_bookmark))
                    }
                    TextButton(onClick = onCopy, modifier = Modifier.fillMaxWidth()) {
                        Text(stringResource(R.string.copy))
                    }
                    TextButton(onClick = onShare, modifier = Modifier.fillMaxWidth()) {
                        Text(stringResource(R.string.share))
                    }
                    TextButton(onClick = { editingNote = true }, modifier = Modifier.fillMaxWidth()) {
                        Text(stringResource(R.string.note))
                    }
                    TextButton(onClick = onXrefs, modifier = Modifier.fillMaxWidth()) {
                        Text(stringResource(R.string.xrefs))
                    }
                    TextButton(onClick = onCompare, modifier = Modifier.fillMaxWidth()) {
                        Text(stringResource(R.string.compare))
                    }
                    if (onShowOriginal != null) {
                        TextButton(onClick = onShowOriginal, modifier = Modifier.fillMaxWidth()) {
                            Text(stringResource(R.string.verse_original))
                        }
                    }
                    if (onNotes != null) {
                        TextButton(onClick = onNotes, modifier = Modifier.fillMaxWidth()) {
                            Text(stringResource(R.string.verse_notes))
                        }
                    }
                    TextButton(onClick = onListen, modifier = Modifier.fillMaxWidth()) {
                        Text(stringResource(R.string.listen_from_here))
                    }
                    TextButton(onClick = onShareImage, modifier = Modifier.fillMaxWidth()) {
                        Text(stringResource(R.string.share_image))
                    }
                }
            }
        },
        confirmButton = {
            if (editingNote) {
                TextButton(onClick = { onSaveNote(noteText) }) {
                    Text(stringResource(R.string.save))
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) }
        }
    )
}

/** The tapped verse in every translation that has it — the app's namesake view. */
@Composable
private fun CompareDialog(
    primaryId: String,
    book: Int,
    chapter: Int,
    verse: Int,
    refLabel: String,
    enabledIds: Set<String>,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    var rows by remember { mutableStateOf<List<Pair<Translation, String>>?>(null) }
    LaunchedEffect(book, chapter, verse) {
        VerseMap.load(context)
        val (kc, kv) = VerseMap.toKjv(primaryId, book, chapter + 1, verse + 1)
        rows = BibleRepo.ordered()
            .filter { enabledIds.isEmpty() || it.id in enabledIds }
            .mapNotNull { t ->
                val text = VerseMap.textAt(t.id, BibleRepo.load(context, t.id), book, kc, kv)
                if (text.isBlank()) null else t to text
            }
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(refLabel) },
        text = {
            val loaded = rows
            if (loaded == null) {
                Box(Modifier.fillMaxWidth().padding(24.dp), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else {
                LazyColumn {
                    items(loaded) { (t, text) ->
                        Column(Modifier.padding(vertical = 6.dp)) {
                            Text(
                                t.label,
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.primary
                            )
                            Text(text, style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) }
        }
    )
}

/** Strong's + decoded morphology for one tapped original-language word.
 *  [chapter]/[verse] are 0-based positions in the grc/wlc asset's OWN
 *  numbering — the interlinear assets are keyed to exactly those. */
@Composable
private fun InterlinearWordDialog(
    book: Int,
    chapter: Int,
    verse: Int,
    wordIndex: Int,
    word: String,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    var tag by remember(chapter, verse, wordIndex) { mutableStateOf<Pair<String, String>?>(null) }
    var entry by remember(chapter, verse, wordIndex) { mutableStateOf<StrongsRepo.Entry?>(null) }
    var loaded by remember(chapter, verse, wordIndex) { mutableStateOf(false) }
    LaunchedEffect(chapter, verse, wordIndex) {
        tag = Interlinear.word(context, book, chapter, verse, wordIndex)
        tag?.let { entry = StrongsRepo.entry(context, it.first) }
        loaded = true
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(word) },
        text = {
            when {
                !loaded -> Box(Modifier.fillMaxWidth().padding(16.dp), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
                tag == null -> Text(stringResource(R.string.interlinear_none))
                else -> Column(Modifier.verticalScroll(rememberScrollState())) {
                    Text(
                        Interlinear.decode(context, book, tag!!.second),
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.primary
                    )
                    Spacer(Modifier.height(8.dp))
                    entry?.let { e ->
                        Text(
                            listOf(tag!!.first, e.word, e.translit)
                                .filter { it.isNotBlank() }.joinToString(" · "),
                            style = MaterialTheme.typography.titleSmall
                        )
                        Spacer(Modifier.height(6.dp))
                        Text(e.def, style = MaterialTheme.typography.bodyMedium)
                    } ?: Text(tag!!.first, style = MaterialTheme.typography.titleSmall)
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) }
        }
    )
}

/** A tapped word inside the "Original text" dialog: the original's own
 *  0-based chapter/verse plus the interlinear word index. */
private data class OrigWordTap(val chapter: Int, val verse: Int, val wordIndex: Int, val word: String)

/** The long-pressed verse in the original language (wlc for OT, grc for NT),
 *  resolved through the KJV pivot exactly like CompareDialog. Words tap into
 *  the same Strong's + morphology flow as the grc/wlc reader panes. */
@Composable
private fun OriginalDialog(
    primaryId: String,
    book: Int,
    chapter: Int,
    verse: Int,
    fontSize: Float,
    fontFamily: FontFamily,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    val origId = if (book < 39) "wlc" else "grc"
    val trans = BibleRepo.translation(origId)
    var bookName by remember { mutableStateOf("") }
    // Mapped segments in the original's OWN 1-based numbering (usually one;
    // several when the KJV verse spans merged verses there). The interlinear
    // assets are keyed to these same positions, so each segment's word taps
    // carry its own chapter/verse.
    var segs by remember { mutableStateOf<List<Triple<Int, Int, String>>?>(null) }
    LaunchedEffect(book, chapter, verse) {
        VerseMap.load(context)
        val obooks = BibleRepo.load(context, origId)
        bookName = obooks.getOrNull(book)?.name ?: ""
        val (kc, kv) = VerseMap.toKjv(primaryId, book, chapter + 1, verse + 1)
        segs = VerseMap.fromKjv(origId, book, kc, kv).mapNotNull { (c, ov) ->
            obooks.getOrNull(book)?.chapters?.getOrNull(c - 1)?.getOrNull(ov - 1)
                ?.takeIf { it.isNotBlank() }?.let { Triple(c, ov, it) }
        }
    }
    var tap by remember { mutableStateOf<OrigWordTap?>(null) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Column {
                Text(
                    trans.label,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary
                )
                val s = segs
                if (!s.isNullOrEmpty()) {
                    val ref = when {
                        s.size == 1 -> "${s[0].first}:${s[0].second}"
                        s.all { it.first == s[0].first } ->
                            "${s[0].first}:${s.first().second}–${s.last().second}"
                        else -> s.joinToString("; ") { "${it.first}:${it.second}" }
                    }
                    Text("$bookName $ref")
                }
            }
        },
        text = {
            val loaded = segs
            if (loaded == null) {
                Box(Modifier.fillMaxWidth().padding(24.dp), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else {
                SelectionContainer {
                    Column(Modifier.verticalScroll(rememberScrollState())) {
                        loaded.forEach { (c, ov, text) ->
                            VerseText(
                                ov, text, fontSize, fontFamily, Modifier.fillMaxWidth(),
                                onWordIndexed = { w, t -> tap = OrigWordTap(c - 1, ov - 1, w, t) },
                                showNumber = loaded.size > 1
                            )
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) }
        }
    )
    tap?.let { t ->
        InterlinearWordDialog(
            book = book, chapter = t.chapter, verse = t.verse,
            wordIndex = t.wordIndex, word = t.word,
            onDismiss = { tap = null }
        )
    }
}

private data class SearchHit(
    val book: Int,
    val chapter: Int,
    val verse: Int,
    val text: String,
    val translationLabel: String? = null
)

/** Case- and diacritic-insensitive form: strips accents, Hebrew niqqud, Greek breathing marks. */
private fun searchNorm(s: String): String =
    Normalizer.normalize(s, Normalizer.Form.NFD)
        .replace(Regex("\\p{Mn}+"), "")
        .lowercase()

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun SearchDialog(
    books: List<Book>,
    onDismiss: () -> Unit,
    onSelect: (book: Int, chapter: Int, verse: Int) -> Unit
) {
    val context = LocalContext.current
    var query by remember { mutableStateOf("") }
    var allTranslations by remember { mutableStateOf(false) }
    var results by remember { mutableStateOf<List<SearchHit>>(emptyList()) }
    var searched by remember { mutableStateOf(false) }

    LaunchedEffect(query, allTranslations) {
        if (query.trim().length < 2) {
            results = emptyList(); searched = false
            return@LaunchedEffect
        }
        val q = searchNorm(query.trim())
        val sources: List<Pair<String?, List<Book>>> = if (allTranslations)
            BibleRepo.ordered().map { t -> t.label to BibleRepo.load(context, t.id) }
        else listOf(null to books)
        results = withContext(Dispatchers.Default) {
            val hits = ArrayList<SearchHit>()
            outer@ for ((label, text) in sources) {
                for (b in text.indices) {
                    val chapters = text[b].chapters
                    for (c in chapters.indices) {
                        val vs = chapters[c]
                        for (v in vs.indices) {
                            if (searchNorm(vs[v]).contains(q)) {
                                hits.add(SearchHit(b, c, v, vs[v], label))
                                if (hits.size >= 300) break@outer
                            }
                        }
                    }
                }
            }
            hits
        }
        searched = true
    }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Surface(
            modifier = Modifier.fillMaxSize().padding(12.dp),
            shape = RoundedCornerShape(16.dp),
            color = MaterialTheme.colorScheme.surface
        ) {
            Column(Modifier.padding(12.dp)) {
                OutlinedTextField(
                    value = query,
                    onValueChange = { query = it },
                    placeholder = { Text(stringResource(R.string.search_hint)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        stringResource(R.string.search_all),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.weight(1f)
                    )
                    Switch(checked = allTranslations, onCheckedChange = { allTranslations = it })
                }
                Spacer(Modifier.height(4.dp))
                if (searched && results.isEmpty()) {
                    Text(
                        stringResource(R.string.no_results),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(16.dp)
                    )
                }
                LazyColumn(Modifier.weight(1f)) {
                    items(results) { hit ->
                        Column(
                            Modifier
                                .fillMaxWidth()
                                .combinedClickable(
                                    onClick = { onSelect(hit.book, hit.chapter, hit.verse) },
                                    onLongClick = {}
                                )
                                .padding(vertical = 8.dp)
                        ) {
                            Text(
                                "${books.getOrNull(hit.book)?.name ?: "?"} ${hit.chapter + 1}:${hit.verse + 1}" +
                                        (hit.translationLabel?.let { "  ·  $it" } ?: ""),
                                style = MaterialTheme.typography.labelLarge,
                                color = MaterialTheme.colorScheme.primary
                            )
                            Text(
                                hit.text,
                                style = MaterialTheme.typography.bodyMedium,
                                maxLines = 3,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
                        HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant)
                    }
                }
                TextButton(onClick = onDismiss, modifier = Modifier.align(Alignment.End)) {
                    Text(stringResource(R.string.cancel))
                }
            }
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun BookChapterPicker(
    books: List<Book>,
    currentBook: Int,
    currentChapter: Int,
    splitEnabled: Boolean,
    primaryId: String,
    secondaryId: String,
    onDismiss: () -> Unit,
    onSelect: (book: Int, chapter: Int) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    // Opens straight into the CURRENT book's chapter grid — jumping from
    // Psalm 130 to Psalm 20 must not require re-finding Psalms in the book
    // list first. The back arrow reaches the full list.
    var pickedBook by remember { mutableStateOf<Int?>(currentBook) }
    // null = navigating; 0 = choosing primary; 1 = choosing secondary.
    var pickTranslation by remember { mutableStateOf<Int?>(null) }

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            shape = RoundedCornerShape(16.dp),
            color = MaterialTheme.colorScheme.surface,
            tonalElevation = 4.dp
        ) {
            // A translation switch can shrink the canon (66 vs 83 books) or
            // land on an empty book — fall back to the book list rather than
            // indexing out of bounds.
            val picked = pickedBook?.takeIf { it < books.size && books[it].chapters.isNotEmpty() }
            val choosing = pickTranslation
            if (choosing != null) {
                Column(Modifier.padding(vertical = 8.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconButton(onClick = { pickTranslation = null }) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.cancel))
                        }
                        Text(
                            stringResource(
                                if (choosing == 0) R.string.primary_translation
                                else R.string.secondary_translation
                            ),
                            style = MaterialTheme.typography.titleMedium
                        )
                    }
                    LazyColumn {
                        item {
                            Column(Modifier.padding(horizontal = 16.dp)) {
                                TranslationPicker(
                                    selectedIds = setOf(if (choosing == 0) primaryId else secondaryId),
                                    multiSelect = false
                                ) { id ->
                                    scope.launch {
                                        if (choosing == 0) Store.setPrimary(context, id)
                                        else Store.setSecondary(context, id)
                                    }
                                    pickTranslation = null
                                }
                            }
                        }
                    }
                }
            } else Column(Modifier.padding(vertical = 8.dp)) {
                // Current translation(s) — switchable without leaving the
                // navigation dialog.
                Row(
                    Modifier.padding(horizontal = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    AssistChip(
                        onClick = { pickTranslation = 0 },
                        label = { Text(TranslationGroups.shortTag(BibleRepo.translation(primaryId))) }
                    )
                    if (splitEnabled) AssistChip(
                        onClick = { pickTranslation = 1 },
                        label = { Text("+ " + TranslationGroups.shortTag(BibleRepo.translation(secondaryId))) }
                    )
                }
                if (picked == null) {
                    // Back to the current book's chapter grid — without
                    // this the list view had no way back (owner report).
                    if (currentBook < books.size && books[currentBook].chapters.isNotEmpty()) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            IconButton(onClick = { pickedBook = currentBook }) {
                                Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.cancel))
                            }
                            Text(
                                books[currentBook].name,
                                style = MaterialTheme.typography.titleMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                    // Land the list on the current book, not Genesis.
                    val listState = rememberLazyListState(
                        initialFirstVisibleItemIndex = maxOf(0, currentBook - 2)
                    )
                    LazyColumn(state = listState) {
                        itemsIndexed(books) { i, b ->
                            if (i == 0 || i == 39 || i == 66) {
                                Text(
                                    stringResource(
                                        when (i) {
                                            0 -> R.string.old_testament
                                            39 -> R.string.new_testament
                                            else -> R.string.apocrypha
                                        }
                                    ),
                                    style = MaterialTheme.typography.labelLarge,
                                    color = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.padding(horizontal = 20.dp, vertical = 8.dp)
                                )
                            }
                            TextButton(
                                onClick = { pickedBook = i },
                                enabled = b.chapters.isNotEmpty(),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text(
                                    b.name,
                                    modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp),
                                    textAlign = TextAlign.Start,
                                    color = if (i == currentBook) MaterialTheme.colorScheme.primary
                                    else Color.Unspecified,
                                    fontWeight = if (i == currentBook) FontWeight.Bold else null
                                )
                            }
                        }
                    }
                } else {
                    Column(Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.padding(bottom = 8.dp)
                        ) {
                            IconButton(onClick = { pickedBook = null }) {
                                Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.cancel))
                            }
                            Text(
                                books[picked].name,
                                style = MaterialTheme.typography.titleMedium,
                                modifier = Modifier
                                    .weight(1f)
                                    .clickable { pickedBook = null }
                            )
                        }
                        LazyVerticalGrid(
                            columns = GridCells.Fixed(5),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            items((1..books[picked].chapters.size).toList()) { ch ->
                                val isCurrent = picked == currentBook && ch - 1 == currentChapter
                                TextButton(onClick = { onSelect(picked, ch - 1) }) {
                                    Text(
                                        "$ch",
                                        color = if (isCurrent) MaterialTheme.colorScheme.primary
                                        else Color.Unspecified,
                                        fontWeight = if (isCurrent) FontWeight.Bold else null
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun XrefsDialog(
    primaryId: String,
    books: List<Book>,
    book: Int,
    chapter: Int,
    verse: Int,
    refLabel: String,
    onDismiss: () -> Unit,
    onSelect: (book: Int, chapter: Int, verse: Int) -> Unit
) {
    val context = LocalContext.current
    var refs by remember { mutableStateOf<List<IntArray>?>(null) }
    LaunchedEffect(book, chapter, verse) {
        VerseMap.load(context)
        // xrefs.json is KJV-indexed on both key and targets.
        val (kc, kv) = VerseMap.toKjv(primaryId, book, chapter + 1, verse + 1)
        refs = Xrefs.refs(context, book, kc - 1, kv - 1)
    }

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            shape = RoundedCornerShape(16.dp),
            color = MaterialTheme.colorScheme.surface,
            tonalElevation = 4.dp
        ) {
            Column(Modifier.padding(16.dp)) {
                Text(
                    stringResource(R.string.xrefs) + " — " + refLabel,
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier.padding(bottom = 8.dp)
                )
                val loaded = refs
                when {
                    loaded == null -> Box(
                        Modifier.fillMaxWidth().padding(24.dp),
                        contentAlignment = Alignment.Center
                    ) { CircularProgressIndicator() }

                    loaded.isEmpty() -> Text(
                        stringResource(R.string.no_results),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(vertical = 16.dp)
                    )

                    else -> LazyColumn {
                        items(loaded) { t ->
                            // Targets are KJV refs; show them at the primary
                            // translation's own position.
                            val pos = VerseMap.fromKjv(primaryId, t[0], t[1] + 1, t[2] + 1)
                                .firstOrNull() ?: (t[1] + 1 to t[2] + 1)
                            val (tb, tc, tv) = Triple(t[0], pos.first - 1, pos.second - 1)
                            val tBook = books.getOrNull(tb)
                            val text = tBook?.chapters?.getOrNull(tc)?.getOrNull(tv) ?: ""
                            Column(
                                Modifier
                                    .fillMaxWidth()
                                    .combinedClickable(
                                        onClick = { onSelect(tb, tc, tv) },
                                        onLongClick = {}
                                    )
                                    .padding(vertical = 8.dp)
                            ) {
                                Text(
                                    "${tBook?.name ?: "?"} ${tc + 1}:${tv + 1}",
                                    style = MaterialTheme.typography.labelLarge,
                                    color = MaterialTheme.colorScheme.primary
                                )
                                if (text.isNotBlank()) Text(
                                    text,
                                    style = MaterialTheme.typography.bodyMedium,
                                    maxLines = 3,
                                    overflow = TextOverflow.Ellipsis
                                )
                            }
                            HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant)
                        }
                    }
                }
                TextButton(onClick = onDismiss, modifier = Modifier.align(Alignment.End)) {
                    Text(stringResource(R.string.cancel))
                }
            }
        }
    }
}
