package com.pomp.hskai.feature.limit

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.ViewModelStoreOwner
import com.pomp.hskai.data.repository.FeatureRepository

/**
 * The limit gate for the Google Play channel.
 *
 * This build has no subscription flow of its own and never sends the learner
 * out of the app to pay. It does two things: re-read access from the server,
 * and open support. A subscription bought through any other channel shows up
 * here on the next read, because access is only ever the server's answer.
 *
 * [repository] and [viewModelStoreOwner] are unused here and kept so that the
 * `direct` source set — which does need them — can offer the same signature,
 * leaving the app's screens identical in both builds.
 */
@Composable
fun rememberLimitGate(
    repository: FeatureRepository,
    viewModelStoreOwner: ViewModelStoreOwner,
    supportUrl: String,
    isRefreshing: Boolean,
    onRefreshAccess: () -> Unit,
): LimitGate {
    val context = LocalContext.current
    return LimitGate(
        state = LimitGateState(
            isBusy = isRefreshing,
            supportUrl = supportUrl,
        ),
        actions = LimitGateActions(
            onRecheck = onRefreshAccess,
            onSupport = { openExternal(context, supportUrl) },
        ),
    )
}

/** Opens the configured support contact. Never a payment page. */
private fun openExternal(context: Context, url: String): Boolean {
    if (url.isBlank()) return false
    return try {
        context.startActivity(
            Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
        )
        true
    } catch (_: ActivityNotFoundException) {
        false
    }
}
