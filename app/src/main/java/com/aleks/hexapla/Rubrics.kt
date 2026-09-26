package com.aleks.hexapla

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/* ---------------- Clementine Vulgate editorial rubrics ----------------
   Print Clementine editions carry structural rubrics the verse text
   itself no longer does (they shipped as literal "<Aleph>" angle
   brackets in 1.4.3 and were stripped from la_vulgata.json for 1.5.0):
   the Canticum Canticorum speaker labels (Sponsa / Sponsus / Chorus...),
   the Aleph..Thau acrostic letters of Psalm 118 (=119) and
   Lamentationes 1-4, and two Prologus rubrics (Lam 1:1, Sir 1:1).

   Data: assets/rubrics_vul.json, built and offset-verified by
   tools/build_vul_rubrics.py from the same PD clemtext source the asset
   came from. Keyed "book:chapter:verse" in the asset's own native
   numbering (book 0-based slot, chapter/verse 1-based); values are
   [offset, label] pairs where offset indexes into the shipped verse
   text (0 = verse start). The reader currently renders the labels above
   the verse and ignores offsets — they are recorded so a future inline
   renderer needs no re-extraction.

   The Zohrab Armenian OT ("zoh") carries three of its own, in Ezekiel:
   section rubrics that occupied verse SLOTS in the TITUS text
   («Դարձեալ ՛ի վերայ Եգիպտոսի» = "Again, concerning Egypt"). They are in
   the 1805 print, so they are kept — as structure, not scripture — by
   build_zohrab.py, which also makes Ezekiel 29/30/32 land on the KJV
   grid with no versemap curation. */
object Rubrics {

    /** Translation id -> its rubric asset. Add a line to ship more. */
    private val FILES = mapOf(
        "vul" to "rubrics_vul.json",
        "zoh" to "rubrics_zoh.json",
        // The Bakar's 840 rows are mostly the Byzantine lectionary rubrics the
        // 1743 print carries inline, plus each book's closing colophon, the
        // 20 kathisma headings of the Psalter, and the Olympiodorus scholion
        // on Job 39 — all apparatus, kept out of the verse text.
        "bak" to "rubrics_bak.json",
        // KJV 1611 front matter: the two unnumbered Sirach prologues above
        // Sir 1:1 (owner 2026-09-26), from tools/build_kjv_rubrics.py.
        "kjv" to "rubrics_kjv.json",
    )

    /** A label longer than this is prose (a prologue), not a rubric label. */
    const val LONG = 120

    @Volatile
    private var data: Map<String, Map<String, List<Pair<Int, String>>>>? = null

    suspend fun load(context: Context) {
        if (data != null) return
        withContext(Dispatchers.IO) {
            val all = HashMap<String, Map<String, List<Pair<Int, String>>>>()
            for ((id, file) in FILES) {
                val raw = try {
                    context.assets.open(file).readBytes().toString(Charsets.UTF_8).trim()
                } catch (e: Exception) {
                    android.util.Log.w("Rubrics", "$file unreadable", e); continue
                }
                all[id] = try {
                    if (raw.startsWith("[")) parseRows(org.json.JSONArray(raw))
                    else parseKeyed(org.json.JSONObject(raw))
                } catch (e: Exception) {
                    android.util.Log.w("Rubrics", "$file unparsable", e); continue
                }
            }
            data = all
        }
    }

    /** {"book:chapter:verse": [[offset, label], ...]} — vul, zoh, kjv. */
    private fun parseKeyed(o: org.json.JSONObject): Map<String, List<Pair<Int, String>>> {
        val m = HashMap<String, List<Pair<Int, String>>>()
        for (k in o.keys()) {
            val arr = o.getJSONArray(k)
            m[k] = (0 until arr.length()).map { i ->
                val e = arr.getJSONArray(i)
                e.getInt(0) to e.getString(1)
            }
        }
        return m
    }

    /** The Bakar's rows, as tools/build_bakar.py writes them:
     *  {book, chapter (0-based), verse, kind, text}. The print sets them
     *  BETWEEN verses, so they are keyed for the gap they sit in:
     *  verse 0 (kathisma headings) = before verse 1; verse N (lection marks
     *  "ხNხ", which follow verse N in the source, and the Job 39 scholion) =
     *  after verse N; verse -1 (a book's closing colophon) = after the
     *  chapter's last verse. The loader once read this file as a keyed object,
     *  failed, and skipped it silently — none of the 841 rows ever showed. */
    private fun parseRows(a: org.json.JSONArray): Map<String, List<Pair<Int, String>>> {
        val m = HashMap<String, MutableList<Pair<Int, String>>>()
        for (i in 0 until a.length()) {
            val r = a.getJSONObject(i)
            val bc = "${r.getInt("book")}:${r.getInt("chapter") + 1}"
            val key = when (val v = r.getInt("verse")) {
                0 -> "$bc:1"
                -1 -> ">$bc:end"
                else -> ">$bc:$v"
            }
            m.getOrPut(key) { ArrayList() }.add(0 to r.getString("text"))
        }
        return m
    }

    /** Rubric labels opening or inside this verse, in text order; null when
     *  none. chapter/verse are 1-based in the translation's OWN numbering. */
    fun labels(id: String, book: Int, chapter: Int, verse: Int): List<String>? {
        return data?.get(id)?.get("$book:$chapter:$verse")?.map { it.second }
    }

    /** Rubrics printed AFTER this verse (the Bakar's lection marks, and a
     *  book's colophon after its last verse); null when none. */
    fun after(id: String, book: Int, chapter: Int, verse: Int, last: Boolean): List<String>? {
        val d = data?.get(id) ?: return null
        val here = d[">$book:$chapter:$verse"].orEmpty()
        val end = if (last) d[">$book:$chapter:end"].orEmpty() else emptyList()
        return (here + end).map { it.second }.ifEmpty { null }
    }
}
