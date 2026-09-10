package com.pomp.hskai.feature.profile

import android.content.Intent
import android.net.Uri
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
import androidx.compose.foundation.shape.CircleShape
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
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.LinkedAccount
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.navigation.AppDestination
import com.pomp.hskai.core.navigation.DeepLinkRouter
import com.pomp.hskai.core.navigation.PracticeTool
import com.pomp.hskai.core.settings.AppSettings
import com.pomp.hskai.core.settings.AppThemeMode
import com.pomp.hskai.data.api.AndroidHintDto
import com.pomp.hskai.domain.model.CourseProgress
import com.pomp.hskai.domain.model.CourseUser
import com.pomp.hskai.feature.hint.SectionHint
import kotlinx.coroutines.launch

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
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 24.dp),
        ) {
            item { ProfilePill() }

            item {
                Spacer(Modifier.height(14.dp))
                ProfileSummaryCard(
                    name = state.profile?.user?.name.orEmpty(),
                    level = state.profile?.user?.level.orEmpty(),
                    totalXp = state.profile?.stats?.xp ?: 0,
                    streak = state.profile?.stats?.streak ?: 0,
                    completedLessons = state.profile?.stats?.completedLessons ?: 0,
                    dailyXp = dailyXp,
                    dailyGoal = dailyGoal,
                )
            }

            if (hints.isNotEmpty()) {
                item {
                    Spacer(Modifier.height(10.dp))
                    SectionHint(hints = hints, section = "profile", onDismiss = onDismissHint)
                }
            }

            item {
                Text(
                    text = stringResource(R.string.profile_mini_group_title),
                    color = PompColors.InkSecondary,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                    modifier = Modifier.padding(start = 2.dp, top = 18.dp, bottom = 9.dp),
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
                Spacer(Modifier.height(11.dp))
                ProfileActionCard(
                    icon = Icons.Filled.People,
                    iconBackground = PompColors.JadeSoft,
                    iconTint = PompColors.Jade,
                    title = stringResource(R.string.profile_friends),
                    subtitle = null,
                    onClick = onOpenFriends,
                )
            }

            item {
                Spacer(Modifier.height(11.dp))
                SettingsEntryCard(onClick = { settingsOpen = true })
            }

            state.error?.let { error ->
                item {
                    Spacer(Modifier.height(11.dp))
                    ErrorPill(text = stringResource(error.messageRes), onClick = onRefresh)
                }
            }

            if (state.isLoading) {
                item {
                    Box(
                        modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(24.dp),
                            color = PompColors.Cinnabar,
                            strokeWidth = 2.dp,
                        )
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
            Icon(Icons.Filled.PersonOutline, null, tint = Color.White, modifier = Modifier.size(17.dp))
            Text(
                text = stringResource(R.string.nav_profile),
                color = Color.White,
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium,
            )
        }
    }
}

@Composable
private fun ProfileSummaryCard(
    name: String,
    level: String,
    totalXp: Int,
    streak: Int,
    completedLessons: Int,
    dailyXp: Int,
    dailyGoal: Int,
) {
    val safeGoal = dailyGoal.coerceAtLeast(1)
    val progress = (dailyXp.toFloat() / safeGoal.toFloat()).coerceIn(0f, 1f)
    val levelLabel = level.uppercase().replace("HSK", "HSK ").replace("  ", " ").trim()

    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(
                    modifier = Modifier.size(52.dp),
                    shape = CircleShape,
                    color = PompColors.CinnabarSoft,
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(
                            imageVector = Icons.Filled.PersonOutline,
                            contentDescription = null,
                            tint = PompColors.Cinnabar,
                            modifier = Modifier.size(25.dp),
                        )
                    }
                }
                Spacer(Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = name.ifBlank { stringResource(R.string.nav_profile) },
                        color = PompColors.Ink,
                        fontSize = 19.sp,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        text = "${stringResource(R.string.profile_mini_level)} · ${levelLabel.ifBlank { "HSK" }}",
                        color = PompColors.InkSecondary,
                        fontSize = 12.sp,
                    )
                }
            }

            Spacer(Modifier.height(15.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = stringResource(R.string.profile_mini_today_xp, dailyXp, dailyGoal),
                    color = PompColors.InkSecondary,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Medium,
                    modifier = Modifier.weight(1f),
                )
                Text(text = levelLabel, color = PompColors.InkSecondary, fontSize = 12.sp)
            }
            Spacer(Modifier.height(7.dp))
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier.fillMaxWidth().height(7.dp),
                color = PompColors.Gold,
                trackColor = PompColors.Divider,
            )

            Spacer(Modifier.height(16.dp))
            Row(modifier = Modifier.fillMaxWidth()) {
                ProfileMetric(value = streak.toString(), label = stringResource(R.string.profile_mini_streak), modifier = Modifier.weight(1f))
                ProfileMetric(value = totalXp.toString(), label = stringResource(R.string.profile_mini_total_xp), modifier = Modifier.weight(1f))
                ProfileMetric(value = completedLessons.toString(), label = stringResource(R.string.profile_mini_completed_lessons), modifier = Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun ProfileMetric(value: String, label: String, modifier: Modifier = Modifier) {
    Column(modifier = modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Text(text = value, color = PompColors.Ink, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
        Spacer(Modifier.height(2.dp))
        Text(text = label, color = PompColors.InkSecondary, fontSize = 10.sp, maxLines = 2)
    }
}

@Composable
private fun ProfileActionCard(
    icon: ImageVector,
    iconBackground: Color,
    iconTint: Color,
    title: String,
    subtitle: String?,
    onClick: () -> Unit,
) {
    Surface(
        onClick = onClick,
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(13.dp),
        ) {
            Surface(color = iconBackground, shape = RoundedCornerShape(13.dp), modifier = Modifier.size(46.dp)) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(icon, null, tint = iconTint, modifier = Modifier.size(22.dp))
                }
            }
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.Center) {
                Text(text = title, color = PompColors.Ink, fontSize = 15.sp, fontWeight = FontWeight.Medium)
                if (!subtitle.isNullOrBlank()) {
                    Spacer(Modifier.height(2.dp))
                    Text(text = subtitle, color = PompColors.InkSecondary, fontSize = 12.sp)
                }
            }
            Icon(Icons.Filled.ChevronRight, null, tint = PompColors.InkDisabled, modifier = Modifier.size(20.dp))
        }
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
        LazyColumn(
            modifier = Modifier.fillMaxWidth(),
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, bottom = 28.dp),
        ) {
            item {
                Text(
                    text = stringResource(R.string.profile_mini_settings),
                    color = PompColors.Ink,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.padding(start = 2.dp, bottom = 12.dp),
                )
            }
            item {
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
                        MiniSettingsRow(Icons.Filled.Notifications, stringResource(R.string.profile_notifications), !settings.isBusy, { onToggleNotifications(!notificationsEnabled) }) {
                            Switch(
                                checked = notificationsEnabled,
                                onCheckedChange = onToggleNotifications,
                                enabled = !settings.isBusy,
                                colors = SwitchDefaults.colors(
                                    checkedThumbColor = Color.White,
                                    checkedTrackColor = PompColors.Jade,
                                    uncheckedThumbColor = Color.White,
                                    uncheckedTrackColor = PompColors.InkDisabled,
                                    uncheckedBorderColor = Color.Transparent,
                                ),
                            )
                        }
                        SettingsDivider()
                        MiniSettingsRow(Icons.Filled.TrackChanges, stringResource(R.string.profile_mini_daily_goal), true, onOpenGoal) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text("$dailyGoal XP", color = PompColors.InkDisabled, fontSize = 13.sp)
                                Spacer(Modifier.width(4.dp)); SettingsChevron()
                            }
                        }
                        SettingsDivider()
                        MiniSettingsRow(Icons.Filled.HelpOutline, stringResource(R.string.profile_help), supportUrl.isNotBlank(), { onOpenSupport(supportUrl) }) {
                            if (supportUrl.isBlank()) Text(stringResource(R.string.profile_help_unavailable), color = PompColors.InkDisabled, fontSize = 12.sp) else SettingsChevron()
                        }
                    }
                }
            }
            settings.error?.let { error ->
                item { Spacer(Modifier.height(10.dp)); ErrorPill(text = stringResource(error.messageRes)) }
            }
            item {
                Spacer(Modifier.height(20.dp))
                OutlinedButton(onClick = onLogout, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp), shape = RoundedCornerShape(14.dp)) {
                    Text(stringResource(R.string.profile_logout), color = PompColors.Ink)
                }
                Spacer(Modifier.height(10.dp))
                OutlinedButton(onClick = onUnlinkDevice, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp), shape = RoundedCornerShape(14.dp)) {
                    Text(stringResource(R.string.profile_unlink_device), color = PompColors.CinnabarDark)
                }
            }
        }
    }
}

@Composable
private fun MiniSettingsRow(
    icon: ImageVector,
    label: String,
    enabled: Boolean,
    onClick: () -> Unit,
    trailing: @Composable () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth().clickable(enabled = enabled, onClick = onClick).padding(14.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Icon(icon, null, tint = if (enabled) PompColors.InkSecondary else PompColors.InkDisabled, modifier = Modifier.size(19.dp))
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
                    Row(modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(stringResource(mode.labelRes()), color = if (selected) PompColors.CinnabarDark else PompColors.Ink, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                            Text(stringResource(mode.descriptionRes()), color = PompColors.InkSecondary, fontSize = 12.sp)
                        }
                        if (selected) Text("✓", color = PompColors.Cinnabar, fontSize = 22.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}

@Composable
private fun SettingsChevron() {
    Icon(Icons.Filled.ChevronRight, null, tint = PompColors.InkDisabled, modifier = Modifier.size(17.dp))
}

@Composable
private fun SettingsDivider() {
    Box(modifier = Modifier.fillMaxWidth().padding(start = 45.dp).height(1.dp).background(PompColors.Divider))
}

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
