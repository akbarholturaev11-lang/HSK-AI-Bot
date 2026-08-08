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
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
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
import com.pomp.hskai.core.settings.PinyinVisibility
import com.pomp.hskai.domain.model.CourseLesson
import com.pomp.hskai.domain.model.LessonAccess
import com.pomp.hskai.feature.lesson.LessonScreen
import com.pomp.hskai.feature.lesson.LessonViewModel
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
            val pinyin by app.appSettings.pinyinVisibility
                .collectAsStateWithLifecycle(initialValue = PinyinVisibility.DEFAULT)
            val scope = rememberCoroutineScope()
            var openLesson by remember { mutableStateOf<CourseLesson?>(null) }

            val signOut: (Boolean) -> Unit = { unlink ->
                scope.launch {
                    app.clearLocalData()
                    authRepository.logout(unlinkDevice = unlink)
                }
            }

            val lesson = openLesson
            if (lesson != null) {
                LessonHost(
                    app = app,
                    lesson = lesson,
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
                MainScaffold(initialTab = startTab ?: MainTab.TODAY) { tab, contentModifier ->
                when (tab) {
                    MainTab.TODAY -> TodayScreen(
                        state = courseState,
                        onContinue = { openLesson = it },
                        onRetry = courseViewModel::load,
                        modifier = contentModifier,
                    )

                    MainTab.COURSE -> CourseScreen(
                        state = courseState,
                        onLesson = { openLesson = it },
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
}

/**
 * Hosts one lesson attempt.
 *
 * Keyed by lesson order so a new attempt gets a fresh state machine and a
 * fresh completion event id, while a recomposition keeps the current one.
 */
@Composable
private fun LessonHost(
    app: HskAiApplication,
    lesson: CourseLesson,
    level: String,
    language: com.pomp.hskai.core.i18n.AppLanguage,
    pinyin: PinyinVisibility,
    onExit: () -> Unit,
) {
    val model: LessonViewModel = viewModel(
        key = "lesson-${lesson.order}",
        factory = LessonViewModel.Factory(
            repository = app.courseRepository,
            level = level,
            lessonOrder = lesson.order,
            language = language,
            isHalfPreview = lesson.access == LessonAccess.HalfPreview,
        ),
    )
    val lessonState by model.state.collectAsStateWithLifecycle()

    LessonScreen(
        state = lessonState,
        pinyin = pinyin,
        onAnswerChoice = model::answerChoice,
        onAnswerBuilder = model::answerBuilder,
        onAnswerPairs = model::answerMatchPairs,
        onAcknowledge = model::acknowledge,
        onAdvance = model::advance,
        onRetryCompletion = model::retryCompletion,
        onExit = onExit,
    )
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
