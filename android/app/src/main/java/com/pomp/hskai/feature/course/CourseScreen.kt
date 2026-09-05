package com.pomp.hskai.feature.course

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Diamond
import androidx.compose.material.icons.filled.LocalFireDepartment
import androidx.compose.material.icons.filled.Lock
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
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.domain.model.CourseLesson
import com.pomp.hskai.domain.model.CourseMap
import com.pomp.hskai.domain.model.LessonAccess
import com.pomp.hskai.domain.model.LessonStatus
import com.pomp.hskai.feature.limit.LimitGate
import com.pomp.hskai.feature.limit.SectionLimitBlock

/**
 * Native rendering of the Mini App course shell. The Mini App is the visual
 * source of truth: same warm paper, compact top row, dark unit banner and
 * 64dp path nodes with a 4dp coloured depth layer.
 */
@Composable
fun CourseScreen(
    state: CourseUiState,
    dailyGoal: Int,
    limit: LimitGate,
    onLesson: (CourseLesson) -> Unit,
    onOpenGoal: () -> Unit,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val map = state.map
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        when {
            state.isLoading && map == null -> Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center,
            ) {
                CircularProgressIndicator(color = PompColors.Cinnabar)
            }

            map == null -> CourseErrorBlock(
                messageRes = state.error?.messageRes ?: R.string.error_unknown,
                onRetry = onRetry,
            )

            else -> {
                val rows = remember(map) { map.toRows() }
                val listState = rememberLazyListState()

                LaunchedEffect(map.currentLesson?.order) {
                    val index = rows.indexOfFirst {
                        it is CourseRow.Lesson && it.lesson.isCurrent
                    }
                    if (index >= 0) {
                        listState.scrollToItem(index = index, scrollOffset = -160)
                    }
                }

                Column(Modifier.fillMaxSize()) {
                    CourseHeader(
                        map = map,
                        dailyGoal = dailyGoal,
                        onOpenGoal = onOpenGoal,
                    )
                    if (state.isStale) {
                        StaleBanner()
                    }
                    LazyColumn(
                        state = listState,
                        modifier = Modifier
                            .fillMaxWidth()
                            .weight(1f),
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(
                            horizontal = 16.dp,
                            vertical = 8.dp,
                        ),
                    ) {
                        itemsIndexed(rows) { _, row ->
                            when (row) {
                                is CourseRow.Unit -> UnitHeader(row.title)
                                is CourseRow.Lesson -> PathNode(
                                    lesson = row.lesson,
                                    slot = row.slot,
                                    onLesson = onLesson,
                                )

                                is CourseRow.LockedLesson -> LockedLessonCard(
                                    lesson = row.lesson,
                                    limit = limit,
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

/** Mini App `.htop`: compact level pill + streak + XP + daily goal. */
@Composable
private fun CourseHeader(
    map: CourseMap,
    dailyGoal: Int,
    onOpenGoal: () -> Unit,
) {
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
                    text = map.level.uppercase(),
                    style = MaterialTheme.typography.labelLarge,
                    color = PompColors.Paper,
                )
            }
        }

        Spacer(Modifier.weight(1f))

        StatChip(
            icon = Icons.Filled.LocalFireDepartment,
            tint = PompColors.Flame,
            value = map.progress.streak.toString(),
            label = stringResource(R.string.today_streak),
        )
        Spacer(Modifier.width(8.dp))
        StatChip(
            icon = Icons.Filled.Diamond,
            tint = PompColors.Gold,
            value = map.progress.xp.toString(),
            label = stringResource(R.string.today_xp),
        )
        Spacer(Modifier.width(8.dp))
        GoalRing(
            dailyXp = map.progress.dailyXp,
            dailyGoal = dailyGoal,
            onClick = onOpenGoal,
        )
    }
}

@Composable
private fun StatChip(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    tint: androidx.compose.ui.graphics.Color,
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
                text = value,
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.Ink,
            )
        }
    }
}

@Composable
fun GoalRing(
    dailyXp: Int,
    dailyGoal: Int,
    onClick: () -> Unit,
    size: androidx.compose.ui.unit.Dp = 38.dp,
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
        androidx.compose.foundation.Canvas(Modifier.fillMaxSize()) {
            val stroke = 4.dp.toPx()
            val inset = stroke / 2
            val arcSize = androidx.compose.ui.geometry.Size(
                this.size.width - stroke,
                this.size.height - stroke,
            )
            drawArc(
                color = PompColors.Divider,
                startAngle = 0f,
                sweepAngle = 360f,
                useCenter = false,
                topLeft = androidx.compose.ui.geometry.Offset(inset, inset),
                size = arcSize,
                style = Stroke(width = stroke),
            )
            if (fraction > 0f) {
                drawArc(
                    color = if (complete) PompColors.Gold else PompColors.Cinnabar,
                    startAngle = -90f,
                    sweepAngle = 360f * fraction,
                    useCenter = false,
                    topLeft = androidx.compose.ui.geometry.Offset(inset, inset),
                    size = arcSize,
                    style = Stroke(width = stroke, cap = StrokeCap.Round),
                )
            }
        }
        Icon(
            imageVector = if (complete) Icons.Filled.Check else Icons.Filled.TrackChanges,
            contentDescription = null,
            tint = if (complete) PompColors.Gold else PompColors.Cinnabar,
            modifier = Modifier.size(size * 0.42f),
        )
    }
}

@Composable
private fun StaleBanner() {
    Surface(
        color = PompColors.GoldSoft,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp),
    ) {
        Text(
            text = stringResource(R.string.today_stale),
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.Ink,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
        )
    }
}

/** Mini App `.uban`: dark rounded unit banner, not a floating red title. */
@Composable
private fun UnitHeader(title: String) {
    Surface(
        color = PompColors.Ink,
        shape = RoundedCornerShape(14.dp),
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 8.dp, bottom = 8.dp),
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.titleMedium,
            color = PompColors.Paper,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 11.dp),
            maxLines = 2,
        )
    }
}

/** Horizontal offsets mirror the Mini App's alternating path positions. */
private val PATH_SLOTS = listOf(0f, 0.55f, 0.85f, 0.55f, 0f, -0.55f, -0.85f, -0.55f)
private val PATH_SWING = 84.dp
private val NODE_SIZE = 64.dp
private val CURRENT_RING_SIZE = 76.dp

@Composable
private fun PathNode(
    lesson: CourseLesson,
    slot: Int,
    onLesson: (CourseLesson) -> Unit,
) {
    val clickable = lesson.access == LessonAccess.Open ||
        lesson.access == LessonAccess.HalfPreview
    val label = lesson.stateLabel()
    val offsetX = PATH_SWING * PATH_SLOTS[slot % PATH_SLOTS.size]

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        if (lesson.isCurrent && clickable) {
            Surface(
                color = PompColors.PaperRaised,
                shape = RoundedCornerShape(20.dp),
                border = BorderStroke(1.dp, PompColors.Cinnabar),
                modifier = Modifier.offset(x = offsetX),
            ) {
                Text(
                    text = stringResource(R.string.today_continue).uppercase(),
                    style = MaterialTheme.typography.labelLarge,
                    color = PompColors.CinnabarDark,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 7.dp),
                )
            }
            Spacer(Modifier.height(6.dp))
        }

        Box(
            modifier = Modifier
                .offset(x = offsetX)
                .size(CURRENT_RING_SIZE)
                .then(if (clickable) Modifier.clickable { onLesson(lesson) } else Modifier)
                .semantics { contentDescription = label },
            contentAlignment = Alignment.Center,
        ) {
            NodeFace(lesson)
        }

        Text(
            text = when {
                lesson.isCheckpoint -> stringResource(R.string.course_checkpoint)
                lesson.hanziPreview.isNotBlank() -> lesson.hanziPreview
                else -> stringResource(R.string.course_part_label, lesson.part)
            },
            style = MaterialTheme.typography.bodyMedium,
            color = if (clickable) PompColors.InkSecondary else PompColors.InkDisabled,
            maxLines = 1,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .offset(x = offsetX)
                .padding(top = 4.dp),
        )
        Text(
            text = lesson.subtitle,
            style = MaterialTheme.typography.labelSmall,
            color = if (clickable) PompColors.InkSecondary else PompColors.InkDisabled,
            maxLines = 1,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .offset(x = offsetX)
                .padding(bottom = 8.dp),
        )
    }
}

@Composable
private fun NodeFace(lesson: CourseLesson) {
    val current = lesson.isCurrent
    val (background, depth, content, contentColor) = when {
        lesson.status == LessonStatus.DONE -> Quad(
            PompColors.Jade,
            PompColors.NodeDoneDepth,
            NodeContent.Done,
            PompColors.Paper,
        )
        lesson.access == LessonAccess.PremiumLocked -> Quad(
            PompColors.Divider,
            PompColors.NodeLockedDepth,
            NodeContent.Premium,
            PompColors.InkDisabled,
        )
        lesson.access == LessonAccess.NotReached -> Quad(
            PompColors.Divider,
            PompColors.NodeLockedDepth,
            NodeContent.Locked,
            PompColors.InkDisabled,
        )
        lesson.isCheckpoint -> Quad(
            PompColors.CinnabarSoft,
            PompColors.NodeBossDepth,
            NodeContent.Checkpoint,
            PompColors.Cinnabar,
        )
        else -> Quad(
            PompColors.Cinnabar,
            PompColors.CinnabarDark,
            NodeContent.Glyph,
            PompColors.Paper,
        )
    }

    Box(modifier = Modifier.size(CURRENT_RING_SIZE), contentAlignment = Alignment.Center) {
        if (current) {
            Surface(
                color = androidx.compose.ui.graphics.Color.Transparent,
                shape = CircleShape,
                border = BorderStroke(3.dp, PompColors.Cinnabar),
                modifier = Modifier.size(CURRENT_RING_SIZE),
            ) {}
        }

        Box(
            modifier = Modifier
                .size(NODE_SIZE)
                .offset(y = 4.dp)
                .background(depth, CircleShape),
        )
        Box(
            modifier = Modifier
                .size(NODE_SIZE)
                .clip(CircleShape)
                .background(background),
            contentAlignment = Alignment.Center,
        ) {
            when (content) {
                NodeContent.Done -> Icon(
                    Icons.Filled.Check,
                    contentDescription = null,
                    tint = contentColor,
                    modifier = Modifier.size(28.dp),
                )

                NodeContent.Locked, NodeContent.Premium -> Icon(
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
                    text = lesson.hanziPreview.take(1).ifBlank { lesson.order.toString() },
                    style = PompTextStyles.hanziSmall,
                    color = contentColor,
                )
            }
        }
    }
}

private data class Quad(
    val background: androidx.compose.ui.graphics.Color,
    val depth: androidx.compose.ui.graphics.Color,
    val content: NodeContent,
    val contentColor: androidx.compose.ui.graphics.Color,
)

private enum class NodeContent { Done, Locked, Premium, Checkpoint, Glyph }

@Composable
private fun LockedLessonCard(
    lesson: CourseLesson,
    limit: LimitGate,
) {
    SectionLimitBlock(
        sectionTitle = stringResource(R.string.course_lesson_label, lesson.sourceLesson) +
            lesson.hanziPreview.takeIf { it.isNotBlank() }?.let { " · $it" }.orEmpty(),
        limit = limit,
        modifier = Modifier.padding(vertical = 10.dp),
        reason = lesson.stateLabel(),
        resetAt = null,
    )
}

@Composable
private fun CourseErrorBlock(messageRes: Int, onRetry: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = stringResource(messageRes),
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
                text = stringResource(R.string.action_retry),
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

private sealed interface CourseRow {
    data class Unit(val title: String) : CourseRow
    data class Lesson(val lesson: CourseLesson, val slot: Int) : CourseRow
    data class LockedLesson(val lesson: CourseLesson) : CourseRow
}

private fun CourseMap.toRows(): List<CourseRow> = buildList {
    var slot = 0
    units.forEach { unit ->
        add(CourseRow.Unit(unit.title))
        unit.lessons.forEach { lesson ->
            add(CourseRow.Lesson(lesson, slot))
            slot += 1
            if (lesson.access == LessonAccess.PremiumLocked && lesson.part == 1) {
                add(CourseRow.LockedLesson(lesson))
            }
        }
    }
}
