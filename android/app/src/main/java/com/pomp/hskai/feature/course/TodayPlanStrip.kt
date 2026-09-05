package com.pomp.hskai.feature.course

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.domain.model.CourseToday
import com.pomp.hskai.domain.model.TodayTask
import com.pomp.hskai.domain.model.TodayTaskAccess

/**
 * Native equivalent of Course v3 `.today`.
 *
 * Deliberately one compact horizontal strip: the learning path remains the
 * primary surface and is not pushed down by a dashboard card. The server owns
 * task identity, completion and access; Android only renders those values.
 */
@Composable
fun TodayPlanStrip(
    today: CourseToday,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier.padding(start = 16.dp, top = 2.dp, bottom = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = "⚡",
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.Cinnabar,
        )
        Spacer(Modifier.width(4.dp))
        Text(
            text = "${today.doneXp}/${today.goalXp} XP",
            style = MaterialTheme.typography.labelMedium,
            color = PompColors.Ink,
        )
        Spacer(Modifier.width(8.dp))

        Row(
            modifier = Modifier.horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            today.tasks.forEach { task -> TodayTaskChip(task) }
            Spacer(Modifier.width(10.dp))
        }
    }
}

@Composable
private fun TodayTaskChip(task: TodayTask) {
    val locked = task.access == TodayTaskAccess.LOCKED || !task.available
    val background = if (task.done) PompColors.Paper else PompColors.PaperRaised
    val foreground = when {
        task.done -> PompColors.InkDisabled
        locked -> PompColors.InkDisabled
        else -> PompColors.Ink
    }
    val icon: ImageVector = when {
        task.done -> Icons.Filled.Check
        locked -> Icons.Filled.Lock
        else -> Icons.Filled.PlayArrow
    }
    val iconTint = if (task.done) PompColors.Jade else PompColors.InkDisabled

    Surface(
        color = background,
        contentColor = foreground,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(icon, contentDescription = null, tint = iconTint)
            Spacer(Modifier.width(4.dp))
            Text(
                text = task.displayLabel(),
                style = MaterialTheme.typography.labelMedium,
                color = foreground,
                maxLines = 1,
            )
        }
    }
}

/** Labels mirror the five task identities emitted by DailyPlanService. */
private fun TodayTask.displayLabel(): String = when (type) {
    "continue_lesson" -> "Dars"
    "mistake_review" -> "Xatolar"
    "skill_drill" -> when (skill) {
        "characters" -> "Ieroglif"
        "pronunciation" -> "Talaffuz"
        else -> "Mashq"
    }
    "mock_exam" -> "HSK test"
    "voice_dialog" -> "AI Voice"
    else -> type.replace('_', ' ')
}
