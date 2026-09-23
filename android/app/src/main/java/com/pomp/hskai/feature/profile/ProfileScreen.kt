package com.pomp.hskai.feature.profile

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
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
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
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
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
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.pomp.hskai.BuildConfig
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.AuthProvider
import com.pomp.hskai.core.auth.LinkedAccount
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskBrandLoader
import com.pomp.hskai.core.design.components.HskGlassSurface
import com.pomp.hskai.core.navigation.LocalMainBottomInset
import com.pomp.hskai.feature.update.AppUpdateCard
import com.pomp.hskai.core.navigation.AppDestination
import com.pomp.hskai.core.navigation.DeepLinkRouter
import com.pomp.hskai.core.navigation.PracticeTool
import com.pomp.hskai.core.network.MediaUrl
import com.pomp.hskai.core.settings.AppSettings
import com.pomp.hskai.core.settings.AppThemeMode
import com.pomp.hskai.data.api.AndroidHintDto
import com.pomp.hskai.domain.model.CourseProgress
import com.pomp.hskai.domain.model.CourseUser
import com.pomp.hskai.feature.assistant.AssistantScreen
import com.pomp.hskai.feature.assistant.profileAssistantContext
import com.pomp.hskai.feature.assistant.AssistantModalBottomSheet as ModalBottomSheet
import com.pomp.hskai.feature.course.GoalRing
import com.pomp.hskai.feature.hint.SectionHint
import kotlinx.coroutines.launch

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
    modifier: Modifier = Modifier,
    identities: IdentitiesUiState = IdentitiesUiState(),
    onLoadIdentities: () -> Unit = {},
    onConnectIdentity: (AuthProvider) -> Unit = {},
    onDisconnectIdentity: (String) -> Unit = {},
    onIdentitiesBrowserOpened: () -> Unit = {},
    onSaveProfile: (String, String) -> Unit = { _, _ -> },
    profileSaving: Boolean = false,
) {
    AssistantScreen(profileAssistantContext(state), bottomBar = true)
    var settingsOpen by remember { mutableStateOf(false) }
    var appearancePickerOpen by remember { mutableStateOf(false) }
    var identitiesOpen by remember { mutableStateOf(false) }
    var notificationsOpen by remember { mutableStateOf(false) }
    var notificationDetailOpen by remember { mutableStateOf(false) }
    var privacyOpen by remember { mutableStateOf(false) }
    val context = LocalContext.current
    val appSettings = remember(context) { AppSettings(context) }
    val themeMode by appSettings.themeMode.collectAsState(initial = AppThemeMode.DEFAULT)
    val scope = rememberCoroutineScope()
    val openMistakes = onOpenMistakes ?: {
        val uri = Uri.parse(DeepLinkRouter.uriFor(AppDestination.Practice(PracticeTool.MISTAKES)))
        runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, uri).setPackage(context.packageName)) }
        Unit
    }

    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(
                start = 16.dp,
                end = 16.dp,
                top = 16.dp,
                // The tab bar floats over the list; logout must stay reachable.
                bottom = 16.dp + LocalMainBottomInset.current,
            ),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item { ProfilePill() }

            if (hints.isNotEmpty()) {
                item {
                    SectionHint(hints = hints, section = "profile", onDismiss = onDismissHint)
                }
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
            item {
                DailyGoalCard(
                    dailyXp = dailyXp,
                    dailyGoal = dailyGoal,
                    streak = courseProgress?.streak ?: state.profile?.stats?.streak ?: 0,
                    onOpenGoal = onOpenGoal,
                )
            }
            item { StatsGrid(state) }
            item { StreakCalendar(progress = courseProgress, dailyXp = dailyXp) }
            item {
                Achievements(
                    completedLessons = courseProgress?.completedLessons
                        ?: state.profile?.stats?.completedLessons ?: 0,
                    streak = courseProgress?.streak ?: state.profile?.stats?.streak ?: 0,
                )
            }

            item {
                Text(
                    text = stringResource(R.string.profile_mini_group_title),
                    color = PompColors.InkSecondary,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                    modifier = Modifier.padding(start = 2.dp, top = 4.dp, bottom = 1.dp),
                )
            }
            item {
                ProfileActionCard(
                    icon = Icons.Filled.WarningAmber,
                    iconBackground = PompColors.FlameSoft,
                    iconTint = PompColors.Flame,
                    title = stringResource(R.string.practice_mistakes_title),
                    subtitle = stringResource(R.string.profile_mini_mistakes_subtitle),
                    onClick = openMistakes,
                )
            }
            item {
                ProfileActionCard(
                    icon = Icons.Filled.People,
                    iconBackground = PompColors.JadeSoft,
                    iconTint = PompColors.Jade,
                    title = stringResource(R.string.profile_friends),
                    subtitle = null,
                    onClick = onOpenFriends,
                )
            }

            // Compiled only into the `direct` build; the Play flavour has a
            // no-op here, because Play updates the app itself.
            item { AppUpdateCard() }
            item { SettingsEntryCard(onClick = { settingsOpen = true }) }
            // `onOpenSupport` is the screen's "open this URL outside the app"
            // callback (MainActivity wires it to openExternal); the social row
            // needs exactly that and nothing support-specific.
            item { SocialLinksRow(onOpen = onOpenSupport) }

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
        ProfileSettingsSheet(
            account = account,
            state = state,
            settings = settings,
            themeMode = themeMode,
            dailyGoal = dailyGoal,
            notificationsEnabled = notificationsEnabled,
            onDismiss = { settingsOpen = false },
            onOpenLanguage = { settingsOpen = false; onOpenLanguage() },
            onOpenAppearance = { settingsOpen = false; appearancePickerOpen = true },
            onOpenNotifications = { settingsOpen = false; notificationsOpen = true },
            onOpenWidget = { settingsOpen = false; onOpenWidget() },
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
private fun ProfilePill() {
    Surface(color = PompColors.Cinnabar, shape = RoundedCornerShape(20.dp)) {
        Row(
            modifier = Modifier.padding(horizontal = 13.dp, vertical = 7.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Icon(Icons.Filled.PersonOutline, contentDescription = null, tint = PompColors.Paper, modifier = Modifier.size(17.dp))
            Text(stringResource(R.string.nav_profile), color = PompColors.Paper, fontSize = 13.sp, fontWeight = FontWeight.Medium)
        }
    }
}

@Composable
private fun ProfileHero(
    account: LinkedAccount,
    state: ProfileUiState,
    courseUser: CourseUser?,
    onOpenAccount: () -> Unit,
) {
    val profile = state.profile
    HskGlassSurface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        shadowElevation = 10.dp,
    ) {
        Row(modifier = Modifier.padding(18.dp), verticalAlignment = Alignment.CenterVertically) {
            val customAvatar = profileAvatarDrawable(profile?.user?.avatarKey.orEmpty())
            val photo = courseUser?.avatarUrl?.let { MediaUrl.resolve(it, BuildConfig.API_ORIGIN) }
            Surface(
                onClick = onOpenAccount,
                color = PompColors.Cinnabar,
                shape = RoundedCornerShape(18.dp),
                modifier = Modifier.size(54.dp),
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
                            text = profile?.user?.avatar?.ifBlank { "HSK" }
                                ?: account.displayName.take(2).uppercase(),
                            style = MaterialTheme.typography.titleLarge,
                            color = PompColors.Paper,
                        )
                    }
                }
            }
            Column(modifier = Modifier.padding(start = 14.dp).weight(1f)) {
                Text(
                    text = profile?.user?.name?.ifBlank { account.displayName } ?: account.displayName,
                    style = MaterialTheme.typography.headlineSmall,
                    color = PompColors.Ink,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Spacer(Modifier.height(4.dp))
                LevelLeaguePill(
                    level = (profile?.user?.level ?: account.level).uppercase(),
                    league = profile?.stats?.league.orEmpty(),
                )
            }
            AccessPill(
                isPaid = profile?.subscription?.isPaid == true || account.isPaid,
                modifier = Modifier.align(Alignment.Top),
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
private fun DailyGoalCard(dailyXp: Int, dailyGoal: Int, streak: Int, onOpenGoal: () -> Unit) {
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
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(streak.toString(), style = MaterialTheme.typography.headlineSmall, color = PompColors.Cinnabar, fontWeight = FontWeight.Bold)
                Text(stringResource(R.string.profile_streak), style = MaterialTheme.typography.labelSmall, color = PompColors.InkSecondary)
            }
        }
    }
}

@Composable
private fun StatsGrid(state: ProfileUiState) {
    val stats = state.profile?.stats
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            StatCard(stringResource(R.string.profile_xp), (stats?.xp ?: 0).toString(), Modifier.weight(1f))
            StatCard(stringResource(R.string.profile_streak), (stats?.streak ?: 0).toString(), Modifier.weight(1f))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            StatCard(stringResource(R.string.profile_lessons), (stats?.completedLessons ?: 0).toString(), Modifier.weight(1f))
            StatCard(stringResource(R.string.profile_mistakes), (stats?.mistakes ?: 0).toString(), Modifier.weight(1f))
        }
    }
}

@Composable
private fun StatCard(label: String, value: String, modifier: Modifier = Modifier) {
    HskGlassSurface(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        shadowElevation = 6.dp,
    ) {
        Column(Modifier.padding(14.dp)) {
            Text(value, style = MaterialTheme.typography.headlineSmall, color = PompColors.Ink)
            Text(label, style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
        }
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
private fun AccessPill(isPaid: Boolean, modifier: Modifier = Modifier) {
    Surface(
        color = if (isPaid) PompColors.JadeSoft else PompColors.PaperRaised,
        shape = RoundedCornerShape(999.dp),
        border = BorderStroke(1.dp, if (isPaid) PompColors.Jade else PompColors.Divider),
        modifier = modifier,
    ) {
        Text(
            text = stringResource(
                if (isPaid) R.string.synced_access_paid else R.string.synced_access_free,
            ),
            style = MaterialTheme.typography.labelMedium,
            color = if (isPaid) PompColors.Jade else PompColors.InkSecondary,
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

@Composable
private fun SettingsEntryCard(onClick: () -> Unit) {
    ProfileActionCard(
        icon = Icons.Filled.Settings,
        iconBackground = PompColors.CinnabarSoft,
        iconTint = PompColors.Cinnabar,
        title = stringResource(R.string.profile_mini_settings),
        subtitle = null,
        onClick = onClick,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ProfileSettingsSheet(
    account: LinkedAccount,
    state: ProfileUiState,
    settings: ProfileSettingsState,
    themeMode: AppThemeMode,
    dailyGoal: Int,
    notificationsEnabled: Boolean,
    onDismiss: () -> Unit,
    onOpenLanguage: () -> Unit,
    onOpenAppearance: () -> Unit,
    onOpenNotifications: () -> Unit,
    onOpenWidget: () -> Unit,
    onOpenGoal: () -> Unit,
    onOpenSupport: (String) -> Unit,
    onOpenAccount: () -> Unit,
    onOpenPrivacy: () -> Unit,
    onLogout: () -> Unit,
    onUnlinkDevice: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val supportUrl = state.profile?.supportUrl.orEmpty()
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState, containerColor = PompColors.Paper) {
        Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(bottom = 28.dp)) {
            Text(
                stringResource(R.string.profile_mini_settings),
                color = PompColors.Ink,
                fontSize = 20.sp,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.padding(start = 2.dp, bottom = 12.dp),
            )
            Surface(
                color = PompColors.PaperRaised,
                shape = RoundedCornerShape(16.dp),
                border = BorderStroke(1.dp, PompColors.Divider),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column {
                    MiniSettingsRow(Icons.Filled.Language, stringResource(R.string.profile_language), !settings.isBusy, onOpenLanguage) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(account.language.backendCode.uppercase(), color = PompColors.InkDisabled, fontSize = 13.sp)
                            Spacer(Modifier.width(4.dp)); SettingsChevron()
                        }
                    }
                    SettingsDivider()
                    MiniSettingsRow(Icons.Filled.Settings, stringResource(R.string.profile_appearance), true, onOpenAppearance) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(stringResource(themeMode.labelRes()), color = PompColors.InkDisabled, fontSize = 13.sp)
                            Spacer(Modifier.width(4.dp)); SettingsChevron()
                        }
                    }
                    SettingsDivider()
                    MiniSettingsRow(Icons.Filled.Notifications, stringResource(R.string.profile_notifications), true, onOpenNotifications) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                stringResource(
                                    if (notificationsEnabled) R.string.profile_notifications_status_on
                                    else R.string.profile_notifications_status_off
                                ),
                                color = PompColors.InkDisabled,
                                fontSize = 13.sp,
                            )
                            Spacer(Modifier.width(4.dp)); SettingsChevron()
                        }
                    }
                    SettingsDivider()
                    MiniSettingsRow(Icons.Filled.Settings, stringResource(R.string.widget_name), true, onOpenWidget) { SettingsChevron() }
                    SettingsDivider()
                    MiniSettingsRow(Icons.Filled.TrackChanges, stringResource(R.string.profile_mini_daily_goal), true, onOpenGoal) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("$dailyGoal XP", color = PompColors.InkDisabled, fontSize = 13.sp)
                            Spacer(Modifier.width(4.dp)); SettingsChevron()
                        }
                    }
                    SettingsDivider()
                    MiniSettingsRow(Icons.Filled.PersonOutline, stringResource(R.string.profile_account_title), true, onOpenAccount) { SettingsChevron() }
                    SettingsDivider()
                    MiniSettingsRow(Icons.Filled.Lock, stringResource(R.string.profile_privacy_security), true, onOpenPrivacy) { SettingsChevron() }
                    SettingsDivider()
                    MiniSettingsRow(Icons.Filled.HelpOutline, stringResource(R.string.profile_help), supportUrl.isNotBlank(), { onOpenSupport(supportUrl) }) {
                        if (supportUrl.isBlank()) Text(stringResource(R.string.profile_help_unavailable), color = PompColors.InkDisabled, fontSize = 12.sp)
                        else SettingsChevron()
                    }
                    SettingsDivider()
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(14.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        Icon(Icons.Filled.Settings, contentDescription = null, tint = PompColors.InkSecondary, modifier = Modifier.size(19.dp))
                        Text(stringResource(R.string.profile_app_version), color = PompColors.Ink, fontSize = 14.sp, modifier = Modifier.weight(1f))
                        Text(BuildConfig.VERSION_NAME, color = PompColors.InkDisabled, fontSize = 13.sp)
                    }
                    settings.error?.let { error ->
                        Box(Modifier.padding(horizontal = 14.dp, vertical = 8.dp)) { ErrorPill(stringResource(error.messageRes)) }
                    }
                }
            }
            Spacer(Modifier.height(20.dp))
            OutlinedButton(onClick = onLogout, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp), shape = RoundedCornerShape(14.dp)) {
                Text(stringResource(R.string.profile_logout), color = PompColors.Ink)
            }
            Spacer(Modifier.height(10.dp))
            OutlinedButton(onClick = onUnlinkDevice, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp), shape = RoundedCornerShape(14.dp)) {
                Text(stringResource(R.string.profile_unlink_device), color = PompColors.Flame)
            }
        }
    }
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
    Triple("TikTok", R.drawable.ic_brand_tiktok, "https://www.tiktok.com/@hsk.ai"),
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
        Text(text, color = PompColors.Flame, fontSize = 13.sp, modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp))
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
