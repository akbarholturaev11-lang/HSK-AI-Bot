package com.pomp.hskai.feature.limit

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.ViewModelStoreOwner
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pomp.hskai.data.repository.FeatureRepository

/**
 * The limit gate for the `direct` channel (APK, website, Telegram).
 *
 * This channel may offer the existing subscription flow, which lives in the
 * Telegram bot: the app asks the server to post the subscription menu into
 * the learner's chat and opens it. Nothing is bought here, and entitlement is
 * re-read from the server when the learner comes back — never decided locally.
 *
 * The `play` source set has a function with this exact signature and no
 * subscription flow at all, so the app's screens are identical in both builds.
 */
@Composable
fun rememberLimitGate(
    repository: FeatureRepository,
    viewModelStoreOwner: ViewModelStoreOwner,
    supportUrl: String,
    isRefreshing: Boolean,
    onRefreshAccess: () -> Unit,
): LimitGate {
    val handoffViewModel: SubscriptionHandoffViewModel = viewModel(
        viewModelStoreOwner = viewModelStoreOwner,
        factory = SubscriptionHandoffViewModel.Factory(repository),
    )
    val handoffState by handoffViewModel.state.collectAsStateWithLifecycle()
    val pendingHandoff by handoffViewModel.handoff.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current

    // Opening Telegram is a one-shot effect: the request carries an id so a
    // recomposition cannot launch the same intent twice.
    LaunchedEffect(pendingHandoff?.id) {
        val request = pendingHandoff ?: return@LaunchedEffect
        handoffViewModel.onHandoffDelivered(
            id = request.id,
            opened = openTelegram(context, request.url),
        )
    }

    // Entitlement is re-read when the learner comes back from Telegram.
    DisposableEffect(lifecycleOwner, handoffState.awaitingReturn) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME && handoffState.awaitingReturn) {
                onRefreshAccess()
                handoffViewModel.onReturnHandled()
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    return LimitGate(
        state = LimitGateState(
            isBusy = handoffState.isOpening || isRefreshing,
            error = handoffState.error,
            supportUrl = supportUrl,
        ),
        actions = LimitGateActions(
            onUnlock = handoffViewModel::openSubscription,
            onRecheck = onRefreshAccess,
            onSupport = { openExternal(context, supportUrl) },
        ),
    )
}

/**
 * Opens the bot chat in Telegram, falling back to the browser when Telegram is
 * not installed. Returns false when nothing could handle the link, so the
 * caller can keep the learner informed instead of appearing to do nothing.
 */
private fun openTelegram(context: Context, url: String): Boolean {
    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }
    val telegramFirst = Intent(intent).setPackage("org.telegram.messenger")
    return try {
        context.startActivity(telegramFirst)
        true
    } catch (_: ActivityNotFoundException) {
        try {
            context.startActivity(intent)
            true
        } catch (_: ActivityNotFoundException) {
            false
        }
    }
}

/** Opens the configured support contact. */
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
