package com.aleks.hexapla

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.Shader
import android.graphics.Typeface
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import java.util.Calendar

/**
 * "Album art" for the media notification / lock screen. Books with an iconic
 * Gustave Doré engraving (public domain, 1866) bundled under assets/bookart/
 * show it; the rest get a generated title-page cover with a deterministic
 * color per book.
 *
 * A book may ship more than one plate — "<idx>.webp" plus "<idx>_1.webp",
 * "<idx>_2.webp" and so on. When it does, the day picks which one shows, the
 * same date-seeded trick the widget's verse of the day uses: stable for the
 * whole day, different tomorrow.
 */
object BookArt {

    /** Keyed by resolved asset name, so the day's turnover refreshes it. */
    private val cache = HashMap<String, Bitmap>()
    private var variantIndex: Map<Int, List<String>>? = null

    /** bookIdx -> its plates, base first ('.' sorts before '_'). */
    private fun variants(context: Context): Map<Int, List<String>> = variantIndex ?: run {
        val byBook = HashMap<Int, MutableList<String>>()
        val names = try {
            context.assets.list("bookart") ?: emptyArray()
        } catch (_: Exception) { emptyArray() }
        for (name in names) {
            val stem = name.substringBeforeLast('.')
            val idx = stem.substringBefore('_').toIntOrNull() ?: continue
            byBook.getOrPut(idx) { mutableListOf() }.add(name)
        }
        byBook.mapValues { (_, v) -> v.sorted() }.also { variantIndex = it }
    }

    fun forBook(context: Context, bookIdx: Int, bookName: String): Bitmap {
        val plates = variants(context)[bookIdx].orEmpty()
        val asset = when {
            plates.isEmpty() -> null
            plates.size == 1 -> plates[0]
            else -> {
                val cal = Calendar.getInstance()
                val day = cal.get(Calendar.YEAR) * 1000 + cal.get(Calendar.DAY_OF_YEAR)
                // Offset by book so the whole library does not turn over in
                // lockstep — two books with two plates each stay out of phase.
                plates[Math.floorMod(day + bookIdx * 7, plates.size)]
            }
        }
        val key = asset ?: "generated/$bookIdx"
        cache[key]?.let { return it }
        val bmp = asset?.let { name ->
            try {
                context.assets.open("bookart/$name").use { BitmapFactory.decodeStream(it) }
            } catch (_: Exception) { null }
        } ?: generated(bookIdx, bookName)
        cache[key] = bmp
        return bmp
    }

    private fun generated(bookIdx: Int, bookName: String): Bitmap {
        val size = 512
        val bmp = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bmp)

        // Deterministic hue per book, stepped by the golden ratio for spread;
        // deep, muted tones fitting the app's old-book aesthetic.
        val hue = ((bookIdx * 137.5f) % 360f)
        val top = Color.HSVToColor(floatArrayOf(hue, 0.55f, 0.38f))
        val bottom = Color.HSVToColor(floatArrayOf(hue, 0.65f, 0.20f))
        val bg = Paint().apply {
            shader = LinearGradient(
                0f, 0f, 0f, size.toFloat(), top, bottom, Shader.TileMode.CLAMP
            )
        }
        canvas.drawRect(0f, 0f, size.toFloat(), size.toFloat(), bg)

        val titlePaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.rgb(0xF3, 0xEE, 0xE4)
            typeface = Typeface.create(Typeface.SERIF, Typeface.BOLD)
            textSize = if (bookName.length > 12) 64f else 84f
        }
        val layout = StaticLayout.Builder
            .obtain(bookName, 0, bookName.length, titlePaint, size - 96)
            .setAlignment(Layout.Alignment.ALIGN_CENTER)
            .setLineSpacing(0f, 1.1f)
            .build()
        canvas.save()
        canvas.translate(48f, (size - layout.height) / 2f)
        layout.draw(canvas)
        canvas.restore()

        // Thin rule above and below the title, like a classic title page.
        val rule = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.argb(140, 0xF3, 0xEE, 0xE4)
            strokeWidth = 3f
        }
        val y1 = (size - layout.height) / 2f - 36f
        val y2 = (size + layout.height) / 2f + 36f
        canvas.drawLine(96f, y1, size - 96f, y1, rule)
        canvas.drawLine(96f, y2, size - 96f, y2, rule)

        val appPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.argb(150, 0xF3, 0xEE, 0xE4)
            textSize = 28f
            textAlign = Paint.Align.CENTER
        }
        canvas.drawText("HEXAPLA", size / 2f, size - 44f, appPaint)
        return bmp
    }
}
