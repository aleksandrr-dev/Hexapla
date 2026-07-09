package com.aleks.hexapla

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.view.WindowManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.rememberScrollState
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
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.runtime.withFrameNanos
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.core.content.ContextCompat
import java.text.Normalizer
import kotlinx.coroutines.Dispatchers
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
        AppState.book.intValue = book
        AppState.chapter.intValue = 0
    }
    val chapter = AppState.chapter.intValue
        .coerceIn(0, (books[book].chapters.size - 1).coerceAtLeast(0))
    val verses = books[book].chapters[chapter]
    val secondaryVerses = if (settings.splitEnabled)
        secondaryBooks?.getOrNull(book)?.chapters?.getOrNull(chapter) else null

    LaunchedEffect(book, chapter) { Store.setLastPosition(context, book, chapter) }

    val bookmarks by Store.bookmarks(context).collectAsState(initial = emptyList())
    val bookmarkedVerses = remember(bookmarks, book, chapter) {
        bookmarks.filter { it.book == book && it.chapter == chapter }.map { it.verse }.toSet()
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
    // xrefs, deep links) win over the scroll-to-top on chapter change. Split
    // effects raced — the jump landed first, then the chapter effect saw no
    // pending target and reset to the top.
    var lastPosition by remember { mutableStateOf(-1 to -1) }
    LaunchedEffect(Unit) {
        snapshotFlow {
            Triple(AppState.book.intValue, AppState.chapter.intValue, AppState.scrollToVerse.intValue)
        }.collect { (b, c, target) ->
            val movedChapter = (b to c) != lastPosition
            lastPosition = b to c
            if (target >= 0) {
                // Let the new chapter's list compose before scrolling into it.
                withFrameNanos { }
                withFrameNanos { }
                listState.scrollToItem(target.coerceAtLeast(0))
                AppState.scrollToVerse.intValue = -1
            } else if (movedChapter) {
                listState.scrollToItem(0)
            }
        }
    }
    // Follow the voice: when the service reads this chapter, keep the spoken
    // verse in view; when it advances to a new chapter, follow it there.
    val playbackHere = Playback.active.value &&
        Playback.book.intValue == book && Playback.chapter.intValue == chapter
    LaunchedEffect(Playback.verse.intValue, playbackHere) {
        val v = Playback.verse.intValue
        if (playbackHere && v in verses.indices) listState.animateScrollToItem(v)
    }
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
                    Text(
                        "${books[book].name} ${chapter + 1}",
                        style = MaterialTheme.typography.titleMedium,
                        textAlign = TextAlign.Center,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
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
                    val red = redLetters?.get(book)?.getOrNull(chapter)?.contains(i) == true
                    val tagged = strongsBooks?.getOrNull(book)?.chapters
                        ?.getOrNull(chapter)?.getOrNull(i)
                    // Word ranges refer to the plain text; skip them when the
                    // Strong's-tagged text is displayed instead.
                    val spoken = if (tagged == null && highlighted && Playback.wordStart.intValue >= 0)
                        Playback.wordStart.intValue..Playback.wordEnd.intValue else null
                    val bookmarked = bookmarkedVerses.contains(i)
                    val noteText = notes["$book:$chapter:$i"]
                    val userColor = liveHighlights["$book:$chapter:$i"]
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
                        if (settings.splitEnabled && secondaryVerses != null) {
                            val second = secondaryVerses.getOrNull(i) ?: ""
                            if (settings.splitHorizontal) {
                                Row(Modifier.fillMaxWidth()) {
                                    VerseText(i + 1, verse, settings.fontSize, fontFamily, Modifier.weight(1f), spokenRange = spoken, taggedText = tagged, onStrongs = { strongsId = it }, onWord = if (dictPrimary) ({ dictWord = it }) else null, red = red, showNumber = !settings.hideVerseNumbers)
                                    Spacer(Modifier.width(12.dp))
                                    VerseText(i + 1, second, settings.fontSize, fontFamily, Modifier.weight(1f), onWord = if (dictSecondary) ({ dictWord = it }) else null, red = red, showNumber = !settings.hideVerseNumbers)
                                }
                            } else {
                                VerseText(i + 1, verse, settings.fontSize, fontFamily, Modifier.fillMaxWidth(), spokenRange = spoken, taggedText = tagged, onStrongs = { strongsId = it }, onWord = if (dictPrimary) ({ dictWord = it }) else null, red = red, showNumber = !settings.hideVerseNumbers)
                                Spacer(Modifier.height(4.dp))
                                VerseText(
                                    i + 1, second, settings.fontSize, fontFamily,
                                    Modifier.fillMaxWidth(), secondary = true,
                                    onWord = if (dictSecondary) ({ dictWord = it }) else null,
                                    red = red, showNumber = !settings.hideVerseNumbers
                                )
                            }
                        } else {
                            VerseText(i + 1, verse, settings.fontSize, fontFamily, Modifier.fillMaxWidth(), spokenRange = spoken, taggedText = tagged, onStrongs = { strongsId = it }, onWord = if (dictPrimary) ({ dictWord = it }) else null, red = red, showNumber = !settings.hideVerseNumbers)
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
        VerseActionsDialog(
            refLabel = refLabel,
            bookmarked = bookmarkedVerses.contains(v),
            existingNote = notes["$book:$chapter:$v"] ?: "",
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
                scope.launch { Store.setNote(context, book, chapter, v, text) }
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
            onListen = {
                ensureNotificationPermission()
                ReadingService.play(context, book, chapter, v)
                actionVerse = null
            },
            onShareImage = {
                ShareImage.share(context, verseText, refLabel)
                actionVerse = null
            },
            currentHighlight = liveHighlights["$book:$chapter:$v"],
            onHighlight = { color ->
                val key = "$book:$chapter:$v"
                if (color == null) liveHighlights.remove(key) else liveHighlights[key] = color
                scope.launch { Store.setHighlight(context, book, chapter, v, color) }
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

    compareVerse?.let { v ->
        CompareDialog(
            book = book,
            chapter = chapter,
            verse = v,
            refLabel = "${books[book].name} ${chapter + 1}:${v + 1}",
            enabledIds = settings.compareIds,
            onDismiss = { compareVerse = null }
        )
    }

    xrefVerse?.let { v ->
        XrefsDialog(
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
    var b = AppState.book.intValue
    var c = AppState.chapter.intValue + delta
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

private val wordRegex = Regex("""[A-Za-z]+(?:['’-][A-Za-z]+)*""")

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
    red: Boolean = false,
    showNumber: Boolean = true
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
        spokenRange != null && spokenRange.first >= 0 && spokenRange.last <= text.length -> {
            val mark = MaterialTheme.colorScheme.primary.copy(alpha = 0.35f)
            buildAnnotatedString {
                append(text)
                addStyle(SpanStyle(background = mark), spokenRange.first, spokenRange.last)
            }
        }
        onWord != null -> buildAnnotatedString { appendWords(text, onWord) }
        else -> AnnotatedString(text)
    }
    // Classic red-letter tone, adjusted for theme luminance.
    val redColor = if (MaterialTheme.colorScheme.background.luminance() < 0.5f)
        Color(0xFFEF9A9A) else Color(0xFFB71C1C)
    Row(modifier) {
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
        rows = BibleRepo.ordered()
            .filter { enabledIds.isEmpty() || it.id in enabledIds }
            .mapNotNull { t ->
                val text = BibleRepo.load(context, t.id)
                    .getOrNull(book)?.chapters?.getOrNull(chapter)?.getOrNull(verse)
                if (text.isNullOrBlank()) null else t to text
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
    onDismiss: () -> Unit,
    onSelect: (book: Int, chapter: Int) -> Unit
) {
    var pickedBook by remember { mutableStateOf<Int?>(null) }

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            shape = RoundedCornerShape(16.dp),
            color = MaterialTheme.colorScheme.surface,
            tonalElevation = 4.dp
        ) {
            val picked = pickedBook
            if (picked == null) {
                LazyColumn(Modifier.padding(vertical = 8.dp)) {
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
                                textAlign = TextAlign.Start
                            )
                        }
                    }
                }
            } else {
                Column(Modifier.padding(16.dp)) {
                    Text(
                        books[picked].name,
                        style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.padding(bottom = 12.dp)
                    )
                    LazyVerticalGrid(
                        columns = GridCells.Fixed(5),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items((1..books[picked].chapters.size).toList()) { ch ->
                            TextButton(onClick = { onSelect(picked, ch - 1) }) {
                                Text("$ch")
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
        refs = Xrefs.refs(context, book, chapter, verse)
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
                            val (tb, tc, tv) = Triple(t[0], t[1], t[2])
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
