package com.pomp.hskai.feature.update

import android.content.Context

/** Google Play owns updates in the Play flavour; external update push is ignored. */
object UpdatePushHandler {
    @Suppress("UNUSED_PARAMETER")
    suspend fun handle(context: Context, announcedVersionCode: Int): Boolean = false
}
