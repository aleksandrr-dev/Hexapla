package com.aleks.hexapla

import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.util.Calendar

object Reminders {
    const val CHANNEL_ID = "reading_reminder"
    private const val REQUEST_CODE = 1001

    fun ensureChannel(context: Context) {
        val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (nm.getNotificationChannel(CHANNEL_ID) == null) {
            nm.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_ID,
                    context.getString(R.string.notification_channel),
                    NotificationManager.IMPORTANCE_DEFAULT
                )
            )
        }
    }

    private fun pendingIntent(context: Context): PendingIntent =
        PendingIntent.getBroadcast(
            context, REQUEST_CODE,
            Intent(context, ReminderReceiver::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

    fun schedule(context: Context, hour: Int, minute: Int) {
        ensureChannel(context)
        val am = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val cal = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, hour)
            set(Calendar.MINUTE, minute)
            set(Calendar.SECOND, 0)
            if (timeInMillis <= System.currentTimeMillis()) add(Calendar.DAY_OF_YEAR, 1)
        }
        am.setInexactRepeating(
            AlarmManager.RTC_WAKEUP,
            cal.timeInMillis,
            AlarmManager.INTERVAL_DAY,
            pendingIntent(context)
        )
    }

    fun cancel(context: Context) {
        val am = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        am.cancel(pendingIntent(context))
    }
}

class ReminderReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val pending = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            Reminders.ensureChannel(context)
            // Verse of the day, in the user's primary translation, from the
            // curated topical pool; falls back to the generic reminder text.
            var target: IntArray? = null
            val (title, text) = try {
                val settings = Store.currentSettings(context)
                val books = BibleRepo.load(context, settings.primaryId)
                val pool = (Topics.study + Topics.help).flatMap { it.refs }
                val day = Calendar.getInstance().get(Calendar.DAY_OF_YEAR)
                val ref = pool[day % pool.size]
                val bk = books.getOrNull(ref.book)
                val chIdx = if (ref.book == 18 && (bk?.chapters?.size ?: 0) >= 151 &&
                    ref.chapter in 9..146) ref.chapter - 1 else ref.chapter
                val verse = bk?.chapters?.getOrNull(chIdx)?.getOrNull(ref.verseStart)
                if (bk != null && !verse.isNullOrBlank()) {
                    target = intArrayOf(ref.book, chIdx, ref.verseStart)
                    "${bk.name} ${chIdx + 1}:${ref.verseStart + 1}" to verse
                } else
                    context.getString(R.string.notification_title) to
                            context.getString(R.string.notification_text)
            } catch (_: Exception) {
                context.getString(R.string.notification_title) to
                        context.getString(R.string.notification_text)
            }

            // Tapping the notification opens the app at the shown verse.
            val openIntent = Intent(context, MainActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
                target?.let {
                    putExtra(MainActivity.EXTRA_BOOK, it[0])
                    putExtra(MainActivity.EXTRA_CHAPTER, it[1])
                    putExtra(MainActivity.EXTRA_VERSE, it[2])
                }
            }
            val open = PendingIntent.getActivity(
                context, 0, openIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            val notification = android.app.Notification.Builder(context, Reminders.CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_book)
                .setContentTitle(title)
                .setContentText(text)
                .setStyle(android.app.Notification.BigTextStyle().bigText(text))
                .setContentIntent(open)
                .setAutoCancel(true)
                .build()
            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            try {
                nm.notify(1, notification)
            } catch (_: SecurityException) {
                // Notification permission revoked; ignore.
            }
            pending.finish()
        }
    }
}

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            val pending = goAsync()
            CoroutineScope(Dispatchers.IO).launch {
                val s = Store.currentSettings(context)
                if (s.reminderEnabled) Reminders.schedule(context, s.reminderHour, s.reminderMinute)
                pending.finish()
            }
        }
    }
}
