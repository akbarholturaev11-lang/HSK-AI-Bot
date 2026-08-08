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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.domain.model.CourseLesson
import com.pomp.hskai.domain.model.CourseMap
import com.pomp.hskai.domain.model.LessonAccess
import com.pomp.hskai.domain.model.LessonStatus

/**
 * The learning path.
 *
 * Node state is never carried by colour alone: every node also has a glyph and
 * a text label, so the screen still reads correctly without colour vision.
 */
@Composable
fun CourseScreen(
    state: CourseUiState,
    onLesson: (CourseLesson) -> Unit,
    modifier: Modifier = Modifier,
) {
    val map = state.map
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        if (map == null) {
            Column(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                CircularProgressIndicator(color = PompColors.Cinnabar)
            }
            return@Surface
        }

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

        LazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize(),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(
                horizontal = 20.dp,
                vertical = 20.dp,
            ),
        ) {
            item {
                CourseHeader(map)
                Spacer(Modifier.height(16.dp))
            }
            itemsIndexed(rows) { _, row ->
                when (row) {
                    is CourseRow.Unit -> UnitHeader(row.title)
                    is CourseRow.Lesson -> LessonRow(row.lesson, onLesson)
                }
            }
        }
    }
}

@Composable
private fun CourseHeader(map: CourseMap) {
    Column {
        Text(
            text = map.level.uppercase(),
            style = MaterialTheme.typography.headlineMedium,
            color = PompColors.Ink,
        )
        Text(
            text = stringResource(
                R.string.course_progress,
                map.progress.completedLessons,
                map.totalLessons,
            ),
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.InkSecondary,
        )
    }
}

@Composable
private fun UnitHeader(title: String) {
    Text(
        text = title,
        style = MaterialTheme.typography.titleMedium,
        color = PompColors.CinnabarDark,
        modifier = Modifier.padding(top = 20.dp, bottom = 8.dp),
    )
}

@Composable
private fun LessonRow(lesson: CourseLesson, onLesson: (CourseLesson) -> Unit) {
    val clickable = lesson.access == LessonAccess.Open ||
        lesson.access == LessonAccess.HalfPreview
    val label = lesson.stateLabel()

    Surface(
        color = if (lesson.isCurrent) PompColors.CinnabarSoft else PompColors.PaperRaised,
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(
            1.dp,
            if (lesson.isCurrent) PompColors.Cinnabar else PompColors.Divider,
        ),
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
            .heightIn(min = 64.dp)
            .then(
                if (clickable) {
                    Modifier.clickable { onLesson(lesson) }
                } else {
                    Modifier
                }
            )
            .semantics { contentDescription = label },
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            NodeGlyph(lesson)
            Spacer(Modifier.size(14.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = if (lesson.isCheckpoint) {
                        stringResource(R.string.course_checkpoint)
                    } else {
                        lesson.hanziPreview.ifBlank {
                            stringResource(R.string.course_part_label, lesson.part)
                        }
                    },
                    style = MaterialTheme.typography.titleMedium,
                    color = if (lesson.access == LessonAccess.Open ||
                        lesson.access == LessonAccess.HalfPreview
                    ) {
                        PompColors.Ink
                    } else {
                        PompColors.InkDisabled
                    },
                )
                Text(
                    text = lesson.subtitle,
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                )
            }
        }
    }
}

@Composable
private fun NodeGlyph(lesson: CourseLesson) {
    val (background, glyph) = when {
        lesson.status == LessonStatus.DONE -> PompColors.Jade to "✓"
        lesson.access == LessonAccess.PremiumLocked -> PompColors.Gold to "★"
        lesson.access == LessonAccess.NotReached -> PompColors.Locked to "•"
        lesson.isCheckpoint -> PompColors.Gold to "⚑"
        else -> PompColors.Cinnabar to lesson.order.toString()
    }
    Box(
        modifier = Modifier
            .size(40.dp)
            .background(background, CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = glyph,
            style = MaterialTheme.typography.labelLarge,
            color = PompColors.Paper,
        )
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
    data class Lesson(val lesson: CourseLesson) : CourseRow
}

private fun CourseMap.toRows(): List<CourseRow> = buildList {
    units.forEach { unit ->
        add(CourseRow.Unit(unit.title))
        unit.lessons.forEach { add(CourseRow.Lesson(it)) }
    }
}
