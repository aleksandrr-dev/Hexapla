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

    fun open(book: Int, chapter: Int, verse: Int = -1) {
        this.book.intValue = book
        this.chapter.intValue = chapter
        this.scrollToVerse.intValue = verse
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
            val settings by Store.settings(context).collectAsState(initial = AppSettings())
            var startRoute by remember { mutableStateOf("read") }
            BibleTheme(settings.themeMode) {
                if (!settings.welcomeSeen) {
                    WelcomeScreen { route ->
                        startRoute = route
                        lifecycleScope.launch { Store.setWelcomeSeen(this@MainActivity) }
                    }
                } else {
                    AppScaffold(settings, startRoute)
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        openFromIntent(intent)
    }

    /** Deep link from the daily-verse notification. */
    private fun openFromIntent(intent: Intent?) {
        if (intent == null) return
        val book = intent.getIntExtra(EXTRA_BOOK, -1)
        if (book < 0) return
        AppState.open(
            book,
            intent.getIntExtra(EXTRA_CHAPTER, 0),
            intent.getIntExtra(EXTRA_VERSE, 0)
        )
        AppState.initialized.value = true
    }

    companion object {
        const val EXTRA_BOOK = "open_book"
        const val EXTRA_CHAPTER = "open_chapter"
        const val EXTRA_VERSE = "open_verse"
    }
}

private data class Dest(val route: String, val labelRes: Int, val icon: ImageVector)

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
                Text(stringResource(R.string.welcome_gospel))
            }
            Spacer(Modifier.height(12.dp))
            OutlinedButton(onClick = { onChoice("plans") }, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.welcome_plan))
            }
            Spacer(Modifier.height(12.dp))
            TextButton(onClick = { onChoice("read") }, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.welcome_read))
            }
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
            NavigationBar {
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
                        label = {
                            Text(
                                stringResource(d.labelRes),
                                style = MaterialTheme.typography.labelSmall,
                                maxLines = 1,
                                softWrap = false,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
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
