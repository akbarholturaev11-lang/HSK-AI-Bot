package com.pomp.hskai.feature.limit

import androidx.compose.foundation.background
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors

/**
 * The choice a learner is given when a section is spent: subscribe, or take
 * the free week.
 *
 * It is the same block everywhere and it appears IN PLACE — centred over
 * whatever section the learner was in, on a dimmed background — rather than
 * opening a screen of its own. Two reasons. A separate screen loses the
 * context the offer is about, and it makes the offer feel like a punishment
 * for having pressed something; centred over the section it reads as an
 * answer to what just happened. Only the wording changes per section.
 *
 * The card itself is [SectionLimitBlock], which each distribution channel
 * builds its own way — the Google Play build has no checkout to offer, so
 * this must not assume what is inside.
 */
@Composable
fun SectionLimitOverlay(
    sectionTitle: String,
    limit: LimitGate,
    onClose: () -> Unit,
    modifier: Modifier = Modifier,
    reason: String? = null,
    resetAt: String? = null,
) {
    // A scrim that swallows taps: the section behind is closed, so letting a
    // press through to it would do nothing and read as a frozen screen.
    val interaction = remember { MutableInteractionSource() }
    Box(
        modifier = modifier
            .fillMaxSize()
            .background(PompColors.Ink.copy(alpha = 0.58f))
            .clickable(
                interactionSource = interaction,
                indication = null,
                onClick = onClose,
            ),
        contentAlignment = Alignment.Center,
    ) {
        Box(
            modifier = Modifier
                .padding(horizontal = 20.dp)
                .widthIn(max = 360.dp)
                // The card must not take the scrim's tap-to-close with it.
                .clickable(
                    interactionSource = remember { MutableInteractionSource() },
                    indication = null,
                    onClick = {},
                ),
        ) {
            SectionLimitBlock(
                sectionTitle = sectionTitle,
                limit = limit,
                reason = reason,
                resetAt = resetAt,
            )
            Surface(
                color = PompColors.PaperRaised,
                shape = CircleShape,
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .offset(x = 6.dp, y = (-6).dp)
                    .size(30.dp)
                    .clickable(onClick = onClose),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = Icons.Filled.Close,
                        contentDescription = stringResource(R.string.action_back),
                        tint = PompColors.InkSecondary,
                        modifier = Modifier.size(16.dp),
                    )
                }
            }
        }
    }
}
