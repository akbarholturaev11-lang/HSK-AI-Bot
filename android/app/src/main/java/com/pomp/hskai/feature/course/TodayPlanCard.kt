package com.pomp.hskai.feature.course

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.domain.model.CourseToday
import com.pomp.hskai.domain.model.TodayTask
import com.pomp.hskai.domain.model.TodayTaskAccess

private val NodeSize = 34.dp
private val NodeSwing = 9.dp
private val PathPadding = 9.dp

@Composable
private fun planSurface(): Color = if (PompColors.IsDark) PompColors.PaperRaised else PompColors.Ink

@Composable
private fun planPrimaryInk(): Color = if (PompColors.IsDark) PompColors.Ink else Color.White

@Composable
private fun planTrackIdle(): Color = if (PompColors.IsDark) PompColors.Divider.copy(alpha = 0.72f) else Color.White.copy(alpha = 0.16f)

@Composable
private fun planNodeIdleFill(): Color = if (PompColors.IsDark) Color(0xFF0E4D6B) else Color.White.copy(alpha = 0.09f)

@Composable
private fun planNodeIdleBorder(): Color = if (PompColors.IsDark) PompColors.Divider else Color.White.copy(alpha = 0.20f)

@Composable
private fun planNodeIdleInk(): Color = if (PompColors.IsDark) PompColors.InkSecondary else Color.White.copy(alpha = 0.60f)

@Composable
private fun planHeaderInk(): Color = if (PompColors.IsDark) PompColors.InkSecondary else Color.White.copy(alpha = 0.70f)

@Composable
private fun planLabelInk(): Color = if (PompColors.IsDark) PompColors.InkSecondary else Color.White.copy(alpha = 0.66f)

@Composable
private fun planLockedInk(): Color = if (PompColors.IsDark) PompColors.InkDisabled else Color.White.copy(alpha = 0.38f)

@Composable
internal fun TodayPlanCard(
    today: CourseToday,
    onTask: (TodayTask) -> Unit,
    modifier: Modifier = Modifier,
) {
    val tasks = today.tasks
    if (tasks.isEmpty()) return
    val nextIndex = remember(tasks) { tasks.indexOfFirst { !it.done && it.available } }

    Surface(
        color = planSurface(),
        shape = RoundedCornerShape(18.dp),
        border = if (PompColors.IsDark) BorderStroke(1.dp, PompColors.Divider) else null,
        modifier = modifier
            .fillMaxWidth()
            .padding(start = 16.dp, end = 16.dp, bottom = 10.dp),
    ) {
        Box {
            PlanWatermark()
            Column(
                modifier = Modifier.padding(start = 14.dp, end = 14.dp, top = 12.dp, bottom = 14.dp),
            ) {
                PlanHeader(today)
                PlanPath(tasks = tasks, nextIndex = nextIndex, onTask = onTask)
                when {
                    today.complete -> PlanDoneRow()
                    nextIndex >= 0 -> PlanGoButton(onClick = { onTask(tasks[nextIndex]) })
                }
            }
        }
    }
}

@Composable
private fun BoxScope.PlanWatermark() {
    Text(
        text = "计",
        style = PompTextStyles.hanziLarge.copy(fontSize = 74.sp, lineHeight = 74.sp),
        color = planPrimaryInk().copy(alpha = if (PompColors.IsDark) 0.05f else 0.06f),
        modifier = Modifier.align(Alignment.TopEnd).offset(x = 6.dp, y = (-20).dp),
    )
}

@Composable
private fun PlanHeader(today: CourseToday) {
    val primaryInk = planPrimaryInk()
    Row(verticalAlignment = Alignment.CenterVertically) {
        MiniAppNodeIcon(
            kind = if (today.complete) CourseNodeIconKind.CircleCheck else CourseNodeIconKind.TargetArrow,
            tint = if (today.complete) PompColors.PlanDone else PompColors.Gold,
            size = 13.dp,
        )
        Spacer(Modifier.width(5.dp))
        Text(
            text = buildAnnotatedString {
                append(stringResource(R.string.today_plan_label))
                append(' ')
                withStyle(SpanStyle(color = primaryInk, fontWeight = FontWeight.SemiBold)) {
                    append(today.doneXp.toString())
                }
                append("/${today.goalXp} XP")
            },
            style = MaterialTheme.typography.labelSmall.copy(fontSize = 11.5.sp),
            fontWeight = FontWeight.Medium,
            color = planHeaderInk(),
        )
    }
}

@Composable
private fun PlanPath(tasks: List<TodayTask>, nextIndex: Int, onTask: (TodayTask) -> Unit) {
    val pulse = rememberInfiniteTransition(label = "planPulse")
    val pulseProgress by pulse.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(animation = tween(durationMillis = 1600), repeatMode = RepeatMode.Restart),
        label = "planPulseProgress",
    )

    Box(modifier = Modifier.fillMaxWidth().padding(top = 6.dp).padding(vertical = PathPadding)) {
        PlanTrail(tasks)
        Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
            tasks.forEachIndexed { index, task ->
                PlanStep(
                    task = task,
                    index = index,
                    isNext = index == nextIndex,
                    pulseProgress = pulseProgress,
                    onTask = onTask,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun BoxScope.PlanTrail(tasks: List<TodayTask>) {
    if (tasks.size < 2) return
    val idle = planTrackIdle()
    Canvas(modifier = Modifier.matchParentSize()) {
        val cell = size.width / tasks.size
        val centreY = NodeSize.toPx() / 2f
        val swing = NodeSwing.toPx()
        fun cx(index: Int) = cell * (index + 0.5f)
        fun cy(index: Int) = centreY + if (index % 2 == 0) -swing else swing

        for (index in 1 until tasks.size) {
            val ax = cx(index - 1)
            val ay = cy(index - 1)
            val bx = cx(index)
            val by = cy(index)
            val mx = (ax + bx) / 2f
            val segment = Path().apply {
                moveTo(ax, ay)
                cubicTo(mx, ay, mx, by, bx, by)
            }
            drawPath(
                path = segment,
                color = if (tasks[index - 1].done) PompColors.Jade else idle,
                style = Stroke(width = 3.dp.toPx(), cap = StrokeCap.Round),
            )
        }
    }
}

@Composable
private fun RowScope.PlanStep(
    task: TodayTask,
    index: Int,
    isNext: Boolean,
    pulseProgress: Float,
    onTask: (TodayTask) -> Unit,
    modifier: Modifier = Modifier,
) {
    val locked = !task.available && !task.done
    val label = todayTaskLabel(task)
    Column(
        modifier = modifier.widthIn(min = 56.dp).offset(y = if (index % 2 == 0) -NodeSwing else NodeSwing),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Top,
    ) {
        PlanNode(task, isNext, pulseProgress, label) { onTask(task) }
        Spacer(Modifier.height(4.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.5.sp, lineHeight = 13.sp),
            fontWeight = FontWeight.Medium,
            color = if (locked) planLockedInk() else planLabelInk(),
            textAlign = TextAlign.Center,
            modifier = Modifier.widthIn(max = 72.dp),
        )
    }
}

@Composable
private fun PlanNode(
    task: TodayTask,
    isNext: Boolean,
    pulseProgress: Float,
    label: String,
    onClick: () -> Unit,
) {
    val fill = when {
        task.done -> PompColors.Jade
        isNext -> PompColors.Gold
        else -> planNodeIdleFill()
    }
    val border = when {
        task.done -> PompColors.Jade
        isNext -> PompColors.Gold
        else -> planNodeIdleBorder()
    }
    val ink = when {
        task.done -> planPrimaryInk()
        isNext -> PompColors.PlanOnGold
        else -> planNodeIdleInk()
    }
    val dimmed = !task.available && !task.done

    Box(modifier = Modifier.graphicsLayer { alpha = if (dimmed) 0.5f else 1f }) {
        if (isNext) {
            Canvas(modifier = Modifier.matchParentSize()) {
                val radius = (size.minDimension / 2f + 4.dp.toPx()) * (1f + 0.25f * pulseProgress)
                drawCircle(
                    color = PompColors.Gold.copy(alpha = 0.7f * (1f - pulseProgress)),
                    radius = radius,
                    center = Offset(size.width / 2f, size.height / 2f),
                    style = Stroke(width = 2.dp.toPx()),
                )
            }
        }
        Surface(
            onClick = onClick,
            enabled = !task.done && task.available,
            shape = CircleShape,
            color = fill,
            border = BorderStroke(1.5.dp, border),
            modifier = Modifier.size(NodeSize).semantics { contentDescription = label },
        ) {
            Box(contentAlignment = Alignment.Center) {
                MiniAppNodeIcon(kind = todayTaskIcon(task), tint = ink, size = 17.dp)
            }
        }
    }
}

@Composable
private fun PlanGoButton(onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(12.dp),
        color = PompColors.Gold,
        modifier = Modifier.fillMaxWidth().padding(top = 10.dp),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 11.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = stringResource(R.string.today_plan_go),
                style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.5.sp),
                fontWeight = FontWeight.SemiBold,
                color = PompColors.PlanOnGold,
            )
            Spacer(Modifier.width(6.dp))
            MiniAppNodeIcon(kind = CourseNodeIconKind.ArrowRight, tint = PompColors.PlanOnGold, size = 16.dp)
        }
    }
}

@Composable
private fun PlanDoneRow() {
    val dashed = PompColors.PlanDone.copy(alpha = 0.55f)
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 10.dp)
            .drawBehind {
                drawRoundRect(
                    color = dashed,
                    cornerRadius = CornerRadius(12.dp.toPx(), 12.dp.toPx()),
                    style = Stroke(width = 1.5.dp.toPx(), pathEffect = PathEffect.dashPathEffect(floatArrayOf(6.dp.toPx(), 5.dp.toPx()))),
                )
            }
            .padding(horizontal = 14.dp, vertical = 11.dp),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        MiniAppNodeIcon(kind = CourseNodeIconKind.CircleCheck, tint = PompColors.PlanDone, size = 16.dp)
        Spacer(Modifier.width(6.dp))
        Text(
            text = stringResource(R.string.today_plan_done),
            style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.5.sp),
            fontWeight = FontWeight.SemiBold,
            color = PompColors.PlanDone,
        )
    }
}

private fun todayTaskIcon(task: TodayTask): CourseNodeIconKind = when {
    task.done -> CourseNodeIconKind.Check
    !task.available -> CourseNodeIconKind.Lock
    task.access == TodayTaskAccess.AD -> CourseNodeIconKind.PlayerPlay
    task.type == "continue_lesson" -> CourseNodeIconKind.Book2
    task.type == "mistake_review" -> CourseNodeIconKind.AlertTriangle
    task.type == "mock_exam" -> CourseNodeIconKind.Certificate
    task.type == "voice_dialog" -> CourseNodeIconKind.Microphone
    task.type == "skill_drill" -> CourseNodeIconKind.Cards
    else -> CourseNodeIconKind.Circle
}

@Composable
private fun todayTaskLabel(task: TodayTask): String = when (task.type) {
    "continue_lesson" -> {
        val part = task.ref.orEmpty().split(":").getOrNull(1).orEmpty()
        if (part.isBlank()) stringResource(R.string.today_task_part)
        else stringResource(R.string.today_task_part_n, part)
    }
    "mistake_review" -> stringResource(R.string.today_task_mistakes)
    "mock_exam" -> stringResource(R.string.today_task_test)
    "voice_dialog" -> stringResource(R.string.today_task_talk)
    "skill_drill" -> if (task.skill == "pronunciation") {
        stringResource(R.string.today_task_pron)
    } else {
        stringResource(R.string.today_task_chars)
    }
    else -> ""
}
