package com.pomp.hskai.feature.offline

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.Stable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.navigation.LocalMainBottomInset
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay

const val OFFLINE_BANNER_TAG = "offline_banner"
const val OFFLINE_REQUIRED_TAG = "offline_required"

/** A request that arrives with the network gets this long for DNS and routes to settle. */
private const val SETTLE_MILLIS = 1_000L

/** How the offline app asks to be let back in. */
@Stable
class OfflineReconnect internal constructor(private val requests: Channel<Unit>) {
    /** True while an attempt is on its way to the server. */
    var retrying by mutableStateOf(false)
        internal set

    fun retryNow() {
        requests.trySend(Unit)
    }
}

/**
 * Calls [retry] whenever there is a reason to believe the server is back: a
 * network came up or became validated, the app returned to the foreground,
 * or the learner tapped the banner.
 *
 * Attempts never overlap. Reasons that arrive during one are folded into a
 * single attempt after it, so a flapping connection cannot pile them up.
 */
@Composable
fun rememberOfflineReconnect(retry: suspend () -> Unit): OfflineReconnect {
    val context = LocalContext.current.applicationContext
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    val requests = remember { Channel<Unit>(Channel.CONFLATED) }
    val reconnect = remember(requests) { OfflineReconnect(requests) }
    val currentRetry by rememberUpdatedState(retry)

    DisposableEffect(context) {
        val manager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
        val callback = object : ConnectivityManager.NetworkCallback() {
            // Touched only on the callback thread.
            private val validated = mutableSetOf<Network>()

            override fun onAvailable(network: Network) {
                requests.trySend(Unit)
            }

            override fun onCapabilitiesChanged(network: Network, capabilities: NetworkCapabilities) {
                if (capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)) {
                    if (validated.add(network)) requests.trySend(Unit)
                } else {
                    validated.remove(network)
                }
            }

            override fun onLost(network: Network) {
                validated.remove(network)
            }
        }
        val registered = manager != null &&
            runCatching { manager.registerDefaultNetworkCallback(callback) }.isSuccess
        onDispose {
            if (registered) runCatching { manager?.unregisterNetworkCallback(callback) }
        }
    }

    DisposableEffect(lifecycle) {
        // Adding an observer replays the events up to the current state. The
        // replayed resume is not a return to the app, so it is skipped.
        var skipReplayedResume = lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                if (skipReplayedResume) skipReplayedResume = false else requests.trySend(Unit)
            }
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer) }
    }

    LaunchedEffect(requests) {
        for (request in requests) {
            reconnect.retrying = true
            try {
                delay(SETTLE_MILLIS)
                currentRetry()
            } finally {
                reconnect.retrying = false
            }
        }
    }
    return reconnect
}

/** The strip under the status bar while the app runs without the server. */
@Composable
fun OfflineBanner(
    retrying: Boolean,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        color = PompColors.GoldSoft,
        shape = RoundedCornerShape(12.dp),
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 6.dp)
            .testTag(OFFLINE_BANNER_TAG),
    ) {
        Row(
            modifier = Modifier
                .clickable(enabled = !retrying, role = Role.Button, onClick = onRetry)
                .padding(horizontal = 14.dp, vertical = 9.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                imageVector = Icons.Filled.CloudOff,
                contentDescription = null,
                tint = PompColors.Ink,
                modifier = Modifier.size(18.dp),
            )
            Spacer(Modifier.width(10.dp))
            Text(
                text = stringResource(R.string.offline_banner),
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
                color = PompColors.Ink,
                modifier = Modifier.weight(1f),
            )
            if (retrying) {
                CircularProgressIndicator(
                    color = PompColors.InkSecondary,
                    strokeWidth = 2.dp,
                    modifier = Modifier.size(16.dp),
                )
            } else {
                Text(
                    text = stringResource(R.string.action_retry),
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                )
            }
        }
    }
}

/** A section that has nothing to show until the server can be reached. */
@Composable
fun OfflineRequired(modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 32.dp)
            .padding(bottom = LocalMainBottomInset.current)
            .testTag(OFFLINE_REQUIRED_TAG),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Icon(
                imageVector = Icons.Filled.CloudOff,
                contentDescription = null,
                tint = PompColors.InkDisabled,
                modifier = Modifier.size(40.dp),
            )
            Spacer(Modifier.height(14.dp))
            Text(
                text = stringResource(R.string.offline_section_title),
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.Ink,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(6.dp))
            Text(
                text = stringResource(R.string.offline_section_body),
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.InkSecondary,
                textAlign = TextAlign.Center,
            )
        }
    }
}
