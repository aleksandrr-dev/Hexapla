package com.aleks.hexapla

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/* ---------------- Verse-level versification map ----------------
   Translations keep their authentic native numbering (Luther and the
   Synodal count psalm titles as verse 1, the Synodal psalter follows
   the LXX, the Hebrew WLC uses Masoretic chapter bounds, Martin merges
   a few verses, Meiji omits some). The app's pairing features — split
   view, Compare, cross-references, red letters, Topics — are indexed
   by the KJV backbone, so verse references pivot through this map.

   Data: assets/versemap.json, generated and verified by
   tools/build_versemap.py. Per translation per book, runs of
   [kjvCh, kjvV0, kjvV1, transCh, transV0, transV1] (1-based).
   Equal-length runs pair verse-for-verse; unequal runs are blocks
   (all their verses correspond together); transV0 > transV1 marks an
   omission. Anything not listed is identity. */
object VerseMap {

    @Volatile
    private var data: Map<String, Map<Int, List<IntArray>>>? = null

    suspend fun load(context: Context) {
        if (data != null) return
        withContext(Dispatchers.IO) {
            val o = org.json.JSONObject(
                context.assets.open("versemap.json").readBytes().toString(Charsets.UTF_8)
            )
            val m = HashMap<String, Map<Int, List<IntArray>>>()
            for (id in o.keys()) {
                val books = o.getJSONObject(id)
                val bm = HashMap<Int, List<IntArray>>()
                for (b in books.keys()) {
                    val arr = books.getJSONArray(b)
                    bm[b.toInt()] = (0 until arr.length()).map { i ->
                        val r = arr.getJSONArray(i)
                        IntArray(6) { r.getInt(it) }
                    }
                }
                m[id] = bm
            }
            data = m
        }
    }

    private fun runs(id: String, book: Int) = data?.get(id)?.get(book)

    /** The translation's own (chapter, verse) -> KJV (chapter, verse).
     *  1-based on both sides; identity when unmapped (or not loaded). */
    fun toKjv(id: String, book: Int, c: Int, v: Int): Pair<Int, Int> {
        for (r in runs(id, book) ?: return c to v) {
            if (r[3] == c && r[4] <= r[5] && v in r[4]..r[5]) {
                return if (r[2] - r[1] == r[5] - r[4]) r[0] to r[1] + (v - r[4])
                else r[0] to r[1]
            }
        }
        return c to v
    }

    /** KJV (chapter, verse) -> the translation's positions: usually one,
     *  several for merged/moved verses, empty for omissions. 1-based. */
    fun fromKjv(id: String, book: Int, c: Int, v: Int): List<Pair<Int, Int>> {
        val rs = runs(id, book) ?: return listOf(c to v)
        val out = ArrayList<Pair<Int, Int>>(1)
        var matched = false
        for (r in rs) {
            if (r[0] == c && v in r[1]..r[2]) {
                matched = true
                if (r[4] > r[5]) continue                 // omitted verse
                if (r[2] - r[1] == r[5] - r[4]) out.add(r[3] to r[4] + (v - r[1]))
                else for (tv in r[4]..r[5]) out.add(r[3] to tv)
            }
        }
        return if (!matched) listOf(c to v) else out
    }

    /** Convenience: joined text of a KJV reference in the given books. */
    fun textAt(id: String, books: List<Book>, book: Int, kc: Int, kv: Int): String =
        fromKjv(id, book, kc, kv).mapNotNull { (c, v) ->
            books.getOrNull(book)?.chapters?.getOrNull(c - 1)?.getOrNull(v - 1)
        }.filter { it.isNotBlank() }.joinToString(" ")
}
