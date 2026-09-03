package com.pomp.hskai.feature.limit

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
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
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors

/**
 * What the learner sees when a section is out of free allowance.
 *
 * Subscription is never sold inside this app: the button hands the learner to
 * the Telegram bot, which opens the existing subscription Mini App. Access
 * then lifts on the next server refresh. Until it is paid, this block keeps
 * appearing — nothing here unlocks anything on the client.
 *
 * @param sectionTitle the blocked section, named so the learner knows what
 *   they are unlocking rather than seeing a bare paywall.
 */
@Composable
fun LimitBlock(
    sectionTitle: String,
    state: SubscriptionHandoffState,
    onUnlock: () -> Unit,
    modifier: Modifier = Modifier,
    reason: String? = null,
) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, PompColors.Gold),
        modifier = modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(18.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    Icons.Filled.Lock,
                    contentDescription = null,
                    tint = PompColors.Gold,
                    modifier = Modifier.size(18.dp),
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    text = sectionTitle,
                    style = MaterialTheme.typography.titleMedium,
                    color = PompColors.Ink,
                )
            }

            if (!reason.isNullOrBlank()) {
                Spacer(Modifier.height(6.dp))
                Text(
                    text = reason,
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                )
            }

            Spacer(Modifier.height(12.dp))
            Text(
                text = stringResource(R.string.limit_unlock_headline),
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.CinnabarDark,
                fontWeight = FontWeight.Bold,
            )

            Spacer(Modifier.height(10.dp))
            Button(
                onClick = onUnlock,
                enabled = !state.isOpening,
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 52.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = PompColors.Cinnabar,
                    contentColor = PompColors.Paper,
                    disabledContainerColor = PompColors.Locked,
                    disabledContentColor = PompColors.Paper,
                ),
            ) {
                if (state.isOpening) {
                    CircularProgressIndicator(
                        color = PompColors.Paper,
                        strokeWidth = 2.dp,
                        modifier = Modifier.size(18.dp),
                    )
                } else {
                    Text(
                        text = stringResource(R.string.limit_unlock_button),
                        style = MaterialTheme.typography.labelLarge,
                    )
                    Spacer(Modifier.width(6.dp))
                    Icon(
                        Icons.AutoMirrored.Filled.KeyboardArrowRight,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                    )
                }
            }

            Spacer(Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.limit_unlock_hint),
                style = MaterialTheme.typography.bodySmall,
                color = PompColors.InkSecondary,
            )

            state.error?.let { error ->
                Spacer(Modifier.height(10.dp))
                Surface(
                    color = PompColors.CinnabarSoft,
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Column(
                        modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                        verticalArrangement = Arrangement.spacedBy(2.dp),
                    ) {
                        Text(
                            text = stringResource(error.messageRes),
                            style = MaterialTheme.typography.bodyMedium,
                            color = PompColors.CinnabarDark,
                        )
                    }
                }
            }
        }
    }
}
