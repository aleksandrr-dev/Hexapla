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

    /** Human-readable parse; Hebrew/Aramaic (OSHM) or Greek (Robinson).
     *  Grammar terms come from string resources (localized ×12); [context]
     *  resolves them in the UI locale. */
    fun decode(context: Context, book: Int, morph: String): String {
        val s: (Int) -> String = context::getString
        return if (book < 39) decodeOshm(s, morph) else decodeRobinson(s, morph)
    }

    /* ---- Robinson (Greek) ---- */

    private val grkPos = mapOf(
        "N" to R.string.morph_noun, "A" to R.string.morph_adjective,
        "T" to R.string.morph_article, "V" to R.string.morph_verb,
        "P" to R.string.morph_pron_personal, "R" to R.string.morph_pron_relative,
        "C" to R.string.morph_pron_reciprocal, "D" to R.string.morph_pron_demonstrative,
        "F" to R.string.morph_pron_reflexive, "I" to R.string.morph_pron_interrogative,
        "X" to R.string.morph_pron_indefinite, "Q" to R.string.morph_pron_correlative,
        "K" to R.string.morph_pron_correlative, "S" to R.string.morph_pron_possessive,
        "PRT" to R.string.morph_particle, "PREP" to R.string.morph_preposition,
        "CONJ" to R.string.morph_conjunction, "COND" to R.string.morph_cond_particle,
        "ADV" to R.string.morph_adverb, "INJ" to R.string.morph_interjection,
        "ARAM" to R.string.morph_aramaic_word, "HEB" to R.string.morph_hebrew_word
    )
    private val grkTense = mapOf(
        'P' to R.string.morph_tense_present, 'I' to R.string.morph_tense_imperfect,
        'F' to R.string.morph_tense_future, 'A' to R.string.morph_tense_aorist,
        'R' to R.string.morph_tense_perfect, 'L' to R.string.morph_tense_pluperfect
    )
    private val grkVoice = mapOf(
        'A' to R.string.morph_voice_active, 'M' to R.string.morph_voice_middle,
        'P' to R.string.morph_voice_passive, 'E' to R.string.morph_voice_midpass,
        'D' to R.string.morph_voice_mid_deponent, 'O' to R.string.morph_voice_pass_deponent,
        'N' to R.string.morph_voice_midpass_deponent, 'Q' to R.string.morph_voice_impersonal
    )
    private val grkMood = mapOf(
        'I' to R.string.morph_mood_indicative, 'S' to R.string.morph_mood_subjunctive,
        'O' to R.string.morph_mood_optative, 'M' to R.string.morph_mood_imperative,
        'N' to R.string.morph_mood_infinitive, 'P' to R.string.morph_mood_participle
    )
    private val grkCase = mapOf(
        'N' to R.string.morph_case_nominative, 'G' to R.string.morph_case_genitive,
        'D' to R.string.morph_case_dative, 'A' to R.string.morph_case_accusative,
        'V' to R.string.morph_case_vocative
    )
    private val grkGender = mapOf(
        'M' to R.string.morph_masculine, 'F' to R.string.morph_feminine,
        'N' to R.string.morph_neuter
    )
    private val grkNumber = mapOf(
        'S' to R.string.morph_singular, 'P' to R.string.morph_plural
    )
    // Trailing qualifiers and indeclinable markers (PRT-N, N-PRI, A-NUI, ADV-I…)
    private val grkQualifier = mapOf(
        "PRI" to R.string.morph_q_pri, "NUI" to R.string.morph_q_nui,
        "LI" to R.string.morph_q_li, "OI" to R.string.morph_q_oi,
        "N" to R.string.morph_q_negative, "I" to R.string.morph_q_interrogative,
        "K" to R.string.morph_q_crasis, "S" to R.string.morph_q_superlative,
        "C" to R.string.morph_q_comparative, "ATT" to R.string.morph_q_att,
        "ABB" to R.string.morph_q_abb, "P" to R.string.morph_q_attached
    )
    private val person = mapOf(
        '1' to R.string.morph_person_1, '2' to R.string.morph_person_2,
        '3' to R.string.morph_person_3
    )

    private fun grkCNG(s: (Int) -> String, p: String): String? {
        if (p.length < 2) return null
        val case = grkCase[p[0]] ?: return null
        val num = grkNumber[p.getOrNull(1) ?: ' '] ?: return null
        val gen = p.getOrNull(2)?.let { grkGender[it] }
        return listOfNotNull(case, num, gen).joinToString(" ") { s(it) }
    }

    private fun decodeRobinson(s: (Int) -> String, code: String): String {
        val parts = code.split('-')
        val pos = (grkPos[parts[0]] ?: grkPos[code])?.let(s) ?: return code
        if (parts.size == 1) return pos
        // Verb: tense/voice/mood, then person+number or case+number+gender
        if (parts[0] == "V") {
            var t = parts[1]
            val second = t.startsWith("2")
            if (second) t = t.drop(1)
            if (t.length >= 3) {
                val tense = (if (second) s(R.string.morph_second) else "") +
                    (if (t[0] == 'X') "—" else grkTense[t[0]]?.let(s) ?: t[0].toString())
                val voice = if (t[1] == 'X') "—" else grkVoice[t[1]]?.let(s) ?: t[1].toString()
                val mood = grkMood[t[2]]?.let(s) ?: t[2].toString()
                val tail = parts.getOrNull(2)?.let { p ->
                    when {
                        p.length >= 2 && p[0].isDigit() && person.containsKey(p[0]) ->
                            ", ${s(person[p[0]]!!)} ${grkNumber[p[1]]?.let(s) ?: p[1]}"
                        else -> grkCNG(s, p)?.let { ", $it" } ?: ""
                    }
                } ?: ""
                // 4th part is a qualifier: V-RAI-3S-ATT (Attic form) etc.
                val extra = parts.getOrNull(3)?.let { grkQualifier[it] }?.let { ", ${s(it)}" } ?: ""
                return "$pos — $tense $voice $mood$tail$extra"
            }
        }
        val tail = parts.drop(1).mapNotNull { p ->
            val pers = person[p.getOrNull(0) ?: ' ']?.let(s)
            when {
                // person + number (3S) or person + case+number(+gender) (1GS, 3ASM)
                pers != null && p.length >= 2 && grkNumber.containsKey(p[1]) ->
                    "$pers ${s(grkNumber[p[1]]!!)}"
                pers != null -> grkCNG(s, p.drop(1))?.let { "$pers $it" }
                else -> grkCNG(s, p) ?: grkQualifier[p]?.let(s)
            }
        }
        return if (tail.isEmpty()) "$pos ${parts.drop(1).joinToString("-")}"
        else "$pos — ${tail.joinToString(", ")}"
    }

    /* ---- OSHM (Hebrew/Aramaic) ---- */

    private val hebStem = mapOf(
        'q' to R.string.morph_stem_qal, 'N' to R.string.morph_stem_niphal,
        'p' to R.string.morph_stem_piel, 'P' to R.string.morph_stem_pual,
        'h' to R.string.morph_stem_hiphil, 'H' to R.string.morph_stem_hophal,
        't' to R.string.morph_stem_hithpael, 'o' to R.string.morph_stem_polel,
        'O' to R.string.morph_stem_polal, 'r' to R.string.morph_stem_hithpolel,
        'm' to R.string.morph_stem_poel, 'M' to R.string.morph_stem_poal,
        'k' to R.string.morph_stem_palel, 'K' to R.string.morph_stem_pulal,
        'Q' to R.string.morph_stem_qal_passive, 'l' to R.string.morph_stem_pilpel,
        'L' to R.string.morph_stem_polpal, 'f' to R.string.morph_stem_hithpalpel,
        'D' to R.string.morph_stem_nithpael, 'j' to R.string.morph_stem_pealal,
        'i' to R.string.morph_stem_pilel, 'u' to R.string.morph_stem_hothpaal,
        'c' to R.string.morph_stem_tiphil, 'v' to R.string.morph_stem_hishtaphel,
        'w' to R.string.morph_stem_nithpalel, 'y' to R.string.morph_stem_nithpoel,
        'z' to R.string.morph_stem_hithpoel,
        // Aramaic stems (book of Daniel/Ezra portions)
        'a' to R.string.morph_stem_peal, 'b' to R.string.morph_stem_peil,
        'e' to R.string.morph_stem_hithpeel, 's' to R.string.morph_stem_saphel,
        'd' to R.string.morph_stem_pael, 'g' to R.string.morph_stem_ithpaal,
        'x' to R.string.morph_stem_ithpeel
    )
    private val hebConj = mapOf(
        'p' to R.string.morph_hconj_perfect, 'q' to R.string.morph_hconj_seq_perfect,
        'i' to R.string.morph_hconj_imperfect, 'w' to R.string.morph_hconj_seq_imperfect,
        'h' to R.string.morph_hconj_cohortative, 'j' to R.string.morph_hconj_jussive,
        'v' to R.string.morph_hconj_imperative, 'r' to R.string.morph_hconj_participle,
        's' to R.string.morph_hconj_passive_participle,
        'a' to R.string.morph_hconj_inf_absolute, 'c' to R.string.morph_hconj_inf_construct
    )
    private val hebGender = mapOf(
        'm' to R.string.morph_masculine, 'f' to R.string.morph_feminine,
        'b' to R.string.morph_common, 'c' to R.string.morph_common
    )
    private val hebNumber = mapOf(
        's' to R.string.morph_singular, 'p' to R.string.morph_plural,
        'd' to R.string.morph_dual
    )
    private val hebState = mapOf(
        'a' to R.string.morph_state_absolute, 'c' to R.string.morph_state_construct,
        'd' to R.string.morph_state_determined
    )

    /* OSHM tails are positional; a per-character lookup mislabels the state
       slot ('c' construct reads as gender "common", Aramaic 'd' determined
       as number "dual"). */

    /** gender + number + state — nouns, adjectives, participles. */
    private fun hebGNS(s: (Int) -> String, p: String): String = listOfNotNull(
        p.getOrNull(0)?.let { hebGender[it] },
        p.getOrNull(1)?.let { hebNumber[it] },
        p.getOrNull(2)?.let { hebState[it] }
    ).joinToString(" ") { s(it) }

    /** person + gender + number — pronouns, suffixes, finite verbs
     *  (the person slot may be 'x' = unmarked, which simply drops out). */
    private fun hebPGN(s: (Int) -> String, p: String): String = listOfNotNull(
        p.getOrNull(0)?.let { person[it] },
        p.getOrNull(1)?.let { hebGender[it] },
        p.getOrNull(2)?.let { hebNumber[it] }
    ).joinToString(" ") { s(it) }

    private fun decodeSegment(s: (Int) -> String, seg: String): String = when {
        seg.isEmpty() -> ""
        seg[0] == 'C' -> s(R.string.morph_conjunction)
        seg[0] == 'D' -> s(R.string.morph_adverb)
        seg[0] == 'R' -> if (seg.getOrNull(1) == 'd') s(R.string.morph_prep_article)
                         else s(R.string.morph_preposition)
        seg[0] == 'T' -> s(when (seg.getOrNull(1)) {
            'd' -> R.string.morph_article; 'a' -> R.string.morph_affirmation
            'e' -> R.string.morph_exhortation; 'i' -> R.string.morph_int_particle
            'j' -> R.string.morph_interjection; 'n' -> R.string.morph_neg_particle
            'o' -> R.string.morph_obj_marker; 'r' -> R.string.morph_rel_particle
            else -> R.string.morph_particle
        })
        seg[0] == 'N' -> {
            val kind = s(when (seg.getOrNull(1)) {
                'p' -> R.string.morph_proper_noun; 'g' -> R.string.morph_gentilic_noun
                else -> R.string.morph_noun
            })
            val tail = hebGNS(s, seg.drop(2))
            if (tail.isEmpty()) kind else "$kind, $tail"
        }
        seg[0] == 'A' -> {
            val kind = s(when (seg.getOrNull(1)) {
                'c' -> R.string.morph_cardinal; 'o' -> R.string.morph_ordinal
                'g' -> R.string.morph_gentilic_adj; else -> R.string.morph_adjective
            })
            val tail = hebGNS(s, seg.drop(2))
            if (tail.isEmpty()) kind else "$kind, $tail"
        }
        seg[0] == 'P' -> {
            val kind = s(when (seg.getOrNull(1)) {
                'd' -> R.string.morph_pron_demonstrative; 'i' -> R.string.morph_pron_interrogative
                'p' -> R.string.morph_pron_personal; 'r' -> R.string.morph_pron_relative
                'f' -> R.string.morph_pron_indefinite; else -> R.string.morph_pronoun
            })
            val tail = hebPGN(s, seg.drop(2))
            if (tail.isEmpty()) kind else "$kind, $tail"
        }
        seg[0] == 'S' -> when (seg.getOrNull(1)) {
            'd' -> s(R.string.morph_suffix_dir); 'h' -> s(R.string.morph_paragogic_he)
            'n' -> s(R.string.morph_paragogic_nun)
            'p' -> {
                val tail = hebPGN(s, seg.drop(2))
                if (tail.isEmpty()) s(R.string.morph_suffix_pron)
                else "${s(R.string.morph_suffix_pron)}, $tail"
            }
            else -> s(R.string.morph_suffix)
        }
        seg[0] == 'V' -> {
            val stem = hebStem[seg.getOrNull(1) ?: ' ']?.let(s) ?: "${seg.getOrNull(1)}"
            val conjCh = seg.getOrNull(2)
            val conj = hebConj[conjCh ?: ' ']?.let(s) ?: ""
            // Participles decline like nouns (gender-number-state);
            // finite forms conjugate (person-gender-number).
            val tail = if (conjCh == 'r' || conjCh == 's') hebGNS(s, seg.drop(3))
                       else hebPGN(s, seg.drop(3))
            listOf(s(R.string.morph_verb), stem, conj, tail)
                .filter { it.isNotBlank() }.joinToString(", ")
        }
        else -> seg
    }

    private fun decodeOshm(s: (Int) -> String, code: String): String {
        if (code.isEmpty()) return code
        val aramaic = code[0] == 'A'
        val body = code.drop(1)
        val parts = body.split('/').map { decodeSegment(s, it) }
            .filter { it.isNotBlank() }
        val prefix = if (aramaic) s(R.string.morph_aramaic_prefix) else ""
        return prefix + parts.joinToString(" + ")
    }
}
