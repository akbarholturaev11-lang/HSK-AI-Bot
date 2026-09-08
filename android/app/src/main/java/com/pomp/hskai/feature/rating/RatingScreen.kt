package com.pomp.hskai.feature.rating

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowUpward
import androidx.compose.material.icons.filled.Group
import androidx.compose.material.icons.filled.WorkspacePremium
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.data.api.AndroidHintDto
import com.pomp.hskai.feature.hint.SectionHints
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
    onChallenge: (String) -> Unit,
    onRespond: (Int, Boolean) -> Unit,
    onStartChallenge: (ChallengeDto) -> Unit,
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
                SectionPill(
                    icon = Icons.Filled.WorkspacePremium,
                    text = stringResource(R.string.nav_rating),
                )
            }
            item {
                // Mini App `hintsHtml("rating")`.
                SectionHints(
                    hints = hints,
                    section = "rating",
                    onDismiss = onDismissHint,
                )
            }
            item {
                TabSwitch(selected = state.tab, onSelect = onSelectTab)
            }

            // Duels sit above the table: they are waiting on the learner,
            // and the leaderboard is not.
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

            state.error?.let { error ->
                item {
                    ErrorBlock(
                        text = stringResource(error.messageRes),
                        onRetry = onRetry,
                    )
                }
            }

            when (state.tab) {
                RatingTab.LEAGUE -> {
                    val rows = rating?.leaderboard.orEmpty()
                    if (rows.size >= PROMOTION_ZONE) {
                        item { PromotionZone() }
                    }
                    items(rows, key = { "league-${it.rank}-${it.name}" }) { row ->
                        LeagueRow(
                            row = row,
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
                    val friends = state.referral?.items.orEmpty()
                    items(friends, key = { "friend-${it.name}-${it.status}" }) { friend ->
                        FriendRow(friend)
                    }
                    if (friends.isEmpty() && !state.isLoading && state.error == null) {
                        item { EmptyBlock(stringResource(R.string.rating_friends_empty)) }
                    }
                }
            }
        }
    }
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
    canChallenge: Boolean,
    onChallenge: () -> Unit,
) {
    val name = row.name.ifBlank { row.username.ifBlank { stringResource(R.string.rating_unnamed) } }
    Surface(
        color = if (row.isCurrentUser) PompColors.CinnabarSoft else PompColors.Paper,
        shape = RoundedCornerShape(12.dp),
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
            // The Mini App lets you challenge anyone you can see on the board.
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
            color = PompColors.Paper,
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
private fun FriendRow(friend: ReferralItemDto) {
    val name = friend.name.ifBlank { stringResource(R.string.rating_unnamed) }
    val active = friend.status == "active"
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(12.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            InitialsAvatar(name)
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text(
                    text = name,
                    style = MaterialTheme.typography.bodyLarge,
                    color = PompColors.Ink,
                    maxLines = 1,
                )
                Text(
                    text = stringResource(
                        if (active) R.string.rating_friend_active else R.string.rating_friend_pending
                    ),
                    style = MaterialTheme.typography.bodyMedium,
                    color = if (active) PompColors.Jade else PompColors.InkSecondary,
                )
            }
        }
    }
}

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
        color = PompColors.CinnabarSoft,
        shape = RoundedCornerShape(14.dp),
        modifier = Modifier.fillMaxWidth().clickable(onClick = onRetry),
    ) {
        Column(Modifier.padding(14.dp)) {
            Text(
                text = text,
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.CinnabarDark,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = stringResource(R.string.action_retry),
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.CinnabarDark,
            )
        }
    }
}
