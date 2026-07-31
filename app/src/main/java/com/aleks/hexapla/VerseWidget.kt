package com.aleks.hexapla

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapShader
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Shader
import android.widget.RemoteViews
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.util.Calendar
import kotlin.random.Random

/**
 * Home-screen widget: verse of the day + a "continue reading" tap target.
 * The verse is picked deterministically from the primary translation, seeded
 * by the date, so every update that day shows the same verse.
 */
class VerseWidget : AppWidgetProvider() {

    override fun onUpdate(context: Context, manager: AppWidgetManager, ids: IntArray) {
        // updatePeriodMillis is batched and not midnight-aligned; schedule our
        // own refresh just past midnight so the verse changes with the date.
        scheduleMidnightUpdate(context)
        val pending = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val settings = Store.currentSettings(context)
                val books = BibleRepo.load(context, settings.primaryId).take(66)
                val cal = Calendar.getInstance()
                val seed = cal.get(Calendar.YEAR) * 1000 + cal.get(Calendar.DAY_OF_YEAR)
                val rnd = Random(seed)
                val candidates = books.indices.filter { books[it].chapters.isNotEmpty() }
                val b = candidates[rnd.nextInt(candidates.size)]
                val c = rnd.nextInt(books[b].chapters.size)
                val verses = books[b].chapters[c]
                val v = rnd.nextInt(verses.size)

                val continueLabel = context.getString(
                    R.string.widget_continue,
                    "${books[settings.lastBook.coerceIn(books.indices)].name} ${settings.lastChapter + 1}"
                )
                // Book cover art, scaled down and rounded for the widget.
                val art = roundedCorners(
                    Bitmap.createScaledBitmap(BookArt.forBook(context, b, books[b].name), 256, 256, true),
                    28f
                )
                ids.forEach { id ->
                    val views = RemoteViews(context.packageName, R.layout.widget_verse).apply {
                        setImageViewBitmap(R.id.widget_art, art)
                        setTextViewText(R.id.widget_verse, "«${verses[v].trim()}»")
                        setTextViewText(R.id.widget_ref, "${books[b].name} ${c + 1}:${v + 1}")
                        setTextViewText(R.id.widget_continue, continueLabel)
                        // TWO tap targets. The widget shows a verse AND a
                        // "continue reading" line, so it needs one intent each
                        // — it previously had a single root target, and the
                        // verse only ever seemed to open because the daily
                        // reminder was overwriting this PendingIntent's extras
                        // (owner-reported 2026-07-31: tapping Philemon 1:19
                        // opened Exodus once that collision was fixed).
                        //
                        // ⚠ REQUEST CODES MUST STAY DISTINCT. PendingIntent
                        // identity ignores extras, so any two built with the
                        // same code collapse into one object and
                        // FLAG_UPDATE_CURRENT lets the later one rewrite the
                        // earlier one's extras. Allocation across the app:
                        //   1 widget "continue reading"   2 media notification
                        //   3 daily reminder              4 widget verse
                        // Root = continue reading; a child target wins for
                        // taps inside it, so the verse area overrides the root.
                        // "Continue reading" must carry the saved position
                        // EXPLICITLY. An extras-free intent only brings the
                        // existing task to the front — and since the saved
                        // position is restored just once per process, tapping
                        // it while the app was already showing the widget's
                        // verse did nothing at all (owner-reported 2026-07-31:
                        // "Continue reading Exodus" kept showing Philemon).
                        // EXTRA_PEEK=false marks it a deliberate move, so it
                        // sets the reading spot rather than peeking at it.
                        setOnClickPendingIntent(
                            R.id.widget_root,
                            PendingIntent.getActivity(
                                context, 1,
                                Intent(context, MainActivity::class.java)
                                    .putExtra(MainActivity.EXTRA_BOOK,
                                        settings.lastBook.coerceIn(books.indices))
                                    .putExtra(MainActivity.EXTRA_CHAPTER, settings.lastChapter)
                                    .putExtra(MainActivity.EXTRA_VERSE, settings.lastVerse)
                                    .putExtra(MainActivity.EXTRA_PEEK, false),
                                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
                            )
                        )
                        // Opens the verse being quoted. MainActivity treats a
                        // deep link as a PEEK, so looking at today's verse does
                        // not overwrite the saved reading position.
                        val versePi = PendingIntent.getActivity(
                            context, 4,
                            Intent(context, MainActivity::class.java)
                                .putExtra(MainActivity.EXTRA_BOOK, b)
                                .putExtra(MainActivity.EXTRA_CHAPTER, c)
                                .putExtra(MainActivity.EXTRA_VERSE, v),
                            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
                        )
                        setOnClickPendingIntent(R.id.widget_verse, versePi)
                        setOnClickPendingIntent(R.id.widget_ref, versePi)
                        setOnClickPendingIntent(R.id.widget_art, versePi)
                    }
                    manager.updateAppWidget(id, views)
                }
            } catch (_: Exception) {
                // Leave the previous widget content in place on any failure.
            } finally {
                pending.finish()
            }
        }
    }

    private fun scheduleMidnightUpdate(context: Context) {
        val ids = AppWidgetManager.getInstance(context)
            .getAppWidgetIds(android.content.ComponentName(context, VerseWidget::class.java))
        if (ids.isEmpty()) return
        val intent = Intent(context, VerseWidget::class.java)
            .setAction(AppWidgetManager.ACTION_APPWIDGET_UPDATE)
            .putExtra(AppWidgetManager.EXTRA_APPWIDGET_IDS, ids)
        val pi = PendingIntent.getBroadcast(
            context, 7, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val midnight = Calendar.getInstance().apply {
            add(Calendar.DAY_OF_YEAR, 1)
            set(Calendar.HOUR_OF_DAY, 0)
            set(Calendar.MINUTE, 2)
            set(Calendar.SECOND, 0)
        }
        val am = context.getSystemService(Context.ALARM_SERVICE) as android.app.AlarmManager
        // Inexact, non-waking: fires when the device is next awake after
        // midnight, which is exactly when a home-screen widget matters.
        am.set(android.app.AlarmManager.RTC, midnight.timeInMillis, pi)
    }

    private fun roundedCorners(src: Bitmap, radius: Float): Bitmap {
        val out = Bitmap.createBitmap(src.width, src.height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(out)
        val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            shader = BitmapShader(src, Shader.TileMode.CLAMP, Shader.TileMode.CLAMP)
        }
        canvas.drawRoundRect(
            RectF(0f, 0f, src.width.toFloat(), src.height.toFloat()), radius, radius, paint
        )
        return out
    }
}
