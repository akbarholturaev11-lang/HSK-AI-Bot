package com.pomp.hskai.feature.update

import android.content.Context
import com.pomp.hskai.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** FCM fast-path for direct APK update notices. */
object UpdatePushHandler {
    suspend fun handle(context: Context, announcedVersionCode: Int): Boolean {
        if (announcedVersionCode <= BuildConfig.VERSION_CODE) return false
        val release = withContext(Dispatchers.IO) { fetchRelease(context) } ?: return false
        if (release.versionCode < announcedVersionCode) return false
        return UpdateNotices.announce(context, release)
    }
}
