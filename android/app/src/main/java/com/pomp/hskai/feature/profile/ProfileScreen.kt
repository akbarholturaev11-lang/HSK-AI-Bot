package com.pomp.hskai.feature.profile

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.HelpOutline
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.HelpOutline
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.People
import androidx.compose.material.icons.filled.PersonOutline
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.TrackChanges
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material.icons.filled.Widgets
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.window.DialogWindowProvider
import androidx.core.view.WindowCompat
import coil.compose.AsyncImage
import com.pomp.hskai.BuildConfig
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.AuthProvider
import com.pomp.hskai.core.auth.LinkedAccount
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskSceneSurface
import com.pomp.hskai.core.design.PompShapes
import com.pomp.hskai.core.design.PompSpacing
import com.pomp.hskai.core.design.components.HskBrandLoader
import com.pomp.hskai.feature.course.Hsk30LevelChoiceDialog
import com.pomp.hskai.core.design.components.HskGlassSurface
import com.pomp.hskai.core.design.components.HskSectionTitle
import com.pomp.hskai.core.navigation.LocalMainBottomInset
import com.pomp.hskai.feature.update.AppUpdateCard
import com.pomp.hskai.core.navigation.AppDestination
import com.pomp.hskai.core.navigation.DeepLinkRouter
import com.pomp.hskai.core.navigation.PracticeTool
import com.pomp.hskai.core.network.MediaUrl
import com.pomp.hskai.core.settings.AppSettings
import com.pomp.hskai.core.settings.AppThemeMode
import com.pomp.hskai.data.api.AndroidHintDto
import com.pomp.hskai.domain.model.CourseHsk30
import com.pomp.hskai.domain.model.CourseProgress
import com.pomp.hskai.domain.model.CourseUser
import com.pomp.hskai.feature.assistant.AssistantScreen
import com.pomp.hskai.feature.assistant.profileAssistantContext
import com.pomp.hskai.feature.assistant.AssistantModalBottomSheet as ModalBottomSheet
import com.pomp.hskai.feature.course.GoalRing
import com.pomp.hskai.feature.hint.SectionHint
import com.pomp.hskai.widget.WidgetScheduler
import kotlinx.coroutines.launch
import java.time.Instant
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * Android profile follows the Mini App profile surface. The Settings entry is
 * intentionally Android-specific because appearance and device controls live there.
 */
@Composable
fun ProfileScreen(
    account: LinkedAccount,
    state: ProfileUiState,
    settings: ProfileSettingsState,
    hints: List<AndroidHintDto> = emptyList(),
    onDismissHint: (String) -> Unit = {},
    courseProgress: CourseProgress?,
    courseUser: CourseUser?,
    onOpenMistakes: (() -> Unit)? = null,
    onOpenFriends: () -> Unit,
    dailyXp: Int,
    dailyGoal: Int,
    notificationsEnabled: Boolean,
    onOpenGoal: () -> Unit,
    onOpenLanguage: () -> Unit,
    onToggleNotifications: (Boolean) -> Unit,
    onOpenWidget: () -> Unit,
    onOpenSupport: (String) -> Unit,
    onRefresh: () -> Unit,
    onLogout: () -> Unit,
    onUnlinkDevice: () -> Unit,
    courseTrack: String = "hsk20",
    hsk30Enabled: Boolean = false,
    hsk30IsNew: Boolean = false,
    hsk30LiveLevels: List<String> = listOf("nhsk1"),
    hsk30: CourseHsk30? = null,
    onOpenApps: () -> Unit = {},
    onOpenCourse: () -> Unit = {},
    onUnlockHsk30: () -> Unit = {},
    onStartTrial: () -> Unit = {},
    onSwitchCourseTrack: (String, String?) -> Unit = { _, _ -> },
    modifier: Modifier = Modifier,
    identities: IdentitiesUiState = IdentitiesUiState(),
    onLoadIdentities: () -> Unit = {},
    onConnectIdentity: (AuthProvider, Activity?) -> Unit = { _, _ -> },
    onDisconnectIdentity: (String) -> Unit = {},
    onIdentitiesBrowserOpened: () -> Unit = {},
    onSaveProfile: (String, String) -> Unit = { _, _ -> },
    profileSaving: Boolean = false,
    onOpenSubscription: (renewal: Boolean) -> Unit = {},
    subscriptionCheckoutAvailable: Boolean = BuildConfig.FLAVOR == "direct",
) {
    AssistantScreen(profileAssistantContext(state), bottomBar = true, showButton = false)
    var settingsOpen by remember { mutableStateOf(false) }
    var profileHsk30BookOpen by remember { mutableStateOf(false) }
    var profileHsk30LevelOpen by remember { mutableStateOf(false) }
    var appearancePickerOpen by remember { mutableStateOf(false) }
    var identitiesOpen by remember { mutableStateOf(false) }
    var notificationsOpen by remember { mutableStateOf(false) }
    var notificationDetailOpen by remember { mutableStateOf(false) }
    var privacyOpen by remember { mutableStateOf(false) }
    val context = LocalContext.current
    var widgetInstalled by remember(context) { mutableStateOf(WidgetScheduler.hasWidgets(context)) }
    val appSettings = remember(context) { AppSettings(context) }
    val themeMode by appSettings.themeMode.collectAsState(initial = AppThemeMode.DEFAULT)
    val scope = rememberCoroutineScope()
    // Mistakes remains available from Practice; it is no longer a profile entry.
    val openSettings = {
        widgetInstalled = WidgetScheduler.hasWidgets(context)
        settingsOpen = true
    }

    HskSceneSurface(modifier = modifier.fillMaxSize()) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(
                start = 16.dp,
                end = 16.dp,
                top = 6.dp,
                // The tab bar floats over the list; logout must stay reachable.
                bottom = 16.dp + LocalMainBottomInset.current,
            ),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item {
                ProfileToolbar(
                    onOpenSettings = openSettings,
                    hints = hints,
                    onDismissHint = onDismissHint,
                )
            }

            item {
                ProfileHero(
                    account = account,
                    state = state,
                    courseUser = courseUser,
                    onOpenAccount = {
                        identitiesOpen = true
                        onLoadIdentities()
                    },
                )
            }
            item { ProfileFriendsLink(onOpenFriends = onOpenFriends) }
            item { ProfileAccuracyRings(state.profile?.stats?.answerAccuracy) }
            item { StreakCalendar(progress = courseProgress, dailyXp = dailyXp) }
            if (subscriptionCheckoutAvailable &&
                !account.isPaid &&
                state.profile?.subscription?.isPaid != true &&
                state.trial?.active != true &&
                state.profile?.subscription?.status != "temporary_trial"
            ) {
                item { ProfileProCta(onClick = { onOpenSubscription(false) }) }
            }
            item {
                Achievements(
                    completedLessons = courseProgress?.completedLessons
                        ?: state.profile?.stats?.completedLessons ?: 0,
                    streak = courseProgress?.streak ?: state.profile?.stats?.streak ?: 0,
                )
            }

            item {
                ProfilePromoCarousel(
                    accountIsPaid = account.isPaid,
                    state = state,
                    checkoutAvailable = subscriptionCheckoutAvailable,
                    onOpenHsk30 = {
                        when {
                            courseTrack == "hsk30" -> onOpenCourse()
                            hsk30 != null -> profileHsk30BookOpen = true
                        }
                    },
                    onOpenSubscription = onOpenSubscription,
                    onStartTrial = onStartTrial,
                )
            }

            // Compiled only into the `direct` build; the Play flavour has a
            // no-op here, because Play updates the app itself.
            item { AppUpdateCard() }
            // `onOpenSupport` is the screen's "open this URL outside the app"
            // callback (MainActivity wires it to openExternal); the social row
            // needs exactly that and nothing support-specific.

            state.error?.let { error ->
                item { ErrorPill(text = stringResource(error.messageRes), onClick = onRefresh) }
            }
            if (state.isLoading) {
                item {
                    Box(Modifier.fillMaxWidth().padding(vertical = 8.dp), contentAlignment = Alignment.Center) {
                        HskBrandLoader(compact = true)
                    }
                }
            }
        }
    }

    if (settingsOpen) {
        ProfileSettingsScreen(
            account = account,
            state = state,
            settings = settings,
            themeMode = themeMode,
            dailyGoal = dailyGoal,
            notificationsEnabled = notificationsEnabled,
            courseTrack = courseTrack,
            showCourseVersion = hsk30Enabled || courseTrack == "hsk30",
            onDismiss = { settingsOpen = false },
            onOpenLanguage = { settingsOpen = false; onOpenLanguage() },
            onOpenCourseVersion = {
                settingsOpen = false
                profileHsk30BookOpen = true
            },
            onOpenAppearance = { settingsOpen = false; appearancePickerOpen = true },
            onOpenNotifications = { settingsOpen = false; notificationsOpen = true },
            widgetInstalled = widgetInstalled,
            onOpenWidget = {
                widgetInstalled = WidgetScheduler.hasWidgets(context)
                settingsOpen = false
                onOpenWidget()
            },
            onOpenGoal = { settingsOpen = false; onOpenGoal() },
            onOpenSupport = { url -> settingsOpen = false; onOpenSupport(url) },
            onOpenAccount = {
                settingsOpen = false
                identitiesOpen = true
                onLoadIdentities()
            },
            onOpenPrivacy = { settingsOpen = false; privacyOpen = true },
            onLogout = { settingsOpen = false; onLogout() },
            onUnlinkDevice = { settingsOpen = false; onUnlinkDevice() },
        )
    }

    // Profile and Settings share the native book-cover entry. The course-path
    // header retains its separate compact version/level selector.
    if (profileHsk30BookOpen && hsk30 != null) {
        ProfileHsk30BookEntryDialog(
            hsk30 = hsk30,
            currentTrack = courseTrack,
            onDismiss = { profileHsk30BookOpen = false },
            onUnlock = {
                profileHsk30BookOpen = false
                onUnlockHsk30()
            },
            onContinue = {
                profileHsk30BookOpen = false
                when {
                    !hsk30.access.featureEnabled -> Unit
                    !hsk30.access.allowed -> onUnlockHsk30()
                    hsk30.hasSavedHsk30 -> onSwitchCourseTrack("hsk30", null)
                    else -> profileHsk30LevelOpen = true
                }
            },
            onReturnHsk20 = {
                profileHsk30BookOpen = false
                onSwitchCourseTrack("hsk20", null)
            },
        )
    }
    if (profileHsk30LevelOpen && hsk30 != null) {
        Hsk30LevelChoiceDialog(
            levels = hsk30.liveLevels,
            onChoose = { level ->
                profileHsk30LevelOpen = false
                onSwitchCourseTrack("hsk30", level)
            },
            onDismiss = { profileHsk30LevelOpen = false },
        )
    }

    if (identitiesOpen) {
        IdentitiesSheet(
            state = identities,
            profile = state.profile,
            savingProfile = profileSaving,
            onSaveProfile = onSaveProfile,
            onConnect = onConnectIdentity,
            onDisconnect = onDisconnectIdentity,
            onBrowserUrlOpened = onIdentitiesBrowserOpened,
            onDismiss = { identitiesOpen = false },
        )
    }

    if (notificationsOpen) {
        NotificationsCategoriesSheet(
            enabled = notificationsEnabled,
            onOpenStudy = {
                notificationsOpen = false
                notificationDetailOpen = true
            },
            onDismiss = { notificationsOpen = false },
        )
    }

    if (notificationDetailOpen) {
        StudyReminderSettingsSheet(
            enabled = notificationsEnabled,
            onToggle = onToggleNotifications,
            onDismiss = { notificationDetailOpen = false },
        )
    }

    if (privacyOpen) {
        PrivacySecuritySheet(
            onTerms = {
                privacyOpen = false
                onOpenSupport(BuildConfig.API_ORIGIN.trimEnd('/') + "/terms")
            },
            onPrivacyPolicy = {
                privacyOpen = false
                onOpenSupport(BuildConfig.API_ORIGIN.trimEnd('/') + "/privacy")
            },
            onDeleteAccount = {
                privacyOpen = false
                onOpenSupport(BuildConfig.API_ORIGIN.trimEnd('/') + "/account-deletion")
            },
            onPermissions = {
                val intent = Intent(
                    Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.parse("package:${context.packageName}"),
                )
                runCatching { context.startActivity(intent) }
            },
            onDismiss = { privacyOpen = false },
        )
    }

    if (appearancePickerOpen) {
        AppearancePicker(
            current = themeMode,
            onPick = { mode ->
                scope.launch { appSettings.setThemeMode(mode) }
                appearancePickerOpen = false
            },
            onDismiss = { appearancePickerOpen = false },
        )
    }
}

@Composable
private fun ProfileToolbar(
    onOpenSettings: () -> Unit,
    hints: List<AndroidHintDto>,
    onDismissHint: (String) -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth().heightIn(min = 46.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = stringResource(R.string.nav_profile),
            fontSize = 22.sp,
            fontWeight = FontWeight.Bold,
            color = PompColors.Ink,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
        )
        SectionHint(hints = hints, section = "profile", onDismiss = onDismissHint)
        Box(
            modifier = Modifier.size(42.dp).clickable(onClick = onOpenSettings),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                Icons.Filled.Settings,
                contentDescription = stringResource(R.string.profile_mini_settings),
                tint = PompColors.InkSecondary,
                modifier = Modifier.size(23.dp),
            )
        }
    }
}

private fun profileExpiryText(raw: String): String {
    val instant = runCatching { Instant.parse(raw) }
        .recoverCatching { OffsetDateTime.parse(raw).toInstant() }
        .getOrNull()
        ?: return raw.take(10)
    val formatter = DateTimeFormatter.ofPattern("d MMM yyyy", Locale.getDefault())
    return formatter.withZone(ZoneId.systemDefault()).format(instant)
}

@Composable
private fun ProfileHero(
    account: LinkedAccount,
    state: ProfileUiState,
    courseUser: CourseUser?,
    onOpenAccount: () -> Unit,
) {
    val profile = state.profile
    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            val customAvatar = profileAvatarDrawable(profile?.user?.avatarKey.orEmpty())
            val photo = courseUser?.avatarUrl?.let { MediaUrl.resolve(it, BuildConfig.API_ORIGIN) }
            Surface(
                onClick = onOpenAccount,
                color = PompColors.Cinnabar,
                shape = RoundedCornerShape(18.dp),
                modifier = Modifier.size(60.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    when {
                        customAvatar != null -> Image(
                            painter = painterResource(customAvatar),
                            contentDescription = null,
                            modifier = Modifier.fillMaxSize().padding(3.dp),
                        )
                        photo != null -> AsyncImage(
                            model = photo,
                            contentDescription = null,
                            contentScale = ContentScale.Crop,
                            modifier = Modifier.fillMaxSize(),
                        )
                        else -> Text(
                            text = profile?.user?.avatar?.takeIf { it.isNotBlank() }
                                ?: account.displayName.take(2).uppercase().ifBlank { "HSK" },
                            style = MaterialTheme.typography.titleLarge,
                            color = PompColors.Paper,
                        )
                    }
                }
            }
            val nickname = profile?.user?.name?.takeIf { it.isNotBlank() }
                ?: account.displayName.takeIf { it.isNotBlank() }
                ?: profile?.user?.telegramUsername?.takeIf { it.isNotBlank() }
                ?: "HSK AI"
            Row(
                modifier = Modifier.padding(start = 12.dp).weight(1f),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text(
                    text = nickname,
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Bold,
                    color = PompColors.Ink,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f),
                )
                AccessPill(
                    isPaid = profile?.subscription?.isPaid == true || account.isPaid,
                    trialActive = state.trial?.active == true,
                )
            }
    }
}

private fun profileAvatarDrawable(key: String): Int? = when (key) {
    "panda_cheer" -> R.drawable.widget_panda_cheer
    "panda_streak" -> R.drawable.widget_panda_streak
    "panda_worried" -> R.drawable.widget_panda_worried
    else -> null
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AvatarNoteSheet(onDismiss: () -> Unit) {
    val sheetState = rememberModalBottomSheetState()
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState, containerColor = PompColors.PaperRaised) {
        Text(
            text = stringResource(R.string.profile_avatar_note),
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth().padding(horizontal = 24.dp, vertical = 20.dp),
        )
    }
}

@Composable
private fun DailyGoalCard(dailyXp: Int, dailyGoal: Int, onOpenGoal: () -> Unit) {
    val remaining = (dailyGoal - dailyXp).coerceAtLeast(0)
    val percent = if (dailyGoal > 0) ((dailyXp.toFloat() / dailyGoal) * 100).toInt().coerceIn(0, 100) else 0
    HskGlassSurface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        shadowElevation = 8.dp,
    ) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            GoalRing(dailyXp = dailyXp, dailyGoal = dailyGoal, onClick = onOpenGoal, size = 58.dp)
            Column(modifier = Modifier.weight(1f).padding(start = 14.dp)) {
                Text(stringResource(R.string.profile_goal_title), style = MaterialTheme.typography.titleMedium, color = PompColors.Ink)
                Text(stringResource(R.string.profile_goal_body, dailyXp, dailyGoal, remaining), style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
                Text(stringResource(R.string.profile_goal_percent, percent), style = MaterialTheme.typography.labelSmall, color = PompColors.InkSecondary)
            }
        }
    }
}

@Composable
private fun StatsGrid(state: ProfileUiState) {
    val stats = state.profile?.stats
    HskGlassSurface(
        modifier = Modifier.fillMaxWidth(),
        shape = PompShapes.Large,
        shadowElevation = 2.dp,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = PompSpacing.Small, vertical = PompSpacing.Large),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            StatMetric(stringResource(R.string.profile_xp), (stats?.xp ?: 0).toString(), Modifier.weight(1f))
            StatMetric(stringResource(R.string.profile_lessons), (stats?.completedLessons ?: 0).toString(), Modifier.weight(1f))
            StatMetric(stringResource(R.string.profile_mistakes), (stats?.mistakes ?: 0).toString(), Modifier.weight(1f))
        }
    }
}

@Composable
private fun StatMetric(label: String, value: String, modifier: Modifier = Modifier) {
    Column(modifier = modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, style = MaterialTheme.typography.headlineSmall, color = PompColors.Ink)
        Text(
            label,
            style = MaterialTheme.typography.bodySmall,
            color = PompColors.InkSecondary,
            maxLines = 1,
            textAlign = TextAlign.Center,
        )
    }
}

@Composable
private fun ProfileFriendsLink(onOpenFriends: () -> Unit) {
    Surface(
        modifier = Modifier.fillMaxWidth().heightIn(min = 44.dp),
        shape = RoundedCornerShape(12.dp),
        color = PompColors.PaperRaised.copy(alpha = 0.72f),
        border = BorderStroke(1.dp, PompColors.Divider),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().clickable(onClick = onOpenFriends)
                .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Filled.People, contentDescription = null, tint = PompColors.JadeInk, modifier = Modifier.size(19.dp))
            Spacer(Modifier.width(9.dp))
            Text(stringResource(R.string.profile_friends), fontSize = 13.sp, fontWeight = FontWeight.SemiBold,
                color = PompColors.Ink, modifier = Modifier.weight(1f))
            SettingsChevron()
        }
    }
}

@Composable
private fun ProfileQuickLinkRow(
    icon: ImageVector,
    title: String,
    subtitle: String?,
    iconTint: Color,
    onClick: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 60.dp)
            .clickable(onClick = onClick)
            .padding(horizontal = PompSpacing.Large, vertical = PompSpacing.Small),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(PompSpacing.Large),
    ) {
        Icon(icon, contentDescription = null, tint = iconTint, modifier = Modifier.size(22.dp))
        Column(Modifier.weight(1f)) {
            Text(title, color = PompColors.Ink, style = MaterialTheme.typography.bodyLarge)
            if (!subtitle.isNullOrBlank()) {
                Text(subtitle, color = PompColors.InkSecondary, style = MaterialTheme.typography.bodySmall)
            }
        }
        SettingsChevron()
    }
}

@Composable
// Not private: the update card is compiled per flavour and reaches for this
// so that it looks like every other row here rather than inventing a
// second visual language for one message.
internal fun ProfileActionCard(icon: ImageVector, iconBackground: Color, iconTint: Color, title: String, subtitle: String?, onClick: () -> Unit, modifier: Modifier = Modifier) {
    HskGlassSurface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        shadowElevation = 7.dp,
        onClick = onClick,
    ) {
        Row(modifier = Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(13.dp)) {
            Surface(color = iconBackground, shape = RoundedCornerShape(13.dp), modifier = Modifier.size(46.dp)) {
                Box(contentAlignment = Alignment.Center) { Icon(icon, contentDescription = null, tint = iconTint, modifier = Modifier.size(22.dp)) }
            }
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.Center) {
                Text(title, color = PompColors.Ink, fontSize = 15.sp, fontWeight = FontWeight.Medium)
                if (!subtitle.isNullOrBlank()) {
                    Spacer(Modifier.height(2.dp)); Text(subtitle, color = PompColors.InkSecondary, fontSize = 12.sp)
                }
            }
            Icon(Icons.Filled.ChevronRight, contentDescription = null, tint = PompColors.InkDisabled, modifier = Modifier.size(20.dp))
        }
    }
}

@Composable
private fun AccessPill(isPaid: Boolean, trialActive: Boolean = false, modifier: Modifier = Modifier) {
    Surface(
        color = if (isPaid || trialActive) Color(0xFF3C2B1C) else PompColors.PaperRaised,
        shape = RoundedCornerShape(999.dp),
        border = BorderStroke(1.dp, if (isPaid || trialActive) Color(0xFFB68D45) else PompColors.Divider),
        modifier = modifier,
    ) {
        Text(
            text = when {
                isPaid -> "✦ Pro"
                trialActive -> stringResource(R.string.profile_access_trial)
                else -> stringResource(R.string.synced_access_free)
            },
            style = MaterialTheme.typography.labelMedium,
            color = if (isPaid || trialActive) Color(0xFFFFD999) else PompColors.InkSecondary,
            maxLines = 1,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
        )
    }
}

@Composable
private fun LevelLeaguePill(level: String, league: String) {
    Surface(color = PompColors.CinnabarSoft, shape = RoundedCornerShape(999.dp)) {
        Text(if (league.isBlank()) level else "$level · $league", style = MaterialTheme.typography.labelLarge, color = PompColors.CinnabarDark, modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp))
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ProfileSettingsScreen(
    account: LinkedAccount,
    state: ProfileUiState,
    settings: ProfileSettingsState,
    themeMode: AppThemeMode,
    dailyGoal: Int,
    notificationsEnabled: Boolean,
    courseTrack: String,
    showCourseVersion: Boolean,
    onDismiss: () -> Unit,
    onOpenLanguage: () -> Unit,
    onOpenCourseVersion: () -> Unit,
    onOpenAppearance: () -> Unit,
    onOpenNotifications: () -> Unit,
    widgetInstalled: Boolean,
    onOpenWidget: () -> Unit,
    onOpenGoal: () -> Unit,
    onOpenSupport: (String) -> Unit,
    onOpenAccount: () -> Unit,
    onOpenPrivacy: () -> Unit,
    onLogout: () -> Unit,
    onUnlinkDevice: () -> Unit,
) {
    val supportUrl = state.profile?.supportUrl.orEmpty()
    var confirmUnlink by remember { mutableStateOf(false) }
    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(
            usePlatformDefaultWidth = false,
            decorFitsSystemWindows = false,
        ),
    ) {
        val view = LocalView.current
        DisposableEffect(view) {
            val window = (view.parent as? DialogWindowProvider)?.window
            window?.let { dialogWindow ->
                dialogWindow.statusBarColor = android.graphics.Color.TRANSPARENT
                dialogWindow.navigationBarColor = android.graphics.Color.TRANSPARENT
                WindowCompat.getInsetsController(dialogWindow, view).apply {
                    isAppearanceLightStatusBars = true
                    isAppearanceLightNavigationBars = true
                }
            }
            onDispose { }
        }
        Surface(modifier = Modifier.fillMaxSize(), color = PompColors.Paper) {
            Column(Modifier.fillMaxSize().statusBarsPadding()) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Surface(
                        color = PompColors.PaperRaised,
                        shape = CircleShape,
                        border = BorderStroke(1.dp, PompColors.Divider),
                        modifier = Modifier.size(48.dp).clickable(role = Role.Button, onClick = onDismiss),
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Icon(
                                Icons.AutoMirrored.Filled.ArrowBack,
                                contentDescription = stringResource(R.string.action_back),
                                tint = PompColors.Ink,
                                modifier = Modifier.size(22.dp),
                            )
                        }
                    }
                    Column(Modifier.weight(1f)) {
                        Text(
                            stringResource(R.string.profile_mini_settings),
                            color = PompColors.Ink,
                            fontSize = 21.sp,
                            fontWeight = FontWeight.SemiBold,
                        )
                        Text(
                            stringResource(R.string.profile_settings_intro),
                            color = PompColors.InkSecondary,
                            fontSize = 12.sp,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
                Box(Modifier.fillMaxWidth().height(1.dp).background(PompColors.Divider))
                LazyColumn(
                    modifier = Modifier.weight(1f).fillMaxWidth().navigationBarsPadding()
                        .testTag("profile-settings-scroll"),
                    contentPadding = PaddingValues(start = 18.dp, top = 18.dp, end = 18.dp, bottom = 28.dp),
                    verticalArrangement = Arrangement.spacedBy(20.dp),
                ) {
                    item {
                        SettingsCategory(stringResource(R.string.profile_settings_section_learning), Icons.Filled.TrackChanges) {
                            ProfileSettingsItem(
                                Icons.Filled.Language,
                                stringResource(R.string.profile_language),
                                account.language.backendCode.uppercase(),
                                !settings.isBusy,
                                onOpenLanguage,
                            )
                            if (showCourseVersion) {
                                ProfileSettingsDivider()
                                ProfileSettingsItem(
                                    Icons.Filled.TrackChanges,
                                    stringResource(R.string.profile_course_version),
                                    if (courseTrack == "hsk30") "HSK 3.0" else "HSK 2.0",
                                    true,
                                    onOpenCourseVersion,
                                )
                            }
                            ProfileSettingsDivider()
                            ProfileSettingsItem(
                                Icons.Filled.TrackChanges,
                                stringResource(R.string.profile_mini_daily_goal),
                                "$dailyGoal XP",
                                true,
                                onOpenGoal,
                            )
                        }
                    }
                    item {
                        SettingsCategory(stringResource(R.string.profile_settings_section_app), Icons.Filled.Settings) {
                            ProfileSettingsItem(
                                Icons.Filled.Settings,
                                stringResource(R.string.profile_appearance),
                                stringResource(themeMode.labelRes()),
                                true,
                                onOpenAppearance,
                            )
                            ProfileSettingsDivider()
                            ProfileSettingsItem(
                                Icons.Filled.Notifications,
                                stringResource(R.string.profile_notifications),
                                stringResource(
                                    if (notificationsEnabled) R.string.profile_notifications_status_on
                                    else R.string.profile_notifications_status_off,
                                ),
                                true,
                                onOpenNotifications,
                            )
                            ProfileSettingsDivider()
                            ProfileSettingsItem(
                                Icons.Filled.Widgets,
                                stringResource(R.string.profile_widgets),
                                stringResource(
                                    if (widgetInstalled) R.string.profile_widget_installed
                                    else R.string.profile_widget_not_installed,
                                ),
                                true,
                                onOpenWidget,
                            )
                        }
                    }
                    item {
                        SettingsCategory(stringResource(R.string.profile_settings_section_account), Icons.Filled.PersonOutline) {
                            ProfileSettingsItem(
                                Icons.Filled.PersonOutline,
                                stringResource(R.string.profile_account_title),
                                stringResource(R.string.profile_account_subtitle),
                                true,
                                onOpenAccount,
                            )
                            ProfileSettingsDivider()
                            ProfileSettingsItem(
                                Icons.Filled.Lock,
                                stringResource(R.string.profile_privacy_security),
                                null,
                                true,
                                onOpenPrivacy,
                            )
                            ProfileSettingsDivider()
                            ProfileSettingsItem(
                                Icons.AutoMirrored.Filled.HelpOutline,
                                stringResource(R.string.profile_help),
                                stringResource(
                                    if (supportUrl.isBlank()) R.string.profile_help_unavailable
                                    else R.string.profile_help_action,
                                ),
                                supportUrl.isNotBlank(),
                            ) { if (supportUrl.isNotBlank()) onOpenSupport(supportUrl) }
                        }
                    }
                    item {
                        settings.error?.let { error ->
                            ErrorPill(stringResource(error.messageRes))
                            Spacer(Modifier.height(12.dp))
                        }
                        Surface(
                            color = PompColors.PaperRaised,
                            shape = RoundedCornerShape(14.dp),
                            border = BorderStroke(1.dp, PompColors.Divider),
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 13.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                Text(stringResource(R.string.profile_app_version), color = PompColors.InkSecondary, fontSize = 13.sp)
                                Text(BuildConfig.VERSION_NAME, color = PompColors.Ink, fontSize = 13.sp, fontWeight = FontWeight.Medium)
                            }
                        }
                    }
                    item { SocialLinksRow(onOpen = onOpenSupport) }
                    item {
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            OutlinedButton(
                                onClick = onLogout,
                                modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp),
                                shape = RoundedCornerShape(15.dp),
                            ) {
                                Text(stringResource(R.string.profile_logout), color = PompColors.Ink)
                            }
                            OutlinedButton(
                                onClick = { confirmUnlink = true },
                                modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp),
                                shape = RoundedCornerShape(15.dp),
                                colors = ButtonDefaults.outlinedButtonColors(contentColor = PompColors.FlameInk),
                            ) {
                                Text(stringResource(R.string.profile_unlink_device), color = PompColors.FlameInk)
                            }
                        }
                    }
                }
            }
        }
    }
    if (confirmUnlink) {
        AlertDialog(
            onDismissRequest = { confirmUnlink = false },
            title = { Text(stringResource(R.string.profile_unlink_device)) },
            text = { Text(stringResource(R.string.profile_unlink_explain)) },
            confirmButton = {
                TextButton(onClick = { confirmUnlink = false; onUnlinkDevice() }) {
                    Text(stringResource(R.string.profile_unlink_device), color = PompColors.FlameInk)
                }
            },
            dismissButton = {
                TextButton(onClick = { confirmUnlink = false }) {
                    Text(stringResource(R.string.action_cancel), color = PompColors.InkSecondary)
                }
            },
        )
    }
}

@Composable
private fun SettingsCategory(
    title: String,
    icon: ImageVector,
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Icon(icon, contentDescription = null, tint = PompColors.CinnabarInk, modifier = Modifier.size(18.dp))
            Text(title, color = PompColors.Ink, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
        }
        Surface(
            color = PompColors.PaperRaised,
            shape = RoundedCornerShape(18.dp),
            border = BorderStroke(1.dp, PompColors.Divider),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(content = content)
        }
    }
}

@Composable
private fun ProfileSettingsItem(
    icon: ImageVector,
    label: String,
    summary: String?,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 68.dp)
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Surface(color = PompColors.CinnabarSoft, shape = RoundedCornerShape(12.dp), modifier = Modifier.size(38.dp)) {
            Box(contentAlignment = Alignment.Center) {
                Icon(icon, contentDescription = null, tint = PompColors.CinnabarInk, modifier = Modifier.size(19.dp))
            }
        }
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(
                label,
                color = PompColors.Ink,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            summary?.let {
                Text(
                    it,
                    color = PompColors.InkSecondary,
                    fontSize = 12.sp,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
        if (enabled) SettingsChevron()
    }
}

@Composable
private fun ProfileSettingsDivider() {
    Box(
        Modifier
            .fillMaxWidth()
            .padding(start = 64.dp, end = 14.dp)
            .height(1.dp)
            .background(PompColors.Divider),
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun NotificationsCategoriesSheet(
    enabled: Boolean,
    onOpenStudy: () -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState, containerColor = PompColors.Paper) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 18.dp).padding(bottom = 28.dp)) {
            Text(stringResource(R.string.profile_notifications), color = PompColors.Ink, fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(14.dp))
            Surface(
                color = PompColors.PaperRaised,
                shape = RoundedCornerShape(16.dp),
                border = BorderStroke(1.dp, PompColors.Divider),
                modifier = Modifier.fillMaxWidth(),
            ) {
                MiniSettingsRow(Icons.Filled.Notifications, stringResource(R.string.profile_notifications_category_study), true, onOpenStudy) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            stringResource(if (enabled) R.string.profile_notifications_status_on else R.string.profile_notifications_status_off),
                            color = PompColors.InkDisabled,
                            fontSize = 12.sp,
                        )
                        Spacer(Modifier.width(4.dp)); SettingsChevron()
                    }
                }
            }
            Text(
                stringResource(R.string.profile_notifications_category_study_desc),
                color = PompColors.InkSecondary,
                fontSize = 12.sp,
                modifier = Modifier.padding(horizontal = 8.dp, vertical = 10.dp),
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun StudyReminderSettingsSheet(
    enabled: Boolean,
    onToggle: (Boolean) -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState, containerColor = PompColors.Paper) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 18.dp).padding(bottom = 28.dp)) {
            Text(
                stringResource(R.string.profile_notifications_category_study),
                color = PompColors.Ink,
                fontSize = 20.sp,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                stringResource(R.string.profile_notifications_detail_intro),
                color = PompColors.InkSecondary,
                fontSize = 13.sp,
                modifier = Modifier.padding(top = 5.dp, bottom = 14.dp),
            )
            Surface(
                color = PompColors.PaperRaised,
                shape = RoundedCornerShape(16.dp),
                border = BorderStroke(1.dp, PompColors.Divider),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(14.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        stringResource(R.string.profile_notifications_category_study),
                        color = PompColors.Ink,
                        fontSize = 14.sp,
                        modifier = Modifier.weight(1f),
                    )
                    Switch(
                        checked = enabled,
                        onCheckedChange = onToggle,
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = Color.White,
                            checkedTrackColor = PompColors.Jade,
                            uncheckedThumbColor = Color.White,
                            uncheckedTrackColor = PompColors.InkDisabled,
                            uncheckedBorderColor = Color.Transparent,
                        ),
                    )
                }
            }
            if (enabled) {
                Column(Modifier.padding(horizontal = 8.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    NotificationBullet(stringResource(R.string.profile_notifications_goal))
                    NotificationBullet(stringResource(R.string.profile_notifications_streak))
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PrivacySecuritySheet(
    onTerms: () -> Unit,
    onPrivacyPolicy: () -> Unit,
    onDeleteAccount: () -> Unit,
    onPermissions: () -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState, containerColor = PompColors.Paper) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 18.dp).padding(bottom = 28.dp)) {
            Text(stringResource(R.string.profile_privacy_security), color = PompColors.Ink, fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(14.dp))
            Surface(
                color = PompColors.PaperRaised,
                shape = RoundedCornerShape(16.dp),
                border = BorderStroke(1.dp, PompColors.Divider),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column {
                    MiniSettingsRow(Icons.Filled.Lock, stringResource(R.string.profile_terms_of_use), true, onTerms) { SettingsChevron() }
                    SettingsDivider()
                    MiniSettingsRow(Icons.Filled.Lock, stringResource(R.string.profile_privacy_policy), true, onPrivacyPolicy) { SettingsChevron() }
                    SettingsDivider()
                    MiniSettingsRow(Icons.Filled.PersonOutline, stringResource(R.string.profile_delete_account), true, onDeleteAccount) { SettingsChevron() }
                    SettingsDivider()
                    MiniSettingsRow(Icons.Filled.Settings, stringResource(R.string.profile_app_permissions), true, onPermissions) { SettingsChevron() }
                }
            }
            Text(
                stringResource(R.string.profile_app_permissions_desc),
                color = PompColors.InkSecondary,
                fontSize = 12.sp,
                modifier = Modifier.padding(horizontal = 8.dp, vertical = 10.dp),
            )
            Text(
                stringResource(R.string.profile_security_note),
                color = PompColors.InkSecondary,
                fontSize = 12.sp,
                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
            )
        }
    }
}

/** HSK AI rasmiy sahifalari, Mini App profilidagi qator bilan bir xil. */
internal val SOCIAL_LINKS = listOf(
    Triple("Instagram", R.drawable.ic_brand_instagram, "https://www.instagram.com/hskai.app"),
    Triple("TikTok", R.drawable.ic_brand_tiktok, "https://www.tiktok.com/@hskai.app"),
    Triple("YouTube", R.drawable.ic_brand_youtube, "https://youtube.com/@hskai_app"),
)

/**
 * Links to the official HSK AI pages.
 *
 * The marks are drawn untinted, in the brands' own colours, the same way the
 * Mini App renders them: three identical grey glyphs in a row are read as one
 * button repeated, not as three destinations.
 *
 * Internal rather than private so the row can be tested on its own: inside the
 * profile's LazyColumn it is off-screen and never composed, so a test of the
 * whole screen could not reach it.
 */
@Composable
internal fun SocialLinksRow(onOpen: (String) -> Unit) {
    Column(modifier = Modifier.fillMaxWidth().padding(top = 8.dp)) {
        Text(
            stringResource(R.string.profile_social_title),
            color = PompColors.InkSecondary,
            fontSize = 13.sp,
            modifier = Modifier.padding(start = 2.dp, bottom = 8.dp),
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            SOCIAL_LINKS.forEach { (label, icon, url) ->
                Surface(
                    color = PompColors.PaperRaised,
                    shape = RoundedCornerShape(15.dp),
                    border = BorderStroke(1.dp, PompColors.Divider),
                    modifier = Modifier
                        .weight(1f)
                        .heightIn(min = 54.dp)
                        .clickable { onOpen(url) },
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Image(
                            painter = painterResource(icon),
                            contentDescription = label,
                            modifier = Modifier.size(26.dp),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun MiniSettingsRow(icon: ImageVector, label: String, enabled: Boolean, onClick: () -> Unit, trailing: @Composable () -> Unit) {
    Row(modifier = Modifier.fillMaxWidth().clickable(enabled = enabled, onClick = onClick).padding(14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Icon(icon, contentDescription = null, tint = if (enabled) PompColors.InkSecondary else PompColors.InkDisabled, modifier = Modifier.size(19.dp))
        Text(label, color = if (enabled) PompColors.Ink else PompColors.InkDisabled, fontSize = 14.sp, modifier = Modifier.weight(1f))
        trailing()
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AppearancePicker(current: AppThemeMode, onPick: (AppThemeMode) -> Unit, onDismiss: () -> Unit) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState, containerColor = PompColors.Paper) {
        Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 8.dp).padding(bottom = 20.dp)) {
            Text(stringResource(R.string.profile_theme_picker_title), color = PompColors.Ink, fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(12.dp))
            AppThemeMode.entries.forEach { mode ->
                val selected = mode == current
                Surface(
                    color = if (selected) PompColors.CinnabarSoft else PompColors.PaperRaised,
                    shape = RoundedCornerShape(14.dp),
                    border = BorderStroke(1.dp, if (selected) PompColors.Cinnabar else PompColors.Divider),
                    modifier = Modifier.fillMaxWidth().heightIn(min = 58.dp).padding(vertical = 4.dp).clickable { onPick(mode) },
                ) {
                    Row(modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(stringResource(mode.labelRes()), color = if (selected) PompColors.CinnabarDark else PompColors.Ink, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                            Spacer(Modifier.height(2.dp)); Text(stringResource(mode.descriptionRes()), color = PompColors.InkSecondary, fontSize = 12.sp)
                        }
                        if (selected) Text("✓", color = PompColors.Cinnabar, fontSize = 22.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable private fun NotificationBullet(text: String) { Text("• $text", color = PompColors.InkSecondary, fontSize = 12.sp, lineHeight = 17.sp) }
@Composable private fun SettingsChevron() { Icon(Icons.Filled.ChevronRight, contentDescription = null, tint = PompColors.InkDisabled, modifier = Modifier.size(17.dp)) }
@Composable private fun SettingsDivider() { Box(Modifier.fillMaxWidth().padding(start = 45.dp).height(1.dp).background(PompColors.Divider)) }

@Composable
private fun ErrorPill(text: String, onClick: (() -> Unit)? = null) {
    val modifier = if (onClick == null) Modifier.fillMaxWidth() else Modifier.fillMaxWidth().clickable(onClick = onClick)
    Surface(color = PompColors.FlameSoft, shape = RoundedCornerShape(12.dp), modifier = modifier) {
        Text(text, color = PompColors.FlameInk, fontSize = 13.sp, modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp))
    }
}

internal fun com.pomp.hskai.core.i18n.AppLanguage.labelRes(): Int = when (this) {
    com.pomp.hskai.core.i18n.AppLanguage.UZBEK -> R.string.language_uz
    com.pomp.hskai.core.i18n.AppLanguage.RUSSIAN -> R.string.language_ru
    com.pomp.hskai.core.i18n.AppLanguage.TAJIK -> R.string.language_tj
}

private fun AppThemeMode.labelRes(): Int = when (this) {
    AppThemeMode.LIGHT -> R.string.profile_theme_light
    AppThemeMode.DARK -> R.string.profile_theme_dark
    AppThemeMode.SYSTEM -> R.string.profile_theme_system
}

private fun AppThemeMode.descriptionRes(): Int = when (this) {
    AppThemeMode.LIGHT -> R.string.profile_theme_light_subtitle
    AppThemeMode.DARK -> R.string.profile_theme_dark_subtitle
    AppThemeMode.SYSTEM -> R.string.profile_theme_system_subtitle
}
