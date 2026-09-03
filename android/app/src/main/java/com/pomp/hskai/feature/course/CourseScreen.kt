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

/**
 * The learning path, laid out like the Mini App: a status header, then a
 * winding column of nodes with the current one calling for the next action.
 *
 * Node state is never carried by colour alone: every node also has a glyph and
 * a content description, so the screen still reads correctly without colour
 * vision.
 */
@Composable
fun CourseScreen(
    state: CourseUiState,
    dailyGoal: Int,
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

                // Bring the current node into a useful position on first composition.
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
                            horizontal = 20.dp,
                            vertical = 12.dp,
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

                                is CourseRow.LockedLesson -> LockedLessonCard(row.lesson)
                            }
                        }
                    }
                }
            }
        }
    }
}

/**
 * Level, streak, XP and the daily-goal ring — the Mini App's course header.
 */
@Composable
private fun CourseHeader(
    map: CourseMap,
    dailyGoal: Int,
    onOpenGoal: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Surface(color = PompColors.Cinnabar, shape = RoundedCornerShape(999.dp)) {
            Row(
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(
                    Icons.Filled.Bolt,
                    contentDescription = null,
                    tint = PompColors.Paper,
                    modifier = Modifier.size(16.dp),
                )
                Spacer(Modifier.width(6.dp))
                Text(
                    text = map.level.uppercase(),
                    style = MaterialTheme.typography.titleMedium,
                    color = PompColors.Paper,
                )
            }
        }

        Spacer(Modifier.weight(1f))

        StatChip(
            icon = Icons.Filled.LocalFireDepartment,
            tint = PompColors.Cinnabar,
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
        shape = RoundedCornerShape(999.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
    ) {
        Row(
            modifier = Modifier
                .padding(horizontal = 12.dp, vertical = 7.dp)
                .semantics { contentDescription = "$label: $value" },
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(16.dp))
            Spacer(Modifier.width(5.dp))
            Text(
                text = value,
                style = MaterialTheme.typography.titleSmall,
                color = PompColors.Ink,
            )
        }
    }
}

/**
 * Progress towards today's XP target. The goal is a personal display setting,
 * so a full ring is encouragement, never an entitlement.
 */
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
            .padding(horizontal = 20.dp),
    ) {
        Text(
            text = stringResource(R.string.today_stale),
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.Ink,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
        )
    }
}

@Composable
private fun UnitHeader(title: String) {
    Text(
        text = title,
        style = MaterialTheme.typography.titleMedium,
        color = PompColors.CinnabarDark,
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 20.dp, bottom = 4.dp),
        textAlign = TextAlign.Center,
    )
}

/** Horizontal offsets of the winding path, in units of [PATH_SWING]. */
private val PATH_SLOTS = listOf(0f, 0.55f, 0.85f, 0.55f, 0f, -0.55f, -0.85f, -0.55f)
private val PATH_SWING = 84.dp
private val NODE_SIZE = 74.dp

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
                shape = RoundedCornerShape(999.dp),
                border = BorderStroke(2.dp, PompColors.Cinnabar),
                modifier = Modifier.offset(x = offsetX),
            ) {
                Text(
                    text = stringResource(R.string.today_continue).uppercase(),
                    style = MaterialTheme.typography.labelLarge,
                    color = PompColors.CinnabarDark,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                )
            }
            Spacer(Modifier.height(6.dp))
        }

        Box(
            modifier = Modifier
                .offset(x = offsetX)
                .size(NODE_SIZE)
                .clip(CircleShape)
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
            color = if (clickable) PompColors.Ink else PompColors.InkDisabled,
            maxLines = 1,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .offset(x = offsetX)
                .padding(top = 6.dp),
        )
        Text(
            text = lesson.subtitle,
            style = MaterialTheme.typography.labelSmall,
            color = PompColors.InkSecondary,
            maxLines = 1,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .offset(x = offsetX)
                .padding(bottom = 10.dp),
        )
    }
}

@Composable
private fun NodeFace(lesson: CourseLesson) {
    val ring = if (lesson.isCurrent) PompColors.Cinnabar else null
    val (background, content) = when {
        lesson.status == LessonStatus.DONE -> PompColors.Jade to NodeContent.Done
        lesson.access == LessonAccess.PremiumLocked -> PompColors.Locked to NodeContent.Premium
        lesson.access == LessonAccess.NotReached -> PompColors.Locked to NodeContent.Locked
        lesson.isCheckpoint -> PompColors.Gold to NodeContent.Checkpoint
        else -> PompColors.Cinnabar to NodeContent.Glyph
    }

    Box(contentAlignment = Alignment.Center) {
        if (ring != null) {
            Box(
                modifier = Modifier
                    .size(NODE_SIZE)
                    .background(PompColors.CinnabarSoft, CircleShape),
            )
        }
        Box(
            modifier = Modifier
                .size(NODE_SIZE - 10.dp)
                .background(background, CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            when (content) {
                NodeContent.Done -> Icon(
                    Icons.Filled.Check,
                    contentDescription = null,
                    tint = PompColors.Paper,
                    modifier = Modifier.size(28.dp),
                )

                NodeContent.Locked, NodeContent.Premium -> Icon(
                    Icons.Filled.Lock,
                    contentDescription = null,
                    tint = PompColors.Paper,
                    modifier = Modifier.size(22.dp),
                )

                NodeContent.Checkpoint -> Text(
                    text = "⚑",
                    style = PompTextStyles.hanziSmall,
                    color = PompColors.Paper,
                )

                NodeContent.Glyph -> Text(
                    text = lesson.hanziPreview.take(1).ifBlank { lesson.order.toString() },
                    style = PompTextStyles.hanziSmall,
                    color = PompColors.Paper,
                )
            }
        }
    }
}

private enum class NodeContent { Done, Locked, Premium, Checkpoint, Glyph }

/**
 * The wide card the Mini App shows for the next textbook lesson that is still
 * closed. It states the lock; it never offers a purchase, because the Android
 * subscription flow does not exist yet.
 */
@Composable
private fun LockedLessonCard(lesson: CourseLesson) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 10.dp)
            .heightIn(min = 60.dp),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    text = stringResource(
                        R.string.course_lesson_label,
                        lesson.sourceLesson,
                    ) + lesson.hanziPreview.takeIf { it.isNotBlank() }
                        ?.let { " · $it" }.orEmpty(),
                    style = MaterialTheme.typography.titleMedium,
                    color = PompColors.Ink,
                    maxLines = 1,
                )
                Text(
                    text = lesson.stateLabel(),
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                )
            }
            Icon(
                Icons.Filled.Lock,
                contentDescription = null,
                tint = PompColors.InkDisabled,
                modifier = Modifier.size(20.dp),
            )
        }
    }
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

    /** [slot] positions the node on the winding path. */
    data class Lesson(val lesson: CourseLesson, val slot: Int) : CourseRow

    data class LockedLesson(val lesson: CourseLesson) : CourseRow
}

/**
 * Flattens the map into path rows.
 *
 * A premium-locked node keeps its place on the path and additionally gets the
 * wide card the Mini App shows, so the learner sees both the shape of the path
 * and a readable reason.
 */
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
