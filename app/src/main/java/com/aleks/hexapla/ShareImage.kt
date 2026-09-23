package com.aleks.hexapla

import android.content.Context
import android.content.Intent
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
import androidx.core.content.FileProvider
import java.io.File

/** Renders a verse to a shareable image card and launches the share sheet. */
object ShareImage {

    /** The whole Good News plan as one tall card: steps, verses, references. */
    fun shareGospel(
        context: Context,
        title: String,
        steps: List<Pair<String, List<Pair<String, String>>>>
    ) {
        val w = 1080
        val margin = 84f
        val bg = Color.rgb(0x21, 0x1F, 0x1A)
        val ink = Color.rgb(0xE8, 0xE2, 0xD9)
        val accent = Color.rgb(0xD8, 0xB9, 0xC3)

        val titlePaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
            color = ink; textSize = 64f
            typeface = Typeface.create(Typeface.SERIF, Typeface.BOLD)
        }
        val stepPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
            color = accent; textSize = 44f
            typeface = Typeface.create(Typeface.SERIF, Typeface.BOLD)
        }
        val refPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
            color = accent; textSize = 30f
            typeface = Typeface.create(Typeface.SERIF, Typeface.BOLD)
        }
        val versePaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
            color = ink; textSize = 36f
            typeface = Typeface.create(Typeface.SERIF, Typeface.NORMAL)
        }
        val width = (w - 2 * margin).toInt()
        fun layoutOf(text: String, paint: TextPaint): StaticLayout =
            StaticLayout.Builder.obtain(text, 0, text.length, paint, width)
                .setAlignment(Layout.Alignment.ALIGN_NORMAL)
                .setLineSpacing(0f, 1.25f)
                .build()

        // Header art: Doré's Crucifixion, blending down into the text area.
        val header: Bitmap? = try {
            context.assets.open("gospel_header.webp").use { BitmapFactory.decodeStream(it) }
        } catch (_: Exception) { null }
        val headerH = header?.let { it.height * w / it.width } ?: 0

        // Measure pass.
        val titleL = layoutOf(title, titlePaint)
        var h = headerH + 70f + titleL.height + 60f
        val stepLayouts = steps.map { (stepTitle, verses) ->
            val sl = layoutOf(stepTitle, stepPaint)
            val vls = verses.map { (ref, text) ->
                layoutOf(ref, refPaint) to layoutOf("«$text»", versePaint)
            }
            h += sl.height + 28f + vls.sumOf { (r, v) -> (r.height + v.height + 34).toDouble() }.toFloat() + 40f
            sl to vls
        }
        h += 110f

        val bmp = Bitmap.createBitmap(w, h.toInt(), Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bmp)
        canvas.drawColor(bg)
        if (header != null) {
            canvas.drawBitmap(
                header, null,
                android.graphics.Rect(0, 0, w, headerH), null
            )
            // Fade the engraving's lower third into the background color.
            val fade = Paint().apply {
                shader = LinearGradient(
                    0f, headerH * 0.55f, 0f, headerH.toFloat(),
                    Color.TRANSPARENT, bg, Shader.TileMode.CLAMP
                )
            }
            canvas.drawRect(0f, headerH * 0.55f, w.toFloat(), headerH.toFloat(), fade)
            header.recycle()
        }
        var y = headerH + 70f
        fun draw(l: StaticLayout) {
            canvas.save(); canvas.translate(margin, y); l.draw(canvas); canvas.restore()
            y += l.height
        }
        draw(titleL); y += 60f
        for ((sl, vls) in stepLayouts) {
            draw(sl); y += 28f
            for ((rl, vl) in vls) {
                draw(rl); y += 6f
                draw(vl); y += 28f
            }
            y += 40f
        }
        val appPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.argb(150, 0xE8, 0xE2, 0xD9); textSize = 30f
        }
        canvas.drawText(context.getString(R.string.app_name), margin, h - 60f, appPaint)

        val dir = File(context.cacheDir, "images").apply { mkdirs() }
        val file = File(dir, "gospel.png")
        file.outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
        bmp.recycle()
        val uri = FileProvider.getUriForFile(context, context.packageName + ".fileprovider", file)
        val send = Intent(Intent.ACTION_SEND).apply {
            type = "image/png"
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(Intent.createChooser(send, title))
    }

    fun share(context: Context, verse: String, reference: String) {
        val w = 1080
        val margin = 96f

        val versePaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.rgb(0xE8, 0xE2, 0xD9)
            typeface = Typeface.create(Typeface.SERIF, Typeface.NORMAL)
            textSize = if (verse.length > 300) 44f else 56f
        }
        val refPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.rgb(0xD8, 0xB9, 0xC3)
            typeface = Typeface.create(Typeface.SERIF, Typeface.BOLD)
            textSize = 40f
        }
        val appPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.argb(150, 0xE8, 0xE2, 0xD9)
            textSize = 30f
        }

        val layout = StaticLayout.Builder
            .obtain("«$verse»", 0, verse.length + 2, versePaint, (w - 2 * margin).toInt())
            .setAlignment(Layout.Alignment.ALIGN_NORMAL)
            .setLineSpacing(0f, 1.35f)
            .build()

        val h = (layout.height + 420).coerceAtLeast(720)
        val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bmp)
        canvas.drawColor(Color.rgb(0x21, 0x1F, 0x1A))

        canvas.save()
        canvas.translate(margin, 180f)
        layout.draw(canvas)
        canvas.restore()

        canvas.drawText(reference, margin, 180f + layout.height + 90f, refPaint)
        canvas.drawText(
            context.getString(R.string.app_name),
            margin, h - 72f, appPaint
        )

        val dir = File(context.cacheDir, "images").apply { mkdirs() }
        val file = File(dir, "verse.png")
        file.outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
        bmp.recycle()

        val uri = FileProvider.getUriForFile(
            context, context.packageName + ".fileprovider", file
        )
        val send = Intent(Intent.ACTION_SEND).apply {
            type = "image/png"
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(Intent.createChooser(send, reference))
    }
}
