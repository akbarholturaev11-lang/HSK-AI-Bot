package com.pomp.hskai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.auth.AuthState
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.navigation.DeepLinkRouter
import com.pomp.hskai.feature.auth.LinkScreen
import com.pomp.hskai.feature.auth.LinkViewModel

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val app = application as HskAiApplication
        // Resolved but not acted on until the session and entitlement are
        // loaded: a URI must never open premium content on its own.
        val pendingDestination = DeepLinkRouter.resolve(intent?.data?.toString())

        setContent {
            PompHskAiTheme {
                AppRoot(
                    authRepository = app.authRepository,
                    hasPendingDeepLink = pendingDestination != null,
                )
            }
        }
    }
}

@Composable
private fun AppRoot(
    authRepository: AuthRepository,
    hasPendingDeepLink: Boolean,
) {
    val authState by authRepository.state.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) {
        authRepository.bootstrap()
    }

    when (val state = authState) {
        AuthState.Unknown -> SplashScreen()

        AuthState.Unauthenticated -> {
            val viewModel: LinkViewModel = viewModel(
                factory = LinkViewModelFactory(authRepository),
            )
            val linkState by viewModel.state.collectAsStateWithLifecycle()
            LaunchedEffect(Unit) {
                if (linkState.pending == null && !linkState.isRequestingCode) {
                    viewModel.requestCode()
                }
            }
            LinkScreen(
                state = linkState,
                onRequestCode = viewModel::requestCode,
            )
        }

        is AuthState.Authenticated -> LinkedPlaceholderScreen(
            name = state.account.displayName,
            level = state.account.level,
            isPaid = state.account.isPaid,
            hasPendingDeepLink = hasPendingDeepLink,
        )
    }
}

@Composable
private fun SplashScreen() {
    Surface(color = PompColors.Paper, modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            CircularProgressIndicator(color = PompColors.Cinnabar)
        }
    }
}

/**
 * Phase C stopping point: proves the canonical account really arrived.
 * Phase D replaces this with the "Bugun" screen and bottom navigation.
 */
@Composable
private fun LinkedPlaceholderScreen(
    name: String,
    level: String,
    isPaid: Boolean,
    hasPendingDeepLink: Boolean,
) {
    Surface(color = PompColors.Paper, modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = stringResource(R.string.synced_title),
                style = MaterialTheme.typography.headlineMedium,
                color = PompColors.Ink,
            )
            Text(
                text = name,
                style = MaterialTheme.typography.titleLarge,
                color = PompColors.InkSecondary,
                modifier = Modifier.padding(top = 12.dp),
            )
            Text(
                text = "${stringResource(R.string.synced_level)}: ${level.uppercase()}",
                style = MaterialTheme.typography.bodyLarge,
                color = PompColors.InkSecondary,
                modifier = Modifier.padding(top = 4.dp),
            )
            Text(
                text = stringResource(
                    if (isPaid) R.string.synced_access_paid else R.string.synced_access_free
                ),
                style = MaterialTheme.typography.bodyLarge,
                color = if (isPaid) PompColors.Jade else PompColors.InkSecondary,
                modifier = Modifier.padding(top = 4.dp),
            )
            if (hasPendingDeepLink) {
                Text(
                    text = stringResource(R.string.nav_today),
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                    modifier = Modifier.padding(top = 16.dp),
                )
            }
        }
    }
}

private class LinkViewModelFactory(
    private val authRepository: AuthRepository,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        LinkViewModel(authRepository) as T
}
