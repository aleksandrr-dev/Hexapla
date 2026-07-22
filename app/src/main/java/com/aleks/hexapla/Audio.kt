package com.aleks.hexapla

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * Narrated KJV audio streamed from archive.org and cached on device.
 * LibriVox (public domain) for 44 books; Kokoro TTS (am_adam, Apache 2.0)
 * for the remaining 22. Recordings are per *section* — one file covering
 * one or a few chapters.
 */
object AudioRepo {

    /**
     * One audio file covering chapters [first]..[last] (1-based, inclusive).
     * [generated] true = self-generated per-chapter narration (one file per
     * chapter; its URL tail `<ch>.ogg` repeats across books, so it is cached
     * by full archive path, see [generatedFile]); false = LibriVox section.
     * Both download-and-cache on device — the app plays offline after the
     * first listen either way.
     */
    data class Section(
        val first: Int,
        val last: Int,
        val url: String,
        val generated: Boolean = false
    )

    private var cache: Map<Int, List<Section>>? = null
    private var genCache: MutableMap<String, Map<Int, List<Section>>> = HashMap()
    private val mutex = Mutex()

    /** Book index → ordered sections. Books absent here have no narration. */
    suspend fun index(context: Context): Map<Int, List<Section>> = mutex.withLock {
        cache ?: withContext(Dispatchers.IO) {
            val o = org.json.JSONObject(
                context.assets.open("audio_index.json").readBytes().toString(Charsets.UTF_8)
            )
            val m = HashMap<Int, List<Section>>()
            for (k in o.keys()) {
                val arr = o.getJSONArray(k)
                m[k.toInt()] = (0 until arr.length()).map { i ->
                    val s = arr.getJSONArray(i)
                    Section(s.getInt(0), s.getInt(1), s.getString(2))
                }
            }
            m
        }.also { cache = it }
    }

    /** The section containing the given 0-based chapter, or null. */
    fun sectionFor(sections: List<Section>?, chapter: Int): Section? =
        sections?.firstOrNull { chapter + 1 in it.first..it.last }

    /**
     * Self-generated narration (e.g. Webster), streamed per chapter from
     * archive.org. Returns bookIdx → one single-chapter [Section] per rendered
     * chapter, or an empty map if this translation has no generated audio.
     * Reads assets/audio_index_gen.json, produced by tools/build_audio_index_gen.py.
     */
    suspend fun generated(context: Context, translationId: String): Map<Int, List<Section>> =
        mutex.withLock {
            genCache[translationId] ?: withContext(Dispatchers.IO) {
                val root = try {
                    org.json.JSONObject(
                        context.assets.open("audio_index_gen.json")
                            .readBytes().toString(Charsets.UTF_8)
                    )
                } catch (_: Exception) { org.json.JSONObject() }
                val set = root.optJSONObject(translationId)
                val m = HashMap<Int, List<Section>>()
                if (set != null) {
                    for (bk in set.keys()) {
                        val book = set.getJSONObject(bk)
                        val base = book.getString("base")
                        val chapters = book.getJSONObject("chapters")
                        val list = ArrayList<Section>()
                        for (ck in chapters.keys()) {
                            val ch = ck.toInt()  // 0-based
                            val f = chapters.getJSONObject(ck).getString("f")
                            // One file per chapter: first == last == 1-based chapter.
                            list.add(Section(ch + 1, ch + 1, "$base/$f", generated = true))
                        }
                        m[bk.toInt()] = list.sortedBy { it.first }
                    }
                }
                m
            }.also { genCache[translationId] = it }
        }

    private fun audioDir(context: Context) = File(context.filesDir, "audio")

    fun localFile(context: Context, url: String): File =
        File(audioDir(context), url.substringAfterLast('/'))

    /**
     * Cache file for generated per-chapter audio. Its URL tail (`5.ogg`)
     * repeats across books, so keying by [localFile]'s last-segment rule
     * would collide; key by the full archive path instead
     * (`item/book/chapter.ogg` → `item_book_chapter.ogg`), unique per chapter.
     */
    fun generatedFile(context: Context, url: String): File {
        val key = url.substringAfter("/download/", url.substringAfterLast('/'))
            .replace('/', '_')
        return File(audioDir(context), key)
    }

    fun isDownloaded(context: Context, url: String): Boolean =
        localFile(context, url).let { it.exists() && it.length() > 0 }

    /** LibriVox: download to the last-segment cache file if needed. */
    suspend fun ensureDownloaded(
        context: Context,
        url: String,
        onProgress: (Int) -> Unit = {}
    ): File? = downloadTo(url, localFile(context, url), onProgress)

    /** Generated narration: download to the collision-free cache file. */
    suspend fun ensureDownloadedGen(
        context: Context,
        url: String,
        onProgress: (Int) -> Unit = {}
    ): File? = downloadTo(url, generatedFile(context, url), onProgress)

    /** Download [url] to [dest] if not already cached; local file or null. */
    private suspend fun downloadTo(
        url: String,
        dest: File,
        onProgress: (Int) -> Unit
    ): File? = withContext(Dispatchers.IO) {
        if (dest.exists() && dest.length() > 0) return@withContext dest
        dest.parentFile?.mkdirs()
        val tmp = File(dest.path + ".part")
        try {
            val conn = URL(url).openConnection() as HttpURLConnection
            conn.connectTimeout = 15_000
            conn.readTimeout = 30_000
            conn.instanceFollowRedirects = true
            val total = conn.contentLengthLong
            conn.inputStream.use { input ->
                tmp.outputStream().use { output ->
                    val buf = ByteArray(64 * 1024)
                    var read = 0L
                    while (true) {
                        val n = input.read(buf)
                        if (n < 0) break
                        output.write(buf, 0, n)
                        read += n
                        if (total > 0) onProgress((read * 100 / total).toInt())
                    }
                }
            }
            if (tmp.renameTo(dest)) dest else null
        } catch (_: Exception) {
            tmp.delete()
            null
        }
    }

    fun downloadedBytes(context: Context): Long =
        audioDir(context).walkTopDown().filter { it.isFile }.sumOf { it.length() }

    fun clearDownloads(context: Context) {
        audioDir(context).deleteRecursively()
    }
}
