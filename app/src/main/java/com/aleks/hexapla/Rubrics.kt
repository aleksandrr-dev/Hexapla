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
   renderer needs no re-extraction. Only "vul" has rubrics. */
object Rubrics {

    @Volatile
    private var data: Map<String, List<Pair<Int, String>>>? = null

    suspend fun load(context: Context) {
        if (data != null) return
        withContext(Dispatchers.IO) {
            val o = org.json.JSONObject(
                context.assets.open("rubrics_vul.json").readBytes().toString(Charsets.UTF_8)
            )
            val m = HashMap<String, List<Pair<Int, String>>>()
            for (k in o.keys()) {
                val arr = o.getJSONArray(k)
                m[k] = (0 until arr.length()).map { i ->
                    val e = arr.getJSONArray(i)
                    e.getInt(0) to e.getString(1)
                }
            }
            data = m
        }
    }

    /** Rubric labels opening or inside this verse, in text order; null when
     *  none. chapter/verse are 1-based in the translation's OWN numbering. */
    fun labels(id: String, book: Int, chapter: Int, verse: Int): List<String>? {
        if (id != "vul") return null
        return data?.get("$book:$chapter:$verse")?.map { it.second }
    }
}
