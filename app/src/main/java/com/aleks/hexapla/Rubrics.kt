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
    private val FILES = mapOf("vul" to "rubrics_vul.json", "zoh" to "rubrics_zoh.json")

    @Volatile
    private var data: Map<String, Map<String, List<Pair<Int, String>>>>? = null

    suspend fun load(context: Context) {
        if (data != null) return
        withContext(Dispatchers.IO) {
            val all = HashMap<String, Map<String, List<Pair<Int, String>>>>()
            for ((id, file) in FILES) {
                val o = try {
                    org.json.JSONObject(
                        context.assets.open(file).readBytes().toString(Charsets.UTF_8))
                } catch (_: Exception) { continue }
                val m = HashMap<String, List<Pair<Int, String>>>()
                for (k in o.keys()) {
                    val arr = o.getJSONArray(k)
                    m[k] = (0 until arr.length()).map { i ->
                        val e = arr.getJSONArray(i)
                        e.getInt(0) to e.getString(1)
                    }
                }
                all[id] = m
            }
            data = all
        }
    }

    /** Rubric labels opening or inside this verse, in text order; null when
     *  none. chapter/verse are 1-based in the translation's OWN numbering. */
    fun labels(id: String, book: Int, chapter: Int, verse: Int): List<String>? {
        return data?.get(id)?.get("$book:$chapter:$verse")?.map { it.second }
    }
}
