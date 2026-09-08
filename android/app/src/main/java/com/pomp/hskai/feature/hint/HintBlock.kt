package com.pomp.hskai.feature.hint

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.data.api.AndroidHintDto

/**
 * One small explanation block, as the Mini App draws it.
 *
 * The rules are the product's, not this file's, and they are all kept on the
 * server: a block is never compulsory, it never interrupts anything, it is
 * one title and one sentence, and it is shown once. A section introduction
 * may come back after a long absence — but that too is the server's call, so
 * nothing here counts anything or decides who sees what.
 *
 * All this does is draw it and offer the X.
 */
@Composable
fun HintBlock(
    hint: AndroidHintDto,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
) {
    if (hint.title.isBlank() && hint.body.isBlank()) return
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(start = 12.dp, top = 10.dp, bottom = 10.dp),
            verticalAlignment = Alignment.Top,
        ) {
            Icon(
                imageVector = Icons.Outlined.Info,
                contentDescription = null,
                tint = PompColors.InkSecondary,
                modifier = Modifier
                    .padding(top = 2.dp)
                    .size(16.dp),
            )
            Spacer(Modifier.width(10.dp))
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
            IconButton(onClick = onDismiss, modifier = Modifier.size(36.dp)) {
                Icon(
                    imageVector = Icons.Filled.Close,
                    contentDescription = stringResource(R.string.hint_close),
                    tint = PompColors.InkSecondary,
                    modifier = Modifier.size(16.dp),
                )
            }
        }
    }
}

/**
 * Every block for one section, stacked.
 *
 * Draws nothing at all when there are none, so a caller can place it
 * unconditionally without leaving a gap on the screen.
 */
@Composable
fun SectionHints(
    hints: List<AndroidHintDto>,
    section: String,
    onDismiss: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val mine = hints.filter { it.section == section && it.key.isNotBlank() }
    if (mine.isEmpty()) return
    Column(modifier) {
        mine.forEach { hint ->
            HintBlock(hint = hint, onDismiss = { onDismiss(hint.key) })
            Spacer(Modifier.height(8.dp))
        }
    }
}
