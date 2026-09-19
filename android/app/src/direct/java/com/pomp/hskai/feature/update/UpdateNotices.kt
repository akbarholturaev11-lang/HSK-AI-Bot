package com.pomp.hskai.feature.update

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.pomp.hskai.R
import com.pomp.hskai.core.i18n.AppLocale

/**
 * "A new version exists", said once per release and never again.
 *
 * This is the only part of updating that reaches someone who is not in the
 * app. It is deliberately thin: one notification per published release, no
 * repeat the next day, no second one after a reinstall of the same build. The
 * code of the last release announced is kept on the device, so the promise
 * survives the process dying and the app being reopened.
 *
 * Its own channel, apart from the study reminders: someone who wants to be
 * left alone about lessons may still want to hear about a broken build being
 * fixed, and the reverse. Only the `direct` channel has any of this — the Play
 * build is updated by Play itself.
 */
internal object UpdateNotices {

    const val CHANNEL_ID = "app_updates"
    private const val NOTIFICATION_ID = 4301
    private const val PREFS_NAME = "app_update_notices"
    private const val ANNOUNCED_KEY = "announced_version_code"

    /**
     * Posts the notification when this release has not been announced yet.
     *
     * Returns false whenever nothing was shown — already announced, no
     * permission, notifications switched off, or the system refusing the post
     * — so a release is never recorded as announced on the strength of a
     * notification that never appeared.
     */
    fun announce(context: Context, release: UpdateRelease): Boolean {
        if (!AppUpdate.shouldAnnounce(
                release = release,
                announcedVersionCode = announcedVersionCode(context),
            )
        ) {
            return false
        }

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

        val localized = AppLocale.wrap(context)
        ensureChannel(localized)

        // Tapping opens the app as the launcher would. The update itself is a
        // tap on the card or the banner, never something a notification starts
        // on its own.
        val intent = context.packageManager
            .getLaunchIntentForPackage(context.packageName)
            ?.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            ?: return false
        val pending = PendingIntent.getActivity(
            context,
            NOTIFICATION_ID,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val body = localized.getString(R.string.notify_update_body, release.versionName)
        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(localized.getString(R.string.notify_update_title))
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setCategory(NotificationCompat.CATEGORY_RECOMMENDATION)
            .setAutoCancel(true)
            .setContentIntent(pending)
            .build()

        return try {
            NotificationManagerCompat.from(context).notify(NOTIFICATION_ID, notification)
            recordAnnounced(context, release.versionCode)
            true
        } catch (_: SecurityException) {
            // The permission can be revoked between the check and the post.
            false
        }
    }

    /**
     * The channel must exist before the first post. Creating it again is a
     * no-op, so this is safe to call on every delivery.
     */
    private fun ensureChannel(context: Context) {
        val manager = context.getSystemService(NotificationManager::class.java) ?: return
        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_ID,
                context.getString(R.string.update_channel_name),
                NotificationManager.IMPORTANCE_DEFAULT,
            )
        )
    }

    private fun announcedVersionCode(context: Context): Int =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getInt(ANNOUNCED_KEY, 0)

    private fun recordAnnounced(context: Context, versionCode: Int) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putInt(ANNOUNCED_KEY, versionCode)
            .apply()
    }
}
