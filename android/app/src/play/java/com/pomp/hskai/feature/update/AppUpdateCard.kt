package com.pomp.hskai.feature.update

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

/**
 * No update card in the Google Play build.
 *
 * Play updates the app itself, in the background, without anyone tapping
 * anything — and its policy forbids an app it distributes from updating
 * itself by any other route. So this is not a hidden feature: the download,
 * the install permission and the provider that would make one possible are
 * not compiled into this flavour at all.
 *
 * [modifier] is unused here and kept so that the `direct` source set can offer
 * the same signature, leaving the profile screen identical in both builds.
 */
@Composable
@Suppress("UNUSED_PARAMETER")
fun AppUpdateCard(modifier: Modifier = Modifier) {
    // Intentionally empty.
}
