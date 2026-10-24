package com.pomp.hskai.feature.update

import android.content.Context
import android.app.NotificationManager
import androidx.work.WorkManager
import com.pomp.hskai.core.notify.AccountNoticePolicy

/**
 * No release check in the Google Play build.
 *
 * Play already knows about every version it distributes and installs them
 * itself, so a background check here would only be the app telling someone
 * about work Play has done or is about to do.
 *
 * A same-package Direct -> Play update retains WorkManager's database and
 * notification shade. Cancel that channel's old work and update notice.
 */
object UpdateWatch {

    fun schedule(context: Context) {
        cancel(context)
    }

    fun cancel(context: Context) {
        val manager = WorkManager.getInstance(context)
        manager.cancelUniqueWork("app_update_check_daily")
        manager.cancelUniqueWork("app_update_check_now")
        // WorkRequest adds its worker class name as a tag, including older
        // per-version downloads whose unique names we cannot know here.
        manager.cancelAllWorkByTag("com.pomp.hskai.feature.update.UpdateCheckWorker")
        manager.cancelAllWorkByTag("com.pomp.hskai.feature.update.UpdateDownloadWorker")
        context.getSystemService(NotificationManager::class.java)?.let { notifications ->
            notifications.cancel(4301)
            AccountNoticePolicy.playSuppressedNotificationIds().forEach(notifications::cancel)
        }
    }
}
