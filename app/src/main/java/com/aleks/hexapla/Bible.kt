package com.aleks.hexapla

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import org.json.JSONArray
import java.util.Locale

data class Translation(
    val id: String,
    val assetFile: String,
    val label: String,
    val locale: Locale
)

data class Book(val name: String, val chapters: List<List<String>>)

data class VerseRef(val book: Int, val chapter: Int, val verseStart: Int, val verseEnd: Int = verseStart)

object BibleRepo {

    val translations = listOf(
        Translation("kjv", "bibles/en_kjv.json", "King James Version, 1611 (EN)", Locale.ENGLISH),
        Translation("wbt", "bibles/en_webster.json", "Webster Bible, 1833 (EN)", Locale.ENGLISH),
        Translation("gen1599", "bibles/en_geneva.json", "Geneva Bible, 1599 (EN)", Locale.ENGLISH),
        Translation("tyn", "bibles/en_tyndale.json", "Tyndale, 1525/1531 — partial (EN)", Locale.ENGLISH),
        Translation("wyc", "bibles/enm_wycliffe.json", "Wycliffe, c. 1395 (Middle EN)", Locale.ENGLISH),
        Translation("ylt", "bibles/en_ylt.json", "Young's Literal Translation, 1898 (EN)", Locale.ENGLISH),
        Translation("mar", "bibles/fr_martin.json", "Bible Martin, 1744 (FR)", Locale.FRENCH),
        Translation("lut", "bibles/de_luther.json", "Lutherbibel, 1545 (DE)", Locale.GERMAN),
        Translation("kxii", "bibles/sv_karlxii.json", "Karl XII:s Bibel, 1703 (SV)", Locale("sv")),
        Translation("fi76", "bibles/fi_biblia1776.json", "Biblia — Vanha kirkkoraamattu, 1776 (FI)", Locale("fi")),
        Translation("gda", "bibles/pl_gdanska.json", "Biblia Gdańska, 1632 (PL)", Locale("pl")),
        Translation("srb", "bibles/sr_karadzic.json", "Sveto pismo — Karadžić/Daničić, 1847/1865 (SR)", Locale("sr")),
        Translation("da19", "bibles/da_1819.json", "Dansk Bibel, 1819/1871 (DA)", Locale("da")),
        Translation("svv", "bibles/nl_staten.json", "Statenvertaling, 1637/1888 (NL)", Locale("nl")),
        Translation("rv", "bibles/es_rv.json", "Reina-Valera, 1909 (ES)", Locale("es")),
        Translation("alm", "bibles/pt_almeida.json", "Almeida — Bíblia Livre TR (PT)", Locale("pt")),
        Translation("dio", "bibles/it_diodati.json", "Diodati, 1649/1885 (IT)", Locale.ITALIAN),
        Translation("mei", "bibles/ja_meiji.json", "明治元訳 — Meiji Motoyaku, 1880/87 (JA)", Locale.JAPANESE),
        Translation("cus", "bibles/zh_cuv_s.json", "和合本 — Chinese Union, 1919 (简体)", Locale.SIMPLIFIED_CHINESE),
        Translation("cuv", "bibles/zh_cuv_t.json", "和合本 — Chinese Union, 1919 (繁體)", Locale.TRADITIONAL_CHINESE),
        Translation("syn", "bibles/ru_synodal.json", "Синодальный перевод (RU)", Locale("ru")),
        Translation("csl", "bibles/cu_elizabeth.json", "Елизаветинская Библия, 1757 (ЦСЯ)", Locale("ru")),
        Translation("grc", "bibles/grc_byz.json", "Ελληνικά — Byzantine Textform NT (GRC)", Locale("el")),
        Translation("vam", "bibles/el_vamvas.json", "Η Αγία Γραφή — Βάμβας, 1850 (EL)", Locale("el")),
        Translation("wlc", "bibles/he_wlc.json", "עברית — Westminster Leningrad Codex (HE)", Locale("he")),
        Translation("san", "bibles/sa_nt.json", "संस्कृतम् — Sanskrit NT, 1851 (SA)", Locale("sa")),
        Translation("ta", "bibles/ta_irv.json", "பரிசுத்த வேதாகமம் — Tamil IRV, 2019 (TA)", Locale("ta")),
        Translation("vd", "bibles/ar_vandyck.json", "الكتاب المقدس — Van Dyck, 1865 (AR)", Locale("ar")),
        Translation("vul", "bibles/la_vulgata.json", "Vulgata Clementina, 1592 (LA)", Locale("la"))
    )

    fun translation(id: String): Translation =
        translations.firstOrNull { it.id == id } ?: translations.first()

    /** Pickers list the user's own language first (stable within groups). */
    fun ordered(): List<Translation> {
        val lang = Locale.getDefault().language
        return translations.sortedBy { if (it.locale.language == lang) 0 else 1 }
    }

    /** Default primary translation follows the system language. */
    fun defaultPrimaryId(): String = when (Locale.getDefault().language) {
        "ru" -> "syn"
        "fr" -> "mar"
        "de" -> "lut"
        "es" -> "rv"
        "pt" -> "alm"
        "it" -> "dio"
        "sv" -> "kxii"
        "da", "nb", "nn", "no" -> "da19"  // Norway's classical scripture was the Danish Bible
        "nl" -> "svv"
        "ar" -> "vd"
        "fi" -> "fi76"
        "pl" -> "gda"
        "sr", "bs", "hr" -> "srb"
        // Modern Greek reads Vamvas; grc stays the study/original text.
        "el" -> "vam"
        "ja" -> "mei"
        "ta" -> "ta"
        "la" -> "vul"
        "zh" -> Locale.getDefault().let {
            if (it.script == "Hant" || it.country in setOf("TW", "HK", "MO")) "cuv" else "cus"
        }
        else -> "kjv"
    }

    fun defaultSecondaryId(): String =
        if (Locale.getDefault().language == "en") "syn" else "kjv"

    private val cache = mutableMapOf<String, List<Book>>()
    private val mutex = Mutex()

    suspend fun load(context: Context, id: String): List<Book> = mutex.withLock {
        cache[id]?.let { return it }
        withContext(Dispatchers.IO) {
            val books = parseAsset(context, translation(id).assetFile)
            cache[id] = books
            books
        }
    }

    // "{In: or, For}"-style translator margin notes: drop whole group. Braces
    // without a colon mark supplied (italicized) words: keep the words.
    // The group captures the note body so parseAsset can retain it for the
    // "Translator's notes" verse action (display still gets the clean text).
    private val marginNote = Regex("""\s*\{([^{}]*:[^{}]*)\}""")
    private val multiSpace = Regex("""\s+""")

    // Stripped colon-notes per asset, keyed "book:chapter:verse" (0-based).
    // Only the KJV asset actually has them (~7.8k notes); the map is empty
    // for every other translation, so the memory cost is a few hundred KB.
    private val notesByAsset =
        java.util.concurrent.ConcurrentHashMap<String, Map<String, List<String>>>()

    /** Translator margin notes for a translation ("term: alternative" strings,
     *  exactly as stripped). Populated once the translation has been load()ed;
     *  empty map before that or when the asset has none. */
    fun notes(id: String): Map<String, List<String>> =
        notesByAsset[translation(id).assetFile] ?: emptyMap()

    internal fun parseAsset(context: Context, assetFile: String): List<Book> {
        val text = context.assets.open(assetFile).readBytes()
            .toString(Charsets.UTF_8).trim().removePrefix("\uFEFF")
        val arr = JSONArray(text)
        val books = ArrayList<Book>(arr.length())
        val notes = HashMap<String, List<String>>()
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val chArr = o.getJSONArray("chapters")
            val chapters = ArrayList<List<String>>(chArr.length())
            for (c in 0 until chArr.length()) {
                val vArr = chArr.getJSONArray(c)
                val verses = ArrayList<String>(vArr.length())
                for (v in 0 until vArr.length()) {
                    val raw = vArr.getString(v)
                    if ('{' in raw) {
                        val found = marginNote.findAll(raw)
                            .map { it.groupValues[1].trim() }.toList()
                        if (found.isNotEmpty()) notes["$i:$c:$v"] = found
                    }
                    verses.add(
                        raw
                            .replace(marginNote, "")
                            .replace("{", "").replace("}", "")
                            .replace(multiSpace, " ")
                            .trim()
                    )
                }
                chapters.add(verses)
            }
            books.add(Book(o.getString("name"), chapters))
        }
        notesByAsset[assetFile] = notes
        return books
    }
}

/* ---------------- Strong's concordance (public domain, 1890/1894) ----------------
   Tagged KJV text ("word[H1234]") plus the Hebrew/Greek lexicon. Loaded lazily,
   used only for display when the setting is on \u2014 TTS, search, copy and compare
   all keep using the plain KJV. */

object StrongsRepo {
    data class Entry(val word: String, val translit: String, val pos: String, val def: String)

    val tag = Regex("""\[([HG]\d+)\]""")

    private var textCache: List<Book>? = null
    private var lexCache: Map<String, Entry>? = null
    private val strongsMutex = Mutex()

    suspend fun books(context: Context): List<Book> = strongsMutex.withLock {
        textCache ?: withContext(Dispatchers.IO) {
            BibleRepo.parseAsset(context, "bibles/en_kjv_strongs.json")
        }.also { textCache = it }
    }

    suspend fun entry(context: Context, id: String): Entry? = strongsMutex.withLock {
        val lex = lexCache ?: withContext(Dispatchers.IO) {
            val text = context.assets.open("strongs_lexicon.json").readBytes()
                .toString(Charsets.UTF_8)
            val o = org.json.JSONObject(text)
            val m = HashMap<String, Entry>(o.length())
            for (k in o.keys()) {
                val e = o.getJSONObject(k)
                m[k] = Entry(
                    word = e.optString("w"),
                    translit = e.optString("t"),
                    pos = e.optString("p"),
                    def = e.optString("d")
                )
            }
            m
        }.also { lexCache = it }
        lex[id]
    }
}

/* ---------------- Webster's 1828 American Dictionary ----------------
   Public domain. Tap-a-word definitions for English translations; shows
   what an English word meant in the era of the classic translations.
   Lookup chain mirrors tools/check_1828_coverage.py — keep them in sync.
   Loaded lazily (~13 MB JSON) only when the setting is on. */

object Webster1828 {
    private var cache: Map<String, String>? = null
    private val dictMutex = Mutex()

    // KJV-frequent forms the 1828 lacks as headwords (or spells otherwise).
    private val irregular = mapOf(
        "HATH" to "HAVE", "DOTH" to "DO", "DOST" to "DO", "DIDST" to "DO",
        "SAITH" to "SAY", "SAIDST" to "SAY", "SHALT" to "SHALL", "WILT" to "WILL",
        "CANST" to "CAN", "COULDEST" to "COULD", "WOULDEST" to "WOULD",
        "SHOULDEST" to "SHOULD", "MIGHTEST" to "MIGHT", "MAYEST" to "MAY",
        "SHEW" to "SHOW", "SHEWED" to "SHOW", "SHEWETH" to "SHOW",
        "SHEWN" to "SHOW", "SHEWING" to "SHOW", "SHEWBREAD" to "SHOW-BREAD",
        "BEGAT" to "BEGET", "BEGOTTEN" to "BEGET", "SLEW" to "SLAY", "SLAIN" to "SLAY",
        "SMOTE" to "SMITE", "SMITTEN" to "SMITE", "TRODDEN" to "TREAD", "TROD" to "TREAD",
        "BADE" to "BID", "FORBADE" to "FORBID", "GAVEST" to "GIVE", "GAVE" to "GIVE",
        "TOOK" to "TAKE", "TOOKEST" to "TAKE", "TAKEN" to "TAKE", "WENT" to "GO",
        "WENTEST" to "GO", "CAME" to "COME", "CAMEST" to "COME", "SAW" to "SEE",
        "SAWEST" to "SEE", "SEEN" to "SEE", "STOOD" to "STAND", "STOODEST" to "STAND",
        "BROUGHT" to "BRING", "BROUGHTEST" to "BRING", "SOUGHT" to "SEEK",
        "FOUGHT" to "FIGHT", "BOUGHT" to "BUY", "TAUGHT" to "TEACH", "CAUGHT" to "CATCH",
        "KEPT" to "KEEP", "SLEPT" to "SLEEP", "WEPT" to "WEEP", "SWEPT" to "SWEEP",
        "FLED" to "FLEE", "FED" to "FEED", "LED" to "LEAD", "LEDDEST" to "LEAD",
        "MET" to "MEET", "HELD" to "HOLD", "HELDEST" to "HOLD", "TOLD" to "TELL",
        "TOLDEST" to "TELL", "SOLD" to "SELL", "SENT" to "SEND", "SENTEST" to "SEND",
        "SPENT" to "SPEND", "BENT" to "BEND", "LENT" to "LEND", "RENT" to "REND",
        "BUILT" to "BUILD", "SAT" to "SIT", "SATEST" to "SIT", "LAY" to "LIE",
        "LAIN" to "LIE", "MADE" to "MAKE", "MADEST" to "MAKE", "SPOKEN" to "SPEAK",
        "CHOSE" to "CHOOSE", "CHOSEN" to "CHOOSE", "DROVE" to "DRIVE",
        "DRIVEN" to "DRIVE", "RODE" to "RIDE", "RIDDEN" to "RIDE", "ROSE" to "RISE",
        "RISEN" to "RISE", "AROSE" to "ARISE", "ARISEN" to "ARISE", "WROTE" to "WRITE",
        "WRITTEN" to "WRITE", "SWORE" to "SWEAR", "SWORN" to "SWEAR", "TORE" to "TEAR",
        "TORN" to "TEAR", "WORE" to "WEAR", "WORN" to "WEAR", "BORE" to "BEAR",
        "BORNE" to "BEAR", "BORN" to "BEAR", "GRAVEN" to "GRAVE", "HEWN" to "HEW",
        "SOWN" to "SOW", "MOWN" to "MOW", "KNOWN" to "KNOW", "KNEW" to "KNOW",
        "KNEWEST" to "KNOW", "GREW" to "GROW", "GROWN" to "GROW", "THREW" to "THROW",
        "THROWN" to "THROW", "BLEW" to "BLOW", "BLOWN" to "BLOW", "FLEW" to "FLY",
        "FLOWN" to "FLY", "DREW" to "DRAW", "DRAWN" to "DRAW", "DRAWEST" to "DRAW",
        "ATE" to "EAT", "EATEN" to "EAT", "DRANK" to "DRINK", "DRUNK" to "DRINK",
        "DRUNKEN" to "DRINK", "SANG" to "SING", "SUNG" to "SING", "RANG" to "RING",
        "RUNG" to "RING", "SANK" to "SINK", "SUNK" to "SINK", "SUNKEN" to "SINK",
        "SWAM" to "SWIM", "SWUM" to "SWIM", "RAN" to "RUN", "WON" to "WIN",
        "SHONE" to "SHINE", "STRUCK" to "STRIKE", "STRICKEN" to "STRIKE",
        "STOLE" to "STEAL", "STOLEN" to "STEAL", "FELL" to "FALL", "FELLEST" to "FALL",
        "FALLEN" to "FALL", "FORGAVE" to "FORGIVE", "FORGIVEN" to "FORGIVE",
        "FORSOOK" to "FORSAKE", "FORSAKEN" to "FORSAKE", "FOUND" to "FIND",
        "FOUNDEST" to "FIND", "GROUND" to "GRIND", "BOUND" to "BIND", "WOUND" to "WIND",
        "HID" to "HIDE", "HIDDEN" to "HIDE", "BITTEN" to "BITE", "BIT" to "BITE",
        "SHOT" to "SHOOT", "GOT" to "GET", "GOTTEN" to "GET", "GAT" to "GET",
        "BESOUGHT" to "BESEECH", "WROUGHT" to "WORK", "LEFT" to "LEAVE",
        "LOST" to "LOSE", "PAID" to "PAY", "LAID" to "LAY", "LAIDST" to "LAY",
        "SAID" to "SAY", "HEARD" to "HEAR", "HEARDEST" to "HEAR", "MEANT" to "MEAN",
        "FELT" to "FEEL", "DEALT" to "DEAL", "KNELT" to "KNEEL", "DWELT" to "DWELL",
        "SPAT" to "SPIT", "CLAD" to "CLOTHE", "SHOD" to "SHOE",
        "WAS" to "BE", "WAST" to "BE", "WERT" to "BE", "WERE" to "BE", "BEEN" to "BE",
        "AM" to "BE", "IS" to "BE", "ARE" to "BE", "HAD" to "HAVE", "HADST" to "HAVE",
        "HAS" to "HAVE", "HAST" to "HAVE", "HAVING" to "HAVE", "DID" to "DO",
        "DONE" to "DO", "DOES" to "DO",
        "MEN" to "MAN", "WOMEN" to "WOMAN", "CHILDREN" to "CHILD",
        "BRETHREN" to "BROTHER", "KINE" to "COW", "OXEN" to "OX", "FEET" to "FOOT",
        "TEETH" to "TOOTH", "GEESE" to "GOOSE", "MICE" to "MOUSE", "LICE" to "LOUSE",
        "DIED" to "DIE", "DIETH" to "DIE", "DYING" to "DIE", "LIETH" to "LIE",
        "LYING" to "LIE", "SPUE" to "SPEW", "SPUED" to "SPEW",
        "MARISHES" to "MARSH", "MARISH" to "MARSH", "AGONE" to "AGO",
        "STRAWED" to "STREW", "WOE" to "WO", "BEGAN" to "BEGIN", "BEGUN" to "BEGIN",
        "YOURSELVES" to "YOURSELF", "OURSELVES" to "OURSELF",
        "SELVES" to "SELF", "WOLVES" to "WOLF", "CALVES" to "CALF",
        "HALVES" to "HALF", "LOAVES" to "LOAF", "LIVES" to "LIFE",
        "WIVES" to "WIFE", "KNIVES" to "KNIFE", "THIEVES" to "THIEF",
        "SHEAVES" to "SHEAF", "LEAVES" to "LEAF", "STAVES" to "STAFF",
        "HOOVES" to "HOOF"
    )

    private val vowels = setOf('A', 'E', 'I', 'O', 'U')

    /** Lookup candidates for a tapped word, most specific first. */
    private fun candidates(word: String): List<String> {
        var w = word.uppercase().replace('’', '\'').trim { !it.isLetter() }
        val out = ArrayList<String>(8)
        out.add(w)
        irregular[w]?.let { out.add(it); return out }
        if (w.endsWith("'S")) { w = w.dropLast(2); out.add(w) }
        else if (w.endsWith("S'")) { w = w.dropLast(1); out.add(w) }
        for (suffix in listOf("ETH", "EST", "ES", "ED", "ING", "S")) {
            if (!w.endsWith(suffix) || w.length <= suffix.length + 1) continue
            val stem = w.dropLast(suffix.length)
            if (suffix != "ING" && suffix != "S" && stem.endsWith("I"))
                out.add(stem.dropLast(1) + "Y")     // carrieth -> carry
            out.add(stem)                            // walketh -> walk
            out.add(stem + "E")                      // loveth -> love
            if (stem.length > 2 && stem[stem.length - 1] == stem[stem.length - 2] &&
                stem.last() !in vowels)
                out.add(stem.dropLast(1))            // sitteth -> sit
        }
        if (w.endsWith("LY") && w.length > 4) out.add(w.dropLast(2))
        return out
    }

    /** Returns (headword, definition) or null. */
    suspend fun lookup(context: Context, word: String): Pair<String, String>? {
        val dict = dictMutex.withLock {
            cache ?: withContext(Dispatchers.IO) {
                val text = context.assets.open("webster1828.json").readBytes()
                    .toString(Charsets.UTF_8)
                val o = org.json.JSONObject(text)
                val m = HashMap<String, String>(o.length() * 4 / 3)
                for (k in o.keys()) m[k] = o.getString(k)
                m
            }.also { cache = it }
        }
        for (c in candidates(word)) dict[c]?.let { return c to it }
        return null
    }

    fun unload() { cache = null }
}

/* ---------------- Cross-references (openbible.info, CC-BY) ----------------
   Per-verse index of the strongest community-voted cross-references,
   top 8 per verse. Loaded lazily from assets on first use (~2 MB). */

object Xrefs {
    private var cache: Map<String, List<IntArray>>? = null
    private val xrefMutex = Mutex()

    /** Returns targets as [book, chapter, verse] triples for the given verse. */
    suspend fun refs(context: Context, book: Int, chapter: Int, verse: Int): List<IntArray> =
        withContext(Dispatchers.IO) {
            val map = xrefMutex.withLock {
                cache ?: run {
                    val text = context.assets.open("xrefs.json").readBytes()
                        .toString(Charsets.UTF_8)
                    val o = org.json.JSONObject(text)
                    val m = HashMap<String, List<IntArray>>(o.length())
                    for (k in o.keys()) {
                        val arr = o.getJSONArray(k)
                        m[k] = (0 until arr.length()).map { i ->
                            val p = arr.getString(i).split(":")
                            intArrayOf(p[0].toInt(), p[1].toInt(), p[2].toInt())
                        }
                    }
                    cache = m
                    m
                }
            }
            map["$book:$chapter:$verse"] ?: emptyList()
        }
}

/* ---------------- Voluntary support links ----------------
   Purely optional tips. No features are gated behind these.
   Replace the placeholder URLs with your real pages.
   Note: if distributing via Google Play / App Store, digital tips must go
   through their billing systems instead — external links are for direct
   APK / RuStore distribution. */

object Donation {
    val links = listOf(
        "ЮMoney" to "https://yoomoney.ru/to/4100119568618191"
    )
}

/* ---------------- Reading plans ---------------- */

data class PlanDay(val day: Int, val chapters: List<Pair<Int, Int>>) // (bookIdx, chapterIdx)

data class ReadingPlan(
    val id: String,
    val titleRes: Int,
    val descRes: Int,
    val days: List<PlanDay>,
    val eraByDay: Map<Int, Int> = emptyMap() // day → era heading resource
)

object Plans {
    /** Chapters per canon book in KJV versification (Gen 50 … Rev 22).
     *  Derived programmatically from bibles/en_kjv.json (sums to 1189).
     *  Plan days are pinned to this canonical grid so day contents — and
     *  Store.planProgress day numbers — are identical for every primary
     *  translation; PlansScreen pivots display/open through VerseMap. */
    val KJV_CHAPTERS = intArrayOf(
        50, 40, 27, 36, 34, 24, 21, 4, 31, 24, 22, 25, 29, 36, 10, 13, 10,
        42, 150, 31, 12, 8, 66, 52, 5, 48, 12, 14, 3, 9, 1, 4, 7, 3, 3, 3,
        2, 14, 4, 28, 16, 24, 21, 28, 16, 16, 13, 6, 6, 4, 4, 5, 3, 6, 4,
        3, 1, 13, 5, 5, 3, 5, 1, 1, 1, 22
    )

    /** Distribute a flat list of chapters evenly over [totalDays]. */
    private fun distribute(chapters: List<Pair<Int, Int>>, totalDays: Int): List<PlanDay> {
        val days = totalDays.coerceAtMost(chapters.size).coerceAtLeast(1)
        val result = ArrayList<PlanDay>(days)
        var index = 0
        for (day in 0 until days) {
            val remainingDays = days - day
            val remainingChapters = chapters.size - index
            val take = (remainingChapters + remainingDays - 1) / remainingDays // ceil
            result.add(PlanDay(day + 1, chapters.subList(index, index + take).toList()))
            index += take
        }
        return result
    }

    /** Plans are pinned to the canonical KJV grid — independent of whichever
     *  translation is loaded, so they are built once and cached. */
    private val cached: List<ReadingPlan> by lazy {
        val allChapters = ArrayList<Pair<Int, Int>>(1189)
        // Plans cover the 66-book canon; apocrypha (slots 66+) is read freely.
        KJV_CHAPTERS.forEachIndexed { b, n ->
            for (c in 0 until n) allChapters.add(b to c)
        }
        val ntChapters = allChapters.filter { it.first >= 39 }
        val gospelChapters = allChapters.filter { it.first in 39..42 }
        val proverbsChapters = allChapters.filter { it.first == 19 }
        val psalmChapters = allChapters.filter { it.first == 18 }
        val chronoDays = distribute(ChronoOrder.chapters(), 365)
        listOf(
            ReadingPlan("year", R.string.plan_year, R.string.plan_year_desc, distribute(allChapters, 365)),
            ReadingPlan("chrono", R.string.plan_chrono, R.string.plan_chrono_desc,
                chronoDays, ChronoOrder.eraByDay(chronoDays)),
            ReadingPlan("nt90", R.string.plan_nt90, R.string.plan_nt90_desc, distribute(ntChapters, 90)),
            ReadingPlan("gospels30", R.string.plan_gospels, R.string.plan_gospels_desc, distribute(gospelChapters, 30)),
            ReadingPlan("prov31", R.string.plan_proverbs, R.string.plan_proverbs_desc, distribute(proverbsChapters, 31)),
            ReadingPlan("ps75", R.string.plan_psalms, R.string.plan_psalms_desc, distribute(psalmChapters, 75))
        )
    }

    fun build(): List<ReadingPlan> = cached
}

/* ---------------- Red letters (words of Christ) ----------------
   Verse-level index of where Christ speaks, KJV versification. */

object RedLetters {
    private var cache: Map<Int, List<Set<Int>>>? = null
    private val redMutex = Mutex()

    /** Book index → per-chapter sets of 0-based verse indexes. */
    suspend fun load(context: Context): Map<Int, List<Set<Int>>> = redMutex.withLock {
        cache ?: withContext(Dispatchers.IO) {
            val o = org.json.JSONObject(
                context.assets.open("red_letters.json").readBytes().toString(Charsets.UTF_8)
            )
            val m = HashMap<Int, List<Set<Int>>>()
            for (k in o.keys()) {
                val arr = o.getJSONArray(k)
                m[k.toInt()] = (0 until arr.length()).map { c ->
                    val vs = arr.getJSONArray(c)
                    (0 until vs.length()).map { vs.getInt(it) }.toSet()
                }
            }
            m
        }.also { cache = it }
    }
}

/* ---------------- Topical index ---------------- */

data class Topic(val titleRes: Int, val refs: List<VerseRef>)

object Topics {
    // Book indices: 0=Gen 17=Job 18=Ps 19=Prov 22=Isa 23=Jer 39=Mt 40=Mk 41=Lk 42=Jn 43=Acts
    // 44=Rom 45=1Cor 46=2Cor 47=Gal 48=Eph 49=Php 50=Col 52=2Th 54=2Tim 57=Heb 58=Jas
    // 59=1Pet 61=1Jn 65=Rev
    /* The Good News: God's plan of salvation, step by step, verses only.
       Order follows the classic soul-winning presentation: sin, its penalty,
       Christ's payment, the free gift, belief, eternal security, calling. */
    val gospel = listOf(
        Topic(R.string.gospel_step1, listOf(
            VerseRef(44, 2, 22, 22), VerseRef(44, 2, 9, 9)
        )),
        Topic(R.string.gospel_step2, listOf(
            VerseRef(44, 5, 22, 22), VerseRef(65, 20, 7, 7), VerseRef(65, 19, 13, 14)
        )),
        Topic(R.string.gospel_step3, listOf(
            VerseRef(44, 4, 7, 7), VerseRef(42, 2, 15, 15), VerseRef(45, 14, 2, 3)
        )),
        Topic(R.string.gospel_step4, listOf(
            VerseRef(48, 1, 7, 8), VerseRef(55, 2, 4, 4)
        )),
        Topic(R.string.gospel_step5, listOf(
            VerseRef(43, 15, 29, 30), VerseRef(42, 2, 17, 17)
        )),
        Topic(R.string.gospel_step6, listOf(
            VerseRef(42, 5, 46, 46), VerseRef(42, 9, 27, 27), VerseRef(42, 2, 35, 35)
        )),
        Topic(R.string.gospel_step7, listOf(
            VerseRef(44, 9, 8, 12)
        ))
    )

    val study = listOf(
        // Doctrinal study for believers; the guided walk for the lost lives in
        // the Good News tab, so these refs deliberately avoid repeating it.
        Topic(R.string.topic_salvation, listOf(
            VerseRef(43, 3, 11, 11), VerseRef(42, 13, 5, 5), VerseRef(46, 4, 16, 16),
            VerseRef(46, 4, 20, 20), VerseRef(59, 0, 17, 18), VerseRef(47, 1, 15, 15),
            VerseRef(57, 6, 24, 24)
        )),
        Topic(R.string.topic_prayer, listOf(
            VerseRef(39, 5, 4, 12), VerseRef(49, 3, 5, 6), VerseRef(51, 4, 15, 17),
            VerseRef(58, 4, 12, 15), VerseRef(41, 17, 0, 7), VerseRef(61, 4, 13, 14)
        )),
        Topic(R.string.topic_faith, listOf(
            VerseRef(57, 10, 0, 5), VerseRef(44, 9, 15, 16), VerseRef(58, 1, 1, 7),
            VerseRef(39, 16, 19, 19), VerseRef(40, 8, 22, 23), VerseRef(46, 4, 6, 6)
        )),
        Topic(R.string.topic_love, listOf(
            VerseRef(45, 12, 0, 12), VerseRef(61, 3, 6, 20), VerseRef(42, 12, 33, 34),
            VerseRef(44, 7, 37, 38), VerseRef(59, 3, 7, 7), VerseRef(21, 7, 5, 6)
        )),
        Topic(R.string.topic_forgiveness, listOf(
            VerseRef(39, 5, 13, 14), VerseRef(39, 17, 20, 21), VerseRef(48, 3, 31, 31),
            VerseRef(50, 2, 12, 13), VerseRef(61, 0, 8, 8), VerseRef(18, 102, 7, 13)
        )),
        Topic(R.string.topic_holy_spirit, listOf(
            VerseRef(42, 13, 15, 16), VerseRef(42, 15, 12, 14), VerseRef(43, 0, 7, 7),
            VerseRef(44, 7, 25, 26), VerseRef(47, 4, 21, 22), VerseRef(45, 2, 15, 16)
        )),
        Topic(R.string.topic_wisdom, listOf(
            VerseRef(19, 2, 4, 6), VerseRef(58, 0, 4, 4), VerseRef(19, 8, 9, 9),
            VerseRef(20, 11, 12, 13), VerseRef(50, 1, 1, 2), VerseRef(17, 27, 27, 27)
        )),
        Topic(R.string.topic_hope, listOf(
            VerseRef(23, 28, 10, 12), VerseRef(44, 14, 12, 12), VerseRef(24, 2, 21, 25),
            VerseRef(44, 4, 1, 4), VerseRef(59, 0, 2, 3), VerseRef(65, 20, 3, 4)
        ))
    )

    val help = listOf(
        Topic(R.string.help_anxiety, listOf(
            VerseRef(49, 3, 5, 6), VerseRef(39, 5, 24, 33), VerseRef(59, 4, 6, 6),
            VerseRef(18, 54, 21, 21), VerseRef(42, 13, 26, 26), VerseRef(22, 25, 2, 3)
        )),
        Topic(R.string.help_fear, listOf(
            VerseRef(22, 40, 9, 12), VerseRef(18, 22, 0, 5), VerseRef(18, 26, 0, 2),
            VerseRef(54, 0, 6, 6), VerseRef(61, 3, 17, 17), VerseRef(4, 30, 5, 5)
        )),
        Topic(R.string.help_grief, listOf(
            VerseRef(18, 33, 17, 18), VerseRef(39, 4, 3, 3), VerseRef(65, 20, 3, 3),
            VerseRef(51, 3, 12, 17), VerseRef(42, 10, 24, 25), VerseRef(18, 146, 2, 2)
        )),
        Topic(R.string.help_loneliness, listOf(
            VerseRef(4, 30, 7, 7), VerseRef(18, 67, 4, 5), VerseRef(22, 42, 1, 1),
            VerseRef(39, 27, 19, 19), VerseRef(57, 12, 4, 5), VerseRef(18, 138, 6, 9)
        )),
        Topic(R.string.help_anger, listOf(
            VerseRef(48, 3, 25, 26), VerseRef(58, 0, 18, 19), VerseRef(19, 14, 0, 0),
            VerseRef(19, 15, 31, 31), VerseRef(18, 36, 7, 8), VerseRef(50, 2, 7, 7)
        )),
        Topic(R.string.help_temptation, listOf(
            VerseRef(45, 9, 12, 12), VerseRef(58, 0, 11, 14), VerseRef(39, 25, 40, 40),
            VerseRef(57, 3, 14, 15), VerseRef(18, 118, 8, 10), VerseRef(47, 4, 15, 15)
        )),
        Topic(R.string.help_illness, listOf(
            VerseRef(58, 4, 13, 15), VerseRef(18, 102, 1, 4), VerseRef(23, 16, 13, 13),
            VerseRef(18, 40, 2, 2), VerseRef(59, 1, 23, 23), VerseRef(46, 11, 8, 9)
        )),
        Topic(R.string.help_finances, listOf(
            VerseRef(49, 3, 18, 18), VerseRef(39, 5, 30, 32), VerseRef(19, 2, 8, 9),
            VerseRef(57, 12, 4, 4), VerseRef(18, 36, 24, 24), VerseRef(38, 2, 9, 9)
        )),
        Topic(R.string.help_despair, listOf(
            VerseRef(18, 41, 10, 10), VerseRef(18, 33, 16, 18), VerseRef(22, 60, 0, 2),
            VerseRef(46, 3, 7, 9), VerseRef(18, 29, 4, 4), VerseRef(39, 10, 27, 29)
        )),
        Topic(R.string.help_guidance, listOf(
            VerseRef(19, 2, 4, 5), VerseRef(18, 31, 7, 7), VerseRef(22, 29, 20, 20),
            VerseRef(18, 118, 104, 104), VerseRef(58, 0, 4, 4), VerseRef(19, 15, 8, 8)
        )),
        Topic(R.string.help_marriage, listOf(
            VerseRef(0, 1, 23, 23), VerseRef(48, 4, 24, 32), VerseRef(45, 12, 3, 6),
            VerseRef(50, 2, 13, 18), VerseRef(19, 17, 21, 21), VerseRef(20, 3, 8, 11)
        )),
        Topic(R.string.help_guilt, listOf(
            VerseRef(18, 31, 0, 4), VerseRef(44, 7, 0, 1), VerseRef(61, 0, 8, 8),
            VerseRef(22, 0, 17, 17), VerseRef(18, 102, 11, 11), VerseRef(46, 4, 16, 16)
        ))
    )
}
