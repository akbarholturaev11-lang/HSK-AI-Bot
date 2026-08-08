package com.pomp.hskai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.runtime.rememberCoroutineScope
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.auth.AuthState
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.navigation.DeepLinkRouter
import com.pomp.hskai.core.navigation.toTab
import com.pomp.hskai.feature.auth.LinkScreen
import com.pomp.hskai.feature.auth.LinkViewModel
import com.pomp.hskai.core.navigation.MainScaffold
import com.pomp.hskai.core.navigation.MainTab
import com.pomp.hskai.feature.course.CourseScreen
import com.pomp.hskai.feature.course.CourseViewModel
import com.pomp.hskai.feature.profile.ProfileScreen
import com.pomp.hskai.feature.today.TodayScreen
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val app = application as HskAiApplication
        // Resolved but not acted on until the session and entitlement are
        // loaded: a URI must never open premium content on its own.
        val startTab = DeepLinkRouter.resolve(intent?.data?.toString())?.toTab()

        setContent {
            PompHskAiTheme {
                AppRoot(app = app, startTab = startTab)
            }
        }
    }
}

@Composable
private fun AppRoot(
    app: HskAiApplication,
    startTab: MainTab?,
) {
    val authRepository = app.authRepository
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

        is AuthState.Authenticated -> {
            val courseViewModel: CourseViewModel = viewModel(
                factory = CourseViewModel.Factory(app.courseRepository),
            )
            val courseState by courseViewModel.state.collectAsStateWithLifecycle()
            val scope = rememberCoroutineScope()

            val signOut: (Boolean) -> Unit = { unlink ->
                scope.launch {
                    app.clearLocalData()
                    authRepository.logout(unlinkDevice = unlink)
                }
            }

            MainScaffold(initialTab = startTab ?: MainTab.TODAY) { tab, contentModifier ->
                when (tab) {
                    MainTab.TODAY -> TodayScreen(
                        state = courseState,
                        // Phase E opens the lesson renderer; until then the
                        // action refreshes rather than pretending to navigate.
                        onContinue = { courseViewModel.load() },
                        onRetry = courseViewModel::load,
                        modifier = contentModifier,
                    )

                    MainTab.COURSE -> CourseScreen(
                        state = courseState,
                        onLesson = { courseViewModel.load() },
                        modifier = contentModifier,
                    )

                    MainTab.PROFILE -> ProfileScreen(
                        account = state.account,
                        onLogout = { signOut(false) },
                        onUnlinkDevice = { signOut(true) },
                        modifier = contentModifier,
                    )
                }
            }
        }
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

private class LinkViewModelFactory(
    private val authRepository: AuthRepository,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        LinkViewModel(authRepository) as T
}
