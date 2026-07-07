package com.aleks.hexapla

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import androidx.compose.runtime.mutableStateOf
import java.util.Locale

/**
 * Reads a chapter aloud using the device TTS engine.
 * Language follows the selected translation (English or Russian voice).
 */
class ChapterReader(context: Context) {

    val isSpeaking = mutableStateOf(false)
    val currentVerse = mutableStateOf(-1)
    val ready = mutableStateOf(false)

    private var tts: TextToSpeech? = null

    init {
        tts = TextToSpeech(context.applicationContext) { status ->
            ready.value = status == TextToSpeech.SUCCESS
            if (ready.value) {
                tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(utteranceId: String?) {
                        currentVerse.value = utteranceId?.toIntOrNull() ?: -1
                    }
                    override fun onDone(utteranceId: String?) {
                        if (utteranceId == LAST_ID) {
                            isSpeaking.value = false
                            currentVerse.value = -1
                        }
                    }
                    @Deprecated("Deprecated in Java")
                    override fun onError(utteranceId: String?) {
                        isSpeaking.value = false
                        currentVerse.value = -1
                    }
                })
            }
        }
    }

    /**
     * A short, curated list of voices for the given language. Voices that are not
     * downloaded are dropped, local/online twins are collapsed (online-only voices
     * silently fall back to the default voice without a connection), English is
     * limited to US/British/Australian regions, and where the engine's naming
     * convention reveals gender only one voice per region and gender is kept.
     */
    fun voicesFor(locale: Locale): List<android.speech.tts.Voice> =
        try {
            val usable = tts?.voices?.filter {
                it.locale.language == locale.language &&
                    !it.features.contains(TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED)
            } ?: emptyList()
            val collapsed = usable
                .groupBy { it.name.removeSuffix("-local").removeSuffix("-network") }
                .map { (_, twins) -> twins.firstOrNull { !it.isNetworkConnectionRequired } ?: twins.first() }
                .filter { locale.language != "en" || it.locale.country in EN_COUNTRIES }
            // Engines also register a generic "xx-XX-language" entry that is just the
            // default voice again; drop it when a specific voice exists so languages
            // with a single voice (e.g. Greek) don't show the same voice twice.
            val deduped = collapsed
                .filter { !it.name.endsWith("-language") }
                .ifEmpty { collapsed }
                .sortedWith(compareBy({ it.isNetworkConnectionRequired }, { it.name }))
            // Single-region languages get a few voices per gender for variety;
            // multi-region ones (English) stay at one per region and gender.
            val perGender = if (deduped.map { it.locale.country }.distinct().size > 1) 1 else 3
            deduped
                .groupBy { it.locale.country }
                .toList()
                .sortedBy { (country, _) -> EN_COUNTRIES.indexOf(country).let { if (it < 0) EN_COUNTRIES.size else it } }
                .flatMap { (_, group) ->
                    val female = group.filter { voiceGender(it.name) == true }.take(perGender)
                    val male = group.filter { voiceGender(it.name) == false }.take(perGender)
                    if (female.isNotEmpty() || male.isNotEmpty()) female + male
                    else group.take(3)
                }
        } catch (_: Exception) { emptyList() }

    private fun applyVoice(engine: TextToSpeech, locale: Locale, voiceName: String?): Boolean {
        val result = engine.setLanguage(locale)
        if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
            return false
        }
        if (voiceName != null) {
            try {
                engine.voices?.firstOrNull { it.name == voiceName }?.let { engine.voice = it }
            } catch (_: Exception) { /* keep language default */ }
        }
        return true
    }

    /** Speak a short sample with the given voice (for the voice picker). */
    fun preview(text: String, locale: Locale, voiceName: String?): Boolean {
        val engine = tts ?: return false
        if (!applyVoice(engine, locale, voiceName)) return false
        engine.stop()
        engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, LAST_ID)
        return true
    }

    /** Returns false if the TTS language is unavailable. */
    fun speakChapter(
        verses: List<String>,
        locale: Locale,
        voiceName: String? = null,
        startVerse: Int = 0
    ): Boolean {
        val engine = tts ?: return false
        if (!applyVoice(engine, locale, voiceName)) return false
        engine.stop()
        isSpeaking.value = true
        var queued = false
        for (i in startVerse until verses.size) {
            val isLast = i == verses.size - 1
            val id = if (isLast) LAST_ID else i.toString()
            engine.speak(
                verses[i],
                if (queued) TextToSpeech.QUEUE_ADD else TextToSpeech.QUEUE_FLUSH,
                null,
                id
            )
            queued = true
        }
        return true
    }

    fun stop() {
        tts?.stop()
        isSpeaking.value = false
        currentVerse.value = -1
    }

    fun release() {
        tts?.stop()
        tts?.shutdown()
        tts = null
    }

    companion object {
        private const val LAST_ID = "LAST"
    }
}

/** English regions offered in the voice picker, in display order. */
private val EN_COUNTRIES = listOf("US", "GB", "AU")

/**
 * Best-effort gender from voice naming conventions: explicit "#female_1"-style
 * tokens, else the trailing letter of Google's three-letter variant codes
 * (ruf = female, rud = male). Null when the name reveals nothing.
 */
fun voiceGender(name: String): Boolean? {
    val n = name.lowercase(Locale.ROOT)
    if ("female" in n) return true
    if ("male" in n) return false
    val variant = n.removeSuffix("-local").removeSuffix("-network")
        .split('-').lastOrNull() ?: return null
    // Google's "io*" voices don't follow the trailing-letter convention
    // (iob sounds female despite the nominally male "b").
    if (variant.length == 3 && variant != n && !variant.startsWith("io")) {
        when (variant.last()) {
            'a', 'c', 'e', 'f', 'g' -> return true
            'b', 'd', 'm' -> return false
        }
    }
    return null
}

/**
 * Human-readable label for an engine voice id such as "ru-ru-x-ruf-network" →
 * "Russian (Russia) · RUF". Falls back to the raw id when it doesn't follow the
 * locale-prefixed convention (some engines use opaque names).
 */
fun voiceDisplayName(name: String, includeVariant: Boolean = true): String {
    val parts = name.split('-')
    if (parts.size >= 2 && parts[1].length == 2) {
        val loc = Locale.forLanguageTag("${parts[0]}-${parts[1].uppercase(Locale.ROOT)}")
        val lang = loc.displayLanguage
        if (lang.isNotEmpty() && !lang.equals(parts[0], ignoreCase = true)) {
            val variant = parts.drop(2)
                .filterNot { it == "x" || it == "local" || it == "network" }
                .joinToString(" ") { it.uppercase(Locale.ROOT) }
            return buildString {
                append(lang.replaceFirstChar { it.titlecase() })
                if (loc.displayCountry.isNotEmpty()) append(" (").append(loc.displayCountry).append(")")
                if (includeVariant && variant.isNotEmpty()) append(" · ").append(variant)
            }
        }
    }
    return name
}
