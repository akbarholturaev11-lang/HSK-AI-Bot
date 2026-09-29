package com.pomp.hskai.core.notify

import android.Manifest
import android.app.Notification
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
import com.pomp.hskai.MainActivity
import com.pomp.hskai.R
import com.pomp.hskai.core.i18n.AppLocale
import com.pomp.hskai.core.navigation.DeepLinkRouter
import com.pomp.hskai.data.api.AccountNoticeDto

/**
 * Subscription and limit notices the server sends here before Telegram.
 *
 * The text comes from the server, already in the learner's language. Their own
 * channel keeps them apart from study reminders and payment decisions, so each
 * can be muted without silencing the others.
 */
object AccountNotifications {
    const val CHANNEL_ID = "account_notices_v1"

    fun ensureChannel(context: Context) {
        val manager = context.getSystemService(NotificationManager::class.java) ?: return
        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_ID,
                context.getString(R.string.notify_account_channel),
                NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                description = context.getString(R.string.notify_account_channel_body)
                setShowBadge(true)
                lockscreenVisibility = Notification.VISIBILITY_PUBLIC
            }
        )
    }

    /** Whether a notice would actually appear; the server is told the answer. */
    fun canPost(context: Context): Boolean {
        ensureChannel(AppLocale.wrap(context))
        return NotificationManagerCompat.from(context).areNotificationsEnabled() &&
            (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
                ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) ==
                PackageManager.PERMISSION_GRANTED) &&
            context.getSystemService(NotificationManager::class.java)
                ?.getNotificationChannel(CHANNEL_ID)?.importance != NotificationManager.IMPORTANCE_NONE
    }

    /** Returns false when nothing was shown, so the server falls back to Telegram. */
    fun post(context: Context, notice: AccountNoticeDto): Boolean {
        val title = notice.title.trim()
        val body = notice.body.trim()
        if (title.isEmpty() && body.isEmpty()) return false
        if (!canPost(context)) return false

        val notificationId = AccountNoticePolicy.notificationId(notice.key)
        val intent = Intent(context, MainActivity::class.java).apply {
            action = Intent.ACTION_VIEW
            data = Uri.parse(DeepLinkRouter.uriFor(AccountNoticePolicy.destination(notice.action)))
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pending = PendingIntent.getActivity(
            context, notificationId, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(title.ifEmpty { body })
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_STATUS)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setAutoCancel(true)
            .setContentIntent(pending)
            .build()
        return try {
            NotificationManagerCompat.from(context).notify(notificationId, notification)
            true
        } catch (_: SecurityException) {
            // The permission can be revoked between the check and the post.
            false
        }
    }
}
