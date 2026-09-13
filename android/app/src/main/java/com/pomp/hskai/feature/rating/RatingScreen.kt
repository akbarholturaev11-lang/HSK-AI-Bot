package com.pomp.hskai.feature.rating

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Message
import androidx.compose.material.icons.filled.ArrowUpward
import androidx.compose.material.icons.filled.Group
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.PersonAdd
import androidx.compose.material.icons.filled.WorkspacePremium
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.data.api.AndroidHintDto
import com.pomp.hskai.feature.hint.SectionHint
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.data.api.RatingEntryDto
import com.pomp.hskai.data.api.ChallengeDto
import com.pomp.hskai.data.api.ReferralItemDto

/**
 * Weekly league and invited friends, laid out like the Mini App's Reyting tab.
 *
 * The four ladder steps are the server's four leagues rather than a fixed
 * decoration, so the highlighted step is the learner's real standing.
 */
@Composable
fun RatingScreen(
    state: RatingUiState,
    hints: List<AndroidHintDto> = emptyList(),
    onDismissHint: (String) -> Unit = {},
    onSelectTab: (RatingTab) -> Unit,
    onOpenChallenges: () -> Unit,
    onOpenUser: (RatingEntryDto) -> Unit,
    onInviteFriends: (String) -> Unit,
    onChallenge: (String) -> Unit,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val rating = state.rating
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(horizontal = 20.dp, vertical = 20.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    SectionPill(
                        icon = Icons.Filled.WorkspacePremium,
                        text = stringResource(R.string.nav_rating),
                    )
                    Spacer(Modifier.width(8.dp))
                    SectionHint(
                        hints = hints,
                        section = "rating",
                        onDismiss = onDismissHint,
                    )
                    Spacer(Modifier.weight(1f))
                    ChallengeBell(
                        pendingCount = state.pendingChallenges.size,
                        onClick = onOpenChallenges,
                    )
                }
            }
            item {
                TabSwitch(selected = state.tab, onSelect = onSelectTab)
            }

            if (state.challengeDelivery != null || state.challengeError != null) {
                item {
                    ChallengeFeedbackBanner(
                        delivery = state.challengeDelivery,
                        error = state.challengeError,
                    )
                }
            }

            if (state.tab == RatingTab.LEAGUE) {
                item {
                    LeagueCard(
                        league = rating?.league.orEmpty(),
                        memberCount = rating?.leagueSize ?: 0,
                        resetSeconds = rating?.weeklyResetSeconds ?: 0,
                    )
                }
                item { LeagueLadder(rating?.league.orEmpty()) }
            }

            if (state.isLoading) {
                item {
                    Box(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 24.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        CircularProgressIndicator(color = PompColors.Cinnabar)
                    }
                }
            }

            when (state.tab) {
                RatingTab.LEAGUE -> {
                    state.error?.let { error ->
                        item {
                            ErrorBlock(
                                text = stringResource(error.messageRes),
                                onRetry = onRetry,
                            )
                        }
                    }
                    val rows = rating?.leaderboard.orEmpty()
                    if (rows.size >= PROMOTION_ZONE) {
                        item { PromotionZone() }
                    }
                    items(rows, key = { "league-${it.rank}-${it.name}" }) { row ->
                        LeagueRow(
                            row = row,
                            onOpen = { onOpenUser(row) },
                            canChallenge = row.challengeRef.isNotBlank() &&
                                !row.isCurrentUser &&
                                !state.isChallengeBusy,
                            onChallenge = { onChallenge(row.challengeRef) },
                        )
                    }
                    if (rows.isEmpty() && !state.isLoading && state.error == null) {
                        item { EmptyBlock(stringResource(R.string.rating_empty)) }
                    }
                }

                RatingTab.FRIENDS -> {
                    val referral = state.referral
                    if (!state.isLoading || referral != null || state.referralError != null) {
                        item {
                            FriendInviteCard(
                                link = referral?.link.orEmpty(),
                                onInvite = onInviteFriends,
                            )
                        }
                        item {
                            FriendStats(
                                invited = referral?.invited ?: 0,
                                activated = referral?.activated ?: 0,
                                required = referral?.trialRequired ?: 0,
                            )
                        }
                    }
                    val friends = state.referral?.items.orEmpty()
                    state.referralError?.let { error ->
                        item {
                            ErrorBlock(
                                text = stringResource(error.messageRes),
                                onRetry = onRetry,
                            )
                        }
                    }
                    itemsIndexed(
                        items = friends,
                        key = { index, friend -> "friend-${friend.rank}-$index-${friend.name}" },
                    ) { index, friend ->
                        FriendRow(
                            friend = friend,
                            rank = friend.rank.takeIf { it > 0 } ?: index + 1,
                            onOpen = { onOpenUser(friend.asRatingEntry(index + 1)) },
                        )
                    }
                    if (friends.isEmpty() && !state.isLoading && state.referralError == null) {
                        item { EmptyBlock(stringResource(R.string.rating_friends_empty)) }
                    }
                }
            }
        }
    }
}

@Composable
private fun ChallengeBell(pendingCount: Int, onClick: () -> Unit) {
    Box {
        Surface(
            onClick = onClick,
            shape = CircleShape,
            color = PompColors.PaperRaised,
            border = BorderStroke(1.dp, PompColors.Divider),
            modifier = Modifier.size(44.dp),
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = Icons.Filled.Notifications,
                    contentDescription = stringResource(R.string.rating_challenges_bell),
                    tint = PompColors.CinnabarDark,
                    modifier = Modifier.size(21.dp),
                )
            }
        }
        if (pendingCount > 0) {
            Surface(
                color = PompColors.Cinnabar,
                shape = CircleShape,
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .size(19.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(
                        text = pendingCount.coerceAtMost(9).toString(),
                        style = MaterialTheme.typography.labelSmall,
                        color = PompColors.Paper,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }
    }
}

@Composable
fun RatingChallengesScreen(
    state: RatingUiState,
    onRespond: (Int, Boolean) -> Unit,
    onStartChallenge: (ChallengeDto) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    BackHandler(onBack = onBack)
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding(),
            contentPadding = PaddingValues(horizontal = 20.dp, vertical = 14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            item {
                RatingScreenHeader(
                    title = stringResource(R.string.rating_challenges_title),
                    onBack = onBack,
                )
            }
            if (state.pendingChallenges.isNotEmpty()) {
                item { ChallengeGroupLabel(stringResource(R.string.challenge_pending_title)) }
                items(state.pendingChallenges, key = { "pending-${it.id}" }) { duel ->
                    PendingChallengeRow(
                        duel = duel,
                        busy = state.isChallengeBusy,
                        onRespond = onRespond,
                    )
                }
            }
            if (state.activeChallenges.isNotEmpty()) {
                item { ChallengeGroupLabel(stringResource(R.string.challenge_active_title)) }
                items(state.activeChallenges, key = { "active-${it.id}" }) { duel ->
                    ActiveChallengeRow(duel = duel, onStart = onStartChallenge)
                }
            }
            if (state.pendingChallenges.isEmpty() && state.activeChallenges.isEmpty()) {
                item { EmptyBlock(stringResource(R.string.rating_challenges_empty)) }
            }
        }
    }
}

@Composable
fun RatingUserScreen(
    user: RatingEntryDto,
    league: String,
    currentWeeklyXp: Int,
    isChallengeBusy: Boolean,
    challengeDelivery: ChallengeDelivery?,
    challengeError: ApiError?,
    onChallenge: (String) -> Unit,
    onMessage: (String) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    BackHandler(onBack = onBack)
    val name = user.name.ifBlank {
        user.username.ifBlank { stringResource(R.string.rating_unnamed) }
    }
    val level = ratingLevelLabel(user.courseLevel)
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding(),
            contentPadding = PaddingValues(horizontal = 20.dp, vertical = 14.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item { RatingScreenHeader(title = name, onBack = onBack) }
            item {
                Column(
                    modifier = Modifier.fillMaxWidth().padding(top = 10.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    ProfileAvatar(name = name, premium = user.isPaid)
                    Spacer(Modifier.height(12.dp))
                    Text(
                        text = name,
                        style = MaterialTheme.typography.headlineSmall,
                        color = PompColors.Ink,
                        textAlign = TextAlign.Center,
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        text = stringResource(R.string.rating_league_name, leagueGlyph(league)),
                        style = MaterialTheme.typography.bodyMedium,
                        color = PompColors.InkSecondary,
                    )
                    Spacer(Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        ProfileBadge(
                            text = level,
                            containerColor = PompColors.CinnabarSoft,
                            contentColor = PompColors.CinnabarDark,
                        )
                        ProfileBadge(
                            text = leagueGlyph(league),
                            containerColor = PompColors.GoldSoft,
                            contentColor = PompColors.Gold,
                        )
                        if (user.isPaid) {
                            ProfileBadge(
                                text = stringResource(R.string.rating_premium),
                                containerColor = PompColors.GoldSoft,
                                contentColor = PompColors.Gold,
                            )
                        }
                    }
                }
            }
            item {
                Surface(
                    color = PompColors.PaperRaised,
                    shape = RoundedCornerShape(18.dp),
                    border = BorderStroke(1.dp, PompColors.Divider),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Row(modifier = Modifier.padding(vertical = 16.dp)) {
                        ProfileMetric(
                            value = user.xp.toString(),
                            label = stringResource(R.string.profile_xp),
                            color = PompColors.CinnabarDark,
                        )
                        ProfileMetric(
                            value = "#${user.rank}",
                            label = stringResource(R.string.rating_rank),
                            color = PompColors.Gold,
                        )
                        ProfileMetric(
                            value = level,
                            label = stringResource(R.string.rating_level),
                            color = PompColors.Jade,
                        )
                    }
                }
            }
            if (!user.isCurrentUser) {
                item {
                    RivalryCard(
                        opponentName = name,
                        currentXp = currentWeeklyXp,
                        opponentXp = user.xp,
                    )
                }
                if (user.challengeRef.isNotBlank() || user.username.isNotBlank()) {
                    item {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(10.dp),
                        ) {
                            if (user.challengeRef.isNotBlank()) {
                                Surface(
                                    onClick = { onChallenge(user.challengeRef) },
                                    enabled = !isChallengeBusy && challengeDelivery == null,
                                    modifier = Modifier.weight(1f).heightIn(min = 52.dp),
                                    shape = RoundedCornerShape(14.dp),
                                    color = PompColors.PaperRaised,
                                    contentColor = PompColors.Ink,
                                    border = BorderStroke(1.dp, PompColors.Divider),
                                ) {
                                    Row(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .heightIn(min = 52.dp)
                                            .padding(horizontal = 16.dp),
                                        horizontalArrangement = Arrangement.Center,
                                        verticalAlignment = Alignment.CenterVertically,
                                    ) {
                                        if (isChallengeBusy) {
                                            CircularProgressIndicator(
                                                color = PompColors.Cinnabar,
                                                strokeWidth = 2.dp,
                                                modifier = Modifier.size(18.dp),
                                            )
                                            Spacer(Modifier.width(9.dp))
                                        }
                                        Text(
                                            text = stringResource(
                                                if (isChallengeBusy) {
                                                    R.string.challenge_sending
                                                } else {
                                                    R.string.challenge_invite_send
                                                }
                                            ),
                                            style = MaterialTheme.typography.labelLarge,
                                        )
                                    }
                                }
                            }
                            if (user.username.isNotBlank()) {
                                Surface(
                                    onClick = { onMessage(user.username) },
                                    modifier = Modifier.size(52.dp),
                                    shape = RoundedCornerShape(14.dp),
                                    color = PompColors.PaperRaised,
                                    contentColor = PompColors.Ink,
                                    border = BorderStroke(1.dp, PompColors.Divider),
                                ) {
                                    Box(contentAlignment = Alignment.Center) {
                                        Icon(
                                            imageVector = Icons.AutoMirrored.Filled.Message,
                                            contentDescription = stringResource(
                                                R.string.rating_message_user
                                            ),
                                            modifier = Modifier.size(20.dp),
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
                if (challengeDelivery != null || challengeError != null) {
                    item {
                        ChallengeFeedbackBanner(
                            delivery = challengeDelivery,
                            error = challengeError,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun RatingScreenHeader(title: String, onBack: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Surface(
            onClick = onBack,
            shape = CircleShape,
            color = PompColors.PaperRaised,
            border = BorderStroke(1.dp, PompColors.Divider),
            modifier = Modifier.size(44.dp),
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = stringResource(R.string.action_back),
                    tint = PompColors.Ink,
                )
            }
        }
        Spacer(Modifier.width(12.dp))
        Text(
            text = title,
            style = MaterialTheme.typography.titleMedium,
            color = PompColors.Ink,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
        )
        Spacer(Modifier.size(44.dp))
    }
}

@Composable
private fun ProfileAvatar(name: String, premium: Boolean) {
    Box {
        Box(
            modifier = Modifier
                .size(84.dp)
                .border(2.dp, PompColors.CinnabarDark, RoundedCornerShape(24.dp))
                .background(PompColors.Cinnabar, RoundedCornerShape(24.dp)),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = name.trim().take(1).uppercase().ifBlank { "学" },
                style = PompTextStyles.hanziMedium.copy(fontSize = 38.sp),
                color = PompColors.Paper,
            )
        }
        if (premium) {
            Surface(
                color = PompColors.Gold,
                shape = CircleShape,
                modifier = Modifier.align(Alignment.BottomEnd).size(25.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = Icons.Filled.WorkspacePremium,
                        contentDescription = stringResource(R.string.rating_premium),
                        tint = PompColors.Paper,
                        modifier = Modifier.size(15.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun ProfileBadge(text: String, containerColor: Color, contentColor: Color) {
    Surface(color = containerColor, shape = RoundedCornerShape(999.dp)) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelMedium,
            color = contentColor,
            modifier = Modifier.padding(horizontal = 11.dp, vertical = 6.dp),
        )
    }
}

@Composable
private fun RowScope.ProfileMetric(value: String, label: String, color: androidx.compose.ui.graphics.Color) {
    Column(
        modifier = Modifier.weight(1f),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(text = value, style = MaterialTheme.typography.titleMedium, color = color)
        Spacer(Modifier.height(3.dp))
        Text(text = label, style = MaterialTheme.typography.labelSmall, color = PompColors.InkSecondary)
    }
}

@Composable
private fun RivalryCard(opponentName: String, currentXp: Int, opponentXp: Int) {
    val total = (currentXp + opponentXp).coerceAtLeast(1)
    val progress = currentXp.toFloat() / total.toFloat()
    val difference = kotlin.math.abs(currentXp - opponentXp)
    val note = when {
        currentXp > opponentXp -> stringResource(R.string.rating_xp_ahead, difference)
        currentXp < opponentXp -> stringResource(R.string.rating_xp_behind, difference)
        else -> stringResource(R.string.rating_xp_tied)
    }
    Surface(
        color = PompColors.Ink,
        shape = RoundedCornerShape(20.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Text(
                text = stringResource(R.string.rating_weekly_result),
                style = MaterialTheme.typography.titleSmall,
                color = PompColors.Paper,
            )
            Spacer(Modifier.height(12.dp))
            Row(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = stringResource(R.string.rating_you),
                    style = MaterialTheme.typography.labelMedium,
                    color = PompColors.Paper,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    text = opponentName,
                    style = MaterialTheme.typography.labelMedium,
                    color = PompColors.Paper,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    textAlign = TextAlign.End,
                    modifier = Modifier.weight(1f),
                )
            }
            Spacer(Modifier.height(8.dp))
            LinearProgressIndicator(
                progress = { progress },
                color = PompColors.Cinnabar,
                trackColor = PompColors.Paper.copy(alpha = 0.15f),
                modifier = Modifier.fillMaxWidth().height(7.dp),
            )
            Spacer(Modifier.height(7.dp))
            Row(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = currentXp.toString(),
                    style = MaterialTheme.typography.labelMedium,
                    color = PompColors.Paper,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    text = opponentXp.toString(),
                    style = MaterialTheme.typography.labelMedium,
                    color = PompColors.Paper,
                )
            }
            Spacer(Modifier.height(8.dp))
            Text(
                text = note,
                style = MaterialTheme.typography.bodySmall,
                color = PompColors.Gold,
                modifier = Modifier.align(Alignment.CenterHorizontally),
            )
        }
    }
}

@Composable
private fun ChallengeFeedbackBanner(
    delivery: ChallengeDelivery?,
    error: ApiError?,
) {
    val title: String
    val body: String
    val containerColor: Color
    val contentColor: Color
    when {
        error != null -> {
            title = stringResource(R.string.challenge_invite_failed)
            body = stringResource(error.messageRes)
            containerColor = PompColors.CinnabarSoft
            contentColor = PompColors.CinnabarDark
        }
        delivery == ChallengeDelivery.TELEGRAM_SENT -> {
            title = stringResource(R.string.challenge_invite_sent_title)
            body = stringResource(R.string.challenge_invite_sent_body)
            containerColor = PompColors.JadeSoft
            contentColor = PompColors.Jade
        }
        else -> {
            title = stringResource(R.string.challenge_invite_app_only_title)
            body = stringResource(R.string.challenge_invite_app_only_body)
            containerColor = PompColors.GoldSoft
            contentColor = PompColors.Ink
        }
    }
    Surface(
        color = containerColor,
        shape = RoundedCornerShape(14.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 13.dp)) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleSmall,
                color = contentColor,
            )
            Spacer(Modifier.height(3.dp))
            Text(
                text = body,
                style = MaterialTheme.typography.bodySmall,
                color = PompColors.InkSecondary,
            )
        }
    }
}

private fun ratingLevelLabel(level: String): String {
    val normalized = level.lowercase().removePrefix("hsk").trim()
    return normalized.toIntOrNull()?.let { "HSK $it" } ?: level.uppercase().ifBlank { "HSK" }
}

@Composable
private fun SectionPill(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    text: String,
) {
    Surface(color = PompColors.Cinnabar, shape = RoundedCornerShape(999.dp)) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(icon, contentDescription = null, tint = PompColors.Paper, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text(
                text = text,
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.Paper,
            )
        }
    }
}

@Composable
private fun TabSwitch(selected: RatingTab, onSelect: (RatingTab) -> Unit) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(modifier = Modifier.padding(4.dp)) {
            TabButton(
                label = stringResource(R.string.rating_tab_league),
                selected = selected == RatingTab.LEAGUE,
                onClick = { onSelect(RatingTab.LEAGUE) },
                modifier = Modifier.weight(1f),
            )
            TabButton(
                label = stringResource(R.string.rating_tab_friends),
                selected = selected == RatingTab.FRIENDS,
                onClick = { onSelect(RatingTab.FRIENDS) },
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun TabButton(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        color = if (selected) PompColors.Cinnabar else PompColors.PaperRaised,
        shape = RoundedCornerShape(11.dp),
        modifier = modifier
            .heightIn(min = 44.dp)
            .clickable(onClick = onClick),
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text(
                text = label,
                style = MaterialTheme.typography.titleSmall,
                color = if (selected) PompColors.Paper else PompColors.InkSecondary,
            )
        }
    }
}

@Composable
private fun LeagueCard(league: String, memberCount: Int, resetSeconds: Long) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Surface(
                color = PompColors.Cinnabar,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(2.dp, PompColors.Gold),
            ) {
                Text(
                    text = leagueGlyph(league),
                    style = PompTextStyles.hanziMedium,
                    color = PompColors.Paper,
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                )
            }
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(start = 12.dp),
            ) {
                Text(
                    text = stringResource(R.string.rating_league_name, leagueGlyph(league)),
                    style = MaterialTheme.typography.titleMedium,
                    color = PompColors.Ink,
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        Icons.Filled.Group,
                        contentDescription = null,
                        tint = PompColors.InkSecondary,
                        modifier = Modifier.size(14.dp),
                    )
                    Spacer(Modifier.width(5.dp))
                    Text(
                        text = stringResource(R.string.rating_members, memberCount),
                        style = MaterialTheme.typography.bodyMedium,
                        color = PompColors.InkSecondary,
                    )
                }
            }
            if (resetSeconds > 0) {
                Surface(color = PompColors.CinnabarSoft, shape = RoundedCornerShape(12.dp)) {
                    Column(
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) {
                        Text(
                            text = countdownText(resetSeconds),
                            style = MaterialTheme.typography.titleSmall,
                            color = PompColors.CinnabarDark,
                            fontWeight = FontWeight.Bold,
                        )
                        Text(
                            text = stringResource(R.string.rating_time_left),
                            style = MaterialTheme.typography.labelSmall,
                            color = PompColors.CinnabarDark,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun LeagueLadder(current: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
    ) {
        LEAGUE_LADDER.forEachIndexed { index, (name, glyph) ->
            if (index > 0) {
                Box(
                    modifier = Modifier
                        .width(18.dp)
                        .height(1.dp)
                        .background(PompColors.Divider),
                )
            }
            val isCurrent = name.equals(current, ignoreCase = true)
            Surface(
                color = if (isCurrent) PompColors.GoldSoft else PompColors.PaperRaised,
                shape = RoundedCornerShape(12.dp),
                border = BorderStroke(
                    1.dp,
                    if (isCurrent) PompColors.Gold else PompColors.Divider,
                ),
            ) {
                Text(
                    text = glyph,
                    style = PompTextStyles.hanziSmall,
                    color = if (isCurrent) PompColors.Gold else PompColors.InkDisabled,
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 6.dp),
                )
            }
        }
    }
}

@Composable
private fun PromotionZone() {
    Row(
        modifier = Modifier.fillMaxWidth().padding(top = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            Icons.Filled.ArrowUpward,
            contentDescription = null,
            tint = PompColors.Gold,
            modifier = Modifier.size(15.dp),
        )
        Spacer(Modifier.width(6.dp))
        Text(
            text = stringResource(R.string.rating_promote, PROMOTION_ZONE),
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.Gold,
        )
        Spacer(Modifier.width(8.dp))
        Box(
            modifier = Modifier
                .weight(1f)
                .height(1.dp)
                .background(PompColors.Divider),
        )
    }
}

@Composable
private fun LeagueRow(
    row: RatingEntryDto,
    onOpen: () -> Unit,
    canChallenge: Boolean,
    onChallenge: () -> Unit,
) {
    val name = row.name.ifBlank { row.username.ifBlank { stringResource(R.string.rating_unnamed) } }
    Surface(
        onClick = onOpen,
        color = if (row.isCurrentUser) PompColors.CinnabarSoft else PompColors.PaperRaised,
        shape = RoundedCornerShape(12.dp),
        border = BorderStroke(1.dp, if (row.isCurrentUser) PompColors.Cinnabar.copy(alpha = 0.25f) else PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            RankBadge(row.rank)
            Spacer(Modifier.width(10.dp))
            InitialsAvatar(name)
            Spacer(Modifier.width(10.dp))
            Row(
                modifier = Modifier.weight(1f),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = name,
                    style = MaterialTheme.typography.bodyLarge,
                    color = if (row.isCurrentUser) PompColors.CinnabarDark else PompColors.Ink,
                    maxLines = 1,
                )
                if (row.isPaid) {
                    Spacer(Modifier.width(6.dp))
                    Icon(
                        Icons.Filled.WorkspacePremium,
                        contentDescription = stringResource(R.string.rating_premium),
                        tint = PompColors.Gold,
                        modifier = Modifier.size(15.dp),
                    )
                }
            }
            Text(
                text = row.xp.toString(),
                style = MaterialTheme.typography.titleSmall,
                color = PompColors.InkSecondary,
            )
            if (canChallenge) {
                Spacer(Modifier.width(8.dp))
                Surface(
                    onClick = onChallenge,
                    shape = RoundedCornerShape(999.dp),
                    color = PompColors.CinnabarSoft,
                    border = BorderStroke(1.dp, PompColors.Cinnabar.copy(alpha = 0.25f)),
                ) {
                    Text(
                        text = "战",
                        style = PompTextStyles.hanziSmall.copy(fontSize = 15.sp),
                        color = PompColors.CinnabarDark,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun ChallengeGroupLabel(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp),
        fontWeight = FontWeight.SemiBold,
        color = PompColors.InkSecondary,
        modifier = Modifier.padding(top = 6.dp),
    )
}

@Composable
private fun PendingChallengeRow(
    duel: ChallengeDto,
    busy: Boolean,
    onRespond: (Int, Boolean) -> Unit,
) {
    ChallengeCard(name = duel.otherUser.name) {
        Surface(
            onClick = { onRespond(duel.id, true) },
            enabled = !busy,
            shape = RoundedCornerShape(11.dp),
            color = PompColors.Cinnabar,
        ) {
            Text(
                text = stringResource(R.string.challenge_accept),
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.Paper,
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 9.dp),
            )
        }
        Spacer(Modifier.width(8.dp))
        Surface(
            onClick = { onRespond(duel.id, false) },
            enabled = !busy,
            shape = RoundedCornerShape(11.dp),
            color = PompColors.PaperRaised,
            border = BorderStroke(1.dp, PompColors.Divider),
        ) {
            Text(
                text = stringResource(R.string.challenge_decline),
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.InkSecondary,
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 9.dp),
            )
        }
    }
}

@Composable
private fun ActiveChallengeRow(duel: ChallengeDto, onStart: (ChallengeDto) -> Unit) {
    ChallengeCard(name = duel.otherUser.name) {
        Surface(
            onClick = { onStart(duel) },
            shape = RoundedCornerShape(11.dp),
            color = PompColors.Cinnabar,
        ) {
            Text(
                text = stringResource(R.string.challenge_start),
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.Paper,
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 9.dp),
            )
        }
    }
}

@Composable
private fun ChallengeCard(name: String, actions: @Composable RowScope.() -> Unit) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = "战",
                style = PompTextStyles.hanziSmall,
                color = PompColors.Cinnabar,
            )
            Spacer(Modifier.width(12.dp))
            Text(
                text = name.ifBlank { stringResource(R.string.rating_unnamed) },
                style = MaterialTheme.typography.bodyLarge,
                color = PompColors.Ink,
                modifier = Modifier.weight(1f),
            )
            actions()
        }
    }
}

@Composable
private fun FriendInviteCard(link: String, onInvite: (String) -> Unit) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 2.dp, vertical = 10.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = "友",
            style = PompTextStyles.hanziMedium.copy(fontSize = 42.sp),
            color = PompColors.Cinnabar,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = stringResource(R.string.rating_friends_invite_body),
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(14.dp))
        Surface(
            onClick = { onInvite(link) },
            enabled = link.isNotBlank(),
            color = PompColors.Cinnabar,
            contentColor = PompColors.Paper,
            shape = RoundedCornerShape(12.dp),
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(
                    imageVector = Icons.Filled.PersonAdd,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp),
                )
                Spacer(Modifier.width(7.dp))
                Text(
                    text = stringResource(R.string.rating_friends_invite),
                    style = MaterialTheme.typography.labelLarge,
                )
            }
        }
    }
}

@Composable
private fun FriendStats(invited: Int, activated: Int, required: Int) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        FriendStat(
            value = invited.toString(),
            label = stringResource(R.string.rating_friends_joined),
        )
        FriendStat(
            value = "$activated / $required",
            label = stringResource(R.string.rating_friends_active_count),
        )
    }
}

@Composable
private fun RowScope.FriendStat(value: String, label: String) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(13.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.weight(1f),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 4.dp, vertical = 10.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = value,
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.Ink,
            )
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall,
                color = PompColors.InkSecondary,
            )
        }
    }
}

@Composable
private fun FriendRow(friend: ReferralItemDto, rank: Int, onOpen: () -> Unit) {
    val name = friend.name.ifBlank { stringResource(R.string.rating_unnamed) }
    val active = friend.status == "active"
    Column(modifier = Modifier.fillMaxWidth().clickable(onClick = onOpen)) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = rank.toString(),
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.InkSecondary,
                textAlign = TextAlign.Center,
                modifier = Modifier.width(28.dp),
            )
            InitialsAvatar(name)
            Spacer(Modifier.width(11.dp))
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = name,
                        style = MaterialTheme.typography.bodyLarge,
                        color = PompColors.Ink,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f, fill = false),
                    )
                    if (friend.isPaid) {
                        Spacer(Modifier.width(5.dp))
                        Icon(
                            imageVector = Icons.Filled.WorkspacePremium,
                            contentDescription = stringResource(R.string.rating_premium),
                            tint = PompColors.Gold,
                            modifier = Modifier.size(14.dp),
                        )
                    }
                }
                Spacer(Modifier.height(3.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Surface(
                        color = if (active) PompColors.JadeSoft else PompColors.GoldSoft,
                        shape = RoundedCornerShape(10.dp),
                    ) {
                        Text(
                            text = stringResource(
                                if (active) {
                                    R.string.rating_friend_active
                                } else {
                                    R.string.rating_friend_pending
                                }
                            ),
                            style = MaterialTheme.typography.labelSmall,
                            color = if (active) PompColors.Jade else PompColors.Gold,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                        )
                    }
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = stringResource(
                            R.string.rating_friend_details,
                            ratingLevelLabel(friend.courseLevel),
                            friend.totalXp,
                        ),
                        style = MaterialTheme.typography.labelSmall,
                        color = PompColors.InkSecondary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
            Spacer(Modifier.width(8.dp))
            Text(
                text = friend.xp.toString(),
                style = MaterialTheme.typography.titleSmall,
                color = PompColors.InkSecondary,
            )
        }
        HorizontalDivider(color = PompColors.Divider)
    }
}

private fun ReferralItemDto.asRatingEntry(fallbackRank: Int) = RatingEntryDto(
    rank = rank.takeIf { it > 0 } ?: fallbackRank,
    name = name,
    username = username,
    xp = xp,
    courseLevel = courseLevel,
    isPaid = isPaid,
    challengeRef = challengeRef,
)

@Composable
private fun RankBadge(rank: Int) {
    val color = when (rank) {
        1 -> PompColors.Gold
        2 -> PompColors.InkDisabled
        3 -> PompColors.CinnabarDark
        else -> PompColors.InkSecondary
    }
    Box(
        modifier = Modifier.size(26.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = rank.toString(),
            style = MaterialTheme.typography.titleSmall,
            color = color,
            fontWeight = if (rank <= 3) FontWeight.Bold else FontWeight.Normal,
        )
    }
}

@Composable
private fun InitialsAvatar(name: String) {
    val initials = name.trim()
        .split(' ')
        .filter { it.isNotBlank() }
        .take(2)
        .joinToString("") { it.take(1) }
        .uppercase()
        .ifBlank { "H" }
    Box(
        modifier = Modifier
            .size(34.dp)
            .background(PompColors.GoldSoft, CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = initials,
            style = MaterialTheme.typography.labelLarge,
            color = PompColors.InkSecondary,
        )
    }
}

@Composable
private fun EmptyBlock(text: String) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth().padding(20.dp),
        )
    }
}

@Composable
private fun ErrorBlock(text: String, onRetry: () -> Unit) {
    Surface(
        color = PompColors.FlameSoft,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, PompColors.Flame.copy(alpha = 0.35f)),
        modifier = Modifier.fillMaxWidth().clickable(onClick = onRetry),
    ) {
        Column(Modifier.padding(14.dp)) {
            Text(
                text = text,
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.Flame,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = stringResource(R.string.action_retry),
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.Flame,
            )
        }
    }
}
