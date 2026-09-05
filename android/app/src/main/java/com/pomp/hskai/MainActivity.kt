package com.pomp.hskai

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
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
import com.pomp.hskai.core.notify.StudyNotifications
import com.pomp.hskai.core.notify.StudyReminderScheduler
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
import com.pomp.hskai.feature.course.StudySetupSheet
import com.pomp.hskai.feature.course.StudySetupViewModel
import com.pomp.hskai.feature.dictionary.DictionaryScreen
import com.pomp.hskai.feature.dictionary.DictionaryViewModel
import com.pomp.hskai.feature.onboarding.OnboardingScreen
import com.pomp.hskai.feature.onboarding.OnboardingViewModel
import com.pomp.hskai.feature.profile.ProfileScreen
import com.pomp.hskai.feature.profile.ProfileSettingsViewModel
import com.pomp.hskai.feature.profile.ProfileViewModel
import com.pomp.hskai.feature.profile.labelRes
import com.pomp.hskai.feature.practice.PracticeScreen
import com.pomp.hskai.feature.practice.PracticeViewModel
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.settings.DailyGoal
import com.pomp.hskai.core.settings.PinyinVisibility
import com.pomp.hskai.domain.model.CourseLesson
import com.pomp.hskai.domain.model.LessonAccess
import com.pomp.hskai.feature.lesson.LessonScreen
import com.pomp.hskai.feature.lesson.LessonViewModel
import com.pomp.hskai.feature.ad.AdScreen
import com.pomp.hskai.feature.ad.AdViewModel
import com.pomp.hskai.feature.limit.rememberLimitGate
import com.pomp.hskai.feature.rating.RatingScreen
import com.pomp.hskai.feature.rating.RatingViewModel
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
            val onboardingViewModel: OnboardingViewModel = viewModel(
                viewModelStoreOwner = sessionOwner,
                factory = OnboardingViewModel.Factory(
                    repository = app.onboardingRepository,
                    language = state.account.language.backendCode,
                ),
            )
            val onboardingState by onboardingViewModel.state.collectAsStateWithLifecycle()
            val courseViewModel: CourseViewModel = viewModel(
                viewModelStoreOwner = sessionOwner,
                factory = CourseViewModel.Factory(app.courseRepository),
            )
            val courseState by courseViewModel.state.collectAsStateWithLifecycle()
            val studySetupViewModel: StudySetupViewModel = viewModel(
                viewModelStoreOwner = sessionOwner,
                factory = StudySetupViewModel.Factory(app.studyPreferencesRepository),
            )
            val studySetupState by studySetupViewModel.state.collectAsStateWithLifecycle()
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
            val ratingViewModel: RatingViewModel = viewModel(
                viewModelStoreOwner = sessionOwner,
                factory = RatingViewModel.Factory(app.featureRepository),
            )
            val ratingState by ratingViewModel.state.collectAsStateWithLifecycle()
            val settingsViewModel: ProfileSettingsViewModel = viewModel(
                viewModelStoreOwner = sessionOwner,
                factory = ProfileSettingsViewModel.Factory(
                    courseRepository = app.courseRepository,
                    authRepository = authRepository,
                ),
            )
            val settingsState by settingsViewModel.state.collectAsStateWithLifecycle()
            val settingsReload by settingsViewModel.reload.collectAsStateWithLifecycle()
            var languagePickerOpen by remember { mutableStateOf(false) }
            var dictionaryOpen by remember { mutableStateOf(false) }
            var adRequest by remember { mutableStateOf<AdRequest?>(null) }

            LaunchedEffect(onboardingState.completed) {
                if (onboardingState.completed) {
                    courseViewModel.load()
                    profileViewModel.load()
                }
            }

            LaunchedEffect(courseState.map?.studySetup) {
                studySetupViewModel.sync(courseState.map?.studySetup)
            }

            LaunchedEffect(studySetupState.refreshVersion) {
                if (studySetupState.refreshVersion > 0) {
                    courseViewModel.load()
                    profileViewModel.load()
                }
            }

            LaunchedEffect(settingsReload) {
                if (settingsReload > 0) {
                    courseViewModel.load()
                    profileViewModel.load()
                }
            }

            val context = LocalContext.current
            val notificationPermission = rememberLauncherForActivityResult(
                ActivityResultContracts.RequestPermission()
            ) { granted ->
                if (granted) StudyReminderScheduler.schedule(context)
            }

            val notificationsOn = courseState.map?.notificationsEnabled
            LaunchedEffect(notificationsOn) {
                when (notificationsOn) {
                    true -> if (StudyNotifications.canPost(context)) {
                        StudyReminderScheduler.schedule(context)
                    }
                    false -> {
                        StudyReminderScheduler.cancel(context)
                        StudyNotifications.cancelReminder(context)
                    }
                    null -> Unit
                }
            }

            val limitGate = rememberLimitGate(
                repository = app.featureRepository,
                viewModelStoreOwner = sessionOwner,
                supportUrl = profileState.profile?.supportUrl.orEmpty(),
                isRefreshing = courseState.isLoading || profileState.isLoading,
                onRefreshAccess = {
                    courseViewModel.load()
                    profileViewModel.load()
                    voiceViewModel.loadStatus()
                },
            )

            val dailyGoal by app.appSettings.dailyGoal
                .collectAsStateWithLifecycle(initialValue = DailyGoal.DEFAULT)
            var goalPickerOpen by remember { mutableStateOf(false) }
            var selectedTab by remember { mutableStateOf(MainTab.COURSE) }
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
                onboardingState.completed,
                courseState.snapshot,
                courseState.isRefreshing,
            ) {
                if (!onboardingState.completed) return@LaunchedEffect
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
                        if (courseState.isStale) {
                            if (courseState.isRefreshing) return@LaunchedEffect
                            if (deepLinkRefreshGate.claim(request.id)) {
                                courseViewModel.load()
                            }
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
            val ad = adRequest
            if (onboardingState.loading) {
                SplashScreen()
            } else if (!onboardingState.completed) {
                OnboardingScreen(
                    language = currentLanguage,
                    state = onboardingState.ui,
                    onLevelSelected = onboardingViewModel::selectLevel,
                    onGoalSelected = onboardingViewModel::selectGoal,
                    onBack = onboardingViewModel::back,
                    onNext = onboardingViewModel::next,
                )
            } else if (ad != null) {
                val adViewModel: AdViewModel = viewModel(
                    key = "ad-${ad.accessRef}",
                    viewModelStoreOwner = sessionOwner,
                    factory = AdViewModel.Factory(
                        repository = app.featureRepository,
                        feature = ad.feature,
                        accessRef = ad.accessRef,
                    ),
                )
                val adState by adViewModel.state.collectAsStateWithLifecycle()
                LaunchedEffect(adState.unlocked) {
                    if (adState.unlocked) {
                        adRequest = null
                        practiceViewModel.startWithAd(ad.accessRef)
                    }
                }
                AdScreen(
                    state = adState,
                    onContinue = adViewModel::onContinue,
                    onClose = { adRequest = null },
                    onOpenLink = { url -> openExternal(context, url) },
                )
            } else if (dictionaryOpen) {
                val dictionaryViewModel: DictionaryViewModel = viewModel(
                    key = "dictionary-${state.account.language.backendCode}",
                    viewModelStoreOwner = sessionOwner,
                    factory = DictionaryViewModel.Factory(
                        repository = app.dictionaryRepository,
                        language = state.account.language,
                    ),
                )
                val dictionaryState by dictionaryViewModel.state.collectAsStateWithLifecycle()
                DictionaryScreen(
                    state = dictionaryState,
                    onQueryChange = dictionaryViewModel::onQueryChange,
                    onRetry = dictionaryViewModel::load,
                    onBack = { dictionaryOpen = false },
                )
            } else if (launch != null) {
                LessonHost(
                    app = app,
                    viewModelStoreOwner = sessionOwner,
                    launch = launch,
                    level = courseState.map?.level.orEmpty(),
                    language = state.account.language,
                    pinyin = pinyin,
                    onExit = {
                        openLesson = null
                        courseViewModel.load()
                    },
                )
            } else {
                MainScaffold(
                    selectedTab = selectedTab,
                    onTabSelected = { selectedTab = it },
                ) { tab, contentModifier ->
                    when (tab) {
                        MainTab.COURSE -> CourseScreen(
                            state = courseState,
                            dailyGoal = dailyGoal,
                            limit = limitGate,
                            onLesson = ::launchLesson,
                            onOpenGoal = { goalPickerOpen = true },
                            onOpenChest = courseViewModel::openRewardChest,
                            onChestRewardConsumed = courseViewModel::consumeChestReward,
                            onRetry = courseViewModel::load,
                            modifier = contentModifier,
                        )

                        MainTab.PRACTICE -> PracticeScreen(
                            state = practiceState,
                            level = currentLevel,
                            language = currentLanguage,
                            limit = limitGate,
                            onWatchAd = { feature ->
                                adRequest = AdRequest(
                                    feature = feature,
                                    accessRef = UUID.randomUUID().toString(),
                                )
                            },
                            onOpenDictionary = { dictionaryOpen = true },
                            onStartPractice = { tool, level, language ->
                                practiceViewModel.startPractice(tool, level, language)
                            },
                            onSelectPracticeOption = practiceViewModel::selectPracticeOption,
                            onAdvancePractice = practiceViewModel::advancePractice,
                            onResetPractice = practiceViewModel::resetPractice,
                            onStartMistakeReview = practiceViewModel::startMistakeReview,
                            onAnswerReview = practiceViewModel::answerReview,
                            onAdvanceReview = practiceViewModel::advanceReview,
                            onResetReview = practiceViewModel::resetReview,
                            onStartExam = { examLevel ->
                                practiceViewModel.startExam(examLevel, currentLanguage)
                            },
                            onSelectExamOption = practiceViewModel::selectExamOption,
                            onAdvanceExam = practiceViewModel::advanceExam,
                            onResetExam = practiceViewModel::resetExam,
                            modifier = contentModifier,
                        )

                        MainTab.VOICE -> VoiceScreen(
                            state = voiceState,
                            level = currentLevel,
                            language = currentLanguage,
                            limit = limitGate,
                            onSelectRole = voiceViewModel::selectRole,
                            onStartSession = voiceViewModel::startSession,
                            onToggleRecording = voiceViewModel::toggleRecording,
                            onEndSession = voiceViewModel::endSession,
                            onReset = voiceViewModel::reset,
                            modifier = contentModifier,
                        )

                        MainTab.RATING -> RatingScreen(
                            state = ratingState,
                            onSelectTab = ratingViewModel::selectTab,
                            onRetry = ratingViewModel::load,
                            modifier = contentModifier,
                        )

                        MainTab.PROFILE -> ProfileScreen(
                            account = state.account,
                            state = profileState,
                            settings = settingsState,
                            dailyXp = courseState.map?.progress?.dailyXp ?: 0,
                            dailyGoal = dailyGoal,
                            notificationsEnabled = courseState.map?.notificationsEnabled ?: true,
                            onOpenGoal = { goalPickerOpen = true },
                            onOpenLanguage = { languagePickerOpen = true },
                            onToggleNotifications = { enabled ->
                                if (enabled &&
                                    android.os.Build.VERSION.SDK_INT >=
                                    android.os.Build.VERSION_CODES.TIRAMISU &&
                                    !StudyNotifications.canPost(context)
                                ) {
                                    notificationPermission.launch(
                                        android.Manifest.permission.POST_NOTIFICATIONS,
                                    )
                                }
                                settingsViewModel.setNotifications(enabled)
                            },
                            onOpenSupport = { url -> openExternal(context, url) },
                            onRefresh = profileViewModel::load,
                            onLogout = { signOut(false) },
                            onUnlinkDevice = { signOut(true) },
                            modifier = contentModifier,
                        )
                    }
                }

                if (studySetupState.visible) {
                    StudySetupSheet(
                        language = currentLanguage,
                        state = studySetupState,
                        onDismiss = studySetupViewModel::dismiss,
                        onGoal = studySetupViewModel::chooseGoal,
                        onTime = studySetupViewModel::chooseTime,
                        onFocus = studySetupViewModel::chooseFocus,
                    )
                } else {
                    if (languagePickerOpen) {
                        LanguagePicker(
                            current = state.account.language,
                            onPick = { language ->
                                languagePickerOpen = false
                                settingsViewModel.setLanguage(language)
                            },
                            onDismiss = { languagePickerOpen = false },
                        )
                    }

                    if (goalPickerOpen) {
                        DailyGoalPicker(
                            current = dailyGoal,
                            onPick = { value ->
                                goalPickerOpen = false
                                scope.launch { app.appSettings.setDailyGoal(value) }
                            },
                            onDismiss = { goalPickerOpen = false },
                        )
                    }
                }
            }
        }
    }
}

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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LanguagePicker(
    current: AppLanguage,
    onPick: (AppLanguage) -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState()
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = PompColors.PaperRaised,
    ) {
        Column(Modifier.padding(horizontal = 20.dp, vertical = 8.dp)) {
            Text(
                text = stringResource(R.string.profile_language_picker_title),
                style = androidx.compose.material3.MaterialTheme.typography.titleMedium,
                color = PompColors.Ink,
            )
            androidx.compose.foundation.layout.Spacer(Modifier.padding(6.dp))
            AppLanguage.entries.forEach { language ->
                val selected = language == current
                Surface(
                    color = if (selected) PompColors.CinnabarSoft else PompColors.PaperRaised,
                    shape = androidx.compose.foundation.shape.RoundedCornerShape(14.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 52.dp)
                        .padding(vertical = 4.dp)
                        .clickable { onPick(language) },
                ) {
                    Text(
                        text = stringResource(language.labelRes()),
                        style = androidx.compose.material3.MaterialTheme.typography.bodyLarge,
                        color = if (selected) PompColors.CinnabarDark else PompColors.Ink,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
                    )
                }
            }
            androidx.compose.foundation.layout.Spacer(Modifier.padding(12.dp))
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DailyGoalPicker(
    current: Int,
    onPick: (Int) -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState()
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = PompColors.PaperRaised,
    ) {
        Column(Modifier.padding(horizontal = 20.dp, vertical = 8.dp)) {
            Text(
                text = stringResource(R.string.profile_goal_picker_title),
                style = androidx.compose.material3.MaterialTheme.typography.titleMedium,
                color = PompColors.Ink,
            )
            androidx.compose.foundation.layout.Spacer(Modifier.padding(6.dp))
            DailyGoal.CHOICES.forEach { value ->
                val selected = value == current
                Surface(
                    color = if (selected) PompColors.CinnabarSoft else PompColors.PaperRaised,
                    shape = androidx.compose.foundation.shape.RoundedCornerShape(14.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 52.dp)
                        .padding(vertical = 4.dp)
                        .clickable { onPick(value) },
                ) {
                    Text(
                        text = stringResource(R.string.profile_goal_option, value),
                        style = androidx.compose.material3.MaterialTheme.typography.bodyLarge,
                        color = if (selected) PompColors.CinnabarDark else PompColors.Ink,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
                    )
                }
            }
            androidx.compose.foundation.layout.Spacer(Modifier.padding(12.dp))
        }
    }
}

private fun openExternal(context: android.content.Context, url: String): Boolean {
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

private data class AdRequest(
    val feature: String,
    val accessRef: String,
)

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
