package com.aleks.hexapla

import androidx.compose.foundation.clickable
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Checkbox
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import java.util.Locale

/**
 * Language-grouped translation picker shared by Settings (primary, compare,
 * secondary) and the reader's navigation dialog. Replaces the flat chip
 * lists that repeated every translation once per picker — collapsed, this
 * is one row per LANGUAGE, and it stays that size as translations grow.
 */
object TranslationGroups {
    data class Group(val language: String, val endonym: String, val items: List<Translation>)

    /** Native language name, capitalized in that language. ICU lacks data
     *  for some codes (e.g. "la"), so fall back to the English name, then
     *  to the bare code. */
    fun endonym(locale: Locale): String {
        val own = locale.getDisplayLanguage(locale)
        val name =
            if (own.isNotBlank() && !own.equals(locale.language, ignoreCase = true)) own
            else locale.getDisplayLanguage(Locale.ENGLISH)
        if (name.isBlank() || name.equals(locale.language, ignoreCase = true))
            return locale.language.uppercase(Locale.ROOT)
        return name.replaceFirstChar { it.titlecase(locale) }
    }

    /** Follows BibleRepo.ordered() — the user's language surfaces first —
     *  and groups by first appearance, so both zh scripts share one group. */
    fun build(): List<Group> =
        BibleRepo.ordered().groupBy { it.locale.language }.map { (lang, items) ->
            Group(lang, endonym(items.first().locale), items)
        }

    /** Compact tag for chips: the label's trailing parenthetical —
     *  "Синодальный перевод (RU)" -> "RU". */
    fun shortTag(t: Translation): String {
        val tag = t.label.substringAfterLast('(', "").substringBefore(')')
        return tag.ifBlank { t.id.uppercase(Locale.ROOT) }
    }
}

@Composable
fun TranslationPicker(
    selectedIds: Set<String>,
    multiSelect: Boolean,
    onPick: (String) -> Unit
) {
    val groups = remember { TranslationGroups.build() }
    // Single-select opens the group holding the selection; compare mode
    // (where "all enabled" is the default) starts fully collapsed and
    // communicates through the per-group counts instead.
    val expanded = remember {
        mutableStateMapOf<String, Boolean>().apply {
            if (!multiSelect) groups.forEach { g ->
                if (g.items.any { it.id in selectedIds }) put(g.language, true)
            }
        }
    }
    Column {
        groups.forEach { g ->
            val isOpen = expanded[g.language] == true
            val chosen = g.items.filter { it.id in selectedIds }
            Row(
                Modifier
                    .fillMaxWidth()
                    .clickable { expanded[g.language] = !isOpen }
                    .padding(vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(Modifier.weight(1f)) {
                    Text(g.endonym, style = MaterialTheme.typography.bodyLarge)
                    if (!isOpen && !multiSelect && chosen.isNotEmpty()) Text(
                        chosen.first().label,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
                if (multiSelect) Text(
                    "${chosen.size}/${g.items.size}",
                    style = MaterialTheme.typography.labelMedium,
                    color = if (chosen.isEmpty()) MaterialTheme.colorScheme.onSurfaceVariant
                    else MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(end = 4.dp)
                )
                Icon(
                    if (isOpen) Icons.Filled.ExpandLess else Icons.Filled.ExpandMore,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            if (isOpen) g.items.forEach { t ->
                Row(
                    Modifier
                        .fillMaxWidth()
                        .clickable { onPick(t.id) }
                        .padding(start = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    if (multiSelect)
                        Checkbox(checked = t.id in selectedIds, onCheckedChange = { onPick(t.id) })
                    else
                        RadioButton(selected = t.id in selectedIds, onClick = { onPick(t.id) })
                    Text(t.label, style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
    }
}

/**
 * Compact Settings row for choosing translations: shows [title] + a [summary]
 * of the current choice and a chevron; tapping opens the language-grouped
 * [TranslationPicker] in a dialog. Keeps the Settings screen short as the
 * translation list grows. Single-select closes on pick; multi-select (compare)
 * stays open until dismissed.
 */
@Composable
fun TranslationPickerField(
    title: String,
    summary: String,
    selectedIds: Set<String>,
    multiSelect: Boolean,
    onPick: (String) -> Unit
) {
    var open by remember { mutableStateOf(false) }
    Row(
        Modifier
            .fillMaxWidth()
            .clickable { open = true }
            .padding(vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            Text(
                summary,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.primary
            )
        }
        Icon(
            Icons.Filled.ChevronRight,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
    if (open) {
        AlertDialog(
            onDismissRequest = { open = false },
            confirmButton = {
                TextButton(onClick = { open = false }) {
                    Text(stringResource(android.R.string.ok))
                }
            },
            title = { Text(title) },
            text = {
                Column(Modifier.verticalScroll(rememberScrollState())) {
                    TranslationPicker(selectedIds, multiSelect) { id ->
                        onPick(id)
                        if (!multiSelect) open = false
                    }
                }
            }
        )
    }
}
