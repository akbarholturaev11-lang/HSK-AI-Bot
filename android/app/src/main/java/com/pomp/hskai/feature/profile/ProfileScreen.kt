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
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.LinkedAccount
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.navigation.AppDestination
import com.pomp.hskai.core.navigation.DeepLinkRouter
import com.pomp.hskai.core.navigation.PracticeTool
import com.pomp.hskai.data.api.AndroidHintDto
import com.pomp.hskai.domain.model.CourseProgress
import com.pomp.hskai.domain.model.CourseUser
import com.pomp.hskai.feature.hint.SectionHint

/**
 * Android Profile mirrors the Mini App's profile hierarchy and measurements.
 * Learning actions stay visible; preferences are moved behind one Settings row.
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
    val context = LocalContext.current
    val openMistakes = onOpenMistakes ?: {
        val uri = Uri.parse(
            DeepLinkRouter.uriFor(
                AppDestination.Practice(PracticeTool.MISTAKES),
            ),
        )
        runCatching {
            context.startActivity(
                Intent(Intent.ACTION_VIEW, uri).setPackage(context.packageName),
            )
        }
    }

    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 16.dp),
        ) {
            item { ProfilePill() }

            if (hints.isNotEmpty()) {
                item {
                    Spacer(Modifier.height(10.dp))
                    SectionHint(
                        hints = hints,
                        section = "profile",
                        onDismiss = onDismissHint,
                    )
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
                Spacer(Modifier.height(18.dp))
                SettingsEntryCard(onClick = { settingsOpen = true })
            }

            state.error?.let { error ->
                item {
                    Spacer(Modifier.height(11.dp))
                    ErrorPill(
                        text = stringResource(error.messageRes),
                        onClick = onRefresh,
                    )
                }
            }

            if (state.isLoading) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 12.dp),
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
            dailyGoal = dailyGoal,
            notificationsEnabled = notificationsEnabled,
            onDismiss = { settingsOpen = false },
            onOpenLanguage = {
                settingsOpen = false
                onOpenLanguage()
            },
            onToggleNotifications = onToggleNotifications,
            onOpenGoal = {
                settingsOpen = false
                onOpenGoal()
            },
            onOpenSupport = { url ->
                settingsOpen = false
                onOpenSupport(url)
            },
            onLogout = {
                settingsOpen = false
                onLogout()
            },
            onUnlinkDevice = {
                settingsOpen = false
                onUnlinkDevice()
            },
        )
    }
}

@Composable
private fun ProfilePill() {
    Surface(
        color = PompColors.Cinnabar,
        shape = RoundedCornerShape(20.dp),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 13.dp, vertical = 7.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Icon(
                imageVector = Icons.Filled.PersonOutline,
                contentDescription = null,
                tint = Color.White,
                modifier = Modifier.size(17.dp),
            )
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
            Surface(
                color = iconBackground,
                shape = RoundedCornerShape(13.dp),
                modifier = Modifier.size(46.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = icon,
                        contentDescription = null,
                        tint = iconTint,
                        modifier = Modifier.size(22.dp),
                    )
                }
            }

            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.Center,
            ) {
                Text(
                    text = title,
                    color = PompColors.Ink,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Medium,
                )
                if (!subtitle.isNullOrBlank()) {
                    Spacer(Modifier.height(2.dp))
                    Text(
                        text = subtitle,
                        color = PompColors.InkSecondary,
                        fontSize = 12.sp,
                    )
                }
            }

            Icon(
                imageVector = Icons.Filled.ChevronRight,
                contentDescription = null,
                tint = PompColors.InkDisabled,
                modifier = Modifier.size(20.dp),
            )
        }
    }
}

@Composable
private fun SettingsEntryCard(onClick: () -> Unit) {
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
            Surface(
                color = PompColors.CinnabarSoft,
                shape = RoundedCornerShape(13.dp),
                modifier = Modifier.size(46.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = Icons.Filled.Settings,
                        contentDescription = null,
                        tint = PompColors.Cinnabar,
                        modifier = Modifier.size(22.dp),
                    )
                }
            }
            Text(
                text = stringResource(R.string.profile_mini_settings),
                color = PompColors.Ink,
                fontSize = 15.sp,
                fontWeight = FontWeight.Medium,
                modifier = Modifier.weight(1f),
            )
            Icon(
                imageVector = Icons.Filled.ChevronRight,
                contentDescription = null,
                tint = PompColors.InkDisabled,
                modifier = Modifier.size(20.dp),
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ProfileSettingsSheet(
    account: LinkedAccount,
    state: ProfileUiState,
    settings: ProfileSettingsState,
    dailyGoal: Int,
    notificationsEnabled: Boolean,
    onDismiss: () -> Unit,
    onOpenLanguage: () -> Unit,
    onToggleNotifications: (Boolean) -> Unit,
    onOpenGoal: () -> Unit,
    onOpenSupport: (String) -> Unit,
    onLogout: () -> Unit,
    onUnlinkDevice: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val supportUrl = state.profile?.supportUrl.orEmpty()

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = PompColors.Paper,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
                .padding(bottom = 28.dp),
        ) {
            Text(
                text = stringResource(R.string.profile_mini_settings),
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
                    MiniSettingsRow(
                        icon = Icons.Filled.Language,
                        label = stringResource(R.string.profile_language),
                        enabled = !settings.isBusy,
                        onClick = onOpenLanguage,
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = account.language.backendCode.uppercase(),
                                color = PompColors.InkDisabled,
                                fontSize = 13.sp,
                            )
                            Spacer(Modifier.width(4.dp))
                            SettingsChevron()
                        }
                    }

                    SettingsDivider()

                    MiniSettingsRow(
                        icon = Icons.Filled.Notifications,
                        label = stringResource(R.string.profile_notifications),
                        enabled = !settings.isBusy,
                        onClick = { onToggleNotifications(!notificationsEnabled) },
                    ) {
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

                    if (notificationsEnabled) {
                        NotificationExplanation()
                    }

                    SettingsDivider()

                    MiniSettingsRow(
                        icon = Icons.Filled.TrackChanges,
                        label = stringResource(R.string.profile_mini_daily_goal),
                        enabled = true,
                        onClick = onOpenGoal,
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = "$dailyGoal XP",
                                color = PompColors.InkDisabled,
                                fontSize = 13.sp,
                            )
                            Spacer(Modifier.width(4.dp))
                            SettingsChevron()
                        }
                    }

                    SettingsDivider()

                    MiniSettingsRow(
                        icon = Icons.Filled.HelpOutline,
                        label = stringResource(R.string.profile_help),
                        enabled = supportUrl.isNotBlank(),
                        onClick = { onOpenSupport(supportUrl) },
                    ) {
                        if (supportUrl.isBlank()) {
                            Text(
                                text = stringResource(R.string.profile_help_unavailable),
                                color = PompColors.InkDisabled,
                                fontSize = 12.sp,
                            )
                        } else {
                            SettingsChevron()
                        }
                    }

                    settings.error?.let { error ->
                        Box(Modifier.padding(horizontal = 14.dp, vertical = 8.dp)) {
                            ErrorPill(text = stringResource(error.messageRes))
                        }
                    }
                }
            }

            // Android account controls remain available, but no longer clutter
            // the Mini App-like main profile screen.
            Spacer(Modifier.height(20.dp))
            OutlinedButton(
                onClick = onLogout,
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 48.dp),
                shape = RoundedCornerShape(14.dp),
            ) {
                Text(
                    text = stringResource(R.string.profile_logout),
                    color = PompColors.Ink,
                )
            }

            Spacer(Modifier.height(10.dp))
            OutlinedButton(
                onClick = onUnlinkDevice,
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 48.dp),
                shape = RoundedCornerShape(14.dp),
            ) {
                Text(
                    text = stringResource(R.string.profile_unlink_device),
                    color = PompColors.CinnabarDark,
                )
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
        modifier = Modifier
            .fillMaxWidth()
            .clickable(enabled = enabled, onClick = onClick)
            .padding(14.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = if (enabled) PompColors.InkSecondary else PompColors.InkDisabled,
            modifier = Modifier.size(19.dp),
        )
        Text(
            text = label,
            color = if (enabled) PompColors.Ink else PompColors.InkDisabled,
            fontSize = 14.sp,
            modifier = Modifier.weight(1f),
        )
        trailing()
    }
}

@Composable
private fun NotificationExplanation() {
    Column(
        modifier = Modifier.padding(
            start = 45.dp,
            end = 14.dp,
            top = 0.dp,
            bottom = 12.dp,
        ),
        verticalArrangement = Arrangement.spacedBy(3.dp),
    ) {
        Text(
            text = stringResource(R.string.profile_mini_notify_head),
            color = PompColors.Ink,
            fontSize = 12.sp,
            lineHeight = 17.sp,
            fontWeight = FontWeight.Medium,
        )
        NotificationBullet(stringResource(R.string.profile_mini_notify_rank))
        NotificationBullet(stringResource(R.string.profile_mini_notify_lesson))
        NotificationBullet(stringResource(R.string.profile_mini_notify_streak))
    }
}

@Composable
private fun NotificationBullet(text: String) {
    Text(
        text = "• $text",
        color = PompColors.InkSecondary,
        fontSize = 12.sp,
        lineHeight = 17.sp,
    )
}

@Composable
private fun SettingsChevron() {
    Icon(
        imageVector = Icons.Filled.ChevronRight,
        contentDescription = null,
        tint = PompColors.InkDisabled,
        modifier = Modifier.size(17.dp),
    )
}

@Composable
private fun SettingsDivider() {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(start = 45.dp)
            .height(1.dp)
            .background(PompColors.Divider),
    )
}

@Composable
private fun ErrorPill(
    text: String,
    onClick: (() -> Unit)? = null,
) {
    val modifier = if (onClick == null) {
        Modifier.fillMaxWidth()
    } else {
        Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
    }
    Surface(
        color = PompColors.CinnabarSoft,
        shape = RoundedCornerShape(12.dp),
        modifier = modifier,
    ) {
        Text(
            text = text,
            color = PompColors.CinnabarDark,
            fontSize = 13.sp,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
        )
    }
}

/** The name each supported language is shown under. */
internal fun com.pomp.hskai.core.i18n.AppLanguage.labelRes(): Int = when (this) {
    com.pomp.hskai.core.i18n.AppLanguage.UZBEK -> R.string.language_uz
    com.pomp.hskai.core.i18n.AppLanguage.RUSSIAN -> R.string.language_ru
    com.pomp.hskai.core.i18n.AppLanguage.TAJIK -> R.string.language_tj
}
