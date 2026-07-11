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
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Tab
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

@Composable
fun PlansScreen(settings: AppSettings, openReader: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var books by remember { mutableStateOf<List<Book>?>(null) }
    LaunchedEffect(settings.primaryId) { books = BibleRepo.load(context, settings.primaryId) }
    val loaded = books
    if (loaded == null) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        return
    }

    val plans = remember(loaded) { Plans.build(loaded) }
    // Reopen on the plan the user last had open (persisted across sessions).
    var tab by remember(plans) {
        mutableIntStateOf(plans.indexOfFirst { it.id == settings.lastPlanId }.coerceAtLeast(0))
    }
    val plan = plans[tab]
    val progress by Store.planProgress(context, plan.id).collectAsState(initial = emptySet())
    val nextDay = remember(progress, plan) {
        plan.days.firstOrNull { !progress.contains(it.day) }?.day ?: plan.days.size
    }
    val listState = rememberLazyListState()
    LaunchedEffect(tab, loaded) { listState.scrollToItem((nextDay - 1).coerceAtLeast(0)) }

    Column(Modifier.fillMaxSize()) {
        Row(
            Modifier.fillMaxWidth().padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                stringResource(R.string.plans_title),
                style = MaterialTheme.typography.headlineSmall,
                modifier = Modifier.weight(1f)
            )
            if (settings.streak > 1) {
                Text(
                    stringResource(R.string.streak, settings.streak),
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        }
        ScrollableTabRow(selectedTabIndex = tab, edgePadding = 8.dp) {
            plans.forEachIndexed { i, p ->
                Tab(selected = tab == i, onClick = {
                    tab = i
                    scope.launch { Store.setLastPlan(context, p.id) }
                }, text = { Text(stringResource(p.titleRes), maxLines = 1) })
            }
        }
        Column(Modifier.padding(16.dp)) {
            Text(stringResource(plan.descRes), style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(8.dp))
            LinearProgressIndicator(
                progress = { progress.size.toFloat() / plan.days.size },
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(Modifier.height(4.dp))
            Row(
                Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    stringResource(R.string.days_done, progress.size, plan.days.size),
                    style = MaterialTheme.typography.labelMedium,
                    modifier = Modifier.weight(1f)
                )
                TextButton(onClick = { scope.launch { Store.resetPlan(context, plan.id) } }) {
                    Text(stringResource(R.string.reset_plan))
                }
            }
        }
        HorizontalDivider()

        LazyColumn(state = listState, modifier = Modifier.weight(1f)) {
            items(plan.days, key = { it.day }) { day ->
                val done = progress.contains(day.day)
                val isNext = day.day == nextDay && !done
                Column {
                plan.eraByDay[day.day]?.let { era ->
                    Text(
                        stringResource(era),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 14.dp, bottom = 4.dp)
                    )
                }
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp, vertical = 4.dp),
                    colors = androidx.compose.material3.CardDefaults.cardColors(
                        containerColor = if (isNext) MaterialTheme.colorScheme.primaryContainer
                        else MaterialTheme.colorScheme.surfaceVariant
                    )
                ) {
                    Row(
                        Modifier.padding(start = 12.dp, end = 4.dp, top = 4.dp, bottom = 4.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(Modifier.weight(1f)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(
                                    stringResource(R.string.day_n, day.day),
                                    fontWeight = FontWeight.Bold,
                                    style = MaterialTheme.typography.titleSmall
                                )
                                if (isNext) {
                                    Spacer(Modifier.padding(4.dp))
                                    Text(
                                        stringResource(R.string.today),
                                        color = MaterialTheme.colorScheme.primary,
                                        style = MaterialTheme.typography.labelSmall
                                    )
                                }
                            }
                            Text(
                                day.chapters.joinToString("  ·  ") { (b, c) ->
                                    "${loaded[b].name} ${c + 1}"
                                },
                                style = MaterialTheme.typography.bodySmall,
                                modifier = Modifier
                                    .clickable {
                                        val (b, c) = day.chapters.first()
                                        AppState.open(b, c)
                                        openReader()
                                    }
                                    .padding(vertical = 4.dp)
                            )
                        }
                        Checkbox(
                            checked = done,
                            onCheckedChange = {
                                scope.launch { Store.togglePlanDay(context, plan.id, day.day) }
                            }
                        )
                    }
                }
                }
            }
            item { Spacer(Modifier.height(24.dp)) }
        }
    }
}
