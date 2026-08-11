package com.pomp.hskai.feature.practice

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.data.api.MistakeReviewAnswerResponse
import com.pomp.hskai.data.api.MistakeReviewQuestionDto
import com.pomp.hskai.data.api.PracticeQuestionDto

@Composable
fun PracticeScreen(
    state: PracticeUiState,
    level: String,
    language: String,
    onStartPractice: (PracticeToolSpec, String, String) -> Unit,
    onSelectPracticeOption: (Int) -> Unit,
    onAdvancePractice: (String) -> Unit,
    onResetPractice: () -> Unit,
    onStartMistakeReview: () -> Unit,
    onAnswerReview: (Int) -> Unit,
    onAdvanceReview: () -> Unit,
    onResetReview: () -> Unit,
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
                onStartPractice = onStartPractice,
                onStartMistakeReview = onStartMistakeReview,
            )
        }
    }
}

@Composable
private fun PracticeHome(
    state: PracticeUiState,
    level: String,
    language: String,
    onStartPractice: (PracticeToolSpec, String, String) -> Unit,
    onStartMistakeReview: () -> Unit,
) {
    val tools = remember {
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
                skill = "listening",
                titleRes = R.string.practice_listening_title,
                bodyRes = R.string.practice_listening_body,
                glyph = "听",
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
                skill = "pronunciation",
                titleRes = R.string.practice_pronunciation_title,
                bodyRes = R.string.practice_pronunciation_body,
                glyph = "声",
            ),
            PracticeToolSpec(
                mode = "mock",
                skill = "",
                titleRes = R.string.practice_test_title,
                bodyRes = R.string.practice_test_body,
                glyph = "HSK",
            ),
            PracticeToolSpec(
                mode = "placement",
                skill = "",
                titleRes = R.string.practice_placement_title,
                bodyRes = R.string.practice_placement_body,
                glyph = "测",
            ),
        )
    }
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text(
                text = stringResource(R.string.practice_title),
                style = MaterialTheme.typography.headlineMedium,
                color = PompColors.Ink,
            )
            Text(
                text = stringResource(R.string.practice_subtitle, level.uppercase()),
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.InkSecondary,
            )
            state.error?.let {
                Spacer(Modifier.height(12.dp))
                ErrorPill(stringResource(it.messageRes))
            }
        }
        item {
            MistakesCard(
                state = state,
                onStartMistakeReview = onStartMistakeReview,
            )
        }
        items(tools) { tool ->
            ToolCard(
                tool = tool,
                busy = state.isStarting,
                onClick = { onStartPractice(tool, level, language) },
            )
        }
    }
}

@Composable
private fun MistakesCard(
    state: PracticeUiState,
    onStartMistakeReview: () -> Unit,
) {
    val total = state.mistakes?.summary?.total ?: 0
    Surface(
        color = PompColors.CinnabarSoft,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, PompColors.Cinnabar),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        text = stringResource(R.string.practice_mistakes_title),
                        style = MaterialTheme.typography.titleMedium,
                        color = PompColors.Ink,
                    )
                    Text(
                        text = stringResource(R.string.practice_mistakes_body, total),
                        style = MaterialTheme.typography.bodyMedium,
                        color = PompColors.InkSecondary,
                    )
                }
                if (state.isLoadingMistakes) {
                    CircularProgressIndicator(color = PompColors.Cinnabar)
                }
            }
            Spacer(Modifier.height(12.dp))
            Button(
                onClick = onStartMistakeReview,
                enabled = total > 0 && !state.isStarting,
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 48.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = PompColors.Cinnabar,
                    contentColor = PompColors.Paper,
                ),
            ) {
                Text(stringResource(R.string.practice_review_mistakes))
            }
        }
    }
}

@Composable
private fun ToolCard(
    tool: PracticeToolSpec,
    busy: Boolean,
    onClick: () -> Unit,
) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(enabled = !busy, onClick = onClick),
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Surface(
                color = PompColors.GoldSoft,
                shape = RoundedCornerShape(14.dp),
            ) {
                Text(
                    text = tool.glyph,
                    style = MaterialTheme.typography.titleMedium,
                    color = PompColors.Ink,
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
                )
            }
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(start = 14.dp),
            ) {
                Text(
                    text = stringResource(tool.titleRes),
                    style = MaterialTheme.typography.titleMedium,
                    color = PompColors.Ink,
                )
                Text(
                    text = stringResource(tool.bodyRes),
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                )
            }
            Text(
                text = stringResource(R.string.practice_start_short),
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.CinnabarDark,
            )
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
