package com.aleks.hexapla

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Tab
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@Composable
fun TopicsScreen(settings: AppSettings, openReader: () -> Unit) {
    val context = LocalContext.current
    var books by remember { mutableStateOf<List<Book>?>(null) }
    var fallback by remember { mutableStateOf<List<Book>?>(null) }
    val fallbackId = remember { BibleRepo.defaultPrimaryId() }
    LaunchedEffect(settings.primaryId) {
        // Topic refs are KJV-indexed; the versemap pivots them into each
        // translation's native numbering. Loaded before `books` is set, so
        // every card below resolves with the map ready.
        VerseMap.load(context)
        books = BibleRepo.load(context, settings.primaryId)
        // Testament-only primaries (Hebrew WLC, Greek NT, partial Tyndale) lack
        // many topic refs; show those from the system-language default text.
        fallback = if (fallbackId == settings.primaryId) null
        else BibleRepo.load(context, fallbackId)
    }
    val loaded = books
    if (loaded == null) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        return
    }

    var tab by remember { mutableIntStateOf(0) }
    val topics = when (tab) {
        0 -> Topics.gospel
        1 -> Topics.study
        else -> Topics.help
    }

    Column(Modifier.fillMaxSize()) {
        Text(
            stringResource(R.string.topics_title),
            style = MaterialTheme.typography.headlineSmall,
            modifier = Modifier.padding(16.dp)
        )
        ScrollableTabRow(selectedTabIndex = tab, edgePadding = 8.dp) {
            Tab(selected = tab == 0, onClick = { tab = 0 },
                text = { Text(stringResource(R.string.topics_gospel), maxLines = 1) })
            Tab(selected = tab == 1, onClick = { tab = 1 },
                text = { Text(stringResource(R.string.topics_study), maxLines = 1) })
            Tab(selected = tab == 2, onClick = { tab = 2 },
                text = { Text(stringResource(R.string.topics_help), maxLines = 1) })
        }
        LazyColumn(Modifier.weight(1f)) {
            if (tab == 0) {
                item {
                    Text(
                        stringResource(R.string.gospel_intro),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
                    )
                }
                item {
                    TextButton(
                        onClick = {
                            val steps = Topics.gospel.map { t ->
                                context.getString(t.titleRes) to t.refs.mapNotNull { ref ->
                                    resolveRef(ref, settings.primaryId, loaded, fallbackId, fallback)
                                        ?.let { it.label to it.text }
                                }
                            }
                            ShareImage.shareGospel(
                                context, context.getString(R.string.topics_gospel), steps
                            )
                        },
                        modifier = Modifier.padding(horizontal = 8.dp)
                    ) { Text(stringResource(R.string.gospel_share)) }
                }
            }
            items(topics) { topic ->
                TopicCard(topic, settings.primaryId, loaded, fallbackId, fallback, openReader)
            }
            item { Spacer(Modifier.height(24.dp)) }
        }
    }
}

/** A KJV-indexed topic ref resolved into one translation's own numbering. */
private class ResolvedRef(
    val label: String,
    val text: String,
    val inPrimary: Boolean,
    val chIdx: Int,      // 0-based, the shown translation's own chapter
    val verseIdx: Int    // 0-based, the shown translation's own first verse
)

/** Resolve a ref in the primary text, falling back if absent there. */
private fun resolveRef(
    ref: VerseRef,
    primaryId: String,
    books: List<Book>,
    fallbackId: String,
    fallback: List<Book>?
): ResolvedRef? =
    resolveIn(ref, primaryId, books, inPrimary = true)
        ?: fallback?.let { resolveIn(ref, fallbackId, it, inPrimary = false) }

/** Pivot the KJV-indexed ref through the versemap into `id`'s numbering. */
private fun resolveIn(ref: VerseRef, id: String, books: List<Book>, inPrimary: Boolean): ResolvedRef? {
    val bk = books.getOrNull(ref.book) ?: return null
    // Map both ends of the range; fromKjv is empty for verses this
    // translation omits and identity when the book is unmapped.
    val start = VerseMap.fromKjv(id, ref.book, ref.chapter + 1, ref.verseStart + 1)
        .firstOrNull() ?: return null
    val end = VerseMap.fromKjv(id, ref.book, ref.chapter + 1, ref.verseEnd + 1)
        .lastOrNull() ?: start
    val chIdx = start.first - 1
    val verses = bk.chapters.getOrNull(chIdx)
    if (verses.isNullOrEmpty()) return null
    val vs = (start.second - 1).coerceIn(0, verses.size - 1)
    // A range end that maps into the next chapter (rare) reads to chapter end.
    val ve = if (end.first == start.first) (end.second - 1).coerceIn(vs, verses.size - 1)
    else verses.size - 1
    val text = (vs..ve).mapNotNull { verses.getOrNull(it) }
        .filter { it.isNotBlank() }.joinToString(" ")
    if (text.isBlank()) return null
    val label = if (vs == ve) "${bk.name} ${chIdx + 1}:${vs + 1}"
    else "${bk.name} ${chIdx + 1}:${vs + 1}–${ve + 1}"
    return ResolvedRef(label, text, inPrimary, chIdx, vs)
}

@Composable
private fun TopicCard(
    topic: Topic,
    primaryId: String,
    books: List<Book>,
    fallbackId: String,
    fallback: List<Book>?,
    openReader: () -> Unit
) {
    var expanded by remember { mutableStateOf(false) }
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 6.dp)
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .clickable { expanded = !expanded }
                .padding(12.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    stringResource(topic.titleRes),
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1f)
                )
                Icon(
                    if (expanded) Icons.Filled.ExpandLess else Icons.Filled.ExpandMore,
                    contentDescription = null
                )
            }
            AnimatedVisibility(expanded) {
                Column {
                    topic.refs.forEach { ref ->
                        // Prefer the primary translation; fall back for books it lacks.
                        val r = resolveRef(ref, primaryId, books, fallbackId, fallback)
                            ?: return@forEach
                        val rowModifier = if (r.inPrimary)
                            Modifier
                                .fillMaxWidth()
                                .clickable {
                                    AppState.open(ref.book, r.chIdx, r.verseIdx)
                                    openReader()
                                }
                        else Modifier.fillMaxWidth()
                        Column(rowModifier.padding(vertical = 8.dp)) {
                            Text(
                                r.label,
                                style = MaterialTheme.typography.labelLarge,
                                color = if (r.inPrimary) MaterialTheme.colorScheme.primary
                                else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Text(
                                r.text,
                                style = MaterialTheme.typography.bodyMedium,
                                color = if (r.inPrimary) MaterialTheme.colorScheme.onSurface
                                else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            }
        }
    }
}
