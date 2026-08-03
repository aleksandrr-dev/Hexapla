package com.aleks.hexapla

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

/**
 * Spelling normalization for TEXT-TO-SPEECH ONLY. The reader always shows the
 * original text; this is what the voice is handed.
 *
 * ⚠ WHY THIS EXISTS. Tyndale's orthography keeps a final -e that was already
 * silent by the 1520s, so a device voice says "dee-pee" for "depe", "her-bee"
 * for "herbe" and "lick-ness" for "lycknesse". It also spells "yow" as written
 * and reads ".vij." letter by letter. Measured over the asset, 11% of all
 * tokens were affected — the dominant audio-quality problem for the English
 * sets, and far bigger than any individual glitch.
 *
 * ⚠ The map used to exist ONLY in tools/archaic_english.py, which normalizes
 * text before RENDERING narration to an ogg. So the recorded voice pronounced
 * everything correctly while the app's live TTS still said "yow" and
 * "lickness" — reported by the owner 2026-08-03. The table is now emitted as
 * an asset by tools/build_tyndale_pron.py and applied here, so the two voices
 * agree. Regenerate the asset whenever that table changes.
 *
 * Every entry is corroborated against the KJV parallel verse; see the
 * generator for the method and the traps it guards against.
 */
object Pronounce {

    /** Translation ids that have a map. Others pass through untouched. */
    // ⚠ Geneva and Wycliffe matter as much as Tyndale here: "heauen" occurs
    // 608 times in Geneva and "heuene" 624 times in Wycliffe, and neither was
    // mapped anywhere before 2026-08-03 — which is why the owner heard
    // "heaven" spoken as "hoenn".
    private val ASSETS = mapOf(
        "tyn" to "pron_tyndale.json",
        "gnv" to "pron_gnv.json",
        "wyc" to "pron_wyc.json",
    )

    private val loaded = HashMap<String, Table>()

    private class Table(
        val words: Map<String, String>,
        val roman: Map<String, Int>,
        val phrases: Map<String, String>,
    )

    private val WORD = Regex("[A-Za-z]+")
    // ".vij." — lower-case roman between full stops, as Tyndale prints numbers.
    private val ROMAN_RE = Regex("\\.\\s*([ivxlcdmIVXLCDMj]+)\\s*\\.")

    suspend fun load(context: Context, translationId: String) {
        val asset = ASSETS[translationId] ?: return
        if (loaded.containsKey(translationId)) return
        withContext(Dispatchers.IO) {
            try {
                val root = JSONObject(
                    context.assets.open(asset).bufferedReader().use { it.readText() }
                )
                fun strMap(name: String): Map<String, String> {
                    val o = root.optJSONObject(name) ?: return emptyMap()
                    return buildMap {
                        val keys = o.keys()
                        while (keys.hasNext()) { val k = keys.next(); put(k, o.getString(k)) }
                    }
                }
                val romanObj = root.optJSONObject("roman")
                val roman = buildMap<String, Int> {
                    romanObj?.keys()?.let { keys ->
                        while (keys.hasNext()) { val k = keys.next(); put(k, romanObj.getInt(k)) }
                    }
                }
                loaded[translationId] = Table(strMap("words"), roman, strMap("phrases"))
            } catch (_: Exception) {
                // Never block speech on a missing map — speak the raw text.
            }
        }
    }

    /** Roman numeral value; the trailing "j" is the period's long i (ij = 2). */
    private fun romanValue(s: String): Int? {
        val v = mapOf('i' to 1, 'v' to 5, 'x' to 10, 'l' to 50,
                      'c' to 100, 'd' to 500, 'm' to 1000)
        val t = s.lowercase().replace('j', 'i')
        if (t.isEmpty() || t.any { it !in v }) return null
        var total = 0
        for (i in t.indices) {
            val cur = v[t[i]]!!
            val next = if (i + 1 < t.length) v[t[i + 1]] else null
            total += if (next != null && next > cur) -cur else cur
        }
        return if (total > 0) total else null
    }

    /**
     * Text as it should be SPOKEN. Returns [text] unchanged when the
     * translation has no map, which is every translation but Tyndale today.
     */
    fun forSpeech(translationId: String, text: String): String {
        val t = loaded[translationId] ?: return text
        var s = text

        // Phrases first: "to gedder" is TOGETHER, and "gedder" alone is never
        // "gather" — a word-level map cannot express that.
        for ((from, to) in t.phrases) {
            s = s.replace(Regex("\\b" + Regex.escape(from) + "\\b", RegexOption.IGNORE_CASE), to)
        }
        // ⚠ HYPHENATED PROPER NAMES. Geneva splits them for typesetting —
        // "Nebuchad-nezzar", "Beth-el", "Beer-sheba" — and a voice reads the
        // hyphen as a word break, which is why the owner heard "nebe chad …
        // nazar". 668 such tokens in Geneva, 547 of which join into a real KJV
        // word. Restricted to CAPITALISED tokens so ordinary hyphenated
        // compounds keep their break.
        s = Regex("\\b([A-Z][A-Za-z]*)-([A-Za-z]+)").replace(s) { m ->
            m.groupValues[1] + m.groupValues[2]
        }
        // Roman numerals before words, since the full stops delimiting them
        // would otherwise be treated as sentence ends.
        s = ROMAN_RE.replace(s) { m ->
            romanValue(m.groupValues[1])?.let { " $it " } ?: m.value
        }
        s = WORD.replace(s) { m ->
            val w = m.value
            val repl = t.words[w.lowercase()]
                ?: return@replace earlyModern(w)   // rules catch what the map misses
            when {
                w.all { it.isUpperCase() } && w.length > 1 -> repl.uppercase()
                w.first().isUpperCase() -> repl.replaceFirstChar { c -> c.uppercaseChar() }
                else -> repl
            }
        }
        return s
    }

    private const val VOWELS = "aeiou"

    /**
     * Names where the Early Modern rules below would be WRONG, because the
     * spelling is already modern and the letters are genuine.
     * ⚠ Measured over the Geneva text: the rules fix 44,196 tokens and break
     * exactly these. Do not drop the guard because the list looks trivial —
     * "Deuel" becoming "Devel" is the kind of error nobody reports politely.
     */
    private val RULE_EXCEPTIONS = setOf("deuel", "geuel", "euodias", "iim", "reuel")

    /**
     * The three systematic Early Modern alternations, applied to any word the
     * word-map does not already cover. These are why "heauen" was read as
     * "hoenn", "euel" as "you-ell" and "Iehoiakim" with a hard I.
     *
     *   1. initial I before a vowel is J   — Iesus, Iudah, Iehoiakim
     *   2. u BETWEEN VOWELS is v           — heauen, euel, dauid, loue
     *   3. initial v before a consonant is u — vnto, vs, vp
     *
     * ⚠ Rule 2 is deliberately restricted to INTERVOCALIC u. Widening it would
     * wreck "Samuel", "Bethuel", "Penuel" and every -uel name where the u sits
     * after a consonant. Verified over the whole Geneva vocabulary: 0 cases
     * where a real KJV word is silently swapped for a different real word.
     */
    private fun earlyModern(w: String): String {
        if (w.length < 2 || w.lowercase() in RULE_EXCEPTIONS) return w
        var s = w
        if (s[0].lowercaseChar() == 'i' && s[1].lowercaseChar() in VOWELS) {
            s = (if (s[0].isUpperCase()) "J" else "j") + s.substring(1)
        }
        if (s.length > 2) {
            val b = StringBuilder(s)
            for (i in 1 until s.length - 1) {
                if (s[i].lowercaseChar() == 'u' &&
                    s[i - 1].lowercaseChar() in VOWELS &&
                    s[i + 1].lowercaseChar() in VOWELS
                ) b[i] = if (s[i].isUpperCase()) 'V' else 'v'
            }
            s = b.toString()
        }
        if (s[0].lowercaseChar() == 'v' && s[1].lowercaseChar() !in VOWELS) {
            s = (if (s[0].isUpperCase()) "U" else "u") + s.substring(1)
        }
        return s
    }
}
