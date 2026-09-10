package com.pomp.hskai.feature.profile

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.BorderStroke
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
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.People
import androidx.compose.material.icons.filled.PersonOutline
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.TrackChanges
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.pomp.hskai.BuildConfig
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.LinkedAccount
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.navigation.AppDestination
import com.pomp.hskai.core.navigation.DeepLinkRouter
import com.pomp.hskai.core.navigation.PracticeTool
import com.pomp.hskai.core.network.MediaUrl
import com.pomp.hskai.core.settings.AppSettings
import com.pomp.hskai.core.settings.AppThemeMode
import com.pomp.hskai.data.api.AndroidHintDto
import com.pomp.hskai.domain.model.CourseProgress
import com.pomp.hskai.domain.model.CourseUser
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
    onOpenSupport: (String) -> Unit,
    onRefresh: () -> Unit,
    onStartTrial: () -> Unit,
    onLogout: () -> Unit,
    onUnlinkDevice: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var settingsOpen by remember { mutableStateOf(false) }
    var appearancePickerOpen by remember { mutableStateOf(false) }
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
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item { ProfilePill() }

            if (hints.isNotEmpty()) {
                item {
                    SectionHint(hints = hints, section = "profile", onDismiss = onDismissHint)
                }
            }

            item { ProfileHero(account = account, state = state, courseUser = courseUser) }
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
                    iconBackground = PompColors.CinnabarSoft,
                    iconTint = PompColors.Cinnabar,
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

            item { TrialCard(state = state, onStart = onStartTrial) }
            item { SubscriptionCard(state) }
            item { ReferralCard(state) }
            item { SettingsEntryCard(onClick = { settingsOpen = true }) }

            state.error?.let { error ->
                item { ErrorPill(text = stringResource(error.messageRes), onClick = onRefresh) }
            }
            if (state.isLoading) {
                item {
                    Box(Modifier.fillMaxWidth().padding(vertical = 8.dp), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator(modifier = Modifier.size(24.dp), color = PompColors.Cinnabar, strokeWidth = 2.dp)
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
            onToggleNotifications = onToggleNotifications,
            onOpenGoal = { settingsOpen = false; onOpenGoal() },
            onOpenSupport = { url -> settingsOpen = false; onOpenSupport(url) },
            onLogout = { settingsOpen = false; onLogout() },
            onUnlinkDevice = { settingsOpen = false; onUnlinkDevice() },
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
            Icon(Icons.Filled.PersonOutline, contentDescription = null, tint = Color.White, modifier = Modifier.size(17.dp))
            Text(stringResource(R.string.nav_profile), color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.Medium)
        }
    }
}

@Composable
private fun ProfileHero(account: LinkedAccount, state: ProfileUiState, courseUser: CourseUser?) {
    val profile = state.profile
    var avatarNoteOpen by remember { mutableStateOf(false) }
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(modifier = Modifier.padding(18.dp), verticalAlignment = Alignment.CenterVertically) {
            val photo = courseUser?.avatarUrl?.let { MediaUrl.resolve(it, BuildConfig.API_ORIGIN) }
            Surface(
                onClick = { avatarNoteOpen = true },
                color = PompColors.Cinnabar,
                shape = RoundedCornerShape(18.dp),
                modifier = Modifier.size(54.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    if (photo != null) {
                        AsyncImage(model = photo, contentDescription = null, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
                    } else {
                        Text(
                            text = profile?.user?.avatar?.ifBlank { "HSK" } ?: account.displayName.take(2).uppercase(),
                            style = MaterialTheme.typography.titleLarge,
                            color = PompColors.Paper,
                        )
                    }
                }
            }
            Column(Modifier.padding(start = 14.dp)) {
                Text(
                    text = profile?.user?.name?.ifBlank { account.displayName } ?: account.displayName,
                    style = MaterialTheme.typography.headlineSmall,
                    color = PompColors.Ink,
                )
                Spacer(Modifier.height(4.dp))
                LevelLeaguePill(
                    level = (profile?.user?.level ?: account.level).uppercase(),
                    league = profile?.stats?.league.orEmpty(),
                )
                Text(
                    text = stringResource(
                        if (profile?.subscription?.isPaid == true || account.isPaid) R.string.synced_access_paid
                        else R.string.synced_access_free,
                    ),
                    style = MaterialTheme.typography.bodyMedium,
                    color = if (profile?.subscription?.isPaid == true || account.isPaid) PompColors.Jade else PompColors.InkSecondary,
                )
            }
        }
    }
    if (avatarNoteOpen) AvatarNoteSheet { avatarNoteOpen = false }
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
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
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
    Surface(color = PompColors.PaperRaised, shape = RoundedCornerShape(16.dp), border = BorderStroke(1.dp, PompColors.Divider), modifier = modifier) {
        Column(Modifier.padding(14.dp)) {
            Text(value, style = MaterialTheme.typography.headlineSmall, color = PompColors.Ink)
            Text(label, style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
        }
    }
}

@Composable
private fun ProfileActionCard(icon: ImageVector, iconBackground: Color, iconTint: Color, title: String, subtitle: String?, onClick: () -> Unit) {
    Surface(onClick = onClick, color = PompColors.PaperRaised, shape = RoundedCornerShape(16.dp), border = BorderStroke(1.dp, PompColors.Divider), modifier = Modifier.fillMaxWidth()) {
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
private fun TrialCard(state: ProfileUiState, onStart: () -> Unit) {
    val trial = state.trial ?: return
    if (!trial.eligible && !trial.active) return
    Surface(color = PompColors.GoldSoft, shape = RoundedCornerShape(18.dp), border = BorderStroke(1.dp, PompColors.Gold), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp)) {
            Text(stringResource(if (trial.active) R.string.profile_trial_active_title else R.string.profile_trial_title), style = MaterialTheme.typography.titleMedium, color = PompColors.Ink)
            Text(stringResource(if (trial.active) R.string.profile_trial_active_body else R.string.profile_trial_body), style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
            if (state.trialError.isNotBlank()) Text(stringResource(R.string.profile_trial_failed), style = MaterialTheme.typography.bodySmall, color = PompColors.Cinnabar, modifier = Modifier.padding(top = 6.dp))
            if (trial.eligible) Button(onClick = onStart, enabled = !state.trialStarting, modifier = Modifier.fillMaxWidth().padding(top = 12.dp)) { Text(stringResource(R.string.profile_trial_cta)) }
        }
    }
}

@Composable
private fun SubscriptionCard(state: ProfileUiState) {
    val active = state.subscription?.access?.isPaid == true
    Surface(color = if (active) PompColors.JadeSoft else PompColors.GoldSoft, shape = RoundedCornerShape(18.dp), border = BorderStroke(1.dp, if (active) PompColors.Jade else PompColors.Gold), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp)) {
            Text(stringResource(R.string.profile_subscription_title), style = MaterialTheme.typography.titleMedium, color = PompColors.Ink)
            Text(stringResource(if (active) R.string.profile_subscription_active else R.string.profile_subscription_play_blocked), style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
        }
    }
}

@Composable
private fun ReferralCard(state: ProfileUiState) {
    val referral = state.referral
    Surface(color = PompColors.PaperRaised, shape = RoundedCornerShape(18.dp), border = BorderStroke(1.dp, PompColors.Divider), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp)) {
            Text(stringResource(R.string.profile_referral_title), style = MaterialTheme.typography.titleMedium, color = PompColors.Ink)
            Text(stringResource(R.string.profile_referral_progress, referral?.activated ?: 0, referral?.trialRequired ?: 0), style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
            val link = referral?.link.orEmpty()
            if (link.isNotBlank()) {
                Spacer(Modifier.height(8.dp))
                Text(link, style = MaterialTheme.typography.bodySmall, color = PompColors.CinnabarDark, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(12.dp))
                val context = LocalContext.current
                val copied = stringResource(R.string.profile_referral_copied)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Surface(onClick = {
                        context.getSystemService(ClipboardManager::class.java)?.setPrimaryClip(ClipData.newPlainText("invite", link))
                        Toast.makeText(context, copied, Toast.LENGTH_SHORT).show()
                    }, shape = RoundedCornerShape(12.dp), color = PompColors.Cinnabar) {
                        Text(stringResource(R.string.profile_referral_copy), style = MaterialTheme.typography.labelLarge, color = PompColors.Paper, modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp))
                    }
                    Surface(onClick = {
                        val send = Intent(Intent.ACTION_SEND).apply { type = "text/plain"; putExtra(Intent.EXTRA_TEXT, link) }
                        runCatching { context.startActivity(Intent.createChooser(send, null)) }
                    }, shape = RoundedCornerShape(12.dp), color = PompColors.Paper, border = BorderStroke(1.dp, PompColors.Divider)) {
                        Text(stringResource(R.string.profile_referral_share), style = MaterialTheme.typography.labelLarge, color = PompColors.InkSecondary, modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp))
                    }
                }
            }
        }
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
    onToggleNotifications: (Boolean) -> Unit,
    onOpenGoal: () -> Unit,
    onOpenSupport: (String) -> Unit,
    onLogout: () -> Unit,
    onUnlinkDevice: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val supportUrl = state.profile?.supportUrl.orEmpty()
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState, containerColor = PompColors.Paper) {
        Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(bottom = 28.dp)) {
            Text(stringResource(R.string.profile_mini_settings), color = PompColors.Ink, fontSize = 20.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(start = 2.dp, bottom = 12.dp))
            Surface(color = PompColors.PaperRaised, shape = RoundedCornerShape(16.dp), border = BorderStroke(1.dp, PompColors.Divider), modifier = Modifier.fillMaxWidth()) {
                Column {
                    MiniSettingsRow(Icons.Filled.Language, stringResource(R.string.profile_language), !settings.isBusy, onOpenLanguage) {
                        Row(verticalAlignment = Alignment.CenterVertically) { Text(account.language.backendCode.uppercase(), color = PompColors.InkDisabled, fontSize = 13.sp); Spacer(Modifier.width(4.dp)); SettingsChevron() }
                    }
                    SettingsDivider()
                    MiniSettingsRow(Icons.Filled.Settings, stringResource(R.string.profile_appearance), true, onOpenAppearance) {
                        Row(verticalAlignment = Alignment.CenterVertically) { Text(stringResource(themeMode.labelRes()), color = PompColors.InkDisabled, fontSize = 13.sp); Spacer(Modifier.width(4.dp)); SettingsChevron() }
                    }
                    SettingsDivider()
                    MiniSettingsRow(Icons.Filled.Notifications, stringResource(R.string.profile_notifications), !settings.isBusy, { onToggleNotifications(!notificationsEnabled) }) {
                        Switch(checked = notificationsEnabled, onCheckedChange = onToggleNotifications, enabled = !settings.isBusy, colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = PompColors.Jade, uncheckedThumbColor = Color.White, uncheckedTrackColor = PompColors.InkDisabled, uncheckedBorderColor = Color.Transparent))
                    }
                    if (notificationsEnabled) NotificationExplanation()
                    SettingsDivider()
                    MiniSettingsRow(Icons.Filled.TrackChanges, stringResource(R.string.profile_mini_daily_goal), true, onOpenGoal) {
                        Row(verticalAlignment = Alignment.CenterVertically) { Text("$dailyGoal XP", color = PompColors.InkDisabled, fontSize = 13.sp); Spacer(Modifier.width(4.dp)); SettingsChevron() }
                    }
                    SettingsDivider()
                    MiniSettingsRow(Icons.Filled.HelpOutline, stringResource(R.string.profile_help), supportUrl.isNotBlank(), { onOpenSupport(supportUrl) }) {
                        if (supportUrl.isBlank()) Text(stringResource(R.string.profile_help_unavailable), color = PompColors.InkDisabled, fontSize = 12.sp) else SettingsChevron()
                    }
                    settings.error?.let { error -> Box(Modifier.padding(horizontal = 14.dp, vertical = 8.dp)) { ErrorPill(stringResource(error.messageRes)) } }
                }
            }
            Spacer(Modifier.height(20.dp))
            OutlinedButton(onClick = onLogout, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp), shape = RoundedCornerShape(14.dp)) { Text(stringResource(R.string.profile_logout), color = PompColors.Ink) }
            Spacer(Modifier.height(10.dp))
            OutlinedButton(onClick = onUnlinkDevice, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp), shape = RoundedCornerShape(14.dp)) { Text(stringResource(R.string.profile_unlink_device), color = PompColors.CinnabarDark) }
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

@Composable
private fun NotificationExplanation() {
    Column(modifier = Modifier.padding(start = 45.dp, end = 14.dp, bottom = 12.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Text(stringResource(R.string.profile_mini_notify_head), color = PompColors.Ink, fontSize = 12.sp, lineHeight = 17.sp, fontWeight = FontWeight.Medium)
        NotificationBullet(stringResource(R.string.profile_mini_notify_rank))
        NotificationBullet(stringResource(R.string.profile_mini_notify_lesson))
        NotificationBullet(stringResource(R.string.profile_mini_notify_streak))
    }
}

@Composable private fun NotificationBullet(text: String) { Text("• $text", color = PompColors.InkSecondary, fontSize = 12.sp, lineHeight = 17.sp) }
@Composable private fun SettingsChevron() { Icon(Icons.Filled.ChevronRight, contentDescription = null, tint = PompColors.InkDisabled, modifier = Modifier.size(17.dp)) }
@Composable private fun SettingsDivider() { Box(Modifier.fillMaxWidth().padding(start = 45.dp).height(1.dp).background(PompColors.Divider)) }

@Composable
private fun ErrorPill(text: String, onClick: (() -> Unit)? = null) {
    val modifier = if (onClick == null) Modifier.fillMaxWidth() else Modifier.fillMaxWidth().clickable(onClick = onClick)
    Surface(color = PompColors.CinnabarSoft, shape = RoundedCornerShape(12.dp), modifier = modifier) {
        Text(text, color = PompColors.CinnabarDark, fontSize = 13.sp, modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp))
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
