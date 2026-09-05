package com.pomp.hskai.feature.course

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Diamond
import androidx.compose.material.icons.filled.LocalFireDepartment
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.TrackChanges
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.res.stringArrayResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.domain.model.CourseLesson
import com.pomp.hskai.domain.model.CourseMap
import com.pomp.hskai.domain.model.CourseMilestone
import com.pomp.hskai.domain.model.CourseToday
import com.pomp.hskai.domain.model.CourseUnit
import com.pomp.hskai.domain.model.LessonAccess
import com.pomp.hskai.domain.model.LessonStatus
import com.pomp.hskai.domain.model.TodayTask
import com.pomp.hskai.domain.model.TodayTaskAccess
import com.pomp.hskai.feature.limit.LimitGate
import kotlin.math.roundToInt
import kotlin.math.sin

/** Native rendering of the Mini App course shell. Mini App is source of truth. */
@Composable
fun CourseScreen(
    state: CourseUiState,
    dailyGoal: Int,
    limit: LimitGate,
    onLesson: (CourseLesson) -> Unit,
    onOpenGoal: () -> Unit,
    onOpenChest: () -> Unit,
    onChestRewardConsumed: () -> Unit,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val map = state.map
    Box(modifier = modifier.fillMaxSize()) {
        Surface(modifier = Modifier.fillMaxSize(), color = PompColors.Paper) {
            when {
                state.isLoading && map == null -> Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) { CircularProgressIndicator(color = PompColors.Cinnabar) }

                map == null -> CourseErrorBlock(
                    messageRes = state.error?.messageRes ?: R.string.error_unknown,
                    onRetry = onRetry,
                )

                else -> {
                    val rows = remember(map) { map.toRows() }
                    val listState = rememberLazyListState()
                    val viewportHeight = listState.layoutInfo.viewportSize.height
                    val foundationVisible = map.level.equals("hsk1", ignoreCase = true) && map.foundation != null
                    val foundationMustComeFirst = foundationVisible && map.foundation?.mustComeFirst == true

                    LaunchedEffect(
                        map.currentLesson?.order,
                        viewportHeight,
                        foundationVisible,
                        foundationMustComeFirst,
                    ) {
                        if (foundationMustComeFirst) {
                            listState.scrollToItem(0)
                            return@LaunchedEffect
                        }
                        val rowIndex = rows.indexOfFirst {
                            it is CourseRow.Path &&
                                (it.item as? PathItem.Lesson)?.lesson?.isCurrent == true
                        }
                        if (rowIndex >= 0 && viewportHeight > 0) {
                            listState.scrollToItem(
                                index = rowIndex + if (foundationVisible) 1 else 0,
                                scrollOffset = -(viewportHeight * 0.42f).roundToInt(),
                            )
                        }
                    }

                    Column(Modifier.fillMaxSize()) {
                        CourseHeader(
                            map = map,
                            dailyGoal = dailyGoal,
                            onOpenGoal = onOpenGoal,
                        )
                        CourseProgressBar(map)
                        if (!foundationMustComeFirst) {
                            map.today?.takeIf { it.tasks.isNotEmpty() }?.let { TodayPlanStrip(it) }
                        }
                        if (state.isStale) StaleBanner()

                        LazyColumn(
                            state = listState,
                            modifier = Modifier.fillMaxWidth().weight(1f),
                            contentPadding = androidx.compose.foundation.layout.PaddingValues(
                                vertical = 8.dp,
                            ),
                        ) {
                            if (foundationVisible) {
                                item {
                                    map.foundation?.let { FoundationEntry(it) }
                                }
                            }
                            items(rows) { row ->
                                when (row) {
                                    is CourseRow.Unit -> UnitHeader(row.unit)
                                    is CourseRow.Path -> PathRow(
                                        row = row,
                                        chestReady = map.progress.rewardChest?.ready == true,
                                        isOpeningChest = state.isOpeningChest,
                                        isStale = state.isStale,
                                        onLesson = onLesson,
                                        onOpenChest = onOpenChest,
                                    )
                                }
                            }
                            item { Spacer(Modifier.height(14.dp)) }
                        }
                    }
                }
            }
        }

        state.chestRewardXp?.let { reward ->
            RewardChestOverlay(
                rewardXp = reward,
                onContinue = onChestRewardConsumed,
            )
        }
    }
}

private fun courseLevelLabel(level: String): String {
    val number = level.lowercase().removePrefix("hsk").trim().toIntOrNull()
    return if (number != null) "HSK $number" else level.uppercase()
}

@Composable
private fun CourseHeader(map: CourseMap, dailyGoal: Int, onOpenGoal: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(start = 16.dp, end = 16.dp, top = 14.dp, bottom = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Surface(color = PompColors.Cinnabar, shape = RoundedCornerShape(20.dp)) {
            Row(
                modifier = Modifier.padding(horizontal = 13.dp, vertical = 7.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(
                    Icons.Filled.Bolt,
                    contentDescription = null,
                    tint = PompColors.Paper,
                    modifier = Modifier.size(15.dp),
                )
                Spacer(Modifier.width(6.dp))
                Text(
                    text = courseLevelLabel(map.level),
                    style = MaterialTheme.typography.labelLarge.copy(
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Medium,
                        letterSpacing = 0.sp,
                    ),
                    color = PompColors.Paper,
                )
            }
        }
        Spacer(Modifier.weight(1f))
        StatChip(
            Icons.Filled.LocalFireDepartment,
            PompColors.Cinnabar,
            map.progress.streak.toString(),
            stringResource(R.string.today_streak),
        )
        Spacer(Modifier.width(8.dp))
        StatChip(
            Icons.Filled.Diamond,
            PompColors.Gold,
            map.progress.xp.toString(),
            stringResource(R.string.today_xp),
        )
        Spacer(Modifier.width(8.dp))
        GoalRing(map.progress.dailyXp, dailyGoal, onOpenGoal)
    }
}

@Composable
private fun StatChip(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    tint: Color,
    value: String,
    label: String,
) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
    ) {
        Row(
            modifier = Modifier
                .padding(horizontal = 12.dp, vertical = 6.dp)
                .semantics { contentDescription = "$label: $value" },
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(16.dp))
            Spacer(Modifier.width(5.dp))
            Text(
                value,
                style = MaterialTheme.typography.labelLarge.copy(
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                    letterSpacing = 0.sp,
                ),
                color = tint,
            )
        }
    }
}

@Composable
fun GoalRing(
    dailyXp: Int,
    dailyGoal: Int,
    onClick: () -> Unit,
    size: Dp = 40.dp,
) {
    val goal = dailyGoal.coerceAtLeast(1)
    val fraction = (dailyXp.toFloat() / goal).coerceIn(0f, 1f)
    val complete = fraction >= 1f
    val description = stringResource(R.string.course_goal_progress, dailyXp, goal)
    Box(
        modifier = Modifier
            .size(size)
            .clip(CircleShape)
            .clickable(onClick = onClick)
            .semantics { contentDescription = description },
        contentAlignment = Alignment.Center,
    ) {
        Canvas(Modifier.fillMaxSize()) {
            val stroke = 5.dp.toPx()
            val inset = stroke / 2
            val arcSize = Size(this.size.width - stroke, this.size.height - stroke)
            drawArc(
                PompColors.Divider,
                0f,
                360f,
                false,
                Offset(inset, inset),
                arcSize,
                style = Stroke(stroke),
            )
            if (fraction > 0f) {
                drawArc(
                    if (complete) PompColors.Gold else PompColors.Cinnabar,
                    -90f,
                    360f * fraction,
                    false,
                    Offset(inset, inset),
                    arcSize,
                    style = Stroke(stroke, cap = StrokeCap.Round),
                )
            }
        }
        Icon(
            if (complete) Icons.Filled.Check else Icons.Filled.TrackChanges,
            contentDescription = null,
            tint = if (complete) PompColors.Gold else PompColors.Cinnabar,
            modifier = Modifier.size(size * 0.42f),
        )
    }
}

@Composable
private fun CourseProgressBar(map: CourseMap) {
    val done = map.progress.completedLessons.coerceIn(0, map.totalLessons.coerceAtLeast(0))
    val total = map.totalLessons.coerceAtLeast(1)
    val fraction = (done.toFloat() / total).coerceIn(0f, 1f)
    Row(
        modifier = Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, bottom = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier
                .weight(1f)
                .height(8.dp)
                .clip(RoundedCornerShape(6.dp))
                .background(PompColors.Divider),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(fraction)
                    .height(8.dp)
                    .background(PompColors.Cinnabar),
            )
        }
        Spacer(Modifier.width(10.dp))
        Text(
            text = "$done / ${map.totalLessons} ${stringResource(R.string.course_progress_lessons)}",
            style = MaterialTheme.typography.labelSmall.copy(fontSize = 12.sp),
            color = PompColors.InkSecondary,
            fontWeight = FontWeight.Medium,
        )
    }
}

@Composable
private fun TodayPlanStrip(today: CourseToday) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(start = 16.dp, top = 2.dp, bottom = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                if (today.complete) Icons.Filled.Check else Icons.Filled.TrackChanges,
                contentDescription = null,
                tint = PompColors.Cinnabar,
                modifier = Modifier.size(14.dp),
            )
            Spacer(Modifier.width(4.dp))
            Text(
                text = "${today.doneXp}/${today.goalXp} XP",
                style = MaterialTheme.typography.labelSmall.copy(fontSize = 12.sp),
                color = PompColors.InkSecondary,
                fontWeight = FontWeight.Medium,
            )
        }
        Spacer(Modifier.width(8.dp))
        Row(
            modifier = Modifier
                .weight(1f)
                .horizontalScroll(rememberScrollState())
                .padding(end = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            today.tasks.forEach { task -> TodayTaskChip(task) }
        }
    }
}

@Composable
private fun TodayTaskChip(task: TodayTask) {
    val locked = task.access == TodayTaskAccess.LOCKED || !task.available
    val foreground = if (task.done || locked) PompColors.InkDisabled else PompColors.Ink
    val iconTint = if (task.done) PompColors.Jade else PompColors.InkDisabled
    val icon = when {
        task.done -> Icons.Filled.Check
        locked -> Icons.Filled.Lock
        task.type == "voice_dialog" -> Icons.Filled.Mic
        task.type == "continue_lesson" -> Icons.Filled.School
        else -> Icons.Filled.Bolt
    }
    val text = when (task.type) {
        "continue_lesson" -> stringResource(R.string.today_continue)
        "mistake_review" -> stringResource(R.string.practice_mistakes_title)
        "skill_drill" -> if (task.skill == "pronunciation") {
            stringResource(R.string.practice_pronunciation_title)
        } else {
            stringResource(R.string.practice_characters_title)
        }
        "mock_exam" -> stringResource(R.string.practice_test_title)
        "voice_dialog" -> stringResource(R.string.voice_title)
        else -> stringResource(R.string.practice_title)
    }
    Surface(
        color = if (task.done) PompColors.Paper else PompColors.PaperRaised,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.graphicsLayer { alpha = if (locked) 0.55f else 1f },
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(icon, contentDescription = null, tint = iconTint, modifier = Modifier.size(14.dp))
            Spacer(Modifier.width(4.dp))
            Text(
                text,
                style = MaterialTheme.typography.labelMedium.copy(fontSize = 12.5.sp),
                color = foreground,
                maxLines = 1,
            )
        }
    }
}

@Composable
private fun StaleBanner() {
    Surface(
        color = PompColors.GoldSoft,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
    ) {
        Text(
            stringResource(R.string.today_stale),
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.Ink,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
        )
    }
}

@Composable
private fun UnitHeader(unit: CourseUnit) {
    val background = if (unit.isLocked) PompColors.PaperRaised else PompColors.Ink
    val foreground = if (unit.isLocked) PompColors.InkSecondary else PompColors.Paper
    Surface(
        color = background,
        shape = RoundedCornerShape(14.dp),
        border = if (unit.isLocked) BorderStroke(1.dp, PompColors.Divider) else null,
        modifier = Modifier
            .fillMaxWidth()
            .padding(start = 16.dp, end = 16.dp, top = 8.dp),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 11.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = unit.title.ifBlank { unit.number.toString() },
                style = MaterialTheme.typography.titleMedium.copy(
                    fontSize = 15.sp,
                    lineHeight = 20.sp,
                    fontWeight = FontWeight.SemiBold,
                ),
                color = foreground,
                modifier = Modifier.weight(1f),
                maxLines = 2,
            )
            Icon(
                imageVector = if (unit.isLocked) Icons.Filled.Lock else Icons.Filled.MenuBook,
                contentDescription = null,
                tint = foreground.copy(alpha = 0.85f),
                modifier = Modifier.size(18.dp),
            )
        }
    }
}

private val NODE_SIZE = 64.dp
private val CURRENT_RING_SIZE = 76.dp
private val PATH_ROW_HEIGHT = 84.dp
private val PATH_SWING = 76.dp

private fun pathOffset(unitIndex: Int, nodeIndex: Int): Dp {
    val pxLike = (sin((unitIndex * 3 + nodeIndex) * 0.9) * PATH_SWING.value).roundToInt()
    return pxLike.dp
}

private fun courseNodeLabel(value: String): String =
    if (value.length > 10) value.take(9) + "…" else value

@Composable
private fun PathRow(
    row: CourseRow.Path,
    chestReady: Boolean,
    isOpeningChest: Boolean,
    isStale: Boolean,
    onLesson: (CourseLesson) -> Unit,
    onOpenChest: () -> Unit,
) {
    val offsetX = pathOffset(row.unitIndex, row.nodeIndex)
    val previousX = row.previousNodeIndex?.let { pathOffset(row.unitIndex, it) }
    val pandaPrompts = stringArrayResource(R.array.course_panda_prompts)
    val pandaPrompt = row.pandaPromptIndex?.let { pandaPrompts[it % pandaPrompts.size] }
    val chestDescription = stringResource(R.string.course_chest_cd)

    Box(
        modifier = Modifier.fillMaxWidth().height(PATH_ROW_HEIGHT),
        contentAlignment = Alignment.Center,
    ) {
        if (previousX != null) PathConnector(previousX, offsetX)

        if (pandaPrompt != null) {
            val onLeft = offsetX.value >= 0f
            PathPanda(
                text = pandaPrompt,
                leftBubble = onLeft,
                modifier = Modifier
                    .align(if (onLeft) Alignment.CenterStart else Alignment.CenterEnd)
                    .padding(start = if (onLeft) 8.dp else 0.dp, end = if (onLeft) 0.dp else 8.dp),
            )
        } else if (row.nodeIndex % 2 == 1) {
            val onLeft = offsetX.value >= 0f
            PathScenery(
                seed = row.unitIndex * 5 + row.nodeIndex,
                small = ((row.unitIndex * 3 + row.nodeIndex) % 3 == 0),
                modifier = Modifier
                    .align(if (onLeft) Alignment.CenterStart else Alignment.CenterEnd)
                    .padding(start = if (onLeft) 16.dp else 0.dp, end = if (onLeft) 0.dp else 16.dp),
            )
        }

        Column(
            modifier = Modifier.offset(x = offsetX),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Box(modifier = Modifier.size(CURRENT_RING_SIZE), contentAlignment = Alignment.Center) {
                when (val item = row.item) {
                    is PathItem.Lesson -> {
                        val lesson = item.lesson
                        val clickable = lesson.access == LessonAccess.Open ||
                            lesson.access == LessonAccess.HalfPreview
                        val lessonDescription = lesson.stateLabel()
                        if (lesson.isCurrent && clickable) CurrentBubble()
                        Box(
                            modifier = Modifier
                                .size(CURRENT_RING_SIZE)
                                .then(if (clickable) Modifier.clickable { onLesson(lesson) } else Modifier)
                                .semantics { contentDescription = lessonDescription },
                            contentAlignment = Alignment.Center,
                        ) {
                            LessonNodeFace(lesson)
                        }
                    }

                    PathItem.Chest -> {
                        val clickable = chestReady && !isStale && !isOpeningChest
                        Box(
                            modifier = Modifier
                                .size(CURRENT_RING_SIZE)
                                .then(if (clickable) Modifier.clickable(onClick = onOpenChest) else Modifier)
                                .semantics { contentDescription = chestDescription },
                            contentAlignment = Alignment.Center,
                        ) {
                            ChestNodeFace(isOpeningChest)
                        }
                    }

                    is PathItem.Boss -> BossNodeFace()
                }
            }

            when (val item = row.item) {
                is PathItem.Lesson -> {
                    val lesson = item.lesson
                    Text(
                        text = courseNodeLabel(lesson.hanziPreview),
                        style = MaterialTheme.typography.labelMedium.copy(fontSize = 12.sp),
                        color = if (lesson.status == LessonStatus.LOCKED) {
                            PompColors.InkDisabled
                        } else {
                            PompColors.InkSecondary
                        },
                        fontWeight = FontWeight.Medium,
                        maxLines = 1,
                        textAlign = TextAlign.Center,
                    )
                    Text(
                        text = if (lesson.isCheckpoint) {
                            stringResource(R.string.course_checkpoint)
                        } else {
                            stringResource(R.string.course_part_label, lesson.part)
                        },
                        style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp),
                        color = PompColors.InkDisabled,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                    )
                }

                PathItem.Chest -> Unit
                is PathItem.Boss -> Text(
                    text = item.milestone.title.substringBefore(' ').ifBlank { item.milestone.title },
                    style = MaterialTheme.typography.labelMedium.copy(fontSize = 12.sp),
                    color = PompColors.InkDisabled,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                )
            }
        }
    }
}

@Composable
private fun CurrentBubble() {
    Box(
        modifier = Modifier.offset(y = (-43).dp),
        contentAlignment = Alignment.Center,
    ) {
        Surface(
            color = PompColors.PaperRaised,
            shape = RoundedCornerShape(20.dp),
            border = BorderStroke(1.dp, PompColors.Cinnabar),
        ) {
            Text(
                text = stringResource(R.string.today_continue).uppercase(),
                style = MaterialTheme.typography.labelSmall.copy(fontSize = 12.sp),
                color = PompColors.CinnabarDark,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 7.dp),
            )
        }
        Canvas(
            modifier = Modifier
                .size(10.dp)
                .offset(y = 17.dp),
        ) {
            val path = Path().apply {
                moveTo(size.width / 2f, size.height)
                lineTo(0f, 0f)
                lineTo(size.width, 0f)
                close()
            }
            drawPath(path, color = PompColors.PaperRaised)
            drawLine(
                color = PompColors.Cinnabar,
                start = Offset(0f, 0f),
                end = Offset(size.width / 2f, size.height),
                strokeWidth = 1.dp.toPx(),
            )
            drawLine(
                color = PompColors.Cinnabar,
                start = Offset(size.width, 0f),
                end = Offset(size.width / 2f, size.height),
                strokeWidth = 1.dp.toPx(),
            )
        }
    }
}

@Composable
private fun PathConnector(previousX: Dp, currentX: Dp) {
    Canvas(
        modifier = Modifier
            .fillMaxWidth()
            .height(PATH_ROW_HEIGHT)
            .offset(y = (-42).dp),
    ) {
        val center = size.width / 2f
        val startX = center + previousX.toPx()
        val endX = center + currentX.toPx()
        val middleY = size.height / 2f
        val path = Path().apply {
            moveTo(startX, 0f)
            cubicTo(startX, middleY, endX, middleY, endX, size.height)
        }
        drawPath(
            path,
            color = PompColors.CourseTrail,
            style = Stroke(width = 34.dp.toPx(), cap = StrokeCap.Round),
        )
        drawPath(
            path,
            color = Color.White.copy(alpha = 0.80f),
            style = Stroke(
                width = 4.dp.toPx(),
                cap = StrokeCap.Round,
                pathEffect = PathEffect.dashPathEffect(
                    floatArrayOf(0.5.dp.toPx(), 16.dp.toPx()),
                ),
            ),
        )
    }
}

@Composable
private fun LessonNodeFace(lesson: CourseLesson) {
    val current = lesson.isCurrent
    val checkpoint = lesson.isCheckpoint
    val (background, depth, content, contentColor, border) = when {
        lesson.status == LessonStatus.DONE -> NodeStyle(
            PompColors.Jade,
            PompColors.DoneDepth,
            NodeContent.Done,
            PompColors.Paper,
            null,
        )
        lesson.access == LessonAccess.PremiumLocked || lesson.access == LessonAccess.NotReached -> NodeStyle(
            PompColors.Divider,
            PompColors.LockedDepth,
            if (checkpoint) NodeContent.Checkpoint else NodeContent.Locked,
            PompColors.InkDisabled,
            null,
        )
        checkpoint -> NodeStyle(
            PompColors.CinnabarSoft,
            PompColors.BossDepth,
            NodeContent.Checkpoint,
            PompColors.Cinnabar,
            BorderStroke(2.dp, PompColors.Cinnabar),
        )
        else -> NodeStyle(
            PompColors.Cinnabar,
            PompColors.CinnabarDark,
            NodeContent.Glyph,
            PompColors.Paper,
            null,
        )
    }

    val transition = if (current) rememberInfiniteTransition(label = "course-current-node") else null
    val ringScale = transition?.animateFloat(
        initialValue = 1f,
        targetValue = 1.25f,
        animationSpec = infiniteRepeatable(tween(1600), RepeatMode.Restart),
        label = "course-current-ring-scale",
    )?.value ?: 1f
    val ringAlpha = transition?.animateFloat(
        initialValue = 0.70f,
        targetValue = 0f,
        animationSpec = infiniteRepeatable(tween(1600), RepeatMode.Restart),
        label = "course-current-ring-alpha",
    )?.value ?: 0f

    Box(modifier = Modifier.size(CURRENT_RING_SIZE), contentAlignment = Alignment.Center) {
        if (current) {
            Surface(
                color = Color.Transparent,
                shape = CircleShape,
                border = BorderStroke(3.dp, PompColors.Cinnabar),
                modifier = Modifier.size(NODE_SIZE + 12.dp).graphicsLayer {
                    scaleX = ringScale
                    scaleY = ringScale
                    alpha = ringAlpha
                },
            ) {}
        }
        Box(Modifier.size(NODE_SIZE).offset(y = 4.dp).background(depth, CircleShape))
        Surface(
            color = background,
            shape = CircleShape,
            border = border,
            modifier = Modifier.size(NODE_SIZE),
        ) {
            Box(contentAlignment = Alignment.Center) {
                when (content) {
                    NodeContent.Done -> Icon(
                        Icons.Filled.Check,
                        contentDescription = null,
                        tint = contentColor,
                        modifier = Modifier.size(28.dp),
                    )
                    NodeContent.Locked -> Icon(
                        Icons.Filled.Lock,
                        contentDescription = null,
                        tint = contentColor,
                        modifier = Modifier.size(22.dp),
                    )
                    NodeContent.Checkpoint -> Text(
                        text = "⚑",
                        style = PompTextStyles.hanziSmall,
                        color = contentColor,
                    )
                    NodeContent.Glyph -> Text(
                        text = "学",
                        style = PompTextStyles.hanziSmall.copy(fontSize = 19.sp),
                        color = contentColor,
                    )
                }
            }
        }
    }
}

@Composable
private fun ChestNodeFace(opening: Boolean) {
    Box(modifier = Modifier.size(CURRENT_RING_SIZE), contentAlignment = Alignment.Center) {
        Box(
            Modifier
                .size(NODE_SIZE)
                .offset(y = 4.dp)
                .background(PompColors.ChestDepth, CircleShape),
        )
        Surface(
            color = PompColors.GoldSoft,
            shape = CircleShape,
            border = BorderStroke(2.dp, PompColors.Gold),
            modifier = Modifier.size(NODE_SIZE),
        ) {
            Box(contentAlignment = Alignment.Center) {
                if (opening) {
                    CircularProgressIndicator(
                        color = PompColors.Gold,
                        strokeWidth = 3.dp,
                        modifier = Modifier.size(26.dp),
                    )
                } else {
                    ChestGlyph(Modifier.size(30.dp))
                }
            }
        }
    }
}

@Composable
private fun BossNodeFace() {
    Box(modifier = Modifier.size(CURRENT_RING_SIZE), contentAlignment = Alignment.Center) {
        Box(
            Modifier
                .size(NODE_SIZE)
                .offset(y = 4.dp)
                .background(PompColors.BossDepth, CircleShape),
        )
        Surface(
            color = PompColors.CinnabarSoft,
            shape = CircleShape,
            border = BorderStroke(2.dp, PompColors.Cinnabar),
            modifier = Modifier.size(NODE_SIZE),
        ) {
            Box(contentAlignment = Alignment.Center) {
                Text("★", style = MaterialTheme.typography.headlineSmall, color = PompColors.Cinnabar)
            }
        }
    }
}

@Composable
private fun ChestGlyph(modifier: Modifier = Modifier) {
    Canvas(modifier) {
        val stroke = 2.dp.toPx()
        drawRoundRect(
            color = PompColors.Gold,
            topLeft = Offset(size.width * 0.08f, size.height * 0.30f),
            size = Size(size.width * 0.84f, size.height * 0.58f),
            cornerRadius = androidx.compose.ui.geometry.CornerRadius(5.dp.toPx()),
            style = Stroke(stroke),
        )
        drawRoundRect(
            color = PompColors.Gold,
            topLeft = Offset(size.width * 0.12f, size.height * 0.18f),
            size = Size(size.width * 0.76f, size.height * 0.28f),
            cornerRadius = androidx.compose.ui.geometry.CornerRadius(5.dp.toPx()),
            style = Stroke(stroke),
        )
        drawLine(
            color = PompColors.Gold,
            start = Offset(size.width * 0.50f, size.height * 0.32f),
            end = Offset(size.width * 0.50f, size.height * 0.84f),
            strokeWidth = stroke,
        )
        drawCircle(
            color = PompColors.Gold,
            radius = 2.5.dp.toPx(),
            center = Offset(size.width * 0.50f, size.height * 0.58f),
        )
    }
}

@Composable
private fun PathPanda(
    text: String,
    leftBubble: Boolean,
    modifier: Modifier = Modifier,
) {
    Box(modifier = modifier.size(72.dp), contentAlignment = Alignment.Center) {
        CoursePandaMascot(modifier = Modifier.size(72.dp))
        Box(
            modifier = Modifier
                .align(if (leftBubble) Alignment.TopStart else Alignment.TopEnd)
                .offset(y = (-28).dp),
        ) {
            Surface(
                color = PompColors.PaperRaised,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, PompColors.Divider),
            ) {
                Text(
                    text = text,
                    style = MaterialTheme.typography.labelSmall.copy(
                        fontSize = 11.sp,
                        lineHeight = 11.sp,
                        fontWeight = FontWeight.Medium,
                    ),
                    color = PompColors.Ink,
                    modifier = Modifier.padding(horizontal = 11.dp, vertical = 6.dp),
                    maxLines = 1,
                )
            }
            Canvas(
                modifier = Modifier
                    .size(8.dp)
                    .align(if (leftBubble) Alignment.BottomStart else Alignment.BottomEnd)
                    .offset(
                        x = if (leftBubble) 20.dp else (-20).dp,
                        y = 4.dp,
                    ),
            ) {
                val path = Path().apply {
                    moveTo(size.width / 2f, size.height)
                    lineTo(0f, size.height / 2f)
                    lineTo(size.width / 2f, 0f)
                    lineTo(size.width, size.height / 2f)
                    close()
                }
                drawPath(path, color = PompColors.PaperRaised)
                drawLine(
                    PompColors.Divider,
                    Offset(size.width / 2f, size.height),
                    Offset(size.width, size.height / 2f),
                    strokeWidth = 1.dp.toPx(),
                )
                drawLine(
                    PompColors.Divider,
                    Offset(size.width, size.height / 2f),
                    Offset(size.width / 2f, 0f),
                    strokeWidth = 1.dp.toPx(),
                )
            }
        }
    }
}

@Composable
private fun PathScenery(
    seed: Int,
    small: Boolean,
    modifier: Modifier = Modifier,
) {
    Canvas(modifier = modifier.size(if (small) 42.dp else 52.dp)) {
        val ink = PompColors.Jade.copy(alpha = 0.38f)
        val stone = PompColors.Shadow.copy(alpha = 0.70f)
        if (seed % 2 == 0) {
            val x = size.width * 0.50f
            drawLine(ink, Offset(x, size.height * 0.16f), Offset(x, size.height * 0.84f), 3.dp.toPx())
            drawLine(ink, Offset(x, size.height * 0.36f), Offset(size.width * 0.28f, size.height * 0.22f), 2.dp.toPx())
            drawLine(ink, Offset(x, size.height * 0.54f), Offset(size.width * 0.72f, size.height * 0.40f), 2.dp.toPx())
            drawOval(ink, Offset(size.width * 0.14f, size.height * 0.14f), Size(size.width * 0.28f, size.height * 0.14f))
            drawOval(ink, Offset(size.width * 0.58f, size.height * 0.34f), Size(size.width * 0.28f, size.height * 0.14f))
        } else {
            drawOval(stone, Offset(size.width * 0.10f, size.height * 0.54f), Size(size.width * 0.80f, size.height * 0.30f))
            drawOval(PompColors.Paper.copy(alpha = 0.35f), Offset(size.width * 0.30f, size.height * 0.58f), Size(size.width * 0.26f, size.height * 0.08f))
        }
    }
}

@Composable
private fun RewardChestOverlay(rewardXp: Int, onContinue: () -> Unit) {
    Surface(
        color = PompColors.Overlay.copy(alpha = 0.56f),
        modifier = Modifier.fillMaxSize(),
    ) {
        Box(contentAlignment = Alignment.Center) {
            Surface(
                color = PompColors.Paper,
                shape = RoundedCornerShape(22.dp),
                modifier = Modifier.fillMaxWidth().padding(horizontal = 28.dp),
            ) {
                Column(
                    modifier = Modifier.padding(horizontal = 22.dp, vertical = 24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    CoursePandaMascot(celebrate = true, modifier = Modifier.size(104.dp))
                    Spacer(Modifier.height(6.dp))
                    ChestGlyph(Modifier.size(58.dp))
                    Spacer(Modifier.height(12.dp))
                    Text(
                        text = stringResource(R.string.course_chest_reward, rewardXp),
                        style = MaterialTheme.typography.headlineSmall,
                        color = PompColors.Gold,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(Modifier.height(18.dp))
                    Surface(
                        color = PompColors.Cinnabar,
                        shape = RoundedCornerShape(14.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(min = 50.dp)
                            .clickable(onClick = onContinue),
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Text(
                                text = stringResource(R.string.action_continue),
                                style = MaterialTheme.typography.labelLarge,
                                color = PompColors.Paper,
                                fontWeight = FontWeight.SemiBold,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun CourseErrorBlock(messageRes: Int, onRetry: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            stringResource(messageRes),
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(16.dp))
        androidx.compose.material3.OutlinedButton(
            onClick = onRetry,
            modifier = Modifier.heightIn(min = 48.dp),
            shape = RoundedCornerShape(14.dp),
        ) {
            Text(
                stringResource(R.string.action_retry),
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.CinnabarDark,
            )
        }
    }
}

@Composable
private fun CourseLesson.stateLabel(): String = when (access) {
    LessonAccess.Open -> stringResource(R.string.course_part_label, part)
    LessonAccess.HalfPreview -> stringResource(R.string.today_reason_preview)
    LessonAccess.PremiumLocked -> stringResource(R.string.today_reason_premium)
    LessonAccess.NotReached -> stringResource(R.string.today_reason_not_reached)
}

private data class NodeStyle(
    val background: Color,
    val depth: Color,
    val content: NodeContent,
    val contentColor: Color,
    val border: BorderStroke?,
)

private enum class NodeContent { Done, Locked, Checkpoint, Glyph }

private sealed interface PathItem {
    data class Lesson(val lesson: CourseLesson) : PathItem
    data object Chest : PathItem
    data class Boss(val milestone: CourseMilestone) : PathItem
}

private sealed interface CourseRow {
    data class Unit(val unit: CourseUnit) : CourseRow
    data class Path(
        val item: PathItem,
        val unitIndex: Int,
        val nodeIndex: Int,
        val previousNodeIndex: Int?,
        val pandaPromptIndex: Int?,
    ) : CourseRow
}

private fun CourseMap.toRows(): List<CourseRow> = buildList {
    var mascotCount = 0
    units.forEachIndexed { unitIndex, unit ->
        add(CourseRow.Unit(unit))
        val nodes = unit.lessons
            .map { lesson -> PathItem.Lesson(lesson) as PathItem }
            .toMutableList()
        if (!unit.isLocked && unit.milestone != null) {
            nodes.add(minOf(3, nodes.size), PathItem.Chest)
            nodes.add(PathItem.Boss(unit.milestone))
        }
        nodes.forEachIndexed { nodeIndex, item ->
            val pandaPrompt = if (
                item is PathItem.Lesson &&
                !item.lesson.isCurrent &&
                nodeIndex % 5 == 2
            ) {
                mascotCount++ % 4
            } else {
                null
            }
            add(
                CourseRow.Path(
                    item = item,
                    unitIndex = unitIndex,
                    nodeIndex = nodeIndex,
                    previousNodeIndex = if (nodeIndex > 0) nodeIndex - 1 else null,
                    pandaPromptIndex = pandaPrompt,
                )
            )
        }
    }
}
