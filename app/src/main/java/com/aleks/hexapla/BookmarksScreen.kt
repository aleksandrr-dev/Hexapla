package com.aleks.hexapla

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
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

@Composable
fun BookmarksScreen(settings: AppSettings, openReader: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val bookmarks by Store.bookmarks(context).collectAsState(initial = emptyList())

    var books by remember { mutableStateOf<List<Book>?>(null) }
    LaunchedEffect(settings.primaryId) {
        // Versemap first, so rows never render at unmapped raw indexes.
        VerseMap.load(context)
        books = BibleRepo.load(context, settings.primaryId)
    }
    val loaded = books
    if (loaded == null) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        return
    }

    Column(Modifier.fillMaxSize()) {
        Text(
            stringResource(R.string.bookmarks_title),
            style = MaterialTheme.typography.headlineSmall,
            modifier = Modifier.padding(16.dp)
        )
        if (bookmarks.isEmpty()) {
            Box(Modifier.fillMaxSize().padding(32.dp), contentAlignment = Alignment.Center) {
                Text(
                    stringResource(R.string.no_bookmarks),
                    style = MaterialTheme.typography.bodyLarge,
                    textAlign = TextAlign.Center,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        } else {
            LazyColumn(Modifier.weight(1f)) {
                items(bookmarks, key = { it.encode() }) { bm ->
                    val book = loaded.getOrNull(bm.book)
                    // Display-time pivot: the bookmark stores its SOURCE translation's
                    // own (chapter, verse); map into the current primary through the
                    // KJV backbone. Same-translation bookmarks skip the round-trip so
                    // behavior stays byte-identical to before (block runs in the map
                    // would not round-trip verse-exactly).
                    val mapped: Pair<Int, Int>? = remember(bm, settings.primaryId, loaded) {
                        if (bm.translationId == settings.primaryId) bm.chapter to bm.verse
                        else {
                            val (kc, kv) = VerseMap.toKjv(
                                bm.translationId, bm.book, bm.chapter + 1, bm.verse + 1
                            )
                            VerseMap.fromKjv(settings.primaryId, bm.book, kc, kv)
                                .firstOrNull()?.let { (c, v) -> (c - 1) to (v - 1) }
                        }
                    }
                    val mappedText = mapped?.let { (c, v) ->
                        book?.chapters?.getOrNull(c)?.getOrNull(v)
                    } ?: ""
                    // Mapping onto an omitted/absent verse in the primary (partial
                    // translations, committee omissions): dim, keep the STORED ref.
                    val tappable = bm.translationId == settings.primaryId ||
                        (mapped != null && mappedText.isNotBlank())
                    val verseText = if (tappable) mappedText
                        else book?.chapters?.getOrNull(bm.chapter)?.getOrNull(bm.verse) ?: ""
                    val labelPos = if (tappable && mapped != null) mapped
                        else bm.chapter to bm.verse
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 12.dp, vertical = 4.dp)
                    ) {
                        Row(
                            (if (tappable && mapped != null) Modifier
                                .clickable {
                                    AppState.open(bm.book, mapped.first, mapped.second)
                                    openReader()
                                }
                            else Modifier)
                                .padding(start = 12.dp, top = 8.dp, bottom = 8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(
                                    "${book?.name ?: "?"} ${labelPos.first + 1}:${labelPos.second + 1}",
                                    style = MaterialTheme.typography.labelLarge,
                                    fontWeight = FontWeight.Bold,
                                    color = if (tappable) MaterialTheme.colorScheme.primary
                                    else MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                Text(
                                    verseText,
                                    style = MaterialTheme.typography.bodyMedium,
                                    maxLines = 2,
                                    overflow = TextOverflow.Ellipsis,
                                    color = if (tappable) MaterialTheme.colorScheme.onSurface
                                    else MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            IconButton(onClick = {
                                scope.launch { Store.removeBookmark(context, bm) }
                            }) {
                                Icon(
                                    Icons.Filled.Delete,
                                    contentDescription = stringResource(R.string.delete),
                                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }
                item { Spacer(Modifier.height(24.dp)) }
            }
        }
    }
}
