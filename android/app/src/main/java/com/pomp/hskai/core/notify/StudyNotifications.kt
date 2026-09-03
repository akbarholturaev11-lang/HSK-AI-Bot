package com.pomp.hskai.core.notify

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.pomp.hskai.R
import com.pomp.hskai.core.navigation.AppDestination
import com.pomp.hskai.core.navigation.DeepLinkRouter

/**
 * Study reminders shown on the device itself.
 *
 * These are local: nothing is pushed from a server and no notification token
 * leaves the device. The bot keeps sending its own Telegram reminders — this
 * is the same opt-in flag, honoured a second time on the phone.
 */
object StudyNotifications {

    const val CHANNEL_ID = "study_reminders"
    private const val REMINDER_NOTIFICATION_ID = 4201

    /**
     * The channel must exist before the first post. Creating it again is a
     * no-op, so this is safe to call on every delivery.
     */
    fun ensureChannel(context: Context) {
        val manager = context.getSystemService(NotificationManager::class.java) ?: return
        val channel = NotificationChannel(
            CHANNEL_ID,
            context.getString(R.string.notify_channel_name),
            NotificationManager.IMPORTANCE_DEFAULT,
        ).apply {
            description = context.getString(R.string.notify_channel_body)
            setShowBadge(true)
        }
        manager.createNotificationChannel(channel)
    }

    /**
     * Whether a notification would actually be shown.
     *
     * `POST_NOTIFICATIONS` only exists from Android 13; asking about it on an
     * older release reports "denied" for a permission the platform does not
     * have, which would silence reminders on every device below 13. There the
     * honest question is whether the user has switched the app's notifications
     * off in system settings.
     */
    fun canPost(context: Context): Boolean =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.POST_NOTIFICATIONS,
            ) == PackageManager.PERMISSION_GRANTED
        } else {
            NotificationManagerCompat.from(context).areNotificationsEnabled()
        }

    /**
     * Posts the reminder. Returns false when the system refused it, so the
     * caller does not record a delivery that never happened.
     */
    fun postReminder(context: Context, reminder: Reminder): Boolean {
        if (reminder == Reminder.NONE) return false
        // Repeated inline rather than delegated: this is the guard that keeps
        // the notify() call below legal, and it has to be visible right here.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.POST_NOTIFICATIONS,
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            return false
        }
        if (!NotificationManagerCompat.from(context).areNotificationsEnabled()) return false

        ensureChannel(context)

        val (titleRes, bodyRes) = when (reminder) {
            Reminder.STREAK_AT_RISK ->
                R.string.notify_streak_title to R.string.notify_streak_body

            Reminder.DAILY_GOAL ->
                R.string.notify_goal_title to R.string.notify_goal_body

            Reminder.NONE -> return false
        }

        // Tapping opens the lesson the server says is next. Resolving the link
        // is not authorisation: the app still checks entitlement before the
        // lesson renders.
        val intent = Intent(
            Intent.ACTION_VIEW,
            Uri.parse(DeepLinkRouter.uriFor(AppDestination.CurrentLesson)),
        ).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            setPackage(context.packageName)
        }
        val pending = PendingIntent.getActivity(
            context,
            REMINDER_NOTIFICATION_ID,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(context.getString(titleRes))
            .setContentText(context.getString(bodyRes))
            .setStyle(NotificationCompat.BigTextStyle().bigText(context.getString(bodyRes)))
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setCategory(NotificationCompat.CATEGORY_REMINDER)
            .setAutoCancel(true)
            .setContentIntent(pending)
            .build()

        return try {
            NotificationManagerCompat.from(context)
                .notify(REMINDER_NOTIFICATION_ID, notification)
            true
        } catch (_: SecurityException) {
            // The permission can be revoked between the check and the post.
            false
        }
    }

    /** Clears a pending reminder, used when reminders are switched off. */
    fun cancelReminder(context: Context) {
        NotificationManagerCompat.from(context).cancel(REMINDER_NOTIFICATION_ID)
    }
}
