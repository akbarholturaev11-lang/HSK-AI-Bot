package com.pomp.hskai.feature.limit

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
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
    trialEligible: Boolean = false,
    trialStarting: Boolean = false,
    trialError: String = "",
    onStartTrial: () -> Unit = {},
): LimitGate {
    val context = LocalContext.current
    // A re-check that changed nothing has to say so: a subscription that
    // arrived closes this block, so a block still standing after the read is
    // the answer — and silence reads as a dead button.
    var recheckAsked by remember { mutableStateOf(false) }
    var recheckFoundNothing by remember { mutableStateOf(false) }
    LaunchedEffect(isRefreshing) {
        if (isRefreshing) {
            if (recheckAsked) recheckFoundNothing = false
        } else if (recheckAsked) {
            recheckAsked = false
            recheckFoundNothing = true
        }
    }

    return LimitGate(
        state = LimitGateState(
            isBusy = isRefreshing,
            supportUrl = supportUrl,
            recheckFoundNothing = recheckFoundNothing,
            trialEligible = trialEligible,
            trialStarting = trialStarting,
            trialError = trialError,
            canSubscribe = false,
        ),
        actions = LimitGateActions(
            onRecheck = {
                recheckAsked = true
                recheckFoundNothing = false
                onRefreshAccess()
            },
            onSupport = { openExternal(context, supportUrl) },
            onStartTrial = onStartTrial,
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
