package com.aleks.hexapla

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.MenuBook
import androidx.compose.material.icons.filled.Bookmarks
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController

/** Cross-screen state: where the reader is pointed. */
object AppState {
    val book = mutableIntStateOf(0)
    val chapter = mutableIntStateOf(0)
    val scrollToVerse = mutableIntStateOf(-1)
    val initialized = mutableStateOf(false)

    /**
     * "Peek" mode: the reader was opened by a deep link (daily-verse reminder
     * or widget) rather than by the reader's own navigation.
     *
     * While peeking, ReaderScreen does NOT overwrite the saved reading
     * position — looking at tonight's verse must not cost you your place in
     * Exodus — and offers a one-tap way back. Peeking ends the moment the
     * reader moves off the linked chapter under its own steam, because
     * reading onward from a notification IS a deliberate move and should
     * become the new spot.
     */
    val peeking = mutableStateOf(false)
    /** The chapter the deep link landed on; leaving it ends the peek. */
    var peekBook = -1
    var peekChapter = -1
    /** The reading position to offer as "back to…" while peeking. */
    val spotBook = mutableIntStateOf(0)
    val spotChapter = mutableIntStateOf(0)
    var spotVerse = -1

    fun open(book: Int, chapter: Int, verse: Int = -1) {
        this.book.intValue = book
        this.chapter.intValue = chapter
        this.scrollToVerse.intValue = verse
    }

    /** Open from a deep link, preserving the reader's saved spot. */
    fun peek(book: Int, chapter: Int, verse: Int = -1) {
        open(book, chapter, verse)
        peekBook = book
        peekChapter = chapter
        peeking.value = true
    }

    fun endPeek() {
        peeking.value = false
        peekBook = -1
        peekChapter = -1
    }
}

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        openFromIntent(intent)
        lifecycleScope.launch { Store.touchStreak(this@MainActivity) }
        setContent {
            val context = LocalContext.current
            // No initial placeholder: composing the reader with default
            // settings made the one-shot position restore race the real
            // DataStore load and land on Genesis 1 after cold starts.
            val settings by Store.settings(context).collectAsState(initial = null)
            var startRoute by remember { mutableStateOf("read") }
            val s = settings
            BibleTheme(s?.themeMode ?: "system") {
                when {
                    s == null -> Surface(Modifier.fillMaxSize()) { }
                    !s.welcomeSeen -> WelcomeScreen { route ->
                        if (route == "read") {
                            // A first-time reader's "just start reading" opens
                            // the Gospel of John, not Genesis 1.
                            AppState.open(42, 0)
                            AppState.initialized.value = true
                        }
                        startRoute = route
                        lifecycleScope.launch { Store.setWelcomeSeen(this@MainActivity) }
                    }
                    else -> AppScaffold(s, startRoute)
                }
            }
        }
        refreshWidget()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        openFromIntent(intent)
    }

    /**
     * Deep link from the daily-verse notification.
     *
     * ⚠ The extras MUST be consumed. Android retains the Intent that started
     * the task and hands it back from getIntent() every time the activity is
     * recreated — so a deep link that is not cleared re-fires on every later
     * launch, including plain taps from the app drawer. Combined with
     * AppState's process-lifetime `initialized` latch (which then skips the
     * saved-position restore in ReaderScreen), that pinned the reader to one
     * notification's verse indefinitely: the owner's reader kept reopening at
     * Psalms 41 while his saved position was Exodus 20 (2026-07-31).
     */
    private fun openFromIntent(intent: Intent?) {
        if (intent == null) return
        val book = intent.getIntExtra(EXTRA_BOOK, -1)
        if (book < 0) return
        val chapter = intent.getIntExtra(EXTRA_CHAPTER, 0)
        val verse = intent.getIntExtra(EXTRA_VERSE, 0)
        // EXTRA_PEEK distinguishes "show me this verse" (a reminder or the
        // widget's quote — must not cost the reader its saved place) from
        // "take me back to where I was" (the widget's Continue reading — a
        // deliberate move that IS the reading position).
        if (intent.getBooleanExtra(EXTRA_PEEK, true)) AppState.peek(book, chapter, verse)
        else AppState.open(book, chapter, verse)
        AppState.initialized.value = true
        // Consume it: a one-shot deep link, never a sticky destination.
        intent.removeExtra(EXTRA_BOOK)
        intent.removeExtra(EXTRA_CHAPTER)
        intent.removeExtra(EXTRA_VERSE)
        intent.removeExtra(EXTRA_PEEK)
    }

    /** Keep the widget's verse and continue-reading label fresh. */
    private fun refreshWidget() {
        val manager = android.appwidget.AppWidgetManager.getInstance(this)
        val ids = manager.getAppWidgetIds(
            android.content.ComponentName(this, VerseWidget::class.java)
        )
        if (ids.isEmpty()) return
        sendBroadcast(
            Intent(this, VerseWidget::class.java)
                .setAction(android.appwidget.AppWidgetManager.ACTION_APPWIDGET_UPDATE)
                .putExtra(android.appwidget.AppWidgetManager.EXTRA_APPWIDGET_IDS, ids)
        )
    }

    companion object {
        const val EXTRA_BOOK = "open_book"
        const val EXTRA_CHAPTER = "open_chapter"
        const val EXTRA_VERSE = "open_verse"
        /** false = a deliberate move (widget "Continue reading"); true/absent = a peek. */
        const val EXTRA_PEEK = "open_peek"
    }
}

private data class Dest(val route: String, val labelRes: Int, val icon: ImageVector)

/** Nav label that shrinks instead of ellipsizing — "Einstellungen" and
 *  friends must survive a 360dp screen split five ways. */
@Composable
private fun NavLabel(text: String) {
    var scale by remember(text) { mutableFloatStateOf(1f) }
    val base = MaterialTheme.typography.labelSmall
    Text(
        text,
        style = base,
        fontSize = base.fontSize * scale,
        maxLines = 1,
        softWrap = false,
        overflow = TextOverflow.Ellipsis,
        onTextLayout = { if (it.hasVisualOverflow && scale > 0.6f) scale *= 0.92f }
    )
}

/** One-time first-run screen: language-aware entry points into the app. */
@Composable
private fun WelcomeScreen(onChoice: (route: String) -> Unit) {
    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            Modifier.fillMaxSize().padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Icon(
                Icons.AutoMirrored.Filled.MenuBook,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(72.dp)
            )
            Spacer(Modifier.height(16.dp))
            Text(
                stringResource(R.string.app_name),
                style = MaterialTheme.typography.headlineMedium,
                fontFamily = FontFamily.Serif
            )
            Spacer(Modifier.height(8.dp))
            Text(
                stringResource(R.string.welcome_tagline),
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )
            Spacer(Modifier.height(40.dp))
            Button(onClick = { onChoice("topics") }, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.welcome_gospel), textAlign = TextAlign.Center)
            }
            Spacer(Modifier.height(12.dp))
            OutlinedButton(onClick = { onChoice("plans") }, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.welcome_plan), textAlign = TextAlign.Center)
            }
            Spacer(Modifier.height(12.dp))
            TextButton(onClick = { onChoice("read") }, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.welcome_read), textAlign = TextAlign.Center)
            }
            Text(
                stringResource(R.string.welcome_read_note),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )
        }
    }
}

@Composable
private fun AppScaffold(settings: AppSettings, startRoute: String = "read") {
    val nav = rememberNavController()
    val destinations = listOf(
        Dest("read", R.string.nav_read, Icons.AutoMirrored.Filled.MenuBook),
        Dest("plans", R.string.nav_plans, Icons.Filled.CalendarMonth),
        Dest("topics", R.string.nav_topics, Icons.Filled.School),
        Dest("bookmarks", R.string.nav_bookmarks, Icons.Filled.Bookmarks),
        Dest("settings", R.string.nav_settings, Icons.Filled.Settings)
    )
    val backStack by nav.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route

    Scaffold(
        bottomBar = {
            // M3's default NavigationBar is 80dp of content PLUS the system
            // navigation inset underneath — tall on a 3-button device. Take
            // the inset off the bar itself and re-apply it as outside padding,
            // so the bar can be a trimmer 64dp and still sit clear of the
            // system buttons. 64dp keeps icon+label comfortably above the
            // 48dp minimum touch target.
            NavigationBar(
                windowInsets = WindowInsets(0),
                modifier = Modifier.navigationBarsPadding().height(64.dp)
            ) {
                destinations.forEach { d ->
                    NavigationBarItem(
                        selected = currentRoute == d.route,
                        onClick = {
                            nav.navigate(d.route) {
                                popUpTo(nav.graph.startDestinationId) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(d.icon, contentDescription = null) },
                        label = { NavLabel(stringResource(d.labelRes)) }
                    )
                }
            }
        }
    ) { padding ->
        NavHost(
            navController = nav,
            startDestination = startRoute,
            modifier = Modifier.padding(padding)
        ) {
            composable("read") { ReaderScreen(settings) }
            composable("plans") { PlansScreen(settings) { nav.navigate("read") } }
            composable("topics") { TopicsScreen(settings) { nav.navigate("read") } }
            composable("bookmarks") { BookmarksScreen(settings) { nav.navigate("read") } }
            composable("settings") { SettingsScreen(settings) }
        }
    }
}
