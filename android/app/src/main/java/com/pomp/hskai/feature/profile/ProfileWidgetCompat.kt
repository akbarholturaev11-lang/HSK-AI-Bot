package com.pomp.hskai.feature.profile

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.pomp.hskai.core.auth.LinkedAccount
import com.pomp.hskai.data.api.AndroidHintDto
import com.pomp.hskai.domain.model.CourseProgress
import com.pomp.hskai.domain.model.CourseUser

/**
 * Compatibility bridge for the Smart Widget integration while the richer
 * ProfileScreen remains the Android source of truth. The extra callback keeps
 * MainActivity source-compatible with the widget-enabled main branch without
 * replacing the richer profile hierarchy restored on codex/cloud-ai.
 */
@Suppress("UNUSED_PARAMETER")
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
    onStartTrial: () -> Unit,
    onLogout: () -> Unit,
    onUnlinkDevice: () -> Unit,
    modifier: Modifier = Modifier,
) {
    ProfileScreen(
        account = account,
        state = state,
        settings = settings,
        hints = hints,
        onDismissHint = onDismissHint,
        courseProgress = courseProgress,
        courseUser = courseUser,
        onOpenMistakes = onOpenMistakes,
        onOpenFriends = onOpenFriends,
        dailyXp = dailyXp,
        dailyGoal = dailyGoal,
        notificationsEnabled = notificationsEnabled,
        onOpenGoal = onOpenGoal,
        onOpenLanguage = onOpenLanguage,
        onToggleNotifications = onToggleNotifications,
        onOpenSupport = onOpenSupport,
        onRefresh = onRefresh,
        onStartTrial = onStartTrial,
        onLogout = onLogout,
        onUnlinkDevice = onUnlinkDevice,
        modifier = modifier,
    )
}
