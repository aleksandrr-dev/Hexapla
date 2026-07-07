package com.aleks.hexapla

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.floatPreferencesKey
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

val Context.dataStore by preferencesDataStore("settings")

data class Bookmark(val translationId: String, val book: Int, val chapter: Int, val verse: Int) {
    fun encode() = "$translationId|$book|$chapter|$verse"
    companion object {
        fun decode(s: String): Bookmark? {
            val p = s.split("|")
            return if (p.size == 4) Bookmark(p[0], p[1].toIntOrNull() ?: return null,
                p[2].toIntOrNull() ?: return null, p[3].toIntOrNull() ?: return null) else null
        }
    }
}

data class AppSettings(
    val themeMode: String = "system",          // system | light | dark
    val fontSize: Float = 18f,
    val serifFont: Boolean = true,
    val splitEnabled: Boolean = false,
    val splitHorizontal: Boolean = true,       // true = side by side, false = stacked
    val showApocrypha: Boolean = false,
    val keepScreenOn: Boolean = false,
    val primaryId: String = BibleRepo.defaultPrimaryId(),
    val secondaryId: String = BibleRepo.defaultSecondaryId(),
    val reminderEnabled: Boolean = false,
    val reminderHour: Int = 8,
    val reminderMinute: Int = 0,
    val lastBook: Int = 0,
    val lastChapter: Int = 0,
    val lastVerse: Int = 0,
    val speechRate: Float = 1f,
    val autoContinue: Boolean = true,
    val compareIds: Set<String> = emptySet(),  // empty = compare all translations
    val showStrongs: Boolean = false,
    val audioNarration: Boolean = false,
    val streak: Int = 0,
    val redLetters: Boolean = true,
    val hideVerseNumbers: Boolean = false,
    // Defaults to true so existing sessions don't flash the welcome screen
    // while DataStore loads; the stored value decides for real.
    val welcomeSeen: Boolean = true
)

object Store {
    private val THEME = stringPreferencesKey("theme")
    private val FONT_SIZE = floatPreferencesKey("font_size")
    private val SERIF = booleanPreferencesKey("serif")
    private val SPLIT = booleanPreferencesKey("split")
    private val SPLIT_H = booleanPreferencesKey("split_h")
    private val APOC = booleanPreferencesKey("apocrypha")
    private val KEEP_ON = booleanPreferencesKey("keep_on")
    private val NOTES = stringPreferencesKey("notes")
    private val VOICES = stringPreferencesKey("voices")
    private val PRIMARY = stringPreferencesKey("primary")
    private val SECONDARY = stringPreferencesKey("secondary")
    private val REM_ON = booleanPreferencesKey("rem_on")
    private val REM_H = intPreferencesKey("rem_h")
    private val REM_M = intPreferencesKey("rem_m")
    private val LAST_BOOK = intPreferencesKey("last_book")
    private val LAST_CH = intPreferencesKey("last_ch")
    private val LAST_VERSE = intPreferencesKey("last_verse")
    private val SPEECH_RATE = floatPreferencesKey("speech_rate")
    private val AUTO_CONT = booleanPreferencesKey("auto_continue")
    private val COMPARE_IDS = stringSetPreferencesKey("compare_ids")
    private val SHOW_STRONGS = booleanPreferencesKey("show_strongs")
    private val AUDIO_NARR = booleanPreferencesKey("audio_narration")
    private val STREAK = intPreferencesKey("streak")
    private val STREAK_DAY = longPreferencesKey("streak_day")
    private val HIGHLIGHTS = stringPreferencesKey("highlights")
    private val RED_LETTERS = booleanPreferencesKey("red_letters")
    private val HIDE_NUMBERS = booleanPreferencesKey("hide_numbers")
    private val WELCOME_SEEN = booleanPreferencesKey("welcome_seen")
    private val BOOKMARKS = stringSetPreferencesKey("bookmarks")

    fun settings(context: Context): Flow<AppSettings> = context.dataStore.data.map { p ->
        AppSettings(
            themeMode = p[THEME] ?: "system",
            fontSize = p[FONT_SIZE] ?: 18f,
            serifFont = p[SERIF] ?: true,
            splitEnabled = p[SPLIT] ?: false,
            splitHorizontal = p[SPLIT_H] ?: true,
            showApocrypha = p[APOC] ?: false,
            keepScreenOn = p[KEEP_ON] ?: false,
            primaryId = p[PRIMARY] ?: BibleRepo.defaultPrimaryId(),
            secondaryId = p[SECONDARY] ?: BibleRepo.defaultSecondaryId(),
            reminderEnabled = p[REM_ON] ?: false,
            reminderHour = p[REM_H] ?: 8,
            reminderMinute = p[REM_M] ?: 0,
            lastBook = p[LAST_BOOK] ?: 0,
            lastChapter = p[LAST_CH] ?: 0,
            lastVerse = p[LAST_VERSE] ?: 0,
            speechRate = p[SPEECH_RATE] ?: 1f,
            autoContinue = p[AUTO_CONT] ?: true,
            compareIds = p[COMPARE_IDS] ?: emptySet(),
            showStrongs = p[SHOW_STRONGS] ?: false,
            audioNarration = p[AUDIO_NARR] ?: false,
            streak = p[STREAK] ?: 0,
            redLetters = p[RED_LETTERS] ?: true,
            hideVerseNumbers = p[HIDE_NUMBERS] ?: false,
            welcomeSeen = p[WELCOME_SEEN] ?: false
        )
    }

    suspend fun setTheme(c: Context, v: String) = c.dataStore.edit { it[THEME] = v }
    suspend fun setFontSize(c: Context, v: Float) = c.dataStore.edit { it[FONT_SIZE] = v }
    suspend fun setSerif(c: Context, v: Boolean) = c.dataStore.edit { it[SERIF] = v }
    suspend fun setSplit(c: Context, v: Boolean) = c.dataStore.edit { it[SPLIT] = v }
    suspend fun setSplitHorizontal(c: Context, v: Boolean) = c.dataStore.edit { it[SPLIT_H] = v }
    suspend fun setShowApocrypha(c: Context, v: Boolean) = c.dataStore.edit { it[APOC] = v }
    suspend fun setKeepScreenOn(c: Context, v: Boolean) = c.dataStore.edit { it[KEEP_ON] = v }

    /* Personal verse notes, keyed "book:chapter:verse", stored as one JSON object. */
    fun notes(c: Context): Flow<Map<String, String>> = c.dataStore.data.map { p ->
        val raw = p[NOTES] ?: return@map emptyMap()
        try {
            val o = org.json.JSONObject(raw)
            o.keys().asSequence().associateWith { k -> o.getString(k) }
        } catch (_: Exception) { emptyMap() }
    }

    /* Preferred TTS voice per language, e.g. {"ru": "ru-ru-x-...", "en": "..."}. */
    fun voicePrefs(c: Context): Flow<Map<String, String>> = c.dataStore.data.map { p ->
        val raw = p[VOICES] ?: return@map emptyMap()
        try {
            val o = org.json.JSONObject(raw)
            o.keys().asSequence().associateWith { k -> o.getString(k) }
        } catch (_: Exception) { emptyMap() }
    }

    suspend fun setVoicePref(c: Context, lang: String, voiceName: String?) =
        c.dataStore.edit { p ->
            val o = try { org.json.JSONObject(p[VOICES] ?: "{}") } catch (_: Exception) { org.json.JSONObject() }
            if (voiceName == null) o.remove(lang) else o.put(lang, voiceName)
            p[VOICES] = o.toString()
        }

    suspend fun setNote(c: Context, book: Int, chapter: Int, verse: Int, text: String) =
        c.dataStore.edit { p ->
            val o = try { org.json.JSONObject(p[NOTES] ?: "{}") } catch (_: Exception) { org.json.JSONObject() }
            val key = "$book:$chapter:$verse"
            if (text.isBlank()) o.remove(key) else o.put(key, text.trim())
            p[NOTES] = o.toString()
        }
    suspend fun setPrimary(c: Context, v: String) = c.dataStore.edit { it[PRIMARY] = v }
    suspend fun setSecondary(c: Context, v: String) = c.dataStore.edit { it[SECONDARY] = v }
    suspend fun setReminderEnabled(c: Context, v: Boolean) = c.dataStore.edit { it[REM_ON] = v }
    suspend fun setReminderTime(c: Context, h: Int, m: Int) =
        c.dataStore.edit { it[REM_H] = h; it[REM_M] = m }
    suspend fun setLastPosition(c: Context, book: Int, chapter: Int) =
        c.dataStore.edit { it[LAST_BOOK] = book; it[LAST_CH] = chapter }
    suspend fun setLastVerse(c: Context, verse: Int) =
        c.dataStore.edit { it[LAST_VERSE] = verse }
    suspend fun setSpeechRate(c: Context, v: Float) = c.dataStore.edit { it[SPEECH_RATE] = v }
    suspend fun setAutoContinue(c: Context, v: Boolean) = c.dataStore.edit { it[AUTO_CONT] = v }
    suspend fun setShowStrongs(c: Context, v: Boolean) = c.dataStore.edit { it[SHOW_STRONGS] = v }
    suspend fun setAudioNarration(c: Context, v: Boolean) = c.dataStore.edit { it[AUDIO_NARR] = v }
    suspend fun setRedLetters(c: Context, v: Boolean) = c.dataStore.edit { it[RED_LETTERS] = v }
    suspend fun setHideVerseNumbers(c: Context, v: Boolean) = c.dataStore.edit { it[HIDE_NUMBERS] = v }
    suspend fun setWelcomeSeen(c: Context) = c.dataStore.edit { it[WELCOME_SEEN] = true }

    /** Bumps the daily reading streak; call once per app open. */
    suspend fun touchStreak(c: Context) = c.dataStore.edit { p ->
        val today = java.time.LocalDate.now().toEpochDay()
        val last = p[STREAK_DAY] ?: 0L
        val cur = p[STREAK] ?: 0
        p[STREAK] = when (today) {
            last -> cur.coerceAtLeast(1)
            last + 1 -> cur + 1
            else -> 1
        }
        p[STREAK_DAY] = today
    }

    /* Verse highlights, keyed "book:chapter:verse" -> color index (0-3). */
    fun highlights(c: Context): Flow<Map<String, Int>> = c.dataStore.data.map { p ->
        val raw = p[HIGHLIGHTS] ?: return@map emptyMap()
        try {
            val o = org.json.JSONObject(raw)
            o.keys().asSequence().associateWith { k -> o.getInt(k) }
        } catch (_: Exception) { emptyMap() }
    }

    suspend fun setHighlight(c: Context, book: Int, chapter: Int, verse: Int, color: Int?) =
        c.dataStore.edit { p ->
            val o = try { org.json.JSONObject(p[HIGHLIGHTS] ?: "{}") } catch (_: Exception) { org.json.JSONObject() }
            val key = "$book:$chapter:$verse"
            if (color == null) o.remove(key) else o.put(key, color)
            p[HIGHLIGHTS] = o.toString()
        }
    suspend fun toggleCompareId(c: Context, id: String) = c.dataStore.edit { p ->
        val all = BibleRepo.translations.map { it.id }.toSet()
        // An empty stored set means "all"; materialize it before toggling one off.
        val cur = (p[COMPARE_IDS] ?: emptySet()).ifEmpty { all }.toMutableSet()
        if (cur.contains(id)) cur.remove(id) else cur.add(id)
        p[COMPARE_IDS] = if (cur == all) emptySet() else cur
    }

    fun bookmarks(c: Context): Flow<List<Bookmark>> = c.dataStore.data.map { p ->
        (p[BOOKMARKS] ?: emptySet()).mapNotNull { Bookmark.decode(it) }
            .sortedWith(compareBy({ it.book }, { it.chapter }, { it.verse }))
    }

    suspend fun toggleBookmark(c: Context, b: Bookmark): Boolean {
        var added = false
        c.dataStore.edit { p ->
            val set = (p[BOOKMARKS] ?: emptySet()).toMutableSet()
            val enc = b.encode()
            if (set.contains(enc)) set.remove(enc) else { set.add(enc); added = true }
            p[BOOKMARKS] = set
        }
        return added
    }

    suspend fun removeBookmark(c: Context, b: Bookmark) = c.dataStore.edit { p ->
        p[BOOKMARKS] = (p[BOOKMARKS] ?: emptySet()).toMutableSet().apply { remove(b.encode()) }
    }

    /* Plan progress: one string-set key per plan, values are day numbers */
    private fun planKey(planId: String) = stringSetPreferencesKey("plan_$planId")

    fun planProgress(c: Context, planId: String): Flow<Set<Int>> = c.dataStore.data.map { p ->
        (p[planKey(planId)] ?: emptySet()).mapNotNull { it.toIntOrNull() }.toSet()
    }

    suspend fun togglePlanDay(c: Context, planId: String, day: Int) = c.dataStore.edit { p ->
        val k = planKey(planId)
        val set = (p[k] ?: emptySet()).toMutableSet()
        val s = day.toString()
        if (set.contains(s)) set.remove(s) else set.add(s)
        p[k] = set
    }

    suspend fun resetPlan(c: Context, planId: String) = c.dataStore.edit { p ->
        p[planKey(planId)] = emptySet()
    }

    suspend fun currentSettings(c: Context): AppSettings = settings(c).first()

    /* ---- Backup: personal data (notes, bookmarks, plan progress, voices)
       as a single JSON document. Import merges rather than replaces, so
       restoring on a phone that already has data loses nothing. ---- */

    suspend fun exportJson(c: Context): String {
        val p = c.dataStore.data.first()
        val o = org.json.JSONObject()
        o.put("version", 1)
        o.put("notes", org.json.JSONObject(p[NOTES] ?: "{}"))
        o.put("voices", org.json.JSONObject(p[VOICES] ?: "{}"))
        o.put("highlights", org.json.JSONObject(p[HIGHLIGHTS] ?: "{}"))
        o.put("bookmarks", org.json.JSONArray((p[BOOKMARKS] ?: emptySet()).toList()))
        val plans = org.json.JSONObject()
        p.asMap().keys.map { it.name }.filter { it.startsWith("plan_") }.forEach { name ->
            val days = p[stringSetPreferencesKey(name)] ?: emptySet()
            plans.put(name.removePrefix("plan_"), org.json.JSONArray(days.toList()))
        }
        o.put("plans", plans)
        return o.toString(2)
    }

    suspend fun importJson(c: Context, json: String): Boolean = try {
        val o = org.json.JSONObject(json)
        c.dataStore.edit { p ->
            o.optJSONObject("notes")?.let { incoming ->
                val merged = try { org.json.JSONObject(p[NOTES] ?: "{}") } catch (_: Exception) { org.json.JSONObject() }
                incoming.keys().forEach { k -> merged.put(k, incoming.getString(k)) }
                p[NOTES] = merged.toString()
            }
            o.optJSONObject("voices")?.let { incoming ->
                val merged = try { org.json.JSONObject(p[VOICES] ?: "{}") } catch (_: Exception) { org.json.JSONObject() }
                incoming.keys().forEach { k -> merged.put(k, incoming.getString(k)) }
                p[VOICES] = merged.toString()
            }
            o.optJSONObject("highlights")?.let { incoming ->
                val merged = try { org.json.JSONObject(p[HIGHLIGHTS] ?: "{}") } catch (_: Exception) { org.json.JSONObject() }
                incoming.keys().forEach { k -> merged.put(k, incoming.getInt(k)) }
                p[HIGHLIGHTS] = merged.toString()
            }
            o.optJSONArray("bookmarks")?.let { arr ->
                val set = (p[BOOKMARKS] ?: emptySet()).toMutableSet()
                for (i in 0 until arr.length()) set.add(arr.getString(i))
                p[BOOKMARKS] = set
            }
            o.optJSONObject("plans")?.let { plans ->
                plans.keys().forEach { id ->
                    val k = planKey(id)
                    val set = (p[k] ?: emptySet()).toMutableSet()
                    val arr = plans.getJSONArray(id)
                    for (i in 0 until arr.length()) set.add(arr.getString(i))
                    p[k] = set
                }
            }
        }
        true
    } catch (_: Exception) { false }
}
