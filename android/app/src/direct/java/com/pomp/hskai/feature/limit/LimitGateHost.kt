package com.pomp.hskai.feature.limit

import android.content.ActivityNotFoundException
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

/** The APK opens a native checkout; access is always refreshed from the server. */
@Composable
fun rememberLimitGate(
    repository: FeatureRepository,
    viewModelStoreOwner: ViewModelStoreOwner,
    supportUrl: String,
    isRefreshing: Boolean,
    onRefreshAccess: () -> Unit,
    onOpenSubscription: () -> Unit = {},
    trialEligible: Boolean = false,
    trialStarting: Boolean = false,
    trialError: String = "",
    onStartTrial: () -> Unit = {},
): LimitGate {
    val context = LocalContext.current
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
            canSubscribe = true,
        ),
        actions = LimitGateActions(
            onUnlock = onOpenSubscription,
            onRecheck = {
                recheckAsked = true
                recheckFoundNothing = false
                onRefreshAccess()
            },
            onSupport = {
                if (supportUrl.isNotBlank()) {
                    try {
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(supportUrl)))
                    } catch (_: ActivityNotFoundException) { }
                }
            },
            onStartTrial = onStartTrial,
        ),
    )
}
