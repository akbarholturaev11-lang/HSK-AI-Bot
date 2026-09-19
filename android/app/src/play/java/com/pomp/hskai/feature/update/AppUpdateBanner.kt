package com.pomp.hskai.feature.update

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

/**
 * No update banner in the Google Play build.
 *
 * Play keeps the app current by itself, in the background, so there is nothing
 * to nudge anyone about — and its policy forbids an app it distributes from
 * updating itself by any other route. Nothing is hidden here: the download,
 * the install permission and the provider that would make one possible are not
 * compiled into this flavour at all.
 *
 * [modifier] is unused and kept so the `direct` source set can offer the same
 * signature, leaving the scaffold identical in both builds.
 */
@Composable
@Suppress("UNUSED_PARAMETER")
fun AppUpdateBanner(modifier: Modifier = Modifier) {
    // Intentionally empty.
}
