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
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.pomp.hskai.core.design.PompColors

/**
 * The card a learner sees when a section is out of free allowance.
 *
 * It is deliberately text-free: every word comes from the caller, because the
 * two distribution channels say different things here and the Google Play
 * build must not even contain the other channel's wording. Nothing on this
 * card unlocks anything — access is re-read from the server.
 *
 * @param sectionTitle the blocked section, named so the learner knows what is
 *   closed rather than seeing a bare paywall.
 * @param headline the one line that explains the block.
 * @param hint optional smaller line under the buttons.
 * @param secondaryLabel when null, only the primary button is shown.
 */
@Composable
fun LimitBlock(
    sectionTitle: String,
    headline: String,
    primaryLabel: String,
    onPrimary: () -> Unit,
    modifier: Modifier = Modifier,
    reason: String? = null,
    hint: String? = null,
    secondaryLabel: String? = null,
    onSecondary: (() -> Unit)? = null,
    isBusy: Boolean = false,
    errorText: String? = null,
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
                text = headline,
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.CinnabarDark,
                fontWeight = FontWeight.Bold,
            )

            Spacer(Modifier.height(10.dp))
            Button(
                onClick = onPrimary,
                enabled = !isBusy,
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
                if (isBusy) {
                    CircularProgressIndicator(
                        color = PompColors.Paper,
                        strokeWidth = 2.dp,
                        modifier = Modifier.size(18.dp),
                    )
                } else {
                    Text(
                        text = primaryLabel,
                        style = MaterialTheme.typography.labelLarge,
                    )
                }
            }

            if (secondaryLabel != null && onSecondary != null) {
                Spacer(Modifier.height(8.dp))
                OutlinedButton(
                    onClick = onSecondary,
                    enabled = !isBusy,
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 48.dp),
                    shape = RoundedCornerShape(14.dp),
                ) {
                    Text(
                        text = secondaryLabel,
                        style = MaterialTheme.typography.labelLarge,
                        color = PompColors.CinnabarDark,
                    )
                }
            }

            if (!hint.isNullOrBlank()) {
                Spacer(Modifier.height(8.dp))
                Text(
                    text = hint,
                    style = MaterialTheme.typography.bodySmall,
                    color = PompColors.InkSecondary,
                )
            }

            if (!errorText.isNullOrBlank()) {
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
                            text = errorText,
                            style = MaterialTheme.typography.bodyMedium,
                            color = PompColors.CinnabarDark,
                        )
                    }
                }
            }
        }
    }
}
