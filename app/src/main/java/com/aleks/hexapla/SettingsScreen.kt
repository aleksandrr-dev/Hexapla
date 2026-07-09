package com.aleks.hexapla

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.Locale

/** Landing page listing every way to get the app; QR codes never go stale. */
private const val APP_LINK = "https://aleksandrr-dev.github.io/Hexapla/"

private fun qrBitmap(text: String, size: Int): android.graphics.Bitmap? = try {
    val matrix = com.google.zxing.qrcode.QRCodeWriter()
        .encode(text, com.google.zxing.BarcodeFormat.QR_CODE, size, size)
    val bmp = android.graphics.Bitmap.createBitmap(
        size, size, android.graphics.Bitmap.Config.RGB_565
    )
    for (x in 0 until size) for (y in 0 until size) {
        bmp.setPixel(
            x, y,
            if (matrix[x, y]) android.graphics.Color.BLACK else android.graphics.Color.WHITE
        )
    }
    bmp
} catch (_: Exception) { null }

/** Picker label for a voice: region plus gender when known, e.g. "English (US) · Female". */
@Composable
private fun voiceLabel(name: String): String {
    val gender = voiceGender(name)
    val base = voiceDisplayName(name, includeVariant = gender == null)
    return when (gender) {
        true -> base + " · " + stringResource(R.string.voice_female)
        false -> base + " · " + stringResource(R.string.voice_male)
        null -> base
    }
}

@Composable
fun SettingsScreen(settings: AppSettings) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    val notifPermission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            scope.launch {
                Store.setReminderEnabled(context, true)
                Reminders.schedule(context, settings.reminderHour, settings.reminderMinute)
            }
        }
    }

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        Text(stringResource(R.string.nav_settings), style = MaterialTheme.typography.headlineSmall)
        Spacer(Modifier.height(16.dp))

        /* ---- Appearance ---- */
        SectionHeader(stringResource(R.string.settings_appearance))

        Text(stringResource(R.string.theme), style = MaterialTheme.typography.titleSmall)
        Row(Modifier.padding(vertical = 4.dp)) {
            ChoiceChip(stringResource(R.string.theme_system), settings.themeMode == "system") {
                scope.launch { Store.setTheme(context, "system") }
            }
            ChoiceChip(stringResource(R.string.theme_light), settings.themeMode == "light") {
                scope.launch { Store.setTheme(context, "light") }
            }
            ChoiceChip(stringResource(R.string.theme_dark), settings.themeMode == "dark") {
                scope.launch { Store.setTheme(context, "dark") }
            }
        }

        Spacer(Modifier.height(8.dp))
        Text(
            stringResource(R.string.font_size) + "  (${settings.fontSize.toInt()})",
            style = MaterialTheme.typography.titleSmall
        )
        Slider(
            value = settings.fontSize,
            onValueChange = { scope.launch { Store.setFontSize(context, it) } },
            valueRange = 14f..30f,
            steps = 15
        )
        SwitchRow(stringResource(R.string.font_serif), settings.serifFont) {
            scope.launch { Store.setSerif(context, it) }
        }

        HorizontalDivider(Modifier.padding(vertical = 12.dp))

        /* ---- Reading / translations ---- */
        SectionHeader(stringResource(R.string.settings_reading))

        Text(stringResource(R.string.primary_translation), style = MaterialTheme.typography.titleSmall)
        Column {
            BibleRepo.ordered().forEach { t ->
                ChoiceChip(t.label, settings.primaryId == t.id) {
                    scope.launch { Store.setPrimary(context, t.id) }
                }
            }
        }

        Spacer(Modifier.height(8.dp))
        SectionHeader(stringResource(R.string.compare))
        Text(
            stringResource(R.string.compare_note),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Column {
            val enabled = settings.compareIds
            BibleRepo.ordered().forEach { t ->
                ChoiceChip(t.label, enabled.isEmpty() || t.id in enabled) {
                    scope.launch { Store.toggleCompareId(context, t.id) }
                }
            }
        }

        Spacer(Modifier.height(8.dp))
        SwitchRow(stringResource(R.string.keep_screen_on), settings.keepScreenOn) {
            scope.launch { Store.setKeepScreenOn(context, it) }
        }

        Spacer(Modifier.height(8.dp))
        VoicePicker(settings)

        Text(
            stringResource(R.string.speech_rate) + "  —  " +
                    String.format(Locale.US, "%.1f×", settings.speechRate),
            style = MaterialTheme.typography.bodyLarge
        )
        Slider(
            value = settings.speechRate,
            onValueChange = { scope.launch { Store.setSpeechRate(context, it) } },
            valueRange = 0.5f..2f,
            steps = 5
        )
        SwitchRow(stringResource(R.string.auto_continue), settings.autoContinue) {
            scope.launch { Store.setAutoContinue(context, it) }
        }

        SwitchRow(stringResource(R.string.music_title), settings.musicEnabled) {
            scope.launch { Store.setMusicEnabled(context, it) }
        }
        if (settings.musicEnabled) {
            Text(
                stringResource(R.string.music_volume),
                style = MaterialTheme.typography.labelMedium
            )
            Slider(
                value = settings.musicVolume,
                onValueChange = { scope.launch { Store.setMusicVolume(context, it) } },
                valueRange = 0.1f..1f
            )
        }

        Spacer(Modifier.height(8.dp))
        SwitchRow(stringResource(R.string.audio_title), settings.audioNarration) {
            scope.launch { Store.setAudioNarration(context, it) }
        }
        Text(
            stringResource(R.string.audio_note),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        if (settings.audioNarration) {
            var audioBytes by remember { mutableStateOf(0L) }
            LaunchedEffect(Unit) {
                audioBytes = withContext(Dispatchers.IO) { AudioRepo.downloadedBytes(context) }
            }
            if (audioBytes > 0) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        stringResource(R.string.audio_storage, audioBytes / 1048576),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.weight(1f)
                    )
                    TextButton(onClick = {
                        scope.launch {
                            withContext(Dispatchers.IO) { AudioRepo.clearDownloads(context) }
                            audioBytes = 0L
                        }
                    }) { Text(stringResource(R.string.audio_clear)) }
                }
            }
        }

        Spacer(Modifier.height(8.dp))
        SwitchRow(stringResource(R.string.strongs_title), settings.showStrongs) {
            scope.launch { Store.setShowStrongs(context, it) }
        }
        Text(
            stringResource(R.string.strongs_note),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(Modifier.height(8.dp))
        SwitchRow(stringResource(R.string.dict_title), settings.showDictionary) {
            scope.launch { Store.setShowDictionary(context, it) }
        }
        Text(
            stringResource(R.string.dict_note),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(Modifier.height(8.dp))
        SwitchRow(stringResource(R.string.red_letters_title), settings.redLetters) {
            scope.launch { Store.setRedLetters(context, it) }
        }
        SwitchRow(stringResource(R.string.immersive_title), settings.hideVerseNumbers) {
            scope.launch { Store.setHideVerseNumbers(context, it) }
        }

        Spacer(Modifier.height(8.dp))
        SwitchRow(stringResource(R.string.show_apocrypha), settings.showApocrypha) {
            scope.launch { Store.setShowApocrypha(context, it) }
        }
        Text(
            stringResource(R.string.show_apocrypha_note),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(Modifier.height(8.dp))
        SwitchRow(stringResource(R.string.split_view), settings.splitEnabled) {
            scope.launch { Store.setSplit(context, it) }
        }

        if (settings.splitEnabled) {
            Text(stringResource(R.string.secondary_translation), style = MaterialTheme.typography.titleSmall)
            Column {
                BibleRepo.ordered().forEach { t ->
                    ChoiceChip(t.label, settings.secondaryId == t.id) {
                        scope.launch { Store.setSecondary(context, t.id) }
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
            Text(stringResource(R.string.split_orientation), style = MaterialTheme.typography.titleSmall)
            Row(Modifier.padding(vertical = 4.dp)) {
                ChoiceChip(stringResource(R.string.split_horizontal), settings.splitHorizontal) {
                    scope.launch { Store.setSplitHorizontal(context, true) }
                }
                ChoiceChip(stringResource(R.string.split_vertical), !settings.splitHorizontal) {
                    scope.launch { Store.setSplitHorizontal(context, false) }
                }
            }
        }

        HorizontalDivider(Modifier.padding(vertical = 12.dp))

        /* ---- Daily reminder ---- */
        SectionHeader(stringResource(R.string.settings_reminder))

        SwitchRow(stringResource(R.string.reminder_enable), settings.reminderEnabled) { enable ->
            if (enable) {
                val needPermission = Build.VERSION.SDK_INT >= 33 &&
                        ContextCompat.checkSelfPermission(
                            context, Manifest.permission.POST_NOTIFICATIONS
                        ) != PackageManager.PERMISSION_GRANTED
                if (needPermission) {
                    notifPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
                } else {
                    scope.launch {
                        Store.setReminderEnabled(context, true)
                        Reminders.schedule(context, settings.reminderHour, settings.reminderMinute)
                    }
                }
            } else {
                scope.launch {
                    Store.setReminderEnabled(context, false)
                    Reminders.cancel(context)
                }
            }
        }

        if (settings.reminderEnabled) {
            Text(
                stringResource(R.string.reminder_time) + "  —  " +
                        String.format(Locale.US, "%02d:%02d", settings.reminderHour, settings.reminderMinute),
                style = MaterialTheme.typography.titleSmall
            )
            Text(stringResource(R.string.reminder_hour), style = MaterialTheme.typography.labelMedium)
            Slider(
                value = settings.reminderHour.toFloat(),
                onValueChange = {
                    scope.launch {
                        Store.setReminderTime(context, it.toInt(), settings.reminderMinute)
                        Reminders.schedule(context, it.toInt(), settings.reminderMinute)
                    }
                },
                valueRange = 0f..23f,
                steps = 22
            )
            Text(stringResource(R.string.reminder_minute), style = MaterialTheme.typography.labelMedium)
            Slider(
                value = settings.reminderMinute.toFloat(),
                onValueChange = {
                    scope.launch {
                        Store.setReminderTime(context, settings.reminderHour, it.toInt())
                        Reminders.schedule(context, settings.reminderHour, it.toInt())
                    }
                },
                valueRange = 0f..55f,
                steps = 10
            )
        }
        HorizontalDivider(Modifier.padding(vertical = 12.dp))

        /* ---- Share the app: QR + link to the landing page listing every
           way to get Hexapla. The page is updated as stores go live, so
           printed/shared codes never go stale. ---- */
        SectionHeader(stringResource(R.string.share_app_title))
        Text(
            stringResource(R.string.share_app_note),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        var showQr by remember { mutableStateOf(false) }
        Row {
            TextButton(onClick = { showQr = true }) {
                Text(stringResource(R.string.share_app_qr))
            }
            TextButton(onClick = {
                val send = android.content.Intent(android.content.Intent.ACTION_SEND).apply {
                    type = "text/plain"
                    putExtra(android.content.Intent.EXTRA_TEXT, APP_LINK)
                }
                context.startActivity(
                    android.content.Intent.createChooser(send, null)
                )
            }) {
                Text(stringResource(R.string.share_app_link))
            }
        }
        if (showQr) {
            val qr = remember { qrBitmap(APP_LINK, 720) }
            androidx.compose.material3.AlertDialog(
                onDismissRequest = { showQr = false },
                title = { Text(stringResource(R.string.share_app_title)) },
                text = {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        qr?.let {
                            androidx.compose.foundation.Image(
                                bitmap = it.asImageBitmap(),
                                contentDescription = APP_LINK,
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                        Spacer(Modifier.height(8.dp))
                        Text(APP_LINK, style = MaterialTheme.typography.bodySmall)
                    }
                },
                confirmButton = {
                    TextButton(onClick = { showQr = false }) {
                        Text(stringResource(R.string.cancel))
                    }
                }
            )
        }
        HorizontalDivider(Modifier.padding(vertical = 12.dp))

        /* ---- Backup: notes, bookmarks and plan progress as a JSON file. ---- */
        SectionHeader(stringResource(R.string.backup_title))
        val exportLauncher = rememberLauncherForActivityResult(
            ActivityResultContracts.CreateDocument("application/json")
        ) { uri ->
            if (uri != null) scope.launch {
                val ok = try {
                    val json = Store.exportJson(context)
                    context.contentResolver.openOutputStream(uri)?.use {
                        it.write(json.toByteArray())
                    } != null
                } catch (_: Exception) { false }
                android.widget.Toast.makeText(
                    context,
                    if (ok) R.string.backup_saved else R.string.backup_failed,
                    android.widget.Toast.LENGTH_SHORT
                ).show()
            }
        }
        val importLauncher = rememberLauncherForActivityResult(
            ActivityResultContracts.OpenDocument()
        ) { uri ->
            if (uri != null) scope.launch {
                val ok = try {
                    context.contentResolver.openInputStream(uri)
                        ?.use { it.readBytes().decodeToString() }
                        ?.let { Store.importJson(context, it) } == true
                } catch (_: Exception) { false }
                android.widget.Toast.makeText(
                    context,
                    if (ok) R.string.restore_done else R.string.backup_failed,
                    android.widget.Toast.LENGTH_SHORT
                ).show()
            }
        }
        Row {
            TextButton(onClick = { exportLauncher.launch("hexapla-backup.json") }) {
                Text(stringResource(R.string.backup_export))
            }
            TextButton(onClick = { importLauncher.launch(arrayOf("application/json")) }) {
                Text(stringResource(R.string.backup_import))
            }
        }
        HorizontalDivider(Modifier.padding(vertical = 12.dp))

        /* ---- Voluntary support: no features gated, purely a thank-you.
           Google Play build: consumable Play Billing tips (policy-compliant).
           No Play services (APK / RuStore / de-Googled): external links. ---- */
        SectionHeader(stringResource(R.string.support_title))
        Text(
            stringResource(R.string.support_note),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(bottom = 8.dp)
        )

        val tipManager = remember { TipManager(context) }
        DisposableEffect(Unit) {
            tipManager.connect()
            onDispose { tipManager.release() }
        }

        if (tipManager.available.value) {
            // Play services present: only ever offer Play Billing tips here.
            // External links on a Play build would violate payments policy,
            // so an empty product list simply shows nothing.
            Row {
                tipManager.products.value.forEach { product ->
                    val price = product.oneTimePurchaseOfferDetails?.formattedPrice ?: ""
                    ChoiceChip(price, selected = false) {
                        (context as? android.app.Activity)?.let { tipManager.tip(it, product) }
                    }
                }
            }
        } else if (BuildConfig.EXTERNAL_DONATIONS) {
            Row {
                Donation.links.forEach { (label, url) ->
                    ChoiceChip(label, selected = false) {
                        try {
                            context.startActivity(
                                android.content.Intent(
                                    android.content.Intent.ACTION_VIEW,
                                    android.net.Uri.parse(url)
                                )
                            )
                        } catch (_: Exception) {
                            // No browser available; ignore.
                        }
                    }
                }
            }
        }
        HorizontalDivider(Modifier.padding(vertical = 12.dp))

        /* ---- Attribution (CC-BY requirement for cross-references) ---- */
        SectionHeader(stringResource(R.string.sources_title))
        Text(
            stringResource(R.string.sources_text),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(32.dp))
    }
}

@Composable
private fun SectionHeader(text: String) {
    Text(
        text,
        style = MaterialTheme.typography.labelLarge,
        color = MaterialTheme.colorScheme.primary,
        modifier = Modifier.padding(bottom = 8.dp)
    )
}

@Composable
private fun SwitchRow(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, Modifier.weight(1f), style = MaterialTheme.typography.bodyLarge)
        Switch(checked = checked, onCheckedChange = onChange)
    }
}

@Composable
private fun ChoiceChip(label: String, selected: Boolean, onClick: () -> Unit) {
    FilterChip(
        selected = selected,
        onClick = onClick,
        label = { Text(label) },
        modifier = Modifier.padding(end = 8.dp)
    )
}


@Composable
private fun VoicePicker(settings: AppSettings) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val voicePrefs by Store.voicePrefs(context)
        .collectAsState(initial = emptyMap<String, String>())
    var showDialog by remember { mutableStateOf(false) }

    val locale = BibleRepo.translation(settings.primaryId).locale
    val lang = locale.language
    val selected = voicePrefs[lang]

    Row(
        Modifier.fillMaxWidth().padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(Modifier.weight(1f)) {
            Text(stringResource(R.string.voice_title), style = MaterialTheme.typography.bodyLarge)
            Text(
                selected?.let { voiceLabel(it) } ?: stringResource(R.string.voice_default),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        TextButton(onClick = { showDialog = true }) {
            Text(stringResource(R.string.voice_title))
        }
    }

    if (showDialog) {
        val reader = remember { ChapterReader(context) }
        DisposableEffect(Unit) { onDispose { reader.release() } }
        val sample = when (lang) {
            "ru" -> "В начале было Слово, и Слово было у Бога."
            "el" -> "Ἐν ἀρχῇ ἦν ὁ Λόγος, καὶ ὁ Λόγος ἦν πρὸς τὸν Θεόν."
            "he" -> "בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם"
            "fr" -> "Au commencement était la Parole, et la Parole était avec Dieu."
            "de" -> "Im Anfang war das Wort, und das Wort war bei Gott."
            "es" -> "En el principio era el Verbo, y el Verbo era con Dios."
            else -> "In the beginning was the Word, and the Word was with God."
        }
        androidx.compose.material3.AlertDialog(
            onDismissRequest = { reader.stop(); showDialog = false },
            title = { Text(stringResource(R.string.voice_title)) },
            text = {
                Column(
                    Modifier.verticalScroll(rememberScrollState())
                ) {
                    Text(
                        stringResource(R.string.voice_note),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(bottom = 8.dp)
                    )
                    if (!reader.ready.value) {
                        Text("…", modifier = Modifier.padding(8.dp))
                    } else {
                        TextButton(
                            onClick = {
                                scope.launch { Store.setVoicePref(context, lang, null) }
                                reader.preview(sample, locale, null)
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                (if (selected == null) "✓  " else "") +
                                        stringResource(R.string.voice_default)
                            )
                        }
                        val voices = reader.voicesFor(locale)
                        val baseLabels = voices.map { voiceLabel(it.name) }
                        val dupCounts = baseLabels.groupingBy { it }.eachCount()
                        val running = mutableMapOf<String, Int>()
                        voices.forEachIndexed { i, v ->
                            val base = baseLabels[i]
                            val label = if ((dupCounts[base] ?: 0) > 1) {
                                val n = (running[base] ?: 0) + 1
                                running[base] = n
                                "$base $n"
                            } else base
                            TextButton(
                                onClick = {
                                    scope.launch { Store.setVoicePref(context, lang, v.name) }
                                    reader.preview(sample, locale, v.name)
                                },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                val online = if (v.isNetworkConnectionRequired)
                                    " · " + stringResource(R.string.voice_online) else ""
                                Text(
                                    (if (selected == v.name) "✓  " else "") + label + online,
                                    maxLines = 1
                                )
                            }
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { reader.stop(); showDialog = false }) {
                    Text(stringResource(R.string.save))
                }
            }
        )
    }
}
