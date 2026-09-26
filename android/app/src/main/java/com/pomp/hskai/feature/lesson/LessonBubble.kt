package com.pomp.hskai.feature.lesson

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.core.design.PompColors

/*
 * The lesson's own pieces of the stage layout: the ready answer after a wrong
 * one and the questions the learner can take to the AI chat. The bubble, the
 * coach, the heading and the buttons are shared with practice and live in
 * `core/design/components/HskStage.kt`.
 */

/**
 * The ready answer after a wrong one, said by the AI tutor's avatar. It is the
 * card's own explanation, already in the lesson data: no model is asked, so
 * showing it costs nothing.
 */
@Composable
internal fun ReadyAnswer(text: String, modifier: Modifier = Modifier) {
    Row(
        modifier = modifier.fillMaxWidth(),
        verticalAlignment = Alignment.Top,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier.size(28.dp).clip(RoundedCornerShape(50)).background(PompColors.Cinnabar),
        ) {
            // The same mark the AI chat uses for its own messages.
            Text("AI", color = PompColors.Paper, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
        }
        Surface(
            color = PompColors.PaperRaised,
            shape = RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp, bottomEnd = 20.dp, bottomStart = 6.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, PompColors.Divider),
        ) {
            Text(
                text = text,
                fontSize = 15.sp,
                lineHeight = 21.sp,
                color = PompColors.Ink,
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
            )
        }
    }
}

/** One question the learner can hand to the AI chat with this card as context. */
@Composable
internal fun AskChip(text: String, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(999.dp),
        color = PompColors.PaperRaised,
        border = androidx.compose.foundation.BorderStroke(1.dp, PompColors.Divider),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelLarge,
            color = PompColors.Ink,
            modifier = Modifier.padding(horizontal = 13.dp, vertical = 8.dp),
        )
    }
}
