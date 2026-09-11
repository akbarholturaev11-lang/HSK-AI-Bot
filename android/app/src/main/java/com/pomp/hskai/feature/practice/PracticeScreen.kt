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
import androidx.compose.foundation.layout.width
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
import androidx.compose.runtime.LaunchedEffect
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
import com.pomp.hskai.data.api.AndroidHintDto
import com.pomp.hskai.feature.hint.SectionHint
import com.pomp.hskai.data.api.MistakeReviewAnswerResponse
import com.pomp.hskai.data.api.MistakeReviewQuestionDto
import com.pomp.hskai.data.api.PracticeQuestionDto
import com.pomp.hskai.feature.limit.LimitGate
import com.pomp.hskai.feature.limit.SectionLimitOverlay

@Composable
fun PracticeScreen(
    state: PracticeUiState,
    level: String,
    language: String,
    limit: LimitGate,
    hints: List<AndroidHintDto> = emptyList(),
    onDismissHint: (String) -> Unit = {},
    onDismissLimit: () -> Unit = {},
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
    onOpenDrill: (DrillMode) -> Unit,
    onSelectExamOption: (Int) -> Unit,
    onAdvanceExam: (String) -> Unit,
    onResetExam: () -> Unit,
    request: PracticeRequest? = null,
    onRequestConsumed: () -> Unit = {},
    modifier: Modifier = Modifier,
) {
    var mistakesOpen by rememberSaveable { mutableStateOf(false) }

    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
      Box(Modifier.fillMaxSize()) {
        when {
            state.result != null -> PracticeSummary(state = state, onDone = onResetPractice)
            state.reviewResult != null -> MistakesReviewResult(result = state.reviewResult, onDone = onResetReview)
            state.examResult != null -> ExamSummary(state = state, onDone = onResetExam)
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
            state.isReviewRunning -> MistakesReviewRun(
                state = state,
                onSelect = onAnswerReview,
                onAdvance = onAdvanceReview,
                onCancel = onResetReview,
            )
            mistakesOpen -> MistakesOverviewScreen(
                state = state,
                onBack = { mistakesOpen = false },
                onStartReview = onStartMistakeReview,
                onReload = onResetReview,
            )
            else -> PracticeHome(
                state = state,
                level = level,
                language = language,
                limit = limit,
                hints = hints,
                onDismissHint = onDismissHint,
                onOpenDictionary = onOpenDictionary,
                onStartPractice = onStartPractice,
                onOpenMistakes = { mistakesOpen = true },
                onStartExam = onStartExam,
                onOpenDrill = onOpenDrill,
                request = request,
                onRequestConsumed = onRequestConsumed,
            )
        }

        val spent = state.error as? ApiError.LimitReached
        if (spent != null) {
            val section = state.pendingTool
            SectionLimitOverlay(
                sectionTitle = if (section != null) stringResource(section.titleRes) else stringResource(R.string.practice_title),
                limit = limit,
                reason = spent.limitText ?: stringResource(R.string.limit_practice_reason),
                resetAt = spent.resetAt,
                onClose = onDismissLimit,
            )
        }
      }
    }
}

private enum class PracticeGroup { TEST }
enum class PracticeRequest { MISTAKES, RECOGNITION, PRONUNCIATION, TESTS }
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
    hints: List<AndroidHintDto>,
    onDismissHint: (String) -> Unit,
    onOpenDictionary: () -> Unit,
    onStartPractice: (PracticeToolSpec, String, String) -> Unit,
    onOpenMistakes: () -> Unit,
    onStartExam: (String) -> Unit,
    onOpenDrill: (DrillMode) -> Unit,
    request: PracticeRequest?,
    onRequestConsumed: () -> Unit,
) {
    var openGroup by rememberSaveable { mutableStateOf<PracticeGroup?>(null) }
    val placementTool = remember {
        PracticeToolSpec(
            mode = "placement",
            skill = "",
            titleRes = R.string.practice_placement_title,
            bodyRes = R.string.practice_placement_body,
            glyph = "测",
        )
    }

    LaunchedEffect(request) {
        when (request) {
            null -> return@LaunchedEffect
            PracticeRequest.MISTAKES -> { openGroup = null; onOpenMistakes() }
            PracticeRequest.RECOGNITION -> { openGroup = null; onOpenDrill(DrillMode.RECOGNITION) }
            PracticeRequest.TESTS -> openGroup = PracticeGroup.TEST
            PracticeRequest.PRONUNCIATION -> { openGroup = null; onOpenDrill(DrillMode.PRONUNCIATION) }
        }
        onRequestConsumed()
    }

    BackHandler(enabled = openGroup != null) { openGroup = null }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(11.dp),
    ) {
        item {
            PracticeHeader(group = openGroup, onBack = { openGroup = null }, hints = hints, onDismissHint = onDismissHint)
            PracticeNotice(state = state)
        }
        when (openGroup) {
            null -> {
                item { GroupLabel(stringResource(R.string.practice_group_skills)) }
                item { ToolRow("字", null, TintAmber, stringResource(R.string.practice_dictionary_title), stringResource(R.string.practice_dictionary_body), true, false, onOpenDictionary) }
                item { ToolRow(null, Icons.Filled.Visibility, TintBlue, stringResource(R.string.practice_characters_title), stringResource(R.string.practice_recognition_group_body), !state.isStarting, false) { onOpenDrill(DrillMode.RECOGNITION) } }
                item { ToolRow(null, Icons.Filled.Mic, TintJade, stringResource(R.string.practice_pronunciation_row_title), stringResource(R.string.practice_pronunciation_row_body), !state.isStarting, false) { onOpenDrill(DrillMode.PRONUNCIATION) } }
                item { GroupLabel(stringResource(R.string.practice_group_test_short)) }
                item { ToolRow(null, Icons.Filled.WorkspacePremium, TintCinnabar, stringResource(R.string.practice_group_tests), stringResource(R.string.practice_test_center_body), !state.isStarting, false) { openGroup = PracticeGroup.TEST } }
                item {
                    val total = state.mistakes?.summary?.total ?: 0
                    ToolRow(null, Icons.Filled.WarningAmber, TintCinnabar, stringResource(R.string.practice_mistakes_title), stringResource(R.string.practice_mistakes_body, total), !state.isStarting, state.isLoadingMistakes, onOpenMistakes)
                }
            }
            PracticeGroup.TEST -> testCentre(level, !state.isStarting, { onStartPractice(placementTool, level, language) }, onStartExam)
        }
    }
}

private data class ExamEntry(val level: Int, val questions: Int, val minutes: Int, val sections: List<Int>)
private val EXAM_ENTRIES = listOf(
    ExamEntry(1, 14, 25, listOf(R.string.test_center_section_listening, R.string.test_center_section_reading)),
    ExamEntry(2, 12, 30, listOf(R.string.test_center_section_listening, R.string.test_center_section_reading)),
    ExamEntry(3, 12, 35, listOf(R.string.test_center_section_listening, R.string.test_center_section_reading, R.string.test_center_section_writing)),
    ExamEntry(4, 12, 40, listOf(R.string.test_center_section_listening, R.string.test_center_section_reading, R.string.test_center_section_writing)),
)
private fun levelNumber(level: String): Int = Regex("hsk([1-4])").find(level.lowercase())?.groupValues?.get(1)?.toIntOrNull() ?: 0

private fun LazyListScope.testCentre(level: String, enabled: Boolean, onPlacement: () -> Unit, onExam: (String) -> Unit) {
    item { PlacementCard(enabled, onPlacement) }
    item { GroupLabel(stringResource(R.string.test_center_exams_head)) }
    val mine = levelNumber(level)
    items(EXAM_ENTRIES.sortedByDescending { it.level == mine }, key = { it.level }) { entry ->
        ExamRow(entry, entry.level == mine, enabled) { onExam("hsk${entry.level}") }
    }
}

@Composable
private fun PlacementCard(enabled: Boolean, onClick: () -> Unit) {
    val cardBackground = if (PompColors.IsDark) PompColors.PaperRaised else PompColors.Ink
    val heroInk = if (PompColors.IsDark) PompColors.Ink else PompColors.Paper
    val heroMuted = if (PompColors.IsDark) PompColors.InkSecondary else PompColors.Paper.copy(alpha = 0.72f)
    Surface(
        color = cardBackground,
        shape = RoundedCornerShape(18.dp),
        border = if (PompColors.IsDark) BorderStroke(1.dp, PompColors.Divider) else null,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Box {
            Text(
                text = "级",
                style = PompTextStyles.hanziMedium,
                fontSize = 84.sp,
                color = heroInk.copy(alpha = 0.06f),
                modifier = Modifier.align(Alignment.TopEnd).padding(end = 4.dp),
            )
            Column(Modifier.padding(17.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Filled.TrackChanges, contentDescription = null, tint = PompColors.Gold, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.size(8.dp))
                    Text(stringResource(R.string.test_center_placement_title), style = MaterialTheme.typography.titleMedium, color = heroInk)
                }
                Spacer(Modifier.height(6.dp))
                Text(stringResource(R.string.test_center_placement_body), style = MaterialTheme.typography.bodyMedium, color = heroMuted)
                Spacer(Modifier.height(13.dp))
                Button(
                    onClick = onClick,
                    enabled = enabled,
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = PompColors.Gold, contentColor = PompColors.PlanOnGold),
                ) {
                    Icon(Icons.Filled.PlayArrow, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.size(7.dp))
                    Text(stringResource(R.string.test_center_placement_button))
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ExamRow(entry: ExamEntry, isMine: Boolean, enabled: Boolean, onClick: () -> Unit) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, if (isMine) PompColors.Cinnabar else PompColors.Divider),
        modifier = Modifier.fillMaxWidth().clickable(enabled = enabled, onClick = onClick),
    ) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.Top) {
            Surface(color = PompColors.Cinnabar, shape = RoundedCornerShape(14.dp), border = BorderStroke(2.dp, PompColors.CinnabarDark), modifier = Modifier.size(52.dp)) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                    Text("HSK", style = MaterialTheme.typography.labelSmall, color = if (PompColors.IsDark) PompColors.Ink.copy(alpha = 0.85f) else PompColors.Paper.copy(alpha = 0.85f))
                    Text(entry.level.toString(), style = MaterialTheme.typography.titleLarge, color = if (PompColors.IsDark) PompColors.Ink else PompColors.Paper, fontWeight = FontWeight.SemiBold)
                }
            }
            Column(Modifier.weight(1f).padding(horizontal = 13.dp)) {
                Text("HSK ${entry.level}", style = MaterialTheme.typography.titleMedium, color = PompColors.Ink)
                Text(stringResource(R.string.test_center_exam_meta, entry.questions, entry.minutes), style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.padding(top = 7.dp)) {
                    if (isMine) ExamTag(stringResource(R.string.test_center_your_level), PompColors.CinnabarSoft, PompColors.CinnabarSoft, if (PompColors.IsDark) PompColors.Cinnabar else PompColors.CinnabarDark)
                    entry.sections.forEach { section ->
                        ExamTag(stringResource(section), if (PompColors.IsDark) PompColors.OptionDepth else PompColors.Paper, PompColors.Divider, PompColors.InkSecondary)
                    }
                }
            }
            Surface(color = PompColors.CinnabarSoft, shape = RoundedCornerShape(11.dp)) {
                Text(stringResource(R.string.test_center_start), style = MaterialTheme.typography.labelLarge, color = if (PompColors.IsDark) PompColors.Cinnabar else PompColors.CinnabarDark, modifier = Modifier.padding(horizontal = 13.dp, vertical = 9.dp))
            }
        }
    }
}

@Composable
private fun ExamTag(text: String, background: Color, border: Color, content: Color) {
    Surface(color = background, shape = RoundedCornerShape(7.dp), border = BorderStroke(1.dp, border)) {
        Text(text, style = MaterialTheme.typography.labelSmall, color = content, maxLines = 1, modifier = Modifier.padding(horizontal = 7.dp, vertical = 2.dp))
    }
}

@Composable
private fun PracticeHeader(group: PracticeGroup?, onBack: () -> Unit, hints: List<AndroidHintDto>, onDismissHint: (String) -> Unit) {
    val titleRes = if (group == null) R.string.practice_title else R.string.practice_group_tests
    Row(verticalAlignment = Alignment.CenterVertically) {
        if (group != null) {
            Surface(color = PompColors.PaperRaised, shape = RoundedCornerShape(999.dp), border = BorderStroke(1.dp, PompColors.Divider), modifier = Modifier.padding(end = 8.dp).clickable(onClick = onBack)) {
                Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, contentDescription = stringResource(R.string.practice_back_to_tools), tint = PompColors.InkSecondary, modifier = Modifier.padding(8.dp))
            }
        }
        Surface(color = PompColors.Cinnabar, shape = RoundedCornerShape(999.dp)) {
            Text(stringResource(titleRes), style = MaterialTheme.typography.titleMedium, color = if (PompColors.IsDark) PompColors.Ink else PompColors.Paper, modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp))
        }
        Spacer(Modifier.width(8.dp))
        SectionHint(hints = hints, section = "mashq", onDismiss = onDismissHint)
    }
    if (group == null) {
        Spacer(Modifier.height(8.dp))
        Text(stringResource(R.string.practice_subtitle_short), style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
    }
}

@Composable
private fun PracticeNotice(state: PracticeUiState) {
    val error = state.error
    if (error != null && error !is ApiError.LimitReached) {
        Spacer(Modifier.height(12.dp)); ErrorPill(stringResource(error.messageRes))
    }
}

@Composable
private fun GroupLabel(text: String) {
    Text(text, style = MaterialTheme.typography.titleSmall, color = PompColors.InkSecondary, modifier = Modifier.padding(top = 7.dp, bottom = 2.dp))
}

@Composable
private fun ToolRow(
    glyph: String? = null,
    icon: ImageVector? = null,
    tint: RowTint,
    title: String,
    body: String,
    enabled: Boolean,
    busy: Boolean = false,
    onClick: () -> Unit,
) {
    Surface(color = PompColors.PaperRaised, shape = RoundedCornerShape(16.dp), border = BorderStroke(1.dp, PompColors.Divider), modifier = Modifier.fillMaxWidth().heightIn(min = 68.dp).clickable(enabled = enabled, onClick = onClick)) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(color = tint.background, shape = RoundedCornerShape(13.dp), modifier = Modifier.size(46.dp)) {
                Box(contentAlignment = Alignment.Center) {
                    if (icon != null) Icon(icon, contentDescription = null, tint = tint.foreground, modifier = Modifier.size(22.dp))
                    else Text(glyph.orEmpty(), style = MaterialTheme.typography.titleMedium, color = tint.foreground)
                }
            }
            Column(Modifier.weight(1f).padding(start = 13.dp)) {
                Text(title, style = MaterialTheme.typography.titleMedium, color = if (enabled) PompColors.Ink else PompColors.InkDisabled)
                Text(body, style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
            }
            if (busy) CircularProgressIndicator(color = PompColors.Cinnabar, modifier = Modifier.height(18.dp))
            else Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = PompColors.InkDisabled)
        }
    }
}

@Composable
private fun PracticeRun(state: PracticeUiState, language: String, onSelect: (Int) -> Unit, onAdvance: (String) -> Unit, onCancel: () -> Unit) {
    val session = state.session ?: return
    val question = session.questions.getOrNull(state.questionIndex) ?: return
    QuestionShell(stringResource(R.string.practice_progress, state.questionIndex + 1, session.questions.size), onCancel) {
        PracticeQuestionCard(question, state.selectedIndex, onSelect)
        PrimaryAction(if (state.questionIndex == session.questions.lastIndex) stringResource(R.string.practice_finish) else stringResource(R.string.lesson_next), state.selectedIndex != null && !state.isCompleting) { onAdvance(language) }
    }
}

@Composable
private fun ReviewRun(state: PracticeUiState, onSelect: (Int) -> Unit, onAdvance: () -> Unit, onCancel: () -> Unit) {
    val session = state.reviewSession ?: return
    val question = session.questions.getOrNull(state.reviewIndex) ?: return
    QuestionShell(stringResource(R.string.practice_progress, state.reviewIndex + 1, session.questions.size), onCancel) {
        ReviewQuestionCard(question, state.reviewSelectedIndex, state.reviewFeedback, onSelect)
        PrimaryAction(if (state.reviewIndex == session.questions.lastIndex) stringResource(R.string.practice_finish) else stringResource(R.string.lesson_next), state.reviewFeedback != null && !state.isCompleting, onAdvance)
    }
}

@Composable
private fun ExamRun(state: PracticeUiState, language: String, onSelect: (Int) -> Unit, onAdvance: (String) -> Unit, onCancel: () -> Unit) {
    val session = state.examSession ?: return
    val question = session.questions.getOrNull(state.examIndex) ?: return
    QuestionShell(stringResource(R.string.practice_progress, state.examIndex + 1, session.questions.size), onCancel) {
        Surface(color = PompColors.PaperRaised, shape = RoundedCornerShape(18.dp), border = BorderStroke(1.dp, PompColors.Divider), modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(18.dp)) {
                QuestionText(question.prompt, question.sentence.ifBlank { question.audioText }, "")
                Spacer(Modifier.height(14.dp))
                question.options.forEachIndexed { index, option -> OptionRow(option, state.examSelectedIndex == index, false, false, state.examSelectedIndex == null) { onSelect(index) } }
            }
        }
        PrimaryAction(if (state.examIndex == session.questions.lastIndex) stringResource(R.string.practice_finish) else stringResource(R.string.lesson_next), state.examSelectedIndex != null && !state.isCompleting) { onAdvance(language) }
    }
}

@Composable
private fun ExamSummary(state: PracticeUiState, onDone: () -> Unit) {
    val result = state.examResult ?: return
    val level = state.examLevel.removePrefix("hsk").ifBlank { "1" }
    SummaryShell(
        stringResource(if (result.passed) R.string.exam_result_passed else R.string.exam_result_failed),
        "${result.percent}%",
        stringResource(if (result.passed) R.string.exam_result_passed_body else R.string.exam_result_failed_body, level),
        onDone,
    ) {
        Text(stringResource(R.string.exam_result_score, result.score, result.total), style = MaterialTheme.typography.titleMedium, color = PompColors.Ink)
        Spacer(Modifier.height(10.dp))
        result.sectionScores.forEach { (section, score) ->
            if (score.total > 0) {
                Surface(color = PompColors.PaperRaised, shape = RoundedCornerShape(14.dp), border = BorderStroke(1.dp, PompColors.Divider), modifier = Modifier.fillMaxWidth()) {
                    Row(Modifier.padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(stringResource(examSectionLabel(section)), style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary, modifier = Modifier.weight(1f))
                        Text("${score.score}/${score.total}", style = MaterialTheme.typography.bodyMedium, color = PompColors.Ink)
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
private fun QuestionShell(title: String, onCancel: () -> Unit, content: @Composable ColumnScope.() -> Unit) {
    Column(Modifier.fillMaxSize().padding(20.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text(title, style = MaterialTheme.typography.titleMedium, color = PompColors.Ink)
            OutlinedButton(onClick = onCancel, shape = RoundedCornerShape(12.dp)) { Text(stringResource(R.string.action_close)) }
        }
        Spacer(Modifier.height(16.dp)); content()
    }
}

@Composable
private fun PracticeQuestionCard(question: PracticeQuestionDto, selectedIndex: Int?, onSelect: (Int) -> Unit) {
    Surface(color = PompColors.PaperRaised, shape = RoundedCornerShape(18.dp), border = BorderStroke(1.dp, PompColors.Divider), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp)) {
            QuestionText(question.prompt, question.sentence.ifBlank { question.audioText }, question.pinyin)
            Spacer(Modifier.height(14.dp))
            question.options.forEachIndexed { index, option ->
                val isPicked = selectedIndex == index
                val isCorrect = selectedIndex != null && question.answerIndex == index
                OptionRow(option, isPicked, isCorrect, isPicked && !isCorrect, selectedIndex == null) { onSelect(index) }
            }
            if (selectedIndex != null && question.explanation.isNotBlank()) {
                Spacer(Modifier.height(10.dp)); Text(question.explanation, style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
            }
        }
    }
}

@Composable
private fun ReviewQuestionCard(question: MistakeReviewQuestionDto, selectedIndex: Int?, feedback: MistakeReviewAnswerResponse?, onSelect: (Int) -> Unit) {
    Surface(color = PompColors.PaperRaised, shape = RoundedCornerShape(18.dp), border = BorderStroke(1.dp, PompColors.Divider), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp)) {
            QuestionText(question.prompt, question.sentence.ifBlank { question.audioText }, question.pinyin)
            Spacer(Modifier.height(14.dp))
            question.options.forEachIndexed { index, option ->
                val isPicked = selectedIndex == index
                val isCorrect = feedback?.correctIndex == index
                OptionRow(option, isPicked, feedback != null && isCorrect, feedback != null && isPicked && !isCorrect, feedback == null) { onSelect(index) }
            }
            if (feedback != null) {
                Spacer(Modifier.height(10.dp))
                Text(if (feedback.correct) stringResource(R.string.lesson_correct) else stringResource(R.string.lesson_wrong), style = MaterialTheme.typography.titleSmall, color = if (feedback.correct) PompColors.Jade else PompColors.Flame)
                Text(feedback.explanation.ifBlank { feedback.correctAnswer }, style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
            }
        }
    }
}

@Composable
private fun QuestionText(prompt: String, sentence: String, pinyin: String) {
    if (prompt.isNotBlank()) Text(prompt, style = MaterialTheme.typography.titleLarge, color = PompColors.Ink, fontWeight = FontWeight.SemiBold)
    if (sentence.isNotBlank()) { Spacer(Modifier.height(8.dp)); Text(sentence, style = PompTextStyles.hanziMedium, color = PompColors.Ink) }
    if (pinyin.isNotBlank()) Text(pinyin, style = PompTextStyles.pinyin, color = PompColors.InkSecondary)
}

@Composable
private fun OptionRow(text: String, selected: Boolean, correct: Boolean, wrong: Boolean, enabled: Boolean, onClick: () -> Unit) {
    val color = when {
        correct -> PompColors.JadeSoft
        wrong -> PompColors.FlameSoft
        selected -> PompColors.GoldSoft
        else -> if (PompColors.IsDark) PompColors.OptionDepth else PompColors.Paper
    }
    val border = when {
        correct -> PompColors.Jade
        wrong -> PompColors.Flame
        selected -> PompColors.Gold
        else -> PompColors.Divider
    }
    Surface(color = color, shape = RoundedCornerShape(14.dp), border = BorderStroke(1.dp, border), modifier = Modifier.fillMaxWidth().padding(vertical = 5.dp).clickable(enabled = enabled, onClick = onClick)) {
        Text(text, style = MaterialTheme.typography.bodyLarge, color = PompColors.Ink, modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp))
    }
}

@Composable
private fun PrimaryAction(text: String, enabled: Boolean, onClick: () -> Unit) {
    Spacer(Modifier.height(16.dp))
    Button(onClick = onClick, enabled = enabled, modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp), shape = RoundedCornerShape(14.dp), colors = ButtonDefaults.buttonColors(containerColor = PompColors.Cinnabar, contentColor = if (PompColors.IsDark) PompColors.Ink else PompColors.Paper)) { Text(text) }
}

@Composable
private fun PracticeSummary(state: PracticeUiState, onDone: () -> Unit) {
    val result = state.result ?: return
    SummaryShell(stringResource(R.string.practice_result_title), "${result.percent}%", stringResource(R.string.practice_result_body, result.score, result.total), onDone) {
        result.wrongItems.take(4).forEach { item ->
            Surface(color = PompColors.PaperRaised, shape = RoundedCornerShape(14.dp), border = BorderStroke(1.dp, PompColors.Divider), modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text(item.question, style = MaterialTheme.typography.bodyMedium, color = PompColors.Ink)
                    Text("✓ ${item.correctAnswer}", style = MaterialTheme.typography.bodyMedium, color = PompColors.Jade)
                }
            }
            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
private fun ReviewSummary(state: PracticeUiState, onDone: () -> Unit) {
    val result = state.reviewResult ?: return
    SummaryShell(stringResource(R.string.practice_review_result_title), "${result.percent}%", stringResource(R.string.practice_review_result_body, result.remaining), onDone)
}

@Composable
private fun SummaryShell(title: String, score: String, body: String, onDone: () -> Unit, extra: @Composable ColumnScope.() -> Unit = {}) {
    LazyColumn(modifier = Modifier.fillMaxSize(), contentPadding = PaddingValues(20.dp)) {
        item {
            Text(title, style = MaterialTheme.typography.headlineMedium, color = PompColors.Ink)
            Spacer(Modifier.height(10.dp))
            Text(score, style = MaterialTheme.typography.displaySmall, color = PompColors.Cinnabar)
            Text(body, style = MaterialTheme.typography.bodyLarge, color = PompColors.InkSecondary)
            Spacer(Modifier.height(16.dp)); Column { extra() }
            PrimaryAction(stringResource(R.string.practice_back_to_tools), true, onDone)
        }
    }
}

@Composable
private fun ErrorPill(text: String) {
    Surface(color = PompColors.FlameSoft, shape = RoundedCornerShape(12.dp), modifier = Modifier.fillMaxWidth()) {
        Text(text, style = MaterialTheme.typography.bodyMedium, color = PompColors.Flame, modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp))
    }
}
