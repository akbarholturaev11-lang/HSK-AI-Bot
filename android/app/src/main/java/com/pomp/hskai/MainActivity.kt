package com.pomp.hskai

import android.content.ActivityNotFoundException
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.compose.BackHandler
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.TextButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
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
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.auth.AuthState
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.design.components.HskBrandLoader
import com.pomp.hskai.core.navigation.DeepLinkRouter
import com.pomp.hskai.core.notify.StudyNotifications
import com.pomp.hskai.core.notify.StudyReminderScheduler
import com.pomp.hskai.core.navigation.AppDestination
import com.pomp.hskai.core.navigation.DeepLinkRefreshGate
import com.pomp.hskai.core.navigation.DestinationRequest
import com.pomp.hskai.core.navigation.SessionViewModelStoreOwner
import com.pomp.hskai.core.navigation.toTab
import com.pomp.hskai.feature.auth.LinkScreen
import com.pomp.hskai.feature.onboarding.NotificationPrimerScreen
import com.pomp.hskai.feature.auth.LinkViewModel
import com.pomp.hskai.feature.assistant.AssistantModalBottomSheet as ModalBottomSheet
import com.pomp.hskai.core.navigation.MainScaffold
import com.pomp.hskai.core.navigation.MainTab
import com.pomp.hskai.feature.course.CourseScreen
import com.pomp.hskai.feature.course.CourseViewModel
import com.pomp.hskai.feature.course.SkipTestScreen
import com.pomp.hskai.feature.course.SkipTestViewModel
import com.pomp.hskai.feature.course.StudySetupSheet
import com.pomp.hskai.feature.course.StudySetupViewModel
import com.pomp.hskai.feature.dictionary.DictionaryScreen
import com.pomp.hskai.feature.dictionary.DictionaryViewModel
import com.pomp.hskai.feature.onboarding.OnboardingScreen
import com.pomp.hskai.feature.onboarding.OnboardingViewModel
import com.pomp.hskai.feature.profile.IdentitiesViewModel
import com.pomp.hskai.feature.profile.IdentitiesViewModelFactory
import com.pomp.hskai.feature.profile.ProfileScreen
import com.pomp.hskai.feature.profile.ProfileSettingsViewModel
import com.pomp.hskai.feature.profile.ProfileViewModel
import com.pomp.hskai.feature.profile.labelRes
import com.pomp.hskai.feature.practice.DrillMode
import com.pomp.hskai.feature.practice.PracticeRequest
import com.pomp.hskai.feature.practice.toRequest
import com.pomp.hskai.feature.practice.PracticeScreen
import com.pomp.hskai.feature.practice.PracticeViewModel
import com.pomp.hskai.feature.practice.WordDrillScreen
import com.pomp.hskai.feature.practice.WordDrillViewModel
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.i18n.AppLocale
import com.pomp.hskai.core.settings.DailyGoal
import com.pomp.hskai.core.settings.PinyinVisibility
import com.pomp.hskai.domain.model.CourseLesson
import com.pomp.hskai.domain.model.LessonAccess
import com.pomp.hskai.domain.model.TodayTask
import com.pomp.hskai.feature.lesson.LessonOutcome
import com.pomp.hskai.feature.lesson.LessonScreen
import com.pomp.hskai.feature.lesson.LessonViewModel
import com.pomp.hskai.feature.ad.AdScreen
import com.pomp.hskai.feature.ad.AdViewModel
import com.pomp.hskai.feature.hint.HintsViewModel
import com.pomp.hskai.feature.limit.rememberLimitGate
import com.pomp.hskai.feature.subscription.SubscriptionCheckoutHost
import com.pomp.hskai.feature.limit.LimitGate
import com.pomp.hskai.data.api.ChallengeDto
import com.pomp.hskai.data.api.RatingEntryDto
import com.pomp.hskai.feature.rating.ChallengeRunScreen
import com.pomp.hskai.feature.rating.ChallengeRunViewModel
import com.pomp.hskai.feature.rating.RatingChallengesScreen
import com.pomp.hskai.feature.rating.RatingScreen
import com.pomp.hskai.feature.rating.RatingTab
import com.pomp.hskai.feature.rating.RatingUserScreen
import com.pomp.hskai.feature.rating.RatingViewModel
import com.pomp.hskai.feature.voice.VoiceScreen
import com.pomp.hskai.feature.voice.VoiceViewModel
import java.util.UUID
import java.time.LocalDate
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.flow.first
import com.pomp.hskai.widget.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.MutableStateFlow

class MainActivity : ComponentActivity() {

    private val requestedDestination = MutableStateFlow<DestinationRequest?>(null)

    // Resources are resolved when the activity is built, so the account's
    // language has to be in place before anything is inflated.
    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(AppLocale.wrap(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val app = application as HskAiApplication
        deliverDestination(intent?.data?.toString())
        if (savedInstanceState == null) recordNativeEntry(intent)

        setContent {
            PompHskAiTheme {
                val destination by requestedDestination.collectAsStateWithLifecycle()
                com.pomp.hskai.feature.assistant.AssistantHost(app, ::deliverDestination) {
                  AppRoot(
                    app = app,
                    requestedDestination = destination,
                    onDestinationConsumed = { requestedDestination.value = null },
                )
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        deliverDestination(intent.data?.toString())
        recordNativeEntry(intent)
    }

    private fun recordNativeEntry(intent: Intent?) {
        val source = intent?.getStringExtra(WidgetIntents.SOURCE)
        val name = when (source) {
            "widget" -> "android_widget_opened"
            "notification" -> "android_notification_opened"
            else -> return
        }
        val app = application as HskAiApplication
        val id = if (source == "notification") intent.getStringExtra(WidgetIntents.EVENT_ID) ?: UUID.randomUUID().toString()
            else UUID.randomUUID().toString()
        lifecycleScope.launch { app.widgetCoordinator.event(name, id) }
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
    var offlineCourseEntry by rememberSaveable { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        authRepository.bootstrap()
    }

    when (val state = authState) {
        AuthState.Unknown -> SplashScreen()

        is AuthState.BootstrapFailed -> {
            val courseEntry = offlineCourseEntry || requestedDestination?.destination?.toTab() == MainTab.COURSE
            LaunchedEffect(courseEntry) {
                if (courseEntry) {
                    offlineCourseEntry = true
                    onDestinationConsumed() // Retry must not unexpectedly auto-launch a lesson later.
                }
            }
            if (courseEntry) {
                OfflineCourseEntry(
                    app = app,
                    onRetry = { scope.launch { authRepository.bootstrap() } },
                )
            } else {
                BootstrapErrorScreen(
                    errorRes = state.error.messageRes,
                    onRetry = { scope.launch { authRepository.bootstrap() } },
                )
            }
        }

        AuthState.Unauthenticated -> {
            val sessionOwner = rememberSessionViewModelStoreOwner()
            val viewModel: LinkViewModel = viewModel(
                viewModelStoreOwner = sessionOwner,
                factory = LinkViewModelFactory(authRepository),
            )
            val linkState by viewModel.state.collectAsStateWithLifecycle()
            val localeHost = LocalContext.current
            LaunchedEffect(Unit) {
                app.clearLocalData()
                if (AppLocale.clear(localeHost)) {
                    (localeHost as? Activity)?.recreate()
                } else {
                    // The link itself is reserved only when a provider is
                    // tapped, so switching language here costs no link row.
                    viewModel.loadProviders()
                }
            }
            LinkScreen(
                state = linkState,
                language = AppLocale.current(localeHost),
                onLanguageSelected = { language ->
                    if (AppLocale.choose(localeHost, language)) {
                        (localeHost as? Activity)?.recreate()
                    }
                },
                onContinueWithTelegram = viewModel::continueWithTelegram,
                onSignInWithGoogle = { viewModel.signInWithGoogle(localeHost as? Activity) },
                onSignInWithApple = viewModel::signInWithApple,
                onBrowserUrlOpened = viewModel::browserUrlOpened,
                onTelegramUrlOpened = viewModel::telegramUrlOpened,
                onDismissWaiting = viewModel::dismissWaiting,
            )
        }

        is AuthState.Authenticated -> {
            LaunchedEffect(Unit) { offlineCourseEntry = false }
            val localeHost = LocalContext.current
            var localeReady by rememberSaveable(state.account.language.backendCode) {
                mutableStateOf(false)
            }
            LaunchedEffect(state.account.language) {
                if (AppLocale.sync(localeHost, state.account.language)) {
                    val activity = localeHost as? Activity
                    if (activity != null) {
                        activity.recreate()
                    } else {
                        localeReady = true
                    }
                } else {
                    localeReady = true
                }
            }
            if (!localeReady) {
                SplashScreen()
                return
            }
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
                factory = PracticeViewModel.Factory(
                    repository = app.featureRepository,
                    courseRepository = app.courseRepository,
                    audioPlayer = app.lessonAudioPlayer,
                ),
            )
            val practiceState by practiceViewModel.state.collectAsStateWithLifecycle()
            val voiceViewModel: VoiceViewModel = viewModel(
                viewModelStoreOwner = sessionOwner,
                factory = VoiceViewModel.Factory(
                    repository = app.featureRepository,
                    recorder = app.voiceRecorder,
                    courseRepository = app.courseRepository,
                    audioPlayer = app.lessonAudioPlayer,
                ),
            )
            val voiceState by voiceViewModel.state.collectAsStateWithLifecycle()
            val profileViewModel: ProfileViewModel = viewModel(
                viewModelStoreOwner = sessionOwner,
                factory = ProfileViewModel.Factory(app.featureRepository),
            )
            val profileState by profileViewModel.state.collectAsStateWithLifecycle()
            val identitiesViewModel: IdentitiesViewModel = viewModel(
                viewModelStoreOwner = sessionOwner,
                factory = IdentitiesViewModelFactory(app.authRepository),
            )
            val identitiesState by identitiesViewModel.state.collectAsStateWithLifecycle()
            val hintsViewModel: HintsViewModel = viewModel(
                viewModelStoreOwner = sessionOwner,
                factory = HintsViewModel.Factory(app.featureRepository),
            )
            val hints by hintsViewModel.hints.collectAsStateWithLifecycle()
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
            var screenCenterAdAsked by rememberSaveable { mutableStateOf(false) }
            // Shown once, right after onboarding, and only to someone who has
            // just been through it — `launch` is set by the completion call
            // and stays null for an account that was already onboarded.
            var planChoiceSeen by rememberSaveable { mutableStateOf(false) }
            var planChoiceOpen by remember { mutableStateOf(false) }
            var widgetSetupOpen by remember { mutableStateOf(false) }
            var widgetPlacedNotice by remember { mutableStateOf(false) }
            var widgetPromptFromOnboarding by rememberSaveable { mutableStateOf(false) }
            var widgetOfferHandled by rememberSaveable { mutableStateOf(false) }
            var widgetForegroundTick by remember { mutableStateOf(0) }
            val widgetLifecycle = LocalLifecycleOwner.current.lifecycle
            val widgetSession by app.widgetStore.state.collectAsStateWithLifecycle(initialValue = WidgetSession())
            val widgetTheme by app.appSettings.themeMode.collectAsStateWithLifecycle(initialValue = com.pomp.hskai.core.settings.AppThemeMode.DEFAULT)
            val sessionEpoch = remember { app.widgetStore.state }
            // Capture the account generation before the foreground request can publish anything.
            var widgetEpoch by remember { mutableStateOf<String?>(null) }
            LaunchedEffect(Unit) {
                widgetEpoch = sessionEpoch.first().epoch
                app.widgetCoordinator.flushEvents()
            }
            LaunchedEffect(courseState.snapshot, widgetEpoch, widgetTheme) {
                val epoch = widgetEpoch ?: return@LaunchedEffect
                courseState.snapshot?.let { app.widgetCoordinator.publish(it, epoch) }
            }
            DisposableEffect(widgetLifecycle) {
                val observer = androidx.lifecycle.LifecycleEventObserver { _, event ->
                    if (event == androidx.lifecycle.Lifecycle.Event.ON_RESUME) {
                        widgetForegroundTick += 1
                    }
                }
                widgetLifecycle.addObserver(observer)
                onDispose { widgetLifecycle.removeObserver(observer) }
            }

            // Onboarding uses the same full-screen prompt as the daily reminder.
            // Keep the plan-choice gate closed until this prompt is dismissed,
            // so the two full-screen experiences never stack or swap order.
            LaunchedEffect(onboardingState.launch) {
                if (onboardingState.launch != null && !widgetOfferHandled && !widgetSetupOpen) {
                    val today = LocalDate.now().toString()
                    val session = app.widgetStore.read()
                    val installed = WidgetScheduler.hasWidgets(localeHost)
                    if (
                        WidgetInstallPromptPolicy.shouldAutoShow(
                            installed = installed,
                            lastShownDay = session.lastInstallPromptDay,
                            today = today,
                        )
                    ) {
                        app.widgetStore.markOffered()
                        app.widgetStore.markInstallPromptShown(today)
                        widgetPromptFromOnboarding = true
                        widgetSetupOpen = true
                        app.widgetStore.enqueue(AndroidWidgetEvent("android_widget_onboarding_viewed"))
                        app.applicationScope.launch { app.widgetCoordinator.flushEvents() }
                    } else {
                        widgetOfferHandled = true
                    }
                }
            }

            // Existing accounts already loaded course/profile in their ViewModel init.
            // Refresh only when this process has just completed onboarding; launch
            // stays null for an account that arrived already onboarded.
            LaunchedEffect(onboardingState.launch) {
                if (onboardingState.launch != null) {
                    courseViewModel.load()
                    profileViewModel.load()
                }
            }

            // Existing learners who still have no widget see the same prompt
            // once per local day when the app returns to the foreground.
            LaunchedEffect(
                widgetForegroundTick,
                onboardingState.completed,
                onboardingState.launch,
                widgetOfferHandled,
                widgetSetupOpen,
                planChoiceOpen,
                studySetupState.visible,
                widgetSession.lastInstallPromptDay,
            ) {
                if (!onboardingState.completed || widgetSetupOpen || planChoiceOpen || studySetupState.visible) {
                    return@LaunchedEffect
                }
                if (onboardingState.launch != null && !widgetOfferHandled) {
                    return@LaunchedEffect
                }

                val today = LocalDate.now().toString()
                val installed = WidgetScheduler.hasWidgets(localeHost)
                if (
                    WidgetInstallPromptPolicy.shouldAutoShow(
                        installed = installed,
                        lastShownDay = widgetSession.lastInstallPromptDay,
                        today = today,
                    )
                ) {
                    app.widgetStore.markInstallPromptShown(today)
                    widgetPromptFromOnboarding = false
                    widgetSetupOpen = true
                    app.widgetStore.enqueue(AndroidWidgetEvent("android_widget_daily_prompt_viewed"))
                    app.applicationScope.launch { app.widgetCoordinator.flushEvents() }
                }
            }

            // The Mini App's plan choice after onboarding, in the same place
            // and with the same two ways out. Whether the free week is on
            // offer at all is the server's answer, so this waits for it
            // rather than assuming a new account is eligible.
            LaunchedEffect(onboardingState.launch, profileState.trial?.eligible, widgetSetupOpen, widgetOfferHandled) {
                if (
                    !planChoiceSeen &&
                    widgetOfferHandled && !widgetSetupOpen &&
                    onboardingState.launch != null &&
                    profileState.trial?.eligible == true
                ) {
                    planChoiceSeen = true
                    planChoiceOpen = true
                }
            }

            LaunchedEffect(courseState.map?.studySetup) {
                studySetupViewModel.sync(courseState.map?.studySetup)
                // The daily goal belongs to the account, not to the phone. The
                // local copy is only a mirror so the profile can draw before
                // the map arrives; the server's answer always wins.
                courseState.map?.studySetup?.dailyGoalXp
                    ?.takeIf { it > 0 }
                    ?.let { app.appSettings.setDailyGoal(it) }
            }

            // The blocks arrive with the map, but they belong to every
            // section, so they are handed to their own holder rather than
            // read off the course screen's state.
            LaunchedEffect(courseState.map?.hints) {
                hintsViewModel.onMapLoaded(courseState.map?.hints.orEmpty())
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

            LaunchedEffect(profileState.profileRevision) {
                if (profileState.profileRevision > 0) ratingViewModel.refreshIfLoaded()
            }

            val context = LocalContext.current
            val notificationPermission = rememberLauncherForActivityResult(
                ActivityResultContracts.RequestPermission()
            ) { granted ->
                scope.launch {
                    app.widgetStore.setReminder(granted)
                    if (granted) StudyReminderScheduler.schedule(context)
                }
            }

            val notificationsOn = widgetSession.reminderEnabled
            LaunchedEffect(notificationsOn) {
                when (notificationsOn) {
                    true -> if (StudyNotifications.canPost(context)) {
                        StudyReminderScheduler.schedule(context)
                    }
                    false -> {
                        StudyReminderScheduler.cancel(context)
                        StudyNotifications.cancelReminder(context)
                    }
                }
            }

            val toggleLocalReminder: (Boolean) -> Unit = { enabled ->
                if (enabled && android.os.Build.VERSION.SDK_INT >= 33 && !StudyNotifications.canPost(context)) {
                    notificationPermission.launch(android.Manifest.permission.POST_NOTIFICATIONS)
                } else if (enabled && !StudyNotifications.canPost(context)) {
                    android.widget.Toast.makeText(context, R.string.widget_setup_permission, android.widget.Toast.LENGTH_LONG).show()
                } else {
                    scope.launch { app.widgetStore.setReminder(enabled) }
                }
            }

            var checkoutVisible by rememberSaveable { mutableStateOf(false) }
            var checkoutOrigin by rememberSaveable { mutableStateOf("course_limit") }
            val limitGate = rememberLimitGate(
                repository = app.featureRepository,
                viewModelStoreOwner = sessionOwner,
                supportUrl = profileState.profile?.supportUrl.orEmpty(),
                isRefreshing = courseState.isLoading || profileState.isLoading,
                onRefreshAccess = {
                    courseViewModel.load()
                    profileViewModel.load()
                    voiceViewModel.refreshStatusIfLoaded()
                },
                onOpenSubscription = { origin ->
                    checkoutOrigin = origin
                    checkoutVisible = true
                },
                // Whether this account may still take the free week is the
                // server's answer, read once here and shown everywhere — the
                // same way the Mini App reads it once and uses it on the
                // paywall, the profile and after onboarding.
                trialEligible = profileState.trial?.eligible == true,
                trialStarting = profileState.trialStarting,
                trialError = profileState.trialError,
                onStartTrial = profileViewModel::startTrial,
            )

            // A trial or an admin-approved payment changes every section's
            // access. Re-read spent sections when the server confirms it.
            val accessActive = profileState.trial?.active == true ||
                profileState.profile?.subscription?.isPaid == true
            var accessWasActive by remember { mutableStateOf<Boolean?>(null) }
            LaunchedEffect(accessActive) {
                val previous = accessWasActive
                accessWasActive = accessActive
                if (previous == false && accessActive) {
                    courseViewModel.load()
                    voiceViewModel.refreshStatusIfLoaded()
                    // Limit bloki O'ZI yo'qolishi kerak. Aks holda odam
                    // "7 kun bepul" ni bosgandan keyin ham o'sha oynani
                    // ko'rib turadi va tugma ishlamagandek tuyuladi.
                    practiceViewModel.onAccessChanged()
                }
            }

            val dailyGoal by app.appSettings.dailyGoal
                .collectAsStateWithLifecycle(initialValue = DailyGoal.DEFAULT)
            val voiceSubtitles by app.appSettings.voiceSubtitles
                .collectAsStateWithLifecycle(initialValue = true)
            val voiceSlowSpeech by app.appSettings.voiceSlowSpeech
                .collectAsStateWithLifecycle(initialValue = false)
            // Starts as "seen" so the primer cannot flash on top of the app
            // in the moment before the store has been read.
            val notificationPrimerSeen by app.appSettings.notificationPrimerSeen
                .collectAsStateWithLifecycle(initialValue = true)
            LaunchedEffect(
                onboardingState.completed,
                notificationPrimerSeen,
                widgetSession.reminderEnabled,
            ) {
                if (
                    !screenCenterAdAsked &&
                    onboardingState.completed &&
                    (notificationPrimerSeen || widgetSession.reminderEnabled)
                ) {
                    screenCenterAdAsked = true
                    delay(SCREEN_CENTER_AD_DELAY_MS)
                    if (adRequest == null) {
                        adRequest = AdRequest(placement = AdViewModel.PLACEMENT_SCREEN_CENTER)
                    }
                }
            }
            LaunchedEffect(voiceSlowSpeech) { voiceViewModel.setSlowSpeech(voiceSlowSpeech) }
            var goalPickerOpen by remember { mutableStateOf(false) }
            var practiceRequest by remember { mutableStateOf<PracticeRequest?>(null) }
            var openDrill by remember { mutableStateOf<DrillLaunch?>(null) }
            var openChallenge by remember { mutableStateOf<ChallengeDto?>(null) }
            var ratingChallengesOpen by rememberSaveable { mutableStateOf(false) }
            var ratingUserOpen by remember { mutableStateOf<RatingEntryDto?>(null) }
            var selectedTab by remember { mutableStateOf(MainTab.COURSE) }

            // Secondary tabs own their first server load. Returning to an already
            // opened tab is local unless that feature explicitly requests refresh.
            LaunchedEffect(selectedTab) {
                when (selectedTab) {
                    MainTab.PRACTICE -> practiceViewModel.ensureMistakesLoaded()
                    MainTab.VOICE -> voiceViewModel.ensureStatusLoaded()
                    MainTab.RATING -> ratingViewModel.ensureLoaded()
                    else -> Unit
                }
            }

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

            // Which locked lesson the skip test is running for, if any.
            var skipTestLesson by remember { mutableStateOf<CourseLesson?>(null) }

            fun launchDrill(mode: DrillMode) {
                // A drill is an attempt, not a reusable destination. A fresh
                // key prevents a completed/result state from surviving into
                // another mode or into a later run of the same mode.
                openDrill = DrillLaunch(mode = mode)
            }

            // A daily-plan step opens the same screen its Mini App counterpart
            // does (`TODAY_TASK_ACTION` / `TODAY_SKILL_ACTION` in course-v3).
            fun openTodayTask(task: TodayTask) {
                when (task.type) {
                    "continue_lesson" -> courseState.map?.currentLesson?.let { lesson ->
                        if (
                            lesson.access == LessonAccess.Open ||
                            lesson.access == LessonAccess.HalfPreview
                        ) {
                            launchLesson(lesson)
                        }
                    }

                    "mistake_review" -> {
                        practiceRequest = PracticeRequest.MISTAKES
                        selectedTab = MainTab.PRACTICE
                    }

                    "mock_exam" -> {
                        practiceRequest = PracticeRequest.TESTS
                        selectedTab = MainTab.PRACTICE
                    }

                    "skill_drill" -> {
                        practiceRequest = if (task.skill == "pronunciation") {
                            PracticeRequest.PRONUNCIATION
                        } else {
                            PracticeRequest.RECOGNITION
                        }
                        selectedTab = MainTab.PRACTICE
                    }

                    "voice_dialog" -> {
                        // The plan picks the role that fits the learner's goal;
                        // dropping it would always open the same partner.
                        task.role?.takeIf { it.isNotBlank() }?.let(voiceViewModel::selectRole)
                        selectedTab = MainTab.VOICE
                    }
                }
            }

            LaunchedEffect(requestedDestination, onboardingState.completed) {
                if (!onboardingState.completed) return@LaunchedEffect
                val request = requestedDestination ?: return@LaunchedEffect
                val destination = request.destination
                // Assistant actions enter through the same server-authorized deep-link path.
                openLesson = null
                openDrill = null
                openChallenge = null
                ratingChallengesOpen = false
                ratingUserOpen = null
                dictionaryOpen = false
                selectedTab = destination.toTab() ?: selectedTab
                when (destination) {
                    AppDestination.CurrentLesson,
                    is AppDestination.Lesson,
                    -> {
                        // Every entry gets a NEW server check, even if an older map looked fresh.
                        // A failure is consumed on Kurs, never left queued to open later unexpectedly.
                        val epoch = app.widgetStore.read().epoch
                        val fresh = (app.courseRepository.courseMap() as? com.pomp.hskai.core.network.ApiResult.Success)?.value
                        val map = fresh?.takeUnless { it.isStale }?.map
                        if (fresh != null) app.widgetCoordinator.publish(fresh, epoch)
                        if (map == null || map.foundation?.mustComeFirst == true) {
                            courseViewModel.load()
                            onDestinationConsumed()
                            return@LaunchedEffect
                        }
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
                    AppDestination.WidgetSetup -> {
                        widgetPromptFromOnboarding = false
                        scope.launch {
                            app.widgetStore.markInstallPromptShown(LocalDate.now().toString())
                        }
                        widgetSetupOpen = true
                        onDestinationConsumed()
                    }
                    // `toTab()` above has already moved to Mashq; this opens the
                    // named tool inside it, which the link used to lose.
                    is AppDestination.Practice -> {
                        // Reset kept from the `else` branch this used to fall
                        // into, so a later lesson link can still claim the gate.
                        deepLinkRefreshGate.reset()
                        practiceRequest = destination.tool?.toRequest()
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
                    authRepository.logout(unlinkDevice = unlink)
                    app.clearLocalData()
                }
            }

            val launch = openLesson
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
            } else if (!notificationPrimerSeen && !widgetSession.reminderEnabled) {
                // Asked once, at the end of onboarding, for both kinds of
                // notification at once: Android grants them for the whole app,
                // not per kind, and it stops showing its dialog after two
                // refusals. Whatever the answer, the flag is written and the
                // question never comes back.
                NotificationPrimerScreen(
                    language = currentLanguage,
                    onAllow = {
                        scope.launch { app.appSettings.setNotificationPrimerSeen() }
                        toggleLocalReminder(true)
                    },
                    onSkip = {
                        scope.launch { app.appSettings.setNotificationPrimerSeen() }
                    },
                )
            } else if (checkoutVisible) {
                SubscriptionCheckoutHost(
                    repository = app.featureRepository,
                    viewModelStoreOwner = sessionOwner,
                    origin = checkoutOrigin,
                    onClose = {
                        checkoutVisible = false
                        profileViewModel.load()
                        courseViewModel.load()
                        voiceViewModel.refreshStatusIfLoaded()
                        practiceViewModel.onAccessChanged()
                    },
                )
            } else if (ratingChallengesOpen) {
                RatingChallengesScreen(
                    state = ratingState,
                    onRespond = ratingViewModel::respond,
                    onStartChallenge = { duel ->
                        ratingChallengesOpen = false
                        openChallenge = duel
                    },
                    onBack = { ratingChallengesOpen = false },
                )
            } else if (ratingUserOpen != null) {
                RatingUserScreen(
                    user = checkNotNull(ratingUserOpen),
                    league = ratingState.rating?.league.orEmpty(),
                    currentWeeklyXp = ratingState.rating?.weeklyXp ?: 0,
                    isChallengeBusy = ratingState.isChallengeBusy,
                    challengeDelivery = ratingState.challengeDelivery,
                    challengeError = ratingState.challengeError,
                    onChallenge = { ref ->
                        ratingViewModel.challenge(ref, currentLevel, currentLanguage)
                    },
                    onMessage = { username ->
                        openExternal(context, "https://t.me/${username.trim().lstripAt()}")
                    },
                    onBack = {
                        ratingViewModel.clearChallengeFeedback()
                        ratingUserOpen = null
                    },
                )
            } else if (openChallenge != null) {
                val duel = openChallenge!!
                val challengeViewModel: ChallengeRunViewModel = viewModel(
                    key = "challenge-${duel.id}",
                    viewModelStoreOwner = sessionOwner,
                    factory = ChallengeRunViewModel.Factory(
                        repository = app.featureRepository,
                        challengeId = duel.id,
                    ),
                )
                val challengeState by challengeViewModel.state.collectAsStateWithLifecycle()
                ChallengeRunScreen(
                    state = challengeState,
                    opponentName = duel.otherUser.name,
                    onSelect = challengeViewModel::select,
                    onAdvance = challengeViewModel::advance,
                    onRetry = challengeViewModel::load,
                    onClose = {
                        openChallenge = null
                        ratingViewModel.load()
                    },
                )
            } else if (openDrill != null) {
                val drill = openDrill!!
                val mode = drill.mode
                val drillViewModel: WordDrillViewModel = viewModel(
                    key = drill.viewModelKey,
                    viewModelStoreOwner = sessionOwner,
                    factory = WordDrillViewModel.Factory(
                        repository = app.featureRepository,
                        dictionary = app.dictionaryRepository,
                        recorder = app.voiceRecorder,
                        mode = mode,
                        level = currentLevel,
                        language = state.account.language,
                    ),
                )
                val drillState by drillViewModel.state.collectAsStateWithLifecycle()
                // Mashq ichida turib trial olingan bo'lsa ham blok yopilsin.
                LaunchedEffect(accessActive) {
                    if (accessActive) drillViewModel.onAccessChanged()
                }
                WordDrillScreen(
                    state = drillState,
                    limit = limitGate,
                    onChoose = drillViewModel::choose,
                    onSpeak = drillViewModel::speak,
                    onSkipSpoken = drillViewModel::skipSpoken,
                    onAdvance = drillViewModel::advance,
                    onRetry = { drillViewModel.load() },
                    onClose = {
                        openDrill = null
                        courseViewModel.load()
                    },
                )
            } else if (skipTestLesson != null) {
                // The skip test is its own screen, beside the lesson and the
                // drill rather than inside the map: it runs the lesson's own
                // cards, so it needs the whole window.
                val locked = checkNotNull(skipTestLesson)
                val skipTestViewModel: SkipTestViewModel = viewModel(
                    key = "skip-test-$currentLevel-${locked.order}",
                    viewModelStoreOwner = sessionOwner,
                    factory = SkipTestViewModel.Factory(
                        repository = app.courseRepository,
                        level = currentLevel,
                        language = state.account.language,
                    ),
                )
                val skipTestState by skipTestViewModel.state.collectAsStateWithLifecycle()
                SkipTestScreen(
                    state = skipTestState,
                    pinyin = pinyin,
                    onStart = { skipTestViewModel.start(locked.order) },
                    onSelect = skipTestViewModel::select,
                    onAdvance = skipTestViewModel::advance,
                    onUnlock = { skipTestViewModel.unlock() },
                    onOpenLesson = {
                        // The server moved progress; the map has to be re-read
                        // before the lesson can be walked into.
                        skipTestLesson = null
                        courseViewModel.load()
                        launchLesson(locked)
                    },
                    onClose = {
                        skipTestLesson = null
                        if (skipTestState.unlocked) courseViewModel.load()
                    },
                )
            } else if (dictionaryOpen) {
                val dictionaryViewModel: DictionaryViewModel = viewModel(
                    key = "dictionary-${state.account.language.backendCode}",
                    viewModelStoreOwner = sessionOwner,
                    factory = DictionaryViewModel.Factory(
                        repository = app.dictionaryRepository,
                        courseRepository = app.courseRepository,
                        audioPlayer = app.lessonAudioPlayer,
                        language = state.account.language,
                    ),
                )
                val dictionaryState by dictionaryViewModel.state.collectAsStateWithLifecycle()
                DictionaryScreen(
                    state = dictionaryState,
                    onQueryChange = dictionaryViewModel::onQueryChange,
                    onRetry = dictionaryViewModel::load,
                    onOpenWord = dictionaryViewModel::openWord,
                    onCloseWord = dictionaryViewModel::closeWord,
                    onPreviousCharacter = dictionaryViewModel::previousCharacter,
                    onNextCharacter = dictionaryViewModel::nextCharacter,
                    onPreviousStroke = dictionaryViewModel::previousStroke,
                    onReplayStrokes = dictionaryViewModel::replayStrokes,
                    onNextStroke = dictionaryViewModel::nextStroke,
                    onPlayAudio = dictionaryViewModel::playAudio,
                    onPreviousWord = dictionaryViewModel::previousWord,
                    onNextWord = dictionaryViewModel::nextWord,
                    onOpenRecognition = {
                        dictionaryOpen = false
                        launchDrill(DrillMode.RECOGNITION)
                    },
                    onOpenPronunciation = {
                        dictionaryOpen = false
                        launchDrill(DrillMode.PRONUNCIATION)
                    },
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
                    limit = limitGate,
                    accessChanged = accessActive,
                    onExit = { completed ->
                        val finishedOrder = launch.lesson.order
                        openLesson = null
                        courseViewModel.load()
                        if (completed) {
                            // Mini App `playLessonEnd`: one block after the
                            // lesson, for learners the server still shows ads
                            // to. It opens nothing, so it carries no gate.
                            adRequest = AdRequest(
                                placement = AdViewModel.PLACEMENT_LESSON_END,
                                lessonOrder = finishedOrder,
                            )
                        }
                    },
                )
            } else {
                // A running AI Voice conversation takes the whole screen:
                // the tabs are not a place to leave a call from, the Close
                // button is, and the Mini App shows no tabs there either.
                val voiceCallActive = selectedTab == MainTab.VOICE &&
                    voiceState.hasSession &&
                    voiceState.result == null

                // Kurs is the home screen: back from any other tab lands on it,
                // and only back from Kurs leaves the app. Registered before the
                // tabs, so a tab's own back (a call, an open list) goes first.
                BackHandler(enabled = selectedTab != MainTab.COURSE) {
                    selectedTab = MainTab.COURSE
                }

                Box(Modifier.fillMaxSize()) {
                    MainScaffold(
                        selectedTab = selectedTab,
                        onTabSelected = { selectedTab = it },
                        bottomBarVisible = !voiceCallActive,
                    ) { tab, contentModifier ->
                        when (tab) {
                            MainTab.COURSE -> CourseScreen(
                                state = courseState,
                                dailyGoal = dailyGoal,
                                limit = limitGate,
                                hints = hints,
                                onDismissHint = hintsViewModel::dismiss,
                                onLesson = { lesson -> launchLesson(lesson) },
                                onLockedLesson = { lesson -> skipTestLesson = lesson },
                                onTodayTask = ::openTodayTask,
                                onOpenGoal = { goalPickerOpen = true },
                                onOpenChest = courseViewModel::openRewardChest,
                                onChestRewardConsumed = courseViewModel::consumeChestReward,
                                onUnlockAnimationConsumed = courseViewModel::consumeLessonUnlock,
                                onRetry = courseViewModel::load,
                                modifier = contentModifier,
                            )

                            MainTab.PRACTICE -> PracticeScreen(
                                state = practiceState,
                                level = currentLevel,
                                language = currentLanguage,
                                limit = limitGate,
                                hints = hints,
                                onDismissHint = hintsViewModel::dismiss,
                                onDismissLimit = practiceViewModel::dismissLimit,
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
                                onSpeakReview = practiceViewModel::playReviewAudio,
                                onStartExam = { examLevel ->
                                    practiceViewModel.startExam(examLevel, currentLanguage)
                                },
                                onSelectExamOption = practiceViewModel::selectExamOption,
                                onAdvanceExam = practiceViewModel::advanceExam,
                                onResetExam = practiceViewModel::resetExam,
                                onOpenDrill = ::launchDrill,
                                request = practiceRequest,
                                onRequestConsumed = { practiceRequest = null },
                                modifier = contentModifier,
                            )

                            MainTab.VOICE -> VoiceScreen(
                                state = voiceState,
                                level = currentLevel,
                                language = currentLanguage,
                                limit = limitGate,
                                hints = hints,
                                onDismissHint = hintsViewModel::dismiss,
                                subtitlesOn = voiceSubtitles,
                                slowSpeech = voiceSlowSpeech,
                                onToggleSubtitles = { on ->
                                    scope.launch { app.appSettings.setVoiceSubtitles(on) }
                                },
                                onToggleSlowSpeech = { slow ->
                                    scope.launch { app.appSettings.setVoiceSlowSpeech(slow) }
                                },
                                onSelectRole = voiceViewModel::selectRole,
                                onStartSession = voiceViewModel::startSession,
                                onToggleRecording = voiceViewModel::toggleRecording,
                                onSendText = voiceViewModel::sendTypedMessage,
                                onEndSession = voiceViewModel::endSession,
                                onSwapPartner = { role ->
                                    voiceViewModel.swapPartner(role, currentLevel, currentLanguage)
                                },
                                onReset = voiceViewModel::reset,
                                modifier = contentModifier,
                            )

                            MainTab.RATING -> RatingScreen(
                                state = ratingState,
                                hints = hints,
                                onDismissHint = hintsViewModel::dismiss,
                                onSelectTab = ratingViewModel::selectTab,
                                onOpenChallenges = { ratingChallengesOpen = true },
                                onOpenUser = { user ->
                                    ratingViewModel.clearChallengeFeedback()
                                    ratingUserOpen = user
                                },
                                onInviteFriends = { link -> shareText(context, link) },
                                onChallenge = { ref ->
                                    ratingViewModel.challenge(ref, currentLevel, currentLanguage)
                                },
                                onRetry = ratingViewModel::load,
                                modifier = contentModifier,
                            )

                            MainTab.PROFILE -> ProfileScreen(
                                account = state.account,
                                state = profileState,
                                settings = settingsState,
                                hints = hints,
                                onDismissHint = hintsViewModel::dismiss,
                                courseProgress = courseState.map?.progress,
                                courseUser = courseState.map?.user,
                                onOpenMistakes = {
                                    practiceRequest = PracticeRequest.MISTAKES
                                    selectedTab = MainTab.PRACTICE
                                },
                                onOpenFriends = {
                                    ratingViewModel.selectTab(RatingTab.FRIENDS)
                                    selectedTab = MainTab.RATING
                                },
                                dailyXp = courseState.map?.progress?.dailyXp ?: 0,
                                dailyGoal = dailyGoal,
                                notificationsEnabled = notificationsOn,
                                onOpenGoal = { goalPickerOpen = true },
                                onOpenLanguage = { languagePickerOpen = true },
                                onToggleNotifications = toggleLocalReminder,
                                onOpenWidget = {
                                    widgetPromptFromOnboarding = false
                                    scope.launch {
                                        app.widgetStore.markInstallPromptShown(LocalDate.now().toString())
                                    }
                                    widgetSetupOpen = true
                                },
                                onOpenSupport = { url -> openExternal(context, url) },
                                onRefresh = profileViewModel::load,
                                onLogout = { signOut(false) },
                                onUnlinkDevice = { signOut(true) },
                                modifier = contentModifier,
                                identities = identitiesState,
                                onLoadIdentities = identitiesViewModel::refresh,
                                onConnectIdentity = identitiesViewModel::connect,
                                onDisconnectIdentity = identitiesViewModel::disconnect,
                                onIdentitiesBrowserOpened = identitiesViewModel::browserUrlOpened,
                                onSaveProfile = profileViewModel::saveProfile,
                                profileSaving = profileState.profileSaving,
                            )
                        }
                    }

                    if (widgetSetupOpen) {
                        val finishWidgetPrompt: (placed: Boolean) -> Unit = { placed ->
                            WidgetScheduler.schedule(context)
                            widgetSetupOpen = false
                            if (widgetPromptFromOnboarding) {
                                widgetPromptFromOnboarding = false
                                widgetOfferHandled = true
                            }
                            // The prompt closes at once; the confirmation takes its place.
                            if (placed) widgetPlacedNotice = true
                        }
                        WidgetInstallPromptScreen(
                            onDismiss = {
                                widgetSetupOpen = false
                                if (widgetPromptFromOnboarding) {
                                    widgetPromptFromOnboarding = false
                                    widgetOfferHandled = true
                                }
                            },
                            onInstalled = { finishWidgetPrompt(false) },
                            onPlaced = { finishWidgetPrompt(true) },
                        )
                    } else if (studySetupState.visible) {
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

                        if (planChoiceOpen) {
                            PlanChoiceSheet(
                                isStarting = profileState.trialStarting,
                                onStartTrial = {
                                    planChoiceOpen = false
                                    profileViewModel.startTrial()
                                },
                                // Left out entirely in the Google Play build,
                                // which may not send a learner out of the app to
                                // pay. The gate is what knows that, not this file.
                                onSubscribe = if (limitGate.state.canSubscribe) {
                                    {
                                        planChoiceOpen = false
                                        limitGate.actions.onUnlock()
                                    }
                                } else {
                                    null
                                },
                                onDismiss = { planChoiceOpen = false },
                            )
                        }

                        if (goalPickerOpen) {
                            DailyGoalPicker(
                                current = dailyGoal,
                                onPick = { value ->
                                    goalPickerOpen = false
                                    // Written locally at once so the profile does
                                    // not lag behind the tap, and sent on, because
                                    // the Mini App reads the same number.
                                    scope.launch { app.appSettings.setDailyGoal(value) }
                                    studySetupViewModel.chooseDailyGoalXp(value)
                                },
                                onDismiss = { goalPickerOpen = false },
                            )
                        }
                    }

                    if (widgetPlacedNotice) {
                        WidgetPlacedNotice(onDone = { widgetPlacedNotice = false })
                    }

                    val ad = adRequest
                    if (ad != null) {
                        val adViewModel: AdViewModel = viewModel(
                            key = "ad-${ad.requestId}",
                            viewModelStoreOwner = sessionOwner,
                            factory = AdViewModel.Factory(
                                repository = app.featureRepository,
                                placement = ad.placement,
                                lessonOrder = ad.lessonOrder,
                            ),
                        )
                        val adState by adViewModel.state.collectAsStateWithLifecycle()
                        // The learner keeps seeing the current app screen while
                        // media loads. The card appears only when the ad is
                        // real, which avoids the full-screen grey reopening
                        // effect seen in the emulator capture.
                        LaunchedEffect(adState.finished, adState.unavailable) {
                            if (adState.finished || adState.unavailable) adRequest = null
                        }
                        AdScreen(
                            state = adState,
                            onContinue = adViewModel::onContinue,
                            onClose = { adRequest = null },
                            onOpenLink = { url -> openExternal(context, url) },
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
    limit: LimitGate,
    accessChanged: Boolean,
    /** [completed] says whether the lesson was actually finished and reported. */
    onExit: (completed: Boolean) -> Unit,
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
            resumeStore = app.appSettings,
            // Only the rank-up board uses it, and only when the lesson moved
            // the learner up the weekly league.
            featureRepository = app.featureRepository,
            voiceRecorder = app.voiceRecorder,
        ),
    )
    val lessonState by model.state.collectAsStateWithLifecycle()
    LaunchedEffect(lessonState.outcome) {
        if (lessonState.outcome is LessonOutcome.Completed) app.widgetCoordinator.refresh()
    }
    val scope = rememberCoroutineScope()
    var pinyinSheetOpen by remember { mutableStateOf(false) }

    LaunchedEffect(launch.attemptKey) {
        model.beginAttempt(launch.attemptKey)
    }
    LaunchedEffect(accessChanged, launch.attemptKey) {
        if (accessChanged) model.load()
    }
    DisposableEffect(model, launch.attemptKey) {
        onDispose { model.endAttempt(launch.attemptKey) }
    }

    // Registered for its context only: the floating AI button stays off the
    // lesson and its celebration, and the chat is reached from the questions
    // the lesson offers after a wrong answer.
    com.pomp.hskai.feature.assistant.AssistantScreen(
        com.pomp.hskai.feature.assistant.lessonAssistantContext(lessonState, launch.attemptKey),
        bottomBar = false,
        priority = 10,
        showButton = false,
    )
    // After a wrong answer the lesson offers questions for the AI chat; they
    // exist only while the chat itself is switched on.
    val assistant = com.pomp.hskai.feature.assistant.LocalAssistant.current
    val assistantEnabled = assistant?.controller?.state?.collectAsStateWithLifecycle()?.value?.enabled == true

    LessonScreen(
        state = lessonState,
        limit = limit,
        pinyin = pinyin,
        onAnswerChoice = model::answerChoice,
        onAnswerBuilder = model::answerBuilder,
        onAnswerPairs = model::answerMatchPairs,
        onAcknowledge = model::acknowledge,
        onAdvance = model::advance,
        onPlayAudio = model::playAudio,
        onSpeakPronunciation = model::speakPronunciation,
        onSkipPronunciation = model::skipPronunciation,
        onRetryCompletion = model::retryCompletion,
        onOpenPinyinSettings = { pinyinSheetOpen = true },
        onOpenWriter = model::openWriter,
        onShowWriterCharacter = model::showWriterCharacter,
        onCloseWriter = model::closeWriter,
        onExit = {
            val completed = lessonState.outcome is LessonOutcome.Completed
            model.endAttempt(launch.attemptKey)
            onExit(completed)
        },
        onAskAssistant = if (assistant != null && assistantEnabled) assistant.ask else null,
    )

    if (pinyinSheetOpen) {
        PinyinPicker(
            current = pinyin,
            onPick = { value ->
                scope.launch { app.appSettings.setPinyinVisibility(value) }
                pinyinSheetOpen = false
            },
            onDismiss = { pinyinSheetOpen = false },
        )
    }
}

/**
 * Mini App `App.pinyinSheet()`. The setting already existed here but had no
 * control anywhere in the app, so a learner could not turn pinyin off the way
 * the Mini App lets them.
 */
/**
 * The Mini App's plan choice, shown once after onboarding.
 *
 * Two ways forward and one way past: take the free week, subscribe, or carry
 * on free. Nothing here is compulsory — the X and the outside of the sheet
 * both dismiss it, and the learner who dismisses it loses nothing, because
 * the same offer is on the profile and on every paywall.
 *
 * [onSubscribe] is null in the Google Play build, which has no checkout of
 * its own; the button is then not drawn at all rather than drawn dead.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PlanChoiceSheet(
    isStarting: Boolean,
    onStartTrial: () -> Unit,
    onSubscribe: (() -> Unit)?,
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
                text = stringResource(R.string.plan_choice_title),
                style = androidx.compose.material3.MaterialTheme.typography.titleMedium,
                color = PompColors.Ink,
            )
            Spacer(Modifier.height(6.dp))
            Text(
                text = stringResource(R.string.plan_choice_body),
                style = androidx.compose.material3.MaterialTheme.typography.bodyMedium,
                color = PompColors.InkSecondary,
            )
            Spacer(Modifier.height(16.dp))
            Button(
                onClick = onStartTrial,
                enabled = !isStarting,
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 52.dp),
                shape = androidx.compose.foundation.shape.RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = PompColors.Cinnabar,
                    contentColor = PompColors.Paper,
                    disabledContainerColor = PompColors.Locked,
                    disabledContentColor = PompColors.Paper,
                ),
            ) {
                Text(text = stringResource(R.string.plan_choice_trial))
            }
            if (onSubscribe != null) {
                Spacer(Modifier.height(8.dp))
                OutlinedButton(
                    onClick = onSubscribe,
                    enabled = !isStarting,
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 48.dp),
                    shape = androidx.compose.foundation.shape.RoundedCornerShape(14.dp),
                ) {
                    Text(
                        text = stringResource(R.string.plan_choice_pay),
                        color = PompColors.CinnabarDark,
                    )
                }
            }
            Spacer(Modifier.height(4.dp))
            TextButton(
                onClick = onDismiss,
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 44.dp),
            ) {
                Text(
                    text = stringResource(R.string.plan_choice_later),
                    color = PompColors.InkSecondary,
                )
            }
            Spacer(Modifier.height(12.dp))
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PinyinPicker(
    current: PinyinVisibility,
    onPick: (PinyinVisibility) -> Unit,
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
                text = stringResource(R.string.lesson_pinyin_title),
                style = androidx.compose.material3.MaterialTheme.typography.titleMedium,
                color = PompColors.Ink,
            )
            androidx.compose.foundation.layout.Spacer(Modifier.padding(6.dp))
            PinyinVisibility.entries.forEach { option ->
                val selected = option == current
                val labelRes = when (option) {
                    PinyinVisibility.ALL -> R.string.lesson_pinyin_all
                    PinyinVisibility.NEW_WORDS_ONLY -> R.string.lesson_pinyin_new
                    PinyinVisibility.OFF -> R.string.lesson_pinyin_off
                }
                Surface(
                    color = if (selected) PompColors.CinnabarSoft else PompColors.PaperRaised,
                    shape = androidx.compose.foundation.shape.RoundedCornerShape(14.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 52.dp)
                        .padding(vertical = 4.dp)
                        .clickable { onPick(option) },
                ) {
                    Text(
                        text = stringResource(labelRes),
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

private fun shareText(context: Context, text: String): Boolean {
    if (text.isBlank()) return false
    return runCatching {
        val send = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, text)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(Intent.createChooser(send, null).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        })
        true
    }.getOrDefault(false)
}

private fun String.lstripAt(): String = removePrefix("@")

private const val SCREEN_CENTER_AD_DELAY_MS = 700L

/**
 * One ad to show, in one of the two places the product has left: after a
 * lesson, or in the centre of the screen.
 *
 * [requestId] only keys the ViewModel so that a second ad gets a fresh one.
 * It carries no meaning for the server — an ad opens nothing, so there is
 * nothing to bind it to.
 */
private data class AdRequest(
    val placement: String,
    val lessonOrder: Int = 0,
    val requestId: String = UUID.randomUUID().toString(),
)

private data class LessonLaunch(
    val lesson: CourseLesson,
    val attemptKey: String,
)

internal data class DrillLaunch(
    val mode: DrillMode,
    val attemptKey: String = UUID.randomUUID().toString(),
) {
    /** Every opening owns a fresh ViewModel, even for the same drill mode. */
    val viewModelKey: String
        get() = "drill-$attemptKey"
}

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
            HskBrandLoader()
        }
    }
}

/** Shows the last local course map while a cold-start bearer refresh is offline. */
@Composable
private fun OfflineCourseEntry(
    app: HskAiApplication,
    onRetry: () -> Unit,
) {
    val courseState by produceState(
        initialValue = com.pomp.hskai.feature.course.CourseUiState(),
        key1 = app,
    ) {
        value = when (val result = app.courseRepository.courseMap()) {
            is com.pomp.hskai.core.network.ApiResult.Success ->
                com.pomp.hskai.feature.course.CourseUiState(
                    isLoading = false,
                    isRefreshing = false,
                    snapshot = result.value,
                    error = result.value.refreshError,
                )

            is com.pomp.hskai.core.network.ApiResult.Failure ->
                com.pomp.hskai.feature.course.CourseUiState(
                    isLoading = false,
                    isRefreshing = false,
                    error = result.error,
                )
        }
    }
    CourseScreen(
        state = courseState,
        dailyGoal = DailyGoal.DEFAULT,
        limit = LimitGate(),
        onLesson = {},
        onTodayTask = {},
        onOpenGoal = {},
        onOpenChest = {},
        onChestRewardConsumed = {},
        onRetry = onRetry,
        modifier = Modifier.fillMaxSize(),
    )
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
