package com.pomp.hskai.feature.profile

import androidx.compose.foundation.BorderStroke
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.LinkedAccount
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.feature.course.GoalRing

@Composable
fun ProfileScreen(
    account: LinkedAccount,
    state: ProfileUiState,
    dailyXp: Int,
    dailyGoal: Int,
    onOpenGoal: () -> Unit,
    onRefresh: () -> Unit,
    onLogout: () -> Unit,
    onUnlinkDevice: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(horizontal = 20.dp, vertical = 24.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item {
                ProfileHero(account, state)
                state.error?.let {
                    Spacer(Modifier.height(10.dp))
                    ErrorPill(stringResource(it.messageRes))
                }
                if (state.isLoading) {
                    Spacer(Modifier.height(10.dp))
                    CircularProgressIndicator(color = PompColors.Cinnabar)
                }
            }
            item {
                DailyGoalCard(
                    dailyXp = dailyXp,
                    dailyGoal = dailyGoal,
                    streak = state.profile?.stats?.streak ?: 0,
                    onOpenGoal = onOpenGoal,
                )
            }
            item { StatsGrid(state) }
            item { SubscriptionCard(state) }
            item { ReferralCard(state) }
            item {
                OutlinedButton(
                    onClick = onRefresh,
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 48.dp),
                    shape = RoundedCornerShape(14.dp),
                ) {
                    Text(stringResource(R.string.profile_refresh))
                }
            }
            item {
                SessionActions(
                    onLogout = onLogout,
                    onUnlinkDevice = onUnlinkDevice,
                )
            }
        }
    }
}

@Composable
private fun ProfileHero(account: LinkedAccount, state: ProfileUiState) {
    val profile = state.profile
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(18.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Surface(
                color = PompColors.Cinnabar,
                shape = RoundedCornerShape(18.dp),
            ) {
                Text(
                    text = profile?.user?.avatar?.ifBlank { "HSK" }
                        ?: account.displayName.take(2).uppercase(),
                    style = MaterialTheme.typography.titleLarge,
                    color = PompColors.Paper,
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                )
            }
            Column(Modifier.padding(start = 14.dp)) {
                Text(
                    text = profile?.user?.name?.ifBlank { account.displayName }
                        ?: account.displayName,
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
                        if (profile?.subscription?.isPaid == true || account.isPaid) {
                            R.string.synced_access_paid
                        } else {
                            R.string.synced_access_free
                        }
                    ),
                    style = MaterialTheme.typography.bodyMedium,
                    color = if (profile?.subscription?.isPaid == true || account.isPaid) {
                        PompColors.Jade
                    } else {
                        PompColors.InkSecondary
                    },
                )
            }
        }
    }
}

@Composable
private fun StatsGrid(state: ProfileUiState) {
    val stats = state.profile?.stats
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            StatCard(
                label = stringResource(R.string.profile_xp),
                value = (stats?.xp ?: 0).toString(),
                modifier = Modifier.weight(1f),
            )
            StatCard(
                label = stringResource(R.string.profile_streak),
                value = (stats?.streak ?: 0).toString(),
                modifier = Modifier.weight(1f),
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            StatCard(
                label = stringResource(R.string.profile_lessons),
                value = (stats?.completedLessons ?: 0).toString(),
                modifier = Modifier.weight(1f),
            )
            StatCard(
                label = stringResource(R.string.profile_mistakes),
                value = (stats?.mistakes ?: 0).toString(),
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun StatCard(label: String, value: String, modifier: Modifier = Modifier) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = modifier,
    ) {
        Column(Modifier.padding(14.dp)) {
            Text(
                text = value,
                style = MaterialTheme.typography.headlineSmall,
                color = PompColors.Ink,
            )
            Text(
                text = label,
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.InkSecondary,
            )
        }
    }
}

@Composable
private fun SubscriptionCard(state: ProfileUiState) {
    val subscription = state.subscription
    val active = subscription?.access?.isPaid == true
    Surface(
        color = if (active) PompColors.JadeSoft else PompColors.GoldSoft,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, if (active) PompColors.Jade else PompColors.Gold),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(16.dp)) {
            Text(
                text = stringResource(R.string.profile_subscription_title),
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.Ink,
            )
            Text(
                text = if (active) {
                    stringResource(R.string.profile_subscription_active)
                } else {
                    stringResource(R.string.profile_subscription_play_blocked)
                },
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.InkSecondary,
            )
        }
    }
}

@Composable
private fun ReferralCard(state: ProfileUiState) {
    val referral = state.referral
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(16.dp)) {
            Text(
                text = stringResource(R.string.profile_referral_title),
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.Ink,
            )
            Text(
                text = stringResource(
                    R.string.profile_referral_progress,
                    referral?.activated ?: 0,
                    referral?.trialRequired ?: 0,
                ),
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.InkSecondary,
            )
            if (!referral?.link.isNullOrBlank()) {
                Spacer(Modifier.height(8.dp))
                Text(
                    text = referral?.link.orEmpty(),
                    style = MaterialTheme.typography.bodySmall,
                    color = PompColors.CinnabarDark,
                    fontWeight = FontWeight.SemiBold,
                )
            }
        }
    }
}

@Composable
private fun SessionActions(
    onLogout: () -> Unit,
    onUnlinkDevice: () -> Unit,
) {
    Column {
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
        Text(
            text = stringResource(R.string.profile_unlink_explain),
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.InkSecondary,
        )
        Spacer(Modifier.height(8.dp))
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

/**
 * Today's XP against the learner's personal target, mirroring the Mini App's
 * "Kunlik maqsad" card. Tapping it opens the target picker.
 */
@Composable
private fun DailyGoalCard(
    dailyXp: Int,
    dailyGoal: Int,
    streak: Int,
    onOpenGoal: () -> Unit,
) {
    val remaining = (dailyGoal - dailyXp).coerceAtLeast(0)
    val percent = if (dailyGoal > 0) {
        ((dailyXp.toFloat() / dailyGoal) * 100).toInt().coerceIn(0, 100)
    } else {
        0
    }
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(contentAlignment = Alignment.Center) {
                GoalRing(
                    dailyXp = dailyXp,
                    dailyGoal = dailyGoal,
                    onClick = onOpenGoal,
                    size = 58.dp,
                )
            }
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(start = 14.dp),
            ) {
                Text(
                    text = stringResource(R.string.profile_goal_title),
                    style = MaterialTheme.typography.titleMedium,
                    color = PompColors.Ink,
                )
                Text(
                    text = stringResource(
                        R.string.profile_goal_body,
                        dailyXp,
                        dailyGoal,
                        remaining,
                    ),
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                )
                Text(
                    text = stringResource(R.string.profile_goal_percent, percent),
                    style = MaterialTheme.typography.labelSmall,
                    color = PompColors.InkSecondary,
                )
            }
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = streak.toString(),
                    style = MaterialTheme.typography.headlineSmall,
                    color = PompColors.Cinnabar,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = stringResource(R.string.profile_streak),
                    style = MaterialTheme.typography.labelSmall,
                    color = PompColors.InkSecondary,
                )
            }
        }
    }
}

@Composable
private fun LevelLeaguePill(level: String, league: String) {
    Surface(color = PompColors.CinnabarSoft, shape = RoundedCornerShape(999.dp)) {
        Text(
            text = if (league.isBlank()) level else "$level · $league",
            style = MaterialTheme.typography.labelLarge,
            color = PompColors.CinnabarDark,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
        )
    }
}

@Composable
private fun ErrorPill(text: String) {
    Surface(
        color = PompColors.CinnabarSoft,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.CinnabarDark,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
        )
    }
}
