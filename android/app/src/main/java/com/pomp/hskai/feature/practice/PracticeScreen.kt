package com.pomp.hskai.feature.practice

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.TrackChanges
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material.icons.filled.WorkspacePremium
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.data.api.MistakeReviewAnswerResponse
import com.pomp.hskai.data.api.MistakeReviewQuestionDto
import com.pomp.hskai.data.api.PracticeQuestionDto
import com.pomp.hskai.feature.limit.LimitGate
import com.pomp.hskai.feature.limit.SectionLimitBlock

@Composable
fun PracticeScreen(
    state: PracticeUiState,
    level: String,
    language: String,
    limit: LimitGate,
    onWatchAd: (feature: String) -> Unit,
    onOpenDictionary: () -> Unit,
    onStartPractice: (PracticeToolSpec, String, String) -> Unit,
    onSelectPracticeOption: (Int) -> Unit,
    onAdvancePractice: (String) -> Unit,
    onResetPractice: () -> Unit,
    onStartMistakeReview: () -> Unit,
    onAnswerReview: (Int) -> Unit,
    onAdvanceReview: () -> Unit,
    onResetReview: () -> Unit,
    onStartExam: (String) -> Unit,
    onSelectExamOption: (Int) -> Unit,
    onAdvanceExam: (String) -> Unit,
    onResetExam: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        when {
            state.result != null -> PracticeSummary(
                state = state,
                onDone = onResetPractice,
            )

            state.reviewResult != null -> ReviewSummary(
                state = state,
                onDone = onResetReview,
            )

            state.examResult != null -> ExamSummary(
                state = state,
                onDone = onResetExam,
            )

            state.isExamRunning -> ExamRun(
                state = state,
                language = language,
                onSelect = onSelectExamOption,
                onAdvance = onAdvanceExam,
                onCancel = onResetExam,
            )

            state.isPracticeRunning -> PracticeRun(
                state = state,
                language = language,
                onSelect = onSelectPracticeOption,
                onAdvance = onAdvancePractice,
                onCancel = onResetPractice,
            )

            state.isReviewRunning -> ReviewRun(
                state = state,
                onSelect = onAnswerReview,
                onAdvance = onAdvanceReview,
                onCancel = onResetReview,
            )

            else -> PracticeHome(
                state = state,
                level = level,
                language = language,
                limit = limit,
                onWatchAd = onWatchAd,
                onOpenDictionary = onOpenDictionary,
                onStartPractice = onStartPractice,
                onStartMistakeReview = onStartMistakeReview,
                onStartExam = onStartExam,
            )
        }
    }
}

/**
 * The Mini App shows five rows here, not nine. It does not list the raw
 * practice skills the server offers: "Ieroglif tanish" and "Test markazi" are
 * doors, and the individual drills live behind them. This screen follows that
 * shape so a learner who moves between the two clients sees one product.
 */
private enum class PracticeGroup { RECOGNITION, TEST }

/** The tile colours the Mini App gives each row. */
private data class RowTint(val background: Color, val foreground: Color)

private val TintAmber = RowTint(PompColors.TileAmberSoft, PompColors.TileAmberInk)
private val TintBlue = RowTint(PompColors.TileBlueSoft, PompColors.TileBlueInk)
private val TintJade = RowTint(PompColors.JadeSoft, PompColors.Jade)
private val TintCinnabar = RowTint(PompColors.CinnabarSoft, PompColors.Cinnabar)

@Composable
private fun PracticeHome(
    state: PracticeUiState,
    level: String,
    language: String,
    limit: LimitGate,
    onWatchAd: (feature: String) -> Unit,
    onOpenDictionary: () -> Unit,
    onStartPractice: (PracticeToolSpec, String, String) -> Unit,
    onStartMistakeReview: () -> Unit,
    onStartExam: (String) -> Unit,
) {
    // Which door is open, if any. Kept here rather than in the ViewModel: it
    // is where the learner is looking, not something the session depends on.
    var openGroup by rememberSaveable { mutableStateOf<PracticeGroup?>(null) }

    // The drills behind "Ieroglif tanish". Reading and writing practice both
    // come down to picking the right characters, so they share one door.
    val recognitionTools = remember {
        listOf(
            PracticeToolSpec(
                mode = "training",
                skill = "characters",
                titleRes = R.string.practice_characters_title,
                bodyRes = R.string.practice_characters_body,
                glyph = "字",
            ),
            PracticeToolSpec(
                mode = "training",
                skill = "pinyin",
                titleRes = R.string.practice_pinyin_title,
                bodyRes = R.string.practice_pinyin_body,
                glyph = "pin",
            ),
            PracticeToolSpec(
                mode = "training",
                skill = "writing",
                titleRes = R.string.practice_writing_title,
                bodyRes = R.string.practice_writing_body,
                glyph = "句",
            ),
            PracticeToolSpec(
                mode = "training",
                skill = "listening",
                titleRes = R.string.practice_listening_title,
                bodyRes = R.string.practice_listening_body,
                glyph = "听",
            ),
        )
    }
    val pronunciationTool = remember {
        PracticeToolSpec(
            mode = "training",
            skill = "pronunciation",
            titleRes = R.string.practice_pronunciation_title,
            bodyRes = R.string.practice_pronunciation_body,
            glyph = "声",
        )
    }
    // The Mini App keeps the placement test inside the test centre rather than
    // on the practice list ("HSK imtihonlari va daraja aniqlash").
    val placementTool = remember {
        PracticeToolSpec(
            mode = "placement",
            skill = "",
            titleRes = R.string.practice_placement_title,
            bodyRes = R.string.practice_placement_body,
            glyph = "测",
        )
    }

    BackHandler(enabled = openGroup != null) { openGroup = null }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(11.dp),
    ) {
        item {
            PracticeHeader(
                group = openGroup,
                onBack = { openGroup = null },
            )
            // A spent allowance has to stay visible wherever the learner set
            // it off, so it is drawn on the home list and behind a door alike.
            PracticeNotice(
                state = state,
                limit = limit,
                onWatchAd = onWatchAd,
            )
        }

        when (openGroup) {
            null -> {
                item { GroupLabel(stringResource(R.string.practice_group_skills)) }
                item {
                    ToolRow(
                        glyph = "字",
                        tint = TintAmber,
                        title = stringResource(R.string.practice_dictionary_title),
                        body = stringResource(R.string.practice_dictionary_body),
                        enabled = true,
                        onClick = onOpenDictionary,
                    )
                }
                item {
                    ToolRow(
                        icon = Icons.Filled.Visibility,
                        tint = TintBlue,
                        title = stringResource(R.string.practice_characters_title),
                        body = stringResource(R.string.practice_recognition_group_body),
                        enabled = !state.isStarting,
                        onClick = { openGroup = PracticeGroup.RECOGNITION },
                    )
                }
                item {
                    ToolRow(
                        icon = Icons.Filled.Mic,
                        tint = TintJade,
                        title = stringResource(R.string.practice_pronunciation_row_title),
                        body = stringResource(R.string.practice_pronunciation_row_body),
                        enabled = !state.isStarting,
                        onClick = { onStartPractice(pronunciationTool, level, language) },
                    )
                }

                item { GroupLabel(stringResource(R.string.practice_group_test_short)) }
                item {
                    ToolRow(
                        icon = Icons.Filled.WorkspacePremium,
                        tint = TintCinnabar,
                        title = stringResource(R.string.practice_group_tests),
                        body = stringResource(R.string.practice_test_center_body),
                        enabled = !state.isStarting,
                        onClick = { openGroup = PracticeGroup.TEST },
                    )
                }
                item {
                    val total = state.mistakes?.summary?.total ?: 0
                    ToolRow(
                        icon = Icons.Filled.WarningAmber,
                        tint = TintCinnabar,
                        title = stringResource(R.string.practice_mistakes_title),
                        body = stringResource(R.string.practice_mistakes_body, total),
                        enabled = total > 0 && !state.isStarting,
                        busy = state.isLoadingMistakes,
                        onClick = onStartMistakeReview,
                    )
                }
            }

            PracticeGroup.RECOGNITION -> items(recognitionTools) { tool ->
                ToolRow(
                    glyph = tool.glyph,
                    tint = TintBlue,
                    title = stringResource(tool.titleRes),
                    body = stringResource(tool.bodyRes),
                    enabled = !state.isStarting,
                    onClick = { onStartPractice(tool, level, language) },
                )
            }

            PracticeGroup.TEST -> testCentre(
                level = level,
                enabled = !state.isStarting,
                onPlacement = { onStartPractice(placementTool, level, language) },
                onExam = onStartExam,
            )
        }
    }
}

/** One HSK exam as the test centre advertises it, before it is opened. */
private data class ExamEntry(
    val level: Int,
    val questions: Int,
    val minutes: Int,
    val sections: List<Int>,
)

/**
 * What each exam holds. These numbers are the checked-in exam material's own
 * (`app/static/course_v3_data/exams/hsk*.json`) and the Mini App's test centre
 * prints the same ones, so a learner is told the same thing on both clients.
 */
private val EXAM_ENTRIES = listOf(
    ExamEntry(
        1, 14, 25,
        listOf(R.string.test_center_section_listening, R.string.test_center_section_reading),
    ),
    ExamEntry(
        2, 12, 30,
        listOf(R.string.test_center_section_listening, R.string.test_center_section_reading),
    ),
    ExamEntry(
        3, 12, 35,
        listOf(
            R.string.test_center_section_listening,
            R.string.test_center_section_reading,
            R.string.test_center_section_writing,
        ),
    ),
    ExamEntry(
        4, 12, 40,
        listOf(
            R.string.test_center_section_listening,
            R.string.test_center_section_reading,
            R.string.test_center_section_writing,
        ),
    ),
)

private fun levelNumber(level: String): Int =
    Regex("hsk([1-4])").find(level.lowercase())?.groupValues?.get(1)?.toIntOrNull() ?: 0

/**
 * The test centre, laid out as the Mini App lays it out: the placement offer
 * on a dark card first — a learner who does not know their level cannot choose
 * an exam — then the four HSK exams, the learner's own level lifted to the top
 * and marked, so the row they most likely want is the first one they see.
 */
private fun LazyListScope.testCentre(
    level: String,
    enabled: Boolean,
    onPlacement: () -> Unit,
    onExam: (String) -> Unit,
) {
    item { PlacementCard(enabled = enabled, onClick = onPlacement) }
    item { GroupLabel(stringResource(R.string.test_center_exams_head)) }
    val mine = levelNumber(level)
    val entries = EXAM_ENTRIES.sortedByDescending { it.level == mine }
    items(entries, key = { it.level }) { entry ->
        ExamRow(
            entry = entry,
            isMine = entry.level == mine,
            enabled = enabled,
            onClick = { onExam("hsk${entry.level}") },
        )
    }
}

@Composable
private fun PlacementCard(enabled: Boolean, onClick: () -> Unit) {
    Surface(
        color = PompColors.Ink,
        shape = RoundedCornerShape(18.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Box {
            // The Mini App sets a huge 级 behind this card at 6% white. It is
            // decoration, so it is not announced to a screen reader.
            Text(
                text = "级",
                style = PompTextStyles.hanziMedium,
                fontSize = 84.sp,
                color = PompColors.Paper.copy(alpha = 0.06f),
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(end = 4.dp),
            )
            Column(Modifier.padding(17.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Filled.TrackChanges,
                        contentDescription = null,
                        tint = PompColors.Paper,
                        modifier = Modifier.size(18.dp),
                    )
                    Spacer(Modifier.size(8.dp))
                    Text(
                        text = stringResource(R.string.test_center_placement_title),
                        style = MaterialTheme.typography.titleMedium,
                        color = PompColors.Paper,
                    )
                }
                Spacer(Modifier.height(6.dp))
                Text(
                    text = stringResource(R.string.test_center_placement_body),
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.Paper.copy(alpha = 0.72f),
                )
                Spacer(Modifier.height(13.dp))
                Button(
                    onClick = onClick,
                    enabled = enabled,
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = PompColors.Gold,
                        contentColor = PompColors.Ink,
                    ),
                ) {
                    Icon(
                        imageVector = Icons.Filled.PlayArrow,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                    )
                    Spacer(Modifier.size(7.dp))
                    Text(stringResource(R.string.test_center_placement_button))
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ExamRow(
    entry: ExamEntry,
    isMine: Boolean,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, if (isMine) PompColors.Cinnabar else PompColors.Divider),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(enabled = enabled, onClick = onClick),
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.Top,
        ) {
            Surface(
                color = PompColors.Cinnabar,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(2.dp, PompColors.CinnabarDark),
                modifier = Modifier.size(52.dp),
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                ) {
                    Text(
                        text = "HSK",
                        style = MaterialTheme.typography.labelSmall,
                        color = PompColors.Paper.copy(alpha = 0.85f),
                    )
                    Text(
                        text = entry.level.toString(),
                        style = MaterialTheme.typography.titleLarge,
                        color = PompColors.Paper,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
            }
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(horizontal = 13.dp),
            ) {
                Text(
                    text = "HSK ${entry.level}",
                    style = MaterialTheme.typography.titleMedium,
                    color = PompColors.Ink,
                )
                Text(
                    text = stringResource(
                        R.string.test_center_exam_meta,
                        entry.questions,
                        entry.minutes,
                    ),
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                )
                // The Mini App wraps these (`flex-wrap`). Without that, HSK 3
                // and 4 carry four tags, the last ones fall off the row's
                // edge, and the row stretches to hide it.
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                    modifier = Modifier.padding(top = 7.dp),
                ) {
                    if (isMine) {
                        ExamTag(
                            text = stringResource(R.string.test_center_your_level),
                            background = PompColors.CinnabarSoft,
                            border = PompColors.CinnabarSoft,
                            content = PompColors.CinnabarDark,
                        )
                    }
                    entry.sections.forEach { section ->
                        ExamTag(
                            text = stringResource(section),
                            background = PompColors.Paper,
                            border = PompColors.Divider,
                            content = PompColors.InkSecondary,
                        )
                    }
                }
            }
            Surface(
                color = PompColors.CinnabarSoft,
                shape = RoundedCornerShape(11.dp),
            ) {
                Text(
                    text = stringResource(R.string.test_center_start),
                    style = MaterialTheme.typography.labelLarge,
                    color = PompColors.CinnabarDark,
                    modifier = Modifier.padding(horizontal = 13.dp, vertical = 9.dp),
                )
            }
        }
    }
}

@Composable
private fun ExamTag(
    text: String,
    background: Color,
    border: Color,
    content: Color,
) {
    Surface(
        color = background,
        shape = RoundedCornerShape(7.dp),
        border = BorderStroke(1.dp, border),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelSmall,
            color = content,
            // A tag is a label, not a sentence: it wraps to the next tag row
            // rather than breaking across two lines inside its own pill.
            maxLines = 1,
            modifier = Modifier.padding(horizontal = 7.dp, vertical = 2.dp),
        )
    }
}

/**
 * The pill and the one-line subtitle at the top. Behind a door the pill names
 * the door and grows a way back, so the learner is never left guessing which
 * list they are looking at.
 */
@Composable
private fun PracticeHeader(
    group: PracticeGroup?,
    onBack: () -> Unit,
) {
    val titleRes = when (group) {
        null -> R.string.practice_title
        PracticeGroup.RECOGNITION -> R.string.practice_characters_title
        PracticeGroup.TEST -> R.string.practice_group_tests
    }
    Row(verticalAlignment = Alignment.CenterVertically) {
        if (group != null) {
            Surface(
                color = PompColors.PaperRaised,
                shape = RoundedCornerShape(999.dp),
                border = BorderStroke(1.dp, PompColors.Divider),
                modifier = Modifier
                    .padding(end = 8.dp)
                    .clickable(onClick = onBack),
            ) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.KeyboardArrowLeft,
                    contentDescription = stringResource(R.string.practice_back_to_tools),
                    tint = PompColors.InkSecondary,
                    modifier = Modifier.padding(8.dp),
                )
            }
        }
        Surface(color = PompColors.Cinnabar, shape = RoundedCornerShape(999.dp)) {
            Text(
                text = stringResource(titleRes),
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.Paper,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp),
            )
        }
    }
    // The subtitle describes the practice section as a whole, so it belongs
    // on the section's own list and nowhere else.
    if (group == null) {
        Spacer(Modifier.height(8.dp))
        Text(
            text = stringResource(R.string.practice_subtitle_short),
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.InkSecondary,
        )
    }
}

/**
 * Whatever the last attempt left behind: a spent allowance with a way to open
 * it again, or a plain error. Nothing at all when the last attempt went fine.
 */
@Composable
private fun PracticeNotice(
    state: PracticeUiState,
    limit: LimitGate,
    onWatchAd: (feature: String) -> Unit,
) {
    val error = state.error
    val section = state.pendingTool
    if (error is ApiError.LimitReached) {
        // A spent allowance is not a dead end: this is the one place that says
        // what is closed, when it comes back, and how to open it now.
        Spacer(Modifier.height(12.dp))
        SectionLimitBlock(
            sectionTitle = if (section != null) {
                stringResource(section.titleRes)
            } else {
                stringResource(R.string.practice_title)
            },
            limit = limit,
            resetAt = error.resetAt,
            // Watching an ad opens the section without spending the daily
            // allowance. Only offered for a section we know.
            onWatchAd = section?.let { tool -> { onWatchAd(tool.adFeature) } },
        )
    } else if (error != null) {
        Spacer(Modifier.height(12.dp))
        ErrorPill(stringResource(error.messageRes))
    }
}

@Composable
private fun GroupLabel(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.titleSmall,
        color = PompColors.InkSecondary,
        modifier = Modifier.padding(top = 7.dp, bottom = 2.dp),
    )
}

/**
 * One practice entry, styled like the Mini App's `.row-card`: a 46dp tinted
 * tile, title, one-line explanation, and a chevron that says the row opens
 * something. The tile carries the row's own colour — in the Mini App every
 * row has its own, and painting them all one shade was the difference that
 * stood out most between the two clients.
 *
 * A row that cannot do its job is disabled rather than hidden, so the learner
 * sees why (for example: no mistakes to review yet).
 */
@Composable
private fun ToolRow(
    tint: RowTint,
    title: String,
    body: String,
    enabled: Boolean,
    onClick: () -> Unit,
    glyph: String? = null,
    icon: ImageVector? = null,
    busy: Boolean = false,
) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 68.dp)
            .clickable(enabled = enabled, onClick = onClick),
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Surface(
                color = tint.background,
                shape = RoundedCornerShape(13.dp),
                modifier = Modifier.size(46.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    if (icon != null) {
                        Icon(
                            imageVector = icon,
                            contentDescription = null,
                            tint = tint.foreground,
                            modifier = Modifier.size(22.dp),
                        )
                    } else {
                        Text(
                            text = glyph.orEmpty(),
                            style = MaterialTheme.typography.titleMedium,
                            color = tint.foreground,
                        )
                    }
                }
            }
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(start = 13.dp),
            ) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleMedium,
                    color = if (enabled) PompColors.Ink else PompColors.InkDisabled,
                )
                Text(
                    text = body,
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                )
            }
            if (busy) {
                CircularProgressIndicator(
                    color = PompColors.Cinnabar,
                    modifier = Modifier.height(18.dp),
                )
            } else {
                // The Mini App draws this chevron in `--ink3` whatever the
                // row's state, so it never competes with the title.
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                    contentDescription = null,
                    tint = PompColors.InkDisabled,
                )
            }
        }
    }
}

@Composable
private fun PracticeRun(
    state: PracticeUiState,
    language: String,
    onSelect: (Int) -> Unit,
    onAdvance: (String) -> Unit,
    onCancel: () -> Unit,
) {
    val session = state.session ?: return
    val question = session.questions.getOrNull(state.questionIndex) ?: return
    QuestionShell(
        title = stringResource(
            R.string.practice_progress,
            state.questionIndex + 1,
            session.questions.size,
        ),
        onCancel = onCancel,
    ) {
        PracticeQuestionCard(
            question = question,
            selectedIndex = state.selectedIndex,
            onSelect = onSelect,
        )
        PrimaryAction(
            text = if (state.questionIndex == session.questions.lastIndex) {
                stringResource(R.string.practice_finish)
            } else {
                stringResource(R.string.lesson_next)
            },
            enabled = state.selectedIndex != null && !state.isCompleting,
            onClick = { onAdvance(language) },
        )
    }
}

@Composable
private fun ReviewRun(
    state: PracticeUiState,
    onSelect: (Int) -> Unit,
    onAdvance: () -> Unit,
    onCancel: () -> Unit,
) {
    val session = state.reviewSession ?: return
    val question = session.questions.getOrNull(state.reviewIndex) ?: return
    QuestionShell(
        title = stringResource(
            R.string.practice_progress,
            state.reviewIndex + 1,
            session.questions.size,
        ),
        onCancel = onCancel,
    ) {
        ReviewQuestionCard(
            question = question,
            selectedIndex = state.reviewSelectedIndex,
            feedback = state.reviewFeedback,
            onSelect = onSelect,
        )
        PrimaryAction(
            text = if (state.reviewIndex == session.questions.lastIndex) {
                stringResource(R.string.practice_finish)
            } else {
                stringResource(R.string.lesson_next)
            },
            enabled = state.reviewFeedback != null && !state.isCompleting,
            onClick = onAdvance,
        )
    }
}

/**
 * One HSK exam question at a time. The exam grades on the server, so nothing
 * is revealed here — the learner picks, moves on, and sees the whole result at
 * the end. That is what makes it an exam rather than a drill.
 */
@Composable
private fun ExamRun(
    state: PracticeUiState,
    language: String,
    onSelect: (Int) -> Unit,
    onAdvance: (String) -> Unit,
    onCancel: () -> Unit,
) {
    val session = state.examSession ?: return
    val question = session.questions.getOrNull(state.examIndex) ?: return
    QuestionShell(
        title = stringResource(
            R.string.practice_progress,
            state.examIndex + 1,
            session.questions.size,
        ),
        onCancel = onCancel,
    ) {
        Surface(
            color = PompColors.PaperRaised,
            shape = RoundedCornerShape(18.dp),
            border = BorderStroke(1.dp, PompColors.Divider),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(Modifier.padding(18.dp)) {
                QuestionText(
                    prompt = question.prompt,
                    sentence = question.sentence.ifBlank { question.audioText },
                    pinyin = "",
                )
                Spacer(Modifier.height(14.dp))
                question.options.forEachIndexed { index, option ->
                    OptionRow(
                        text = option,
                        selected = state.examSelectedIndex == index,
                        correct = false,
                        wrong = false,
                        enabled = state.examSelectedIndex == null,
                        onClick = { onSelect(index) },
                    )
                }
            }
        }
        PrimaryAction(
            text = if (state.examIndex == session.questions.lastIndex) {
                stringResource(R.string.practice_finish)
            } else {
                stringResource(R.string.lesson_next)
            },
            enabled = state.examSelectedIndex != null && !state.isCompleting,
            onClick = { onAdvance(language) },
        )
    }
}

@Composable
private fun ExamSummary(
    state: PracticeUiState,
    onDone: () -> Unit,
) {
    val result = state.examResult ?: return
    val level = state.examLevel.removePrefix("hsk").ifBlank { "1" }
    SummaryShell(
        title = stringResource(
            if (result.passed) R.string.exam_result_passed else R.string.exam_result_failed
        ),
        score = "${result.percent}%",
        body = stringResource(
            if (result.passed) {
                R.string.exam_result_passed_body
            } else {
                R.string.exam_result_failed_body
            },
            level,
        ),
        onDone = onDone,
    ) {
        Text(
            text = stringResource(R.string.exam_result_score, result.score, result.total),
            style = MaterialTheme.typography.titleMedium,
            color = PompColors.Ink,
        )
        Spacer(Modifier.height(10.dp))
        // Per-section scores are what tell a learner where to go next, and the
        // server already breaks the exam down that way.
        result.sectionScores.forEach { (section, score) ->
            if (score.total > 0) {
                Surface(
                    color = PompColors.PaperRaised,
                    shape = RoundedCornerShape(14.dp),
                    border = BorderStroke(1.dp, PompColors.Divider),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text(
                            text = stringResource(examSectionLabel(section)),
                            style = MaterialTheme.typography.bodyMedium,
                            color = PompColors.InkSecondary,
                            modifier = Modifier.weight(1f),
                        )
                        Text(
                            text = "${score.score}/${score.total}",
                            style = MaterialTheme.typography.bodyMedium,
                            color = PompColors.Ink,
                        )
                    }
                }
                Spacer(Modifier.height(8.dp))
            }
        }
    }
}

private fun examSectionLabel(section: String): Int = when (section) {
    "listening" -> R.string.test_center_section_listening
    "writing" -> R.string.test_center_section_writing
    else -> R.string.test_center_section_reading
}

@Composable
private fun QuestionShell(
    title: String,
    onCancel: () -> Unit,
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(20.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.Ink,
            )
            OutlinedButton(onClick = onCancel, shape = RoundedCornerShape(12.dp)) {
                Text(stringResource(R.string.action_close))
            }
        }
        Spacer(Modifier.height(16.dp))
        content()
    }
}

@Composable
private fun PracticeQuestionCard(
    question: PracticeQuestionDto,
    selectedIndex: Int?,
    onSelect: (Int) -> Unit,
) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(18.dp)) {
            QuestionText(
                prompt = question.prompt,
                sentence = question.sentence.ifBlank { question.audioText },
                pinyin = question.pinyin,
            )
            Spacer(Modifier.height(14.dp))
            question.options.forEachIndexed { index, option ->
                val isPicked = selectedIndex == index
                val isCorrect = selectedIndex != null && question.answerIndex == index
                OptionRow(
                    text = option,
                    selected = isPicked,
                    correct = isCorrect,
                    wrong = isPicked && !isCorrect,
                    enabled = selectedIndex == null,
                    onClick = { onSelect(index) },
                )
            }
            if (selectedIndex != null && question.explanation.isNotBlank()) {
                Spacer(Modifier.height(10.dp))
                Text(
                    text = question.explanation,
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                )
            }
        }
    }
}

@Composable
private fun ReviewQuestionCard(
    question: MistakeReviewQuestionDto,
    selectedIndex: Int?,
    feedback: MistakeReviewAnswerResponse?,
    onSelect: (Int) -> Unit,
) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(18.dp)) {
            QuestionText(
                prompt = question.prompt,
                sentence = question.sentence.ifBlank { question.audioText },
                pinyin = question.pinyin,
            )
            Spacer(Modifier.height(14.dp))
            question.options.forEachIndexed { index, option ->
                val isPicked = selectedIndex == index
                val isCorrect = feedback?.correctIndex == index
                OptionRow(
                    text = option,
                    selected = isPicked,
                    correct = feedback != null && isCorrect,
                    wrong = feedback != null && isPicked && !isCorrect,
                    enabled = feedback == null,
                    onClick = { onSelect(index) },
                )
            }
            if (feedback != null) {
                Spacer(Modifier.height(10.dp))
                Text(
                    text = if (feedback.correct) {
                        stringResource(R.string.lesson_correct)
                    } else {
                        stringResource(R.string.lesson_wrong)
                    },
                    style = MaterialTheme.typography.titleSmall,
                    color = if (feedback.correct) PompColors.Jade else PompColors.CinnabarDark,
                )
                Text(
                    text = feedback.explanation.ifBlank { feedback.correctAnswer },
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                )
            }
        }
    }
}

@Composable
private fun QuestionText(
    prompt: String,
    sentence: String,
    pinyin: String,
) {
    if (prompt.isNotBlank()) {
        Text(
            text = prompt,
            style = MaterialTheme.typography.titleLarge,
            color = PompColors.Ink,
            fontWeight = FontWeight.SemiBold,
        )
    }
    if (sentence.isNotBlank()) {
        Spacer(Modifier.height(8.dp))
        Text(
            text = sentence,
            style = PompTextStyles.hanziMedium,
            color = PompColors.Ink,
        )
    }
    if (pinyin.isNotBlank()) {
        Text(
            text = pinyin,
            style = PompTextStyles.pinyin,
            color = PompColors.InkSecondary,
        )
    }
}

@Composable
private fun OptionRow(
    text: String,
    selected: Boolean,
    correct: Boolean,
    wrong: Boolean,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    val color = when {
        correct -> PompColors.JadeSoft
        wrong -> PompColors.CinnabarSoft
        selected -> PompColors.GoldSoft
        else -> PompColors.Paper
    }
    val border = when {
        correct -> PompColors.Jade
        wrong -> PompColors.Cinnabar
        selected -> PompColors.Gold
        else -> PompColors.Divider
    }
    Surface(
        color = color,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, border),
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 5.dp)
            .clickable(enabled = enabled, onClick = onClick),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.Ink,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
        )
    }
}

@Composable
private fun PrimaryAction(
    text: String,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    Spacer(Modifier.height(16.dp))
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 52.dp),
        shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = PompColors.Cinnabar,
            contentColor = PompColors.Paper,
        ),
    ) {
        Text(text)
    }
}

@Composable
private fun PracticeSummary(
    state: PracticeUiState,
    onDone: () -> Unit,
) {
    val result = state.result ?: return
    SummaryShell(
        title = stringResource(R.string.practice_result_title),
        score = "${result.percent}%",
        body = stringResource(
            R.string.practice_result_body,
            result.score,
            result.total,
        ),
        onDone = onDone,
    ) {
        result.wrongItems.take(4).forEach { item ->
            Surface(
                color = PompColors.PaperRaised,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, PompColors.Divider),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(Modifier.padding(12.dp)) {
                    Text(item.question, style = MaterialTheme.typography.bodyMedium)
                    Text(
                        text = "✓ ${item.correctAnswer}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = PompColors.Jade,
                    )
                }
            }
            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
private fun ReviewSummary(
    state: PracticeUiState,
    onDone: () -> Unit,
) {
    val result = state.reviewResult ?: return
    SummaryShell(
        title = stringResource(R.string.practice_review_result_title),
        score = "${result.percent}%",
        body = stringResource(R.string.practice_review_result_body, result.remaining),
        onDone = onDone,
    )
}

@Composable
private fun SummaryShell(
    title: String,
    score: String,
    body: String,
    onDone: () -> Unit,
    extra: @Composable ColumnScope.() -> Unit = {},
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(20.dp),
    ) {
        item {
            Text(
                text = title,
                style = MaterialTheme.typography.headlineMedium,
                color = PompColors.Ink,
            )
            Spacer(Modifier.height(10.dp))
            Text(
                text = score,
                style = MaterialTheme.typography.displaySmall,
                color = PompColors.CinnabarDark,
            )
            Text(
                text = body,
                style = MaterialTheme.typography.bodyLarge,
                color = PompColors.InkSecondary,
            )
            Spacer(Modifier.height(16.dp))
            Column { extra() }
            PrimaryAction(
                text = stringResource(R.string.practice_back_to_tools),
                enabled = true,
                onClick = onDone,
            )
        }
    }
}

@Composable
private fun ErrorPill(text: String) {
    Surface(
        color = PompColors.CinnabarSoft,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.CinnabarDark,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
        )
    }
}
