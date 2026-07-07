package com.aleks.hexapla

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.content.Intent
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
                ids.forEach { id ->
                    val views = RemoteViews(context.packageName, R.layout.widget_verse).apply {
                        setTextViewText(R.id.widget_verse, "«${verses[v].trim()}»")
                        setTextViewText(R.id.widget_ref, "${books[b].name} ${c + 1}:${v + 1}")
                        setTextViewText(R.id.widget_continue, continueLabel)
                        setOnClickPendingIntent(
                            R.id.widget_root,
                            PendingIntent.getActivity(
                                context, 0,
                                Intent(context, MainActivity::class.java),
                                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
                            )
                        )
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
}
