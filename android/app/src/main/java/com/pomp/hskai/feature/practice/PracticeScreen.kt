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
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material.icons.filled.TrackChanges
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material.icons.filled.WorkspacePremium
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
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
import com.pomp.hskai.core.design.components.HskBrandLoader
import com.pomp.hskai.core.design.components.HskCharacter
import com.pomp.hskai.core.design.components.HskCharacterMood
import com.pomp.hskai.core.design.components.HskCharacterReaction
import com.pomp.hskai.core.design.components.HskCoachBeside
import com.pomp.hskai.core.design.components.HskCoachRow
import com.pomp.hskai.core.design.components.HskGlassButton
import com.pomp.hskai.core.design.components.HskGlassIconButton
import com.pomp.hskai.core.design.components.HskGlassSurface
import com.pomp.hskai.core.design.components.HskPrimaryButton
import com.pomp.hskai.core.design.components.hskReactionFor
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.core.navigation.LocalMainBottomInset
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.data.api.AndroidHintDto
import com.pomp.hskai.feature.hint.SectionHint
import com.pomp.hskai.data.api.MistakeReviewAnswerResponse
import com.pomp.hskai.data.api.MistakeReviewQuestionDto
import com.pomp.hskai.data.api.PracticeQuestionDto
import com.pomp.hskai.feature.assistant.AssistantScreen
import com.pomp.hskai.feature.assistant.practiceAssistantContext
import com.pomp.hskai.core.navigation.PracticeTool
import com.pomp.hskai.feature.limit.LimitGate
import com.pomp.hskai.feature.limit.SectionLimitOverlay
import com.pomp.hskai.core.design.components.rememberExitGuard

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
    onSpeakReview: (String) -> Unit,
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
    AssistantScreen(practiceAssistantContext(state, level, mistakesOpen), bottomBar = true)

    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
      Box(Modifier.fillMaxSize()) {
        // The phone's back follows each screen's own way out, so it no longer
        // falls through to the tabs (or out of the app) from inside a run: a
        // result closes, a running set asks first, the mistakes list goes back.
        when {
            state.result != null -> {
                BackHandler(onBack = onResetPractice)
                PracticeSummary(state = state, onDone = onResetPractice)
            }
            state.reviewResult != null -> {
                BackHandler(onBack = onResetReview)
                MistakesReviewResult(result = state.reviewResult, onDone = onResetReview)
            }
            state.examResult != null -> {
                BackHandler(onBack = onResetExam)
                ExamSummary(state = state, onDone = onResetExam)
            }
            state.isExamRunning -> ExamRun(
                state = state,
                language = language,
                onSelect = onSelectExamOption,
                onAdvance = onAdvanceExam,
                onCancel = rememberRunExit(onResetExam),
                onSpeak = onSpeakReview,
            )
            state.isPracticeRunning -> PracticeRun(
                state = state,
                language = language,
                onSelect = onSelectPracticeOption,
                onAdvance = onAdvancePractice,
                onCancel = rememberRunExit(onResetPractice),
                onSpeak = onSpeakReview,
            )
            state.isReviewRunning -> MistakesReviewRun(
                state = state,
                onSelect = onAnswerReview,
                onAdvance = onAdvanceReview,
                onCancel = rememberRunExit(onResetReview),
                onSpeak = onSpeakReview,
            )
            mistakesOpen -> {
                BackHandler { mistakesOpen = false }
                MistakesOverviewScreen(
                    state = state,
                    onBack = { mistakesOpen = false },
                    onStartReview = onStartMistakeReview,
                    onReload = onResetReview,
                )
            }
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

/** A running set's ✕ and the phone's back: both ask before the attempt is dropped. */
@Composable
private fun rememberRunExit(onCancel: () -> Unit): () -> Unit = rememberExitGuard(
    running = true,
    title = R.string.practice_exit_title,
    body = R.string.practice_exit_body,
    onExit = onCancel,
)

private enum class PracticeGroup { TEST }
enum class PracticeRequest { MISTAKES, RECOGNITION, PRONUNCIATION, TESTS }

/**
 * The screen a deep-linked tool opens, or null to stop on the section home.
 *
 * [PracticeTool.MEMORIZE] is the null: the Mini App's `Yodlash` is a stroke and
 * radical exercise with no Android counterpart yet, and landing on the practice
 * home is a better answer than ignoring the link and leaving the app where it
 * was. Give it a request the day the screen exists.
 */
fun PracticeTool.toRequest(): PracticeRequest? = when (this) {
    PracticeTool.MISTAKES -> PracticeRequest.MISTAKES
    PracticeTool.RECOGNITION -> PracticeRequest.RECOGNITION
    PracticeTool.PRONUNCIATION -> PracticeRequest.PRONUNCIATION
    PracticeTool.TESTS -> PracticeRequest.TESTS
    PracticeTool.MEMORIZE -> null
}
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
        contentPadding = PaddingValues(
            start = 16.dp,
            end = 16.dp,
            top = 20.dp,
            // The tab bar floats over the list; the last tool clears it here.
            bottom = 20.dp + LocalMainBottomInset.current,
        ),
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
    HskGlassSurface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        shadowElevation = 6.dp,
        borderColor = if (isMine) PompColors.Cinnabar else null,
        onClick = onClick,
        enabled = enabled,
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
            HskGlassIconButton(
                icon = Icons.AutoMirrored.Filled.KeyboardArrowLeft,
                contentDescription = stringResource(R.string.practice_back_to_tools),
                onClick = onBack,
                size = 40.dp,
                iconSize = 20.dp,
                tint = PompColors.InkSecondary,
            )
            Spacer(Modifier.width(8.dp))
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
    HskGlassSurface(
        modifier = Modifier.fillMaxWidth().heightIn(min = 68.dp),
        shape = RoundedCornerShape(16.dp),
        shadowElevation = 6.dp,
        onClick = onClick,
        enabled = enabled,
    ) {
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
            if (busy) HskBrandLoader(compact = true)
            else Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = PompColors.InkDisabled)
        }
    }
}

@Composable
private fun PracticeRun(state: PracticeUiState, language: String, onSelect: (Int) -> Unit, onAdvance: (String) -> Unit, onCancel: () -> Unit, onSpeak: (String) -> Unit) {
    val session = state.session ?: return
    val question = session.questions.getOrNull(state.questionIndex) ?: return
    // A listening question that has to be asked for is half a question. The
    // Mini App speaks it as the card appears (`course-v3.html:4014`) and so
    // does this; advancing stops the previous one in the view model.
    LaunchedEffect(question.id) { if (question.audioText.isNotBlank()) onSpeak(question.audioText) }
    val progress = stringResource(R.string.practice_progress, state.questionIndex + 1, session.questions.size)
    QuestionShell(title = progress, onCancel = onCancel) {
        // The placement test answers each question on the spot — the right
        // option and its explanation are already on screen — so a coach that
        // reacts gives nothing away. The HSK exams withhold that until the
        // end and deliberately have no coach at all.
        //
        // The coach says the question's instruction and the sentence stands
        // next to it; the options stay full width below, where they need the
        // room. The instruction used to be the card's own bold headline.
        val answered = state.selectedIndex != null
        val isCorrect = answered && question.answerIndex == state.selectedIndex
        HskCoachBeside(
            character = practiceCharacterFor(question),
            mood = practiceMoodFor(if (answered) isCorrect else null),
            reaction = if (answered) {
                hskReactionFor(correct = isCorrect, streak = state.practiceStreak)
            } else {
                null
            },
            reactionKey = state.questionIndex to state.selectedIndex,
            text = question.prompt.ifBlank { progress },
        ) {
            PracticeQuestionMaterial(question, state.isReviewAudioLoading, onSpeak)
        }
        Spacer(Modifier.height(14.dp))
        PracticeQuestionOptions(question, state.selectedIndex, onSelect)
        if (state.error != null && state.error !is ApiError.LimitReached) {
            Spacer(Modifier.height(12.dp))
            ErrorPill(stringResource(state.error.messageRes))
        }
        PrimaryAction(
            text = if (state.questionIndex == session.questions.lastIndex) stringResource(R.string.practice_finish) else stringResource(R.string.lesson_next),
            enabled = state.selectedIndex != null,
            loading = state.isCompleting,
        ) { onAdvance(language) }
    }
}

/**
 * What the question gives the learner to work on — the sentence, or the
 * speaker when it is a listening question. The instruction is not here: the
 * coach is saying it.
 *
 * Blank material (a bare prompt with nothing to read) draws nothing, so the
 * coach is not left pointing at an empty card.
 */
@Composable
private fun PracticeQuestionMaterial(
    question: PracticeQuestionDto,
    isAudioLoading: Boolean,
    onSpeak: (String) -> Unit,
) {
    if (question.sentence.isBlank() && question.audioText.isBlank()) return
    HskGlassSurface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        shadowElevation = 7.dp,
    ) {
        Column(
            Modifier.padding(horizontal = 14.dp, vertical = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            QuestionText("", question.sentence, question.pinyin, question.audioText, isAudioLoading, onSpeak)
        }
    }
}

/** The answers, and the explanation once one has been picked. */
@Composable
private fun PracticeQuestionOptions(
    question: PracticeQuestionDto,
    selectedIndex: Int?,
    onSelect: (Int) -> Unit,
) {
    question.options.forEachIndexed { index, option ->
        val isPicked = selectedIndex == index
        val isCorrect = selectedIndex != null && question.answerIndex == index
        OptionRow(option, isPicked, isCorrect, isPicked && !isCorrect, selectedIndex == null) { onSelect(index) }
    }
    if (selectedIndex != null && question.explanation.isNotBlank()) {
        Spacer(Modifier.height(10.dp))
        Text(question.explanation, style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
    }
}

/**
 * The coach's place on a practice question: the same row the lesson uses
 * ([HskCoachRow]), so a learner moving between the two sees one character
 * saying one kind of thing rather than two conventions.
 *
 * [text] is the screen's own context line, moved here instead of duplicated.
 */
@Composable
internal fun PracticeCoachRow(
    character: HskCharacter,
    mood: HskCharacterMood,
    reaction: HskCharacterReaction?,
    reactionKey: Any?,
    text: String,
    modifier: Modifier = Modifier,
) {
    HskCoachRow(
        character = character,
        mood = mood,
        reaction = reaction,
        reactionKey = reactionKey,
        text = text,
        modifier = modifier,
    )
}

@Composable
private fun ExamRun(state: PracticeUiState, language: String, onSelect: (Int) -> Unit, onAdvance: (String) -> Unit, onCancel: () -> Unit, onSpeak: (String) -> Unit) {
    val session = state.examSession ?: return
    val question = session.questions.getOrNull(state.examIndex) ?: return
    // A listening question that has to be asked for is half a question. The
    // Mini App speaks it as the card appears (`course-v3.html:4014`) and so
    // does this; advancing stops the previous one in the view model.
    LaunchedEffect(question.id) { if (question.audioText.isNotBlank()) onSpeak(question.audioText) }
    QuestionShell(stringResource(R.string.practice_progress, state.examIndex + 1, session.questions.size), onCancel) {
        HskGlassSurface(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(18.dp),
            shadowElevation = 7.dp,
        ) {
            Column(Modifier.padding(18.dp)) {
                QuestionText(question.prompt, question.sentence, "", question.audioText, state.isReviewAudioLoading, onSpeak)
                Spacer(Modifier.height(14.dp))
                question.options.forEachIndexed { index, option -> OptionRow(option, state.examSelectedIndex == index, false, false, state.examSelectedIndex == null) { onSelect(index) } }
            }
        }
        if (state.error != null && state.error !is ApiError.LimitReached) {
            Spacer(Modifier.height(12.dp))
            ErrorPill(stringResource(state.error.messageRes))
        }
        PrimaryAction(
            text = if (state.examIndex == session.questions.lastIndex) stringResource(R.string.practice_finish) else stringResource(R.string.lesson_next),
            enabled = state.examSelectedIndex != null,
            loading = state.isCompleting,
        ) { onAdvance(language) }
    }
}

@Composable
private fun ExamSummary(state: PracticeUiState, onDone: () -> Unit) {
    val result = state.examResult ?: return
    val level = state.examLevel.removePrefix("hsk").ifBlank { "1" }
    val outcome = result.toCompletionOutcome()
    CompletionSummaryShell(
        outcome = outcome,
        body = stringResource(if (result.passed) R.string.exam_result_passed_body else R.string.exam_result_failed_body, level),
        onDone = onDone,
    ) {
        Text(stringResource(R.string.exam_result_score, result.score, result.total), style = MaterialTheme.typography.titleMedium, color = PompColors.Ink)
        Spacer(Modifier.height(10.dp))
        result.sectionScores.forEach { (section, score) ->
            if (score.total > 0) {
                HskGlassSurface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(14.dp),
                    shadowElevation = 4.dp,
                ) {
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
    // The Next button ends this column, and the tab bar floats over it.
    Column(
        Modifier
            .fillMaxSize()
            .padding(start = 20.dp, end = 20.dp, top = 20.dp)
            .padding(bottom = 20.dp + LocalMainBottomInset.current),
    ) {
        Row(
            Modifier.fillMaxWidth(),
            // A blank title means the coach is carrying it (see PracticeRun);
            // the close button then keeps to its own side rather than
            // drifting left into the gap an empty label leaves behind.
            horizontalArrangement = if (title.isBlank()) Arrangement.End else Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (title.isNotBlank()) {
                Text(title, style = MaterialTheme.typography.titleMedium, color = PompColors.Ink)
            }
            HskGlassButton(
                text = stringResource(R.string.action_close),
                onClick = onCancel,
            )
        }
        Spacer(Modifier.height(if (title.isBlank()) 6.dp else 16.dp)); content()
    }
}

/**
 * The body of a question: the instruction, the sentence, and — when the
 * question is a listening one — a speaker instead of the words.
 *
 * `audioText` is what the learner is meant to HEAR. It used to be printed when
 * `sentence` was empty, which is exactly when it must not be: "Eshiting va
 * to'g'ri javobni tanlang" with 您 written above the options is not a listening
 * question, it is the answer. The same fallback left a gap-fill with no
 * sentence showing nothing at all.
 *
 * The Mini App's rule, which this now matches: a question with `audio_text` is
 * a listening question — speak it, never show it (`course-v3.html:4014`).
 */
@Composable
private fun QuestionText(
    prompt: String,
    sentence: String,
    pinyin: String,
    audioText: String = "",
    isAudioLoading: Boolean = false,
    onSpeak: ((String) -> Unit)? = null,
) {
    if (prompt.isNotBlank()) Text(prompt, style = MaterialTheme.typography.titleLarge, color = PompColors.Ink, fontWeight = FontWeight.SemiBold)
    if (audioText.isNotBlank() && onSpeak != null) {
        Spacer(Modifier.height(10.dp))
        Surface(
            color = PompColors.CinnabarSoft,
            shape = RoundedCornerShape(999.dp),
            modifier = Modifier.size(46.dp).clickable(enabled = !isAudioLoading) { onSpeak(audioText) },
        ) {
            Box(contentAlignment = Alignment.Center) {
                if (isAudioLoading) {
                    HskBrandLoader(compact = true)
                } else {
                    Icon(
                        Icons.Filled.VolumeUp,
                        contentDescription = stringResource(R.string.dictionary_listen),
                        tint = PompColors.Cinnabar,
                        modifier = Modifier.size(22.dp),
                    )
                }
            }
        }
    }
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
private fun PrimaryAction(
    text: String,
    enabled: Boolean,
    loading: Boolean = false,
    onClick: () -> Unit,
) {
    Spacer(Modifier.height(16.dp))
    HskPrimaryButton(
        text = text,
        onClick = onClick,
        enabled = enabled,
        loading = loading,
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun PracticeSummary(state: PracticeUiState, onDone: () -> Unit) {
    val result = state.result ?: return
    val outcome = result.toCompletionOutcome(mode = state.session?.mode.orEmpty())
    CompletionSummaryShell(
        outcome = outcome,
        body = stringResource(R.string.practice_result_body, result.score, result.total),
        onDone = onDone,
    ) {
        result.wrongItems.take(4).forEach { item ->
            HskGlassSurface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(14.dp),
                shadowElevation = 4.dp,
            ) {
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
private fun CompletionSummaryShell(
    outcome: PracticeCompletionOutcome,
    body: String,
    onDone: () -> Unit,
    extra: @Composable ColumnScope.() -> Unit = {},
) {
    // The result first, the flame after it — the Mini App's order. A round
    // that did not move the streak goes straight back, with no empty screen.
    var streakStep by rememberSaveable(outcome.kind, outcome.score, outcome.total) {
        mutableStateOf(false)
    }
    if (streakStep) {
        PracticeStreakStep(outcome = outcome, onDone = onDone)
        return
    }
    val advance: () -> Unit = {
        if (outcome.hasStreakEvent) streakStep = true else onDone()
    }
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(
            start = 20.dp,
            end = 20.dp,
            top = 20.dp,
            bottom = 20.dp + LocalMainBottomInset.current,
        ),
    ) {
        item {
            PracticeCompletionHero(outcome = outcome)
            Spacer(Modifier.height(12.dp))
            Text(body, style = MaterialTheme.typography.bodyLarge, color = PompColors.InkSecondary)
            Spacer(Modifier.height(16.dp))
            Column { extra() }
            PrimaryAction(
                text = if (outcome.hasStreakEvent) {
                    stringResource(R.string.lesson_next)
                } else {
                    stringResource(R.string.practice_back_to_tools)
                },
                enabled = true,
                onClick = advance,
            )
        }
    }
}

@Composable
private fun ErrorPill(text: String) {
    Surface(color = PompColors.FlameSoft, shape = RoundedCornerShape(12.dp), modifier = Modifier.fillMaxWidth()) {
        Text(text, style = MaterialTheme.typography.bodyMedium, color = PompColors.Flame, modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp))
    }
}
