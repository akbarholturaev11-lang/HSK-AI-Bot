package com.pomp.hskai.feature.update

import android.content.Context

/**
 * No release check in the Google Play build.
 *
 * Play already knows about every version it distributes and installs them
 * itself, so a background check here would only be the app telling someone
 * about work Play has done or is about to do.
 *
 * [context] is unused and kept so the `direct` source set can offer the same
 * signature, leaving the application class identical in both builds.
 */
@Suppress("UNUSED_PARAMETER")
object UpdateWatch {

    fun schedule(context: Context) {
        // Intentionally empty.
    }

    fun cancel(context: Context) {
        // Intentionally empty.
    }
}
