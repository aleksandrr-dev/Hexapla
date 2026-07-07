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

/**
 * "Album art" for the media notification / lock screen. Books with an iconic
 * Gustave Doré engraving (public domain, 1866) bundled under assets/bookart/
 * show it; the rest get a generated title-page cover with a deterministic
 * color per book.
 */
object BookArt {

    private val cache = HashMap<Int, Bitmap>()

    fun forBook(context: Context, bookIdx: Int, bookName: String): Bitmap = cache.getOrPut(bookIdx) {
        try {
            context.assets.open("bookart/$bookIdx.webp").use { BitmapFactory.decodeStream(it) }
        } catch (_: Exception) { null } ?: generated(bookIdx, bookName)
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
