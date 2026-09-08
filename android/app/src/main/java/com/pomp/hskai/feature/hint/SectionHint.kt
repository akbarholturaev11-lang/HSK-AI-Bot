package com.pomp.hskai.feature.hint

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Popup
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.data.api.AndroidHintDto

/**
 * The explanation for one section: a small marker, and its text on demand.
 *
 * It is deliberately NOT a card in the layout. An explanation that takes a
 * block of the screen pushes the section's own content down and has to be
 * dealt with before the learner can get on with anything — which is the
 * opposite of what a hint is for. So the section shows one quiet marker next
 * to its title; tapping it floats the text over the section, and the X puts
 * it away for good.
 *
 * One marker per section even when the server sent several: the next one
 * appears after this is closed, so the screen never carries more than one.
 *
 * Draws nothing at all when the section has no hint, so a caller can place it
 * unconditionally without leaving a gap.
 */
@Composable
fun SectionHint(
    hints: List<AndroidHintDto>,
    section: String,
    onDismiss: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val hint = hints.firstOrNull { it.section == section && it.key.isNotBlank() } ?: return
    var open by remember(hint.key) { mutableStateOf(false) }

    Box(modifier) {
        Surface(
            color = PompColors.PaperRaised,
            shape = CircleShape,
            border = BorderStroke(1.dp, PompColors.Divider),
            modifier = Modifier
                .size(24.dp)
                .clickable { open = !open },
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = Icons.Outlined.Info,
                    contentDescription = hint.title.ifBlank {
                        stringResource(R.string.hint_open)
                    },
                    tint = PompColors.InkSecondary,
                    modifier = Modifier.size(15.dp),
                )
            }
        }

        if (open) {
            Popup(
                alignment = Alignment.TopStart,
                // Just under the marker, nudged left so a marker sitting near
                // the right edge does not push the card off screen.
                offset = IntOffset(-360, 80),
                onDismissRequest = { open = false },
            ) {
                HintCard(
                    hint = hint,
                    onClose = {
                        open = false
                        onDismiss(hint.key)
                    },
                )
            }
        }
    }
}

@Composable
private fun HintCard(hint: AndroidHintDto, onClose: () -> Unit) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        shadowElevation = 8.dp,
        modifier = Modifier.widthIn(max = 260.dp),
    ) {
        Row(
            modifier = Modifier.padding(start = 12.dp, top = 10.dp, bottom = 10.dp, end = 4.dp),
            verticalAlignment = Alignment.Top,
        ) {
            Column(Modifier.weight(1f)) {
                if (hint.title.isNotBlank()) {
                    Text(
                        text = hint.title,
                        style = MaterialTheme.typography.titleSmall,
                        color = PompColors.Ink,
                    )
                }
                if (hint.body.isNotBlank()) {
                    if (hint.title.isNotBlank()) Spacer(Modifier.height(2.dp))
                    Text(
                        text = hint.body,
                        style = MaterialTheme.typography.bodySmall,
                        color = PompColors.InkSecondary,
                    )
                }
            }
            Spacer(Modifier.width(4.dp))
            Box(
                modifier = Modifier
                    .size(28.dp)
                    .clickable(onClick = onClose),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = Icons.Filled.Close,
                    contentDescription = stringResource(R.string.hint_close),
                    tint = PompColors.InkSecondary,
                    modifier = Modifier.size(15.dp),
                )
            }
        }
    }
}
