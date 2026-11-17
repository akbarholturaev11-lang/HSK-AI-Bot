package com.pomp.hskai.feature.course

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.domain.model.CourseLesson
import com.pomp.hskai.feature.assistant.AssistantModalBottomSheet as ModalBottomSheet
import kotlin.math.floor

/**
 * The PWA/Mini App `openLessonSheet` for the part that follows a just
 * completed one: "Lesson · Part", the part's hanzi and pinyin (each on one
 * line), its stages and one Continue action. Access is still decided by the
 * server when the part opens.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun NextPartSheet(
    lesson: CourseLesson,
    onContinue: () -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val lessonLabel = stringResource(R.string.hsk_course_lesson_flow_lesson_prefix)
        .replace("{n}", lesson.sourceLesson.toString())
    val partLabel = if (lesson.isCheckpoint) {
        stringResource(R.string.hsk_course_part_sections_r)
    } else {
        stringResource(R.string.hsk_course_lesson_flow_part_prefix).replace("{n}", lesson.part.toString())
    }
    // Same stage list as the web `partSecs(l)`.
    val stages = if (lesson.isCheckpoint) {
        listOf(
            R.string.hsk_course_part_sections_r,
            R.string.hsk_course_part_sections_d,
            R.string.hsk_course_part_sections_s,
        )
    } else {
        listOf(
            R.string.hsk_course_part_sections_w,
            R.string.hsk_course_part_sections_p,
            R.string.hsk_course_part_sections_s,
            R.string.hsk_course_part_sections_x,
        )
    }.map { stringResource(it) }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        modifier = Modifier.testTag("next-part-sheet"),
        sheetState = sheetState,
        containerColor = PompColors.PaperRaised,
        showAssistant = false,
    ) {
        Column(
            Modifier.fillMaxWidth().verticalScroll(rememberScrollState())
                .padding(start = 18.dp, end = 18.dp, bottom = 16.dp),
        ) {
            Box(Modifier.fillMaxWidth()) {
                Column(
                    Modifier.fillMaxWidth().padding(horizontal = 40.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    if (lesson.sourceLesson > 0) {
                        Text(
                            text = "$lessonLabel · $partLabel",
                            color = PompColors.CinnabarInk,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Medium,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.semantics { heading() },
                        )
                    }
                }
                IconButton(onClick = onDismiss, modifier = Modifier.align(Alignment.TopEnd)) {
                    Icon(
                        Icons.Filled.Close,
                        contentDescription = stringResource(R.string.hsk_common_action_close),
                        tint = PompColors.Ink,
                    )
                }
            }
            OneLineFitText(
                text = lesson.hanziPreview,
                style = PompTextStyles.hanziMedium.copy(color = PompColors.Ink, lineHeight = 1.2.em),
                maxSize = 34.sp,
                minSize = 14.sp,
            )
            if (lesson.pinyinPreview.isNotBlank()) {
                OneLineFitText(
                    text = lesson.pinyinPreview,
                    style = TextStyle(color = PompColors.CinnabarInk, fontWeight = FontWeight.Medium),
                    maxSize = 15.sp,
                    minSize = 10.sp,
                    modifier = Modifier.padding(top = 5.dp),
                )
            }
            Spacer(Modifier.height(14.dp))
            Row(
                Modifier.fillMaxWidth().padding(horizontal = 2.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    "${stages.size} ${stringResource(R.string.hsk_course_stage)}",
                    color = PompColors.InkSecondary,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Medium,
                )
                Text(
                    "0 / ${stages.size} ${stringResource(R.string.hsk_course_complete_of)}",
                    color = PompColors.InkSecondary,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Medium,
                )
            }
            Spacer(Modifier.height(8.dp))
            stages.forEachIndexed { index, title ->
                NextPartStage(number = index + 1, title = title, current = index == 0)
                Spacer(Modifier.height(7.dp))
            }
            Spacer(Modifier.height(7.dp))
            Button(
                onClick = onContinue,
                modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp).testTag("next-part-continue"),
                colors = ButtonDefaults.buttonColors(
                    containerColor = PompColors.Cinnabar,
                    contentColor = PompColors.OnCinnabar,
                ),
                shape = RoundedCornerShape(14.dp),
            ) {
                Icon(Icons.Filled.PlayArrow, contentDescription = null, modifier = Modifier.size(20.dp))
                Spacer(Modifier.width(8.dp))
                Text(stringResource(R.string.hsk_course_cont), fontSize = 16.sp, fontWeight = FontWeight.Medium)
            }
        }
    }
}

@Composable
private fun NextPartStage(number: Int, title: String, current: Boolean) {
    val shape = RoundedCornerShape(12.dp)
    Row(
        Modifier.fillMaxWidth()
            .background(if (current) PompColors.CinnabarSoft else PompColors.CardSurface, shape)
            .border(BorderStroke(1.dp, if (current) PompColors.Cinnabar else PompColors.Divider), shape)
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            Modifier.size(26.dp).background(
                if (current) PompColors.Cinnabar else PompColors.Paper,
                RoundedCornerShape(8.dp),
            ),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                if (current) Icons.Filled.PlayArrow else Icons.Filled.Lock,
                contentDescription = null,
                tint = if (current) PompColors.OnCinnabar else PompColors.InkDisabled,
                modifier = Modifier.size(15.dp),
            )
        }
        Spacer(Modifier.width(11.dp))
        Text(
            "$number. $title",
            color = if (current) PompColors.CinnabarInk else PompColors.InkDisabled,
            fontSize = 14.sp,
            fontWeight = if (current) FontWeight.Medium else FontWeight.Normal,
            modifier = Modifier.weight(1f),
        )
    }
}

/**
 * One centred line that shrinks from [maxSize] until it fits the width and
 * never grows above it (web `fitOneLine`). Drawing waits for the final size.
 */
@Composable
private fun OneLineFitText(
    text: String,
    style: TextStyle,
    maxSize: TextUnit,
    minSize: TextUnit,
    modifier: Modifier = Modifier,
) {
    var size by remember(text, maxSize) { mutableStateOf(maxSize) }
    var settled by remember(text, maxSize) { mutableStateOf(false) }
    Text(
        text = text,
        style = style.copy(fontSize = size),
        maxLines = 1,
        softWrap = false,
        overflow = TextOverflow.Clip,
        textAlign = TextAlign.Center,
        onTextLayout = { layout ->
            val available = layout.layoutInput.constraints.maxWidth.toFloat()
            val needed = layout.multiParagraph.width
            if (layout.didOverflowWidth && size.value > minSize.value && needed > 0f) {
                val upper = (size.value - 0.5f).coerceAtLeast(minSize.value)
                size = (floor(size.value * available / needed * 2f) / 2f)
                    .coerceIn(minSize.value, upper).sp
            } else {
                settled = true
            }
        },
        modifier = modifier.fillMaxWidth().drawWithContent { if (settled) drawContent() },
    )
}
