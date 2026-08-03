package com.aleks.hexapla

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File

/**
 * The downloadable music pack: which tracks exist for each mood, and where the
 * cached copies live.
 *
 * The four tracks bundled in the APK stay the offline default for EVERY mood,
 * so nobody loses music by being offline. This adds variety on top: 79 tracks
 * against 24 minutes of bundled audio, hosted on archive.org so the catalogue
 * costs nothing in install size.
 *
 * ⚠ A MISSING TRACK IS NOT SILENCE. If a mood's downloaded file is absent the
 * caller must fall back to a bundled track — unintended silence and the
 * deliberate `silence` mood must never be indistinguishable to the listener.
 */
object MusicRepo {

    data class Track(val file: String, val title: String, val ms: Int, val credit: String)

    private var base: String = ""
    private var byMood: Map<String, List<Track>> = emptyMap()
    private var pinned: Map<String, Track> = emptyMap()
    private var credits: List<String> = emptyList()
    private var loaded = false

    val isLoaded: Boolean get() = loaded
    fun creditLines(): List<String> = credits

    suspend fun load(context: Context) {
        if (loaded) return
        withContext(Dispatchers.IO) {
            try {
                val root = JSONObject(
                    context.assets.open("music_index.json").bufferedReader().use { it.readText() }
                )
                base = root.getString("base")
                val moods = root.getJSONObject("moods")
                byMood = buildMap {
                    for (mood in moods.keys()) {
                        val arr = moods.getJSONArray(mood)
                        put(mood, List(arr.length()) {
                            val o = arr.getJSONObject(it)
                            Track(o.getString("f"), o.getString("t"),
                                  o.getInt("ms"), o.getString("by"))
                        })
                    }
                }
                pinned = root.optJSONObject("pinned")?.let { p ->
                    buildMap {
                        for (k in p.keys()) {
                            val o = p.getJSONObject(k)
                            put(k, Track(o.getString("f"), o.getString("t"),
                                         o.getInt("ms"), o.getString("by")))
                        }
                    }
                } ?: emptyMap()
                credits = root.optJSONArray("credits")?.let { a ->
                    List(a.length()) { a.getString(it) }
                } ?: emptyList()
                loaded = true
            } catch (_: Exception) {
                loaded = false          // bundled tracks carry on regardless
            }
        }
    }

    private fun dir(context: Context) = File(context.filesDir, "music").apply { mkdirs() }

    private fun cacheFile(context: Context, rel: String) =
        File(dir(context), rel.replace('/', '_'))

    /** Total bytes of the pack already on disk. */
    fun downloadedBytes(context: Context): Long =
        dir(context).listFiles()?.sumOf { it.length() } ?: 0L

    fun downloadedCount(context: Context): Int =
        dir(context).listFiles()?.count { it.length() > 0 } ?: 0

    fun trackCount(): Int = byMood.values.sumOf { it.size } + pinned.size

    /** Every track, for the download-all action. */
    fun allTracks(): List<Track> = byMood.values.flatten() + pinned.values

    /**
     * A cached track for [mood], or null to use a bundled one.
     *
     * [seed] keeps the choice stable for a given passage instead of changing
     * every time the mood is re-evaluated — the bed must not shuffle while a
     * chapter is being read.
     */
    fun cachedFor(context: Context, mood: String, seed: Int): File? {
        val list = byMood[mood]?.filter { cacheFile(context, it.file).let { f -> f.exists() && f.length() > 0 } }
        if (list.isNullOrEmpty()) return null
        return cacheFile(context, list[Math.floorMod(seed, list.size)].file)
    }

    /** A specific pinned track (mood_map.json trackPin), if downloaded. */
    fun cachedPinned(context: Context, id: String): File? {
        val t = pinned[id] ?: return null
        val f = cacheFile(context, t.file)
        return if (f.exists() && f.length() > 0) f else null
    }

    fun urlFor(rel: String): String = "$base/$rel"

    /**
     * Download the whole pack. Reuses [AudioRepo.downloadTo]'s behaviour via
     * [AudioRepo.ensureDownloaded]-style retry semantics; progress is reported
     * as tracks completed so the UI can show something honest rather than a
     * spinner.
     */
    suspend fun downloadAll(
        context: Context,
        onProgress: (done: Int, total: Int) -> Unit = { _, _ -> }
    ): Int = withContext(Dispatchers.IO) {
        val all = allTracks()
        var ok = 0
        all.forEachIndexed { i, t ->
            val dest = cacheFile(context, t.file)
            if (dest.exists() && dest.length() > 0) ok++
            else if (AudioRepo.downloadMusic(urlFor(t.file), dest)) ok++
            onProgress(i + 1, all.size)
        }
        ok
    }

    /** Remove the downloaded pack; bundled music is untouched. */
    fun deleteAll(context: Context): Int {
        val files = dir(context).listFiles() ?: return 0
        var n = 0
        for (f in files) if (f.delete()) n++
        return n
    }
}
