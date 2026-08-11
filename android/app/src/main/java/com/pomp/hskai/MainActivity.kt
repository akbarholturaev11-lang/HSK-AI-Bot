package com.pomp.hskai

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStoreOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.auth.AuthState
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.navigation.DeepLinkRouter
import com.pomp.hskai.core.navigation.AppDestination
import com.pomp.hskai.core.navigation.DeepLinkRefreshGate
import com.pomp.hskai.core.navigation.DestinationRequest
import com.pomp.hskai.core.navigation.SessionViewModelStoreOwner
import com.pomp.hskai.core.navigation.toTab
import com.pomp.hskai.feature.auth.LinkScreen
import com.pomp.hskai.feature.auth.LinkViewModel
import com.pomp.hskai.core.navigation.MainScaffold
import com.pomp.hskai.core.navigation.MainTab
import com.pomp.hskai.feature.course.CourseScreen
import com.pomp.hskai.feature.course.CourseViewModel
import com.pomp.hskai.feature.profile.ProfileScreen
import com.pomp.hskai.feature.profile.ProfileViewModel
import com.pomp.hskai.feature.practice.PracticeScreen
import com.pomp.hskai.feature.practice.PracticeViewModel
import com.pomp.hskai.core.settings.PinyinVisibility
import com.pomp.hskai.domain.model.CourseLesson
import com.pomp.hskai.domain.model.LessonAccess
import com.pomp.hskai.feature.lesson.LessonScreen
import com.pomp.hskai.feature.lesson.LessonViewModel
import com.pomp.hskai.feature.today.TodayScreen
import com.pomp.hskai.feature.voice.VoiceScreen
import com.pomp.hskai.feature.voice.VoiceViewModel
import java.util.UUID
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.MutableStateFlow

class MainActivity : ComponentActivity() {

    private val requestedDestination = MutableStateFlow<DestinationRequest?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val app = application as HskAiApplication
        deliverDestination(intent?.data?.toString())

        setContent {
            PompHskAiTheme {
                val destination by requestedDestination.collectAsStateWithLifecycle()
                AppRoot(
                    app = app,
                    requestedDestination = destination,
                    onDestinationConsumed = { requestedDestination.value = null },
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        deliverDestination(intent.data?.toString())
    }

    private fun deliverDestination(raw: String?) {
        requestedDestination.value = DeepLinkRouter.resolve(raw)?.let { destination ->
            DestinationRequest(
                id = UUID.randomUUID().toString(),
                destination = destination,
            )
        }
    }
}

@Composable
private fun AppRoot(
    app: HskAiApplication,
    requestedDestination: DestinationRequest?,
    onDestinationConsumed: () -> Unit,
) {
    val authRepository = app.authRepository
    val authState by authRepository.state.collectAsStateWithLifecycle()
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        authRepository.bootstrap()
    }

    when (val state = authState) {
        AuthState.Unknown -> SplashScreen()

        is AuthState.BootstrapFailed -> BootstrapErrorScreen(
            errorRes = state.error.messageRes,
            onRetry = { scope.launch { authRepository.bootstrap() } },
        )

        AuthState.Unauthenticated -> {
            LaunchedEffect(Unit) { app.clearLocalData() }
            val sessionOwner = rememberSessionViewModelStoreOwner()
            val viewModel: LinkViewModel = viewModel(
                viewModelStoreOwner = sessionOwner,
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
            val sessionOwner = rememberSessionViewModelStoreOwner()
            val courseViewModel: CourseViewModel = viewModel(
                viewModelStoreOwner = sessionOwner,
                factory = CourseViewModel.Factory(app.courseRepository),
            )
            val courseState by courseViewModel.state.collectAsStateWithLifecycle()
            val pinyin by app.appSettings.pinyinVisibility
                .collectAsStateWithLifecycle(initialValue = PinyinVisibility.DEFAULT)
            val practiceViewModel: PracticeViewModel = viewModel(
                viewModelStoreOwner = sessionOwner,
                factory = PracticeViewModel.Factory(app.featureRepository),
            )
            val practiceState by practiceViewModel.state.collectAsStateWithLifecycle()
            val voiceViewModel: VoiceViewModel = viewModel(
                viewModelStoreOwner = sessionOwner,
                factory = VoiceViewModel.Factory(
                    repository = app.featureRepository,
                    recorder = app.voiceRecorder,
                ),
            )
            val voiceState by voiceViewModel.state.collectAsStateWithLifecycle()
            val profileViewModel: ProfileViewModel = viewModel(
                viewModelStoreOwner = sessionOwner,
                factory = ProfileViewModel.Factory(app.featureRepository),
            )
            val profileState by profileViewModel.state.collectAsStateWithLifecycle()
            var selectedTab by remember { mutableStateOf(MainTab.TODAY) }
            var openLesson by remember { mutableStateOf<LessonLaunch?>(null) }
            val deepLinkRefreshGate = remember { DeepLinkRefreshGate() }
            val currentLevel = courseState.map?.level ?: state.account.level
            val currentLanguage = state.account.language.backendCode

            fun launchLesson(lesson: CourseLesson) {
                openLesson = LessonLaunch(
                    lesson = lesson,
                    attemptKey = UUID.randomUUID().toString(),
                )
            }

            LaunchedEffect(
                requestedDestination,
                courseState.snapshot,
                courseState.isRefreshing,
            ) {
                val request = requestedDestination ?: return@LaunchedEffect
                val destination = request.destination
                selectedTab = destination.toTab() ?: selectedTab
                when (destination) {
                    AppDestination.CurrentLesson,
                    is AppDestination.Lesson,
                    -> {
                        val map = courseState.map
                        if (map == null) {
                            if (!courseState.isRefreshing && deepLinkRefreshGate.claim(request.id)) {
                                courseViewModel.load()
                            }
                            return@LaunchedEffect
                        }
                        // A stale map may guide the learner, but it never
                        // authorizes a deep link. Wait for a fresh server map;
                        // the lesson endpoint then checks access once more.
                        if (courseState.isStale) {
                            if (courseState.isRefreshing) return@LaunchedEffect
                            if (deepLinkRefreshGate.claim(request.id)) {
                                courseViewModel.load()
                            }
                            // Keep the request pending after a failed refresh.
                            // A repeated identical URI has a new request id and
                            // may safely trigger another server authorization.
                            return@LaunchedEffect
                        }
                        deepLinkRefreshGate.reset()
                        val candidate = when (destination) {
                            AppDestination.CurrentLesson -> map.currentLesson
                            is AppDestination.Lesson -> map.lessons.firstOrNull {
                                it.order == destination.order
                            }
                            else -> null
                        }
                        if (
                            candidate?.access == LessonAccess.Open ||
                            candidate?.access == LessonAccess.HalfPreview
                        ) {
                            launchLesson(candidate)
                        }
                        onDestinationConsumed()
                    }

                    else -> {
                        deepLinkRefreshGate.reset()
                        onDestinationConsumed()
                    }
                }
            }

            val signOut: (Boolean) -> Unit = { unlink ->
                scope.launch {
                    app.clearLocalData()
                    authRepository.logout(unlinkDevice = unlink)
                }
            }

            val launch = openLesson
            if (launch != null) {
                LessonHost(
                    app = app,
                    viewModelStoreOwner = sessionOwner,
                    launch = launch,
                    level = courseState.map?.level.orEmpty(),
                    language = state.account.language,
                    pinyin = pinyin,
                    onExit = {
                        openLesson = null
                        // Progress, XP and streak all come back from the
                        // server rather than being guessed locally.
                        courseViewModel.load()
                    },
                )
            } else {
                MainScaffold(
                    selectedTab = selectedTab,
                    onTabSelected = { selectedTab = it },
                ) { tab, contentModifier ->
                when (tab) {
                    MainTab.TODAY -> TodayScreen(
                        state = courseState,
                        onContinue = ::launchLesson,
                        onRetry = courseViewModel::load,
                        modifier = contentModifier,
                    )

                    MainTab.COURSE -> CourseScreen(
                        state = courseState,
                        onLesson = ::launchLesson,
                        modifier = contentModifier,
                    )

                    MainTab.PRACTICE -> PracticeScreen(
                        state = practiceState,
                        level = currentLevel,
                        language = currentLanguage,
                        onStartPractice = practiceViewModel::startPractice,
                        onSelectPracticeOption = practiceViewModel::selectPracticeOption,
                        onAdvancePractice = practiceViewModel::advancePractice,
                        onResetPractice = practiceViewModel::resetPractice,
                        onStartMistakeReview = practiceViewModel::startMistakeReview,
                        onAnswerReview = practiceViewModel::answerReview,
                        onAdvanceReview = practiceViewModel::advanceReview,
                        onResetReview = practiceViewModel::resetReview,
                        modifier = contentModifier,
                    )

                    MainTab.VOICE -> VoiceScreen(
                        state = voiceState,
                        level = currentLevel,
                        language = currentLanguage,
                        onSelectRole = voiceViewModel::selectRole,
                        onStartSession = voiceViewModel::startSession,
                        onToggleRecording = voiceViewModel::toggleRecording,
                        onEndSession = voiceViewModel::endSession,
                        onReset = voiceViewModel::reset,
                        modifier = contentModifier,
                    )

                    MainTab.PROFILE -> ProfileScreen(
                        account = state.account,
                        state = profileState,
                        onRefresh = profileViewModel::load,
                        onLogout = { signOut(false) },
                        onUnlinkDevice = { signOut(true) },
                        modifier = contentModifier,
                    )
                    }
                }
            }
        }
    }
}

/**
 * Hosts one lesson attempt.
 *
 * The ViewModel is reused per level/order inside one authenticated session,
 * while [LessonViewModel.beginAttempt] resets it from an opaque launch key.
 * This avoids retaining hundreds of attempts and still guarantees a fresh
 * completion event without sharing lesson state between accounts.
 */
@Composable
private fun LessonHost(
    app: HskAiApplication,
    viewModelStoreOwner: ViewModelStoreOwner,
    launch: LessonLaunch,
    level: String,
    language: com.pomp.hskai.core.i18n.AppLanguage,
    pinyin: PinyinVisibility,
    onExit: () -> Unit,
) {
    val lesson = launch.lesson
    val model: LessonViewModel = viewModel(
        key = "lesson-$level-${lesson.order}",
        viewModelStoreOwner = viewModelStoreOwner,
        factory = LessonViewModel.Factory(
            repository = app.courseRepository,
            audioPlayer = app.lessonAudioPlayer,
            level = level,
            lessonOrder = lesson.order,
            language = language,
        ),
    )
    val lessonState by model.state.collectAsStateWithLifecycle()

    LaunchedEffect(launch.attemptKey) {
        model.beginAttempt(launch.attemptKey)
    }
    DisposableEffect(model, launch.attemptKey) {
        onDispose { model.endAttempt(launch.attemptKey) }
    }

    LessonScreen(
        state = lessonState,
        pinyin = pinyin,
        onAnswerChoice = model::answerChoice,
        onAnswerBuilder = model::answerBuilder,
        onAnswerPairs = model::answerMatchPairs,
        onAcknowledge = model::acknowledge,
        onAdvance = model::advance,
        onPlayAudio = model::playAudio,
        onRetryCompletion = model::retryCompletion,
        onExit = {
            model.endAttempt(launch.attemptKey)
            onExit()
        },
    )
}

private data class LessonLaunch(
    val lesson: CourseLesson,
    val attemptKey: String,
)

@Composable
private fun rememberSessionViewModelStoreOwner(): SessionViewModelStoreOwner {
    val owner = remember { SessionViewModelStoreOwner() }
    DisposableEffect(owner) {
        onDispose(owner::clear)
    }
    return owner
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

@Composable
private fun BootstrapErrorScreen(errorRes: Int, onRetry: () -> Unit) {
    Surface(color = PompColors.Paper, modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = stringResource(errorRes),
                style = androidx.compose.material3.MaterialTheme.typography.bodyLarge,
                color = PompColors.InkSecondary,
                textAlign = TextAlign.Center,
            )
            androidx.compose.foundation.layout.Spacer(Modifier.padding(8.dp))
            OutlinedButton(onClick = onRetry) {
                Text(stringResource(R.string.action_retry))
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
