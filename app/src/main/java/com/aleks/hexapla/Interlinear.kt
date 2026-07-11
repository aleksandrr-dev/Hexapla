package com.aleks.hexapla

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

/* ---------------- Original-language interlinear ----------------
   Word-aligned Strong's + morphology for the Greek NT (Byzantine, Robinson
   parsing, public domain) and the Hebrew Tanakh (Open Scriptures morphology,
   CC-BY). Assets generated and verified by tools/build_interlinear.py —
   the tokenizer contract there must match tokenize() below exactly.
   Active whenever the displayed text is the grc or wlc translation:
   tap a word → Strong's entry + decoded parse. */

object Interlinear {

    /** Word tokens as the interlinear pipeline counts them: maximal runs of
     *  letters+combining marks that contain at least one letter. */
    val token = Regex("""[\p{L}\p{M}]+""")

    fun isOriginal(translationId: String) = translationId == "grc" || translationId == "wlc"

    private val cache = HashMap<String, Map<Int, List<List<String>>>>()
    private val mutex = Mutex()

    private suspend fun load(context: Context, asset: String): Map<Int, List<List<String>>> =
        mutex.withLock {
            cache[asset] ?: withContext(Dispatchers.IO) {
                val o = org.json.JSONObject(
                    context.assets.open(asset).readBytes().toString(Charsets.UTF_8)
                )
                val m = HashMap<Int, List<List<String>>>()
                for (k in o.keys()) {
                    val chapters = o.getJSONArray(k)
                    m[k.toInt()] = (0 until chapters.length()).map { c ->
                        val verses = chapters.getJSONArray(c)
                        (0 until verses.length()).map { v -> verses.getString(v) }
                    }
                }
                m
            }.also { cache[asset] = it }
        }

    /** (strongsId, morphCode) for a tapped word, or null when untagged. */
    suspend fun word(
        context: Context, book: Int, chapter: Int, verse: Int, index: Int
    ): Pair<String, String>? {
        val asset = if (book < 39) "interlinear_he.json" else "interlinear_gr.json"
        val tags = load(context, asset)[book]?.getOrNull(chapter)?.getOrNull(verse)
        if (tags.isNullOrEmpty()) return null
        val tag = tags.split(' ').getOrNull(index) ?: return null
        if (tag == "-" || '|' !in tag) return null
        val (s, m) = tag.split('|', limit = 2)
        return s to m
    }

    /** Human-readable parse; Hebrew/Aramaic (OSHM) or Greek (Robinson). */
    fun decode(book: Int, morph: String): String =
        if (book < 39) decodeOshm(morph) else decodeRobinson(morph)

    /* ---- Robinson (Greek) ---- */

    private val grkPos = mapOf(
        "N" to "noun", "A" to "adjective", "T" to "article", "V" to "verb",
        "P" to "personal pronoun", "R" to "relative pronoun",
        "C" to "reciprocal pronoun", "D" to "demonstrative pronoun",
        "F" to "reflexive pronoun", "I" to "interrogative pronoun",
        "X" to "indefinite pronoun", "Q" to "correlative pronoun",
        "K" to "correlative pronoun", "S" to "possessive pronoun",
        "PRT" to "particle", "PREP" to "preposition", "CONJ" to "conjunction",
        "COND" to "conditional particle", "ADV" to "adverb",
        "INJ" to "interjection", "ARAM" to "Aramaic word", "HEB" to "Hebrew word"
    )
    private val grkTense = mapOf(
        'P' to "present", 'I' to "imperfect", 'F' to "future", 'A' to "aorist",
        'R' to "perfect", 'L' to "pluperfect", 'X' to "—"
    )
    private val grkVoice = mapOf(
        'A' to "active", 'M' to "middle", 'P' to "passive",
        'E' to "middle/passive", 'D' to "middle deponent",
        'O' to "passive deponent", 'N' to "middle/passive deponent",
        'Q' to "impersonal active", 'X' to "—"
    )
    private val grkMood = mapOf(
        'I' to "indicative", 'S' to "subjunctive", 'O' to "optative",
        'M' to "imperative", 'N' to "infinitive", 'P' to "participle"
    )
    private val grkCase = mapOf(
        'N' to "nominative", 'G' to "genitive", 'D' to "dative",
        'A' to "accusative", 'V' to "vocative"
    )
    private val grkGender = mapOf('M' to "masculine", 'F' to "feminine", 'N' to "neuter")
    private val grkNumber = mapOf('S' to "singular", 'P' to "plural")
    // Trailing qualifiers and indeclinable markers (PRT-N, N-PRI, A-NUI, ADV-I…)
    private val grkQualifier = mapOf(
        "PRI" to "proper indeclinable", "NUI" to "numeral indeclinable",
        "LI" to "letter indeclinable", "OI" to "other indeclinable",
        "N" to "negative", "I" to "interrogative", "K" to "crasis",
        "S" to "superlative", "C" to "comparative", "ATT" to "Attic form",
        "ABB" to "abbreviated", "P" to "particle attached"
    )

    private fun grkCNG(s: String): String? {
        if (s.length < 2) return null
        val case = grkCase[s[0]] ?: return null
        val num = grkNumber[s.getOrNull(1) ?: ' '] ?: return null
        val gen = s.getOrNull(2)?.let { grkGender[it] }
        return listOfNotNull(case, num, gen).joinToString(" ")
    }

    private fun decodeRobinson(code: String): String {
        val parts = code.split('-')
        val pos = grkPos[parts[0]] ?: grkPos[code] ?: return code
        if (parts.size == 1) return pos
        // Verb: tense/voice/mood, then person+number or case+number+gender
        if (parts[0] == "V") {
            var t = parts[1]
            val second = t.startsWith("2")
            if (second) t = t.drop(1)
            if (t.length >= 3) {
                val tense = (if (second) "2nd " else "") + (grkTense[t[0]] ?: t[0])
                val voice = grkVoice[t[1]] ?: t[1]
                val mood = grkMood[t[2]] ?: t[2]
                val tail = parts.getOrNull(2)?.let { p ->
                    when {
                        p.length >= 2 && p[0].isDigit() ->
                            ", ${p[0]} ${grkNumber[p[1]] ?: p[1]}".let {
                                it.replace("${p[0]} ", when (p[0]) {
                                    '1' -> "1st person "; '2' -> "2nd person "; else -> "3rd person "
                                })
                            }
                        else -> grkCNG(p)?.let { ", $it" } ?: ""
                    }
                } ?: ""
                // 4th part is a qualifier: V-RAI-3S-ATT (Attic form) etc.
                val extra = parts.getOrNull(3)?.let { grkQualifier[it] }?.let { ", $it" } ?: ""
                return "$pos — $tense $voice $mood$tail$extra"
            }
        }
        val tail = parts.drop(1).mapNotNull { p ->
            val person = when (p.getOrNull(0)) {
                '1' -> "1st person"; '2' -> "2nd person"; '3' -> "3rd person"; else -> null
            }
            when {
                // person + number (3S) or person + case+number(+gender) (1GS, 3ASM)
                person != null && p.length >= 2 && grkNumber.containsKey(p[1]) ->
                    "$person ${grkNumber[p[1]]}"
                person != null -> grkCNG(p.drop(1))?.let { "$person $it" }
                else -> grkCNG(p) ?: grkQualifier[p]
            }
        }
        return if (tail.isEmpty()) "$pos ${parts.drop(1).joinToString("-")}"
        else "$pos — ${tail.joinToString(", ")}"
    }

    /* ---- OSHM (Hebrew/Aramaic) ---- */

    private val hebStem = mapOf(
        'q' to "qal", 'N' to "niphal", 'p' to "piel", 'P' to "pual",
        'h' to "hiphil", 'H' to "hophal", 't' to "hithpael", 'o' to "polel",
        'O' to "polal", 'r' to "hithpolel", 'm' to "poel", 'M' to "poal",
        'k' to "palel", 'K' to "pulal", 'Q' to "qal passive", 'l' to "pilpel",
        'L' to "polpal", 'f' to "hithpalpel", 'D' to "nithpael", 'j' to "pealal",
        'i' to "pilel", 'u' to "hothpaal", 'c' to "tiphil", 'v' to "hishtaphel",
        'w' to "nithpalel", 'y' to "nithpoel", 'z' to "hithpoel",
        // Aramaic stems (book of Daniel/Ezra portions)
        'a' to "peal", 'b' to "peil", 'e' to "hithpeel", 's' to "saphel",
        'd' to "pael", 'g' to "ithpaal", 'x' to "ithpeel"
    )
    private val hebConj = mapOf(
        'p' to "perfect", 'q' to "sequential perfect", 'i' to "imperfect",
        'w' to "sequential imperfect", 'h' to "cohortative", 'j' to "jussive",
        'v' to "imperative", 'r' to "participle", 's' to "passive participle",
        'a' to "infinitive absolute", 'c' to "infinitive construct"
    )
    private val hebGender = mapOf('m' to "masculine", 'f' to "feminine",
        'b' to "common", 'c' to "common")
    private val hebNumber = mapOf('s' to "singular", 'p' to "plural", 'd' to "dual")
    private val hebState = mapOf('a' to "absolute", 'c' to "construct", 'd' to "determined")
    private val hebPerson = mapOf('1' to "1st person", '2' to "2nd person", '3' to "3rd person")

    /* OSHM tails are positional; a per-character lookup mislabels the state
       slot ('c' construct reads as gender "common", Aramaic 'd' determined
       as number "dual"). */

    /** gender + number + state — nouns, adjectives, participles. */
    private fun hebGNS(s: String): String = listOfNotNull(
        s.getOrNull(0)?.let { hebGender[it] },
        s.getOrNull(1)?.let { hebNumber[it] },
        s.getOrNull(2)?.let { hebState[it] }
    ).joinToString(" ")

    /** person + gender + number — pronouns, suffixes, finite verbs
     *  (the person slot may be 'x' = unmarked, which simply drops out). */
    private fun hebPGN(s: String): String = listOfNotNull(
        s.getOrNull(0)?.let { hebPerson[it] },
        s.getOrNull(1)?.let { hebGender[it] },
        s.getOrNull(2)?.let { hebNumber[it] }
    ).joinToString(" ")

    private fun decodeSegment(seg: String, aramaic: Boolean): String = when {
        seg.isEmpty() -> ""
        seg[0] == 'C' -> "conjunction"
        seg[0] == 'D' -> "adverb"
        seg[0] == 'R' -> if (seg.getOrNull(1) == 'd') "preposition + article" else "preposition"
        seg[0] == 'T' -> when (seg.getOrNull(1)) {
            'd' -> "article"; 'a' -> "affirmation"; 'e' -> "exhortation"
            'i' -> "interrogative"; 'j' -> "interjection"; 'n' -> "negative"
            'o' -> "direct object marker"; 'r' -> "relative"
            else -> "particle"
        }
        seg[0] == 'N' -> {
            val kind = when (seg.getOrNull(1)) {
                'p' -> "proper noun"; 'g' -> "gentilic noun"; else -> "noun"
            }
            val tail = hebGNS(seg.drop(2))
            if (tail.isEmpty()) kind else "$kind, $tail"
        }
        seg[0] == 'A' -> {
            val kind = when (seg.getOrNull(1)) {
                'c' -> "cardinal number"; 'o' -> "ordinal number"
                'g' -> "gentilic adjective"; else -> "adjective"
            }
            val tail = hebGNS(seg.drop(2))
            if (tail.isEmpty()) kind else "$kind, $tail"
        }
        seg[0] == 'P' -> {
            val kind = when (seg.getOrNull(1)) {
                'd' -> "demonstrative pronoun"; 'i' -> "interrogative pronoun"
                'p' -> "personal pronoun"; 'r' -> "relative pronoun"
                'f' -> "indefinite pronoun"; else -> "pronoun"
            }
            val tail = hebPGN(seg.drop(2))
            if (tail.isEmpty()) kind else "$kind, $tail"
        }
        seg[0] == 'S' -> when (seg.getOrNull(1)) {
            'd' -> "directional suffix"; 'h' -> "paragogic he"; 'n' -> "paragogic nun"
            'p' -> {
                val tail = hebPGN(seg.drop(2))
                if (tail.isEmpty()) "pronominal suffix" else "pronominal suffix, $tail"
            }
            else -> "suffix"
        }
        seg[0] == 'V' -> {
            val stem = hebStem[seg.getOrNull(1) ?: ' '] ?: "${seg.getOrNull(1)}"
            val conjCh = seg.getOrNull(2)
            val conj = hebConj[conjCh ?: ' '] ?: ""
            // Participles decline like nouns (gender-number-state);
            // finite forms conjugate (person-gender-number).
            val tail = if (conjCh == 'r' || conjCh == 's') hebGNS(seg.drop(3))
                       else hebPGN(seg.drop(3))
            listOf("verb", stem, conj, tail).filter { it.isNotBlank() }.joinToString(", ")
        }
        else -> seg
    }

    private fun decodeOshm(code: String): String {
        if (code.isEmpty()) return code
        val aramaic = code[0] == 'A'
        val body = code.drop(1)
        val parts = body.split('/').map { decodeSegment(it, aramaic) }
            .filter { it.isNotBlank() }
        val prefix = if (aramaic) "Aramaic: " else ""
        return prefix + parts.joinToString(" + ")
    }
}
