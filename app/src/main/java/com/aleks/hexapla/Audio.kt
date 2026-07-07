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
 * Narrated KJV audio (LibriVox, public domain), streamed from archive.org and
 * cached on device. Recordings are per *section* — one MP3 covering one or a
 * few chapters — so playback is section-aligned, not verse-aligned.
 */
object AudioRepo {

    /** One MP3 covering chapters [first]..[last] (1-based, inclusive). */
    data class Section(val first: Int, val last: Int, val url: String)

    private var cache: Map<Int, List<Section>>? = null
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

    private fun audioDir(context: Context) = File(context.filesDir, "audio")

    fun localFile(context: Context, url: String): File =
        File(audioDir(context), url.substringAfterLast('/'))

    fun isDownloaded(context: Context, url: String): Boolean =
        localFile(context, url).let { it.exists() && it.length() > 0 }

    /** Download to cache if needed; returns the local file or null on failure. */
    suspend fun ensureDownloaded(
        context: Context,
        url: String,
        onProgress: (Int) -> Unit = {}
    ): File? = withContext(Dispatchers.IO) {
        val dest = localFile(context, url)
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
