package com.pomp.hskai.feature.lesson

import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Settings
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
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.settings.PinyinVisibility
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.GrammarCard
import com.pomp.hskai.domain.model.LessonCard
import com.pomp.hskai.domain.model.MatchPairsCard
import com.pomp.hskai.domain.model.NewWordCard
import com.pomp.hskai.domain.model.PronunciationCard
import com.pomp.hskai.domain.model.ReverseBuilderCard
import com.pomp.hskai.domain.model.SentenceBuilderCard
import com.pomp.hskai.domain.model.UnsupportedCard
import com.pomp.hskai.feature.limit.LimitGate

@Composable
internal fun PrimaryAction(
    text: String,
    onClick: () -> Unit,
    enabled: Boolean = true,
) {
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
        Text(text = text, style = MaterialTheme.typography.labelLarge)
    }
}

@Composable
internal fun SecondaryAction(text: String, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 48.dp),
        shape = RoundedCornerShape(14.dp),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelLarge,
            color = PompColors.InkSecondary,
        )
    }
}

@Composable
fun LessonScreen(
    state: LessonUiState,
    limit: LimitGate? = null,
    pinyin: PinyinVisibility,
    onAnswerChoice: (ChoiceCard, Int) -> Unit,
    onAnswerBuilder: (LessonCard, List<String>) -> Unit,
    onAnswerPairs: (MatchPairsCard, List<Pair<Int, Int>>) -> Unit,
    onAcknowledge: () -> Unit,
    onAdvance: () -> Unit,
    onPlayAudio: (String) -> Unit,
    onRetryCompletion: () -> Unit,
    onOpenPinyinSettings: () -> Unit,
    onOpenWriter: (WriterTarget) -> Unit,
    onCloseWriter: () -> Unit,
    onExit: () -> Unit,
    modifier: Modifier = Modifier,
) {
    @Suppress("UNUSED_VARIABLE")
    val ignoredLimit = limit
    val outcome = state.outcome
    val context = LocalContext.current
    val app = remember(context) { context.applicationContext as? HskAiApplication }
    var rankBefore by remember(state.lesson) { mutableStateOf<Int?>(null) }
    var rankUp by remember(state.lesson) { mutableStateOf<LessonRankUp?>(null) }

    LaunchedEffect(state.lesson) {
        rankUp = null
        if (state.lesson == null) {
            rankBefore = null
            return@LaunchedEffect
        }
        rankBefore = when (val result = app?.featureRepository?.rating()) {
            is ApiResult.Success -> result.value.rank.takeIf { it > 0 }
            else -> null
        }
    }

    LaunchedEffect(outcome) {
        val completed = outcome as? LessonOutcome.Completed ?: return@LaunchedEffect
        rankUp = null
        if (completed.duplicate) return@LaunchedEffect
        val before = rankBefore ?: return@LaunchedEffect
        val after = when (val result = app?.featureRepository?.rating()) {
            is ApiResult.Success -> result.value.rank.takeIf { it > 0 }
            else -> null
        } ?: return@LaunchedEffect
        if (after < before) rankUp = LessonRankUp(before = before, after = after)
    }

    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        when {
            state.isLoading -> Centered { CircularProgressIndicator(color = PompColors.Cinnabar) }
            state.lesson == null -> Centered {
                Text(
                    text = (state.error as? ApiError.LimitReached)?.limitText
                        ?: stringResource(state.error?.messageRes ?: R.string.error_unknown),
                    style = MaterialTheme.typography.bodyLarge,
                    color = PompColors.InkSecondary,
                    textAlign = TextAlign.Center,
                )
                Spacer(Modifier.height(16.dp))
                SecondaryAction(stringResource(R.string.action_close), onExit)
            }
            outcome is LessonOutcome.PreviewExhausted -> PreviewEndBlock(onExit)
            outcome is LessonOutcome.Completed -> CompletedBlock(outcome, rankUp, onExit)
            outcome is LessonOutcome.Failed -> FailedBlock(outcome, onRetryCompletion, onExit)
            else -> LessonBody(
                state = state,
                pinyin = pinyin,
                onAnswerChoice = onAnswerChoice,
                onAnswerBuilder = onAnswerBuilder,
                onAnswerPairs = onAnswerPairs,
                onAcknowledge = onAcknowledge,
                onAdvance = onAdvance,
                onPlayAudio = onPlayAudio,
                onOpenPinyinSettings = onOpenPinyinSettings,
                onOpenWriter = onOpenWriter,
                onCloseWriter = onCloseWriter,
                onExit = onExit,
            )
        }
    }
}

@Composable
private fun Centered(content: @Composable () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) { content() }
}

@Composable
private fun LessonBody(
    state: LessonUiState,
    pinyin: PinyinVisibility,
    onAnswerChoice: (ChoiceCard, Int) -> Unit,
    onAnswerBuilder: (LessonCard, List<String>) -> Unit,
    onAnswerPairs: (MatchPairsCard, List<Pair<Int, Int>>) -> Unit,
    onAcknowledge: () -> Unit,
    onAdvance: () -> Unit,
    onPlayAudio: (String) -> Unit,
    onOpenPinyinSettings: () -> Unit,
    onOpenWriter: (WriterTarget) -> Unit,
    onCloseWriter: () -> Unit,
    onExit: () -> Unit,
) {
    val haptics = LocalHapticFeedback.current
    val card = state.currentCard ?: return
    var selectedIndex by remember(state.cardIndex) { mutableStateOf<Int?>(null) }

    LaunchedEffect(state.answer, state.cardIndex) {
        val answer = state.answer
        if (answer is AnswerState.Checked) {
            haptics.performHapticFeedback(
                if (answer.isCorrect) HapticFeedbackType.LongPress else HapticFeedbackType.TextHandleMove
            )
        }
    }

    val writeTarget = state.writeTarget
    Box(modifier = Modifier.fillMaxSize()) {
        Column(modifier = Modifier.fillMaxSize()) {
            LessonTopBar(
                progress = state.progress,
                hearts = state.hearts,
                onOpenPinyinSettings = onOpenPinyinSettings,
                onExit = onExit,
            )
            LessonStageLine(
                index = state.cardIndex + 1,
                total = state.totalCards,
                title = state.currentSectionTitle,
            )

            Column(
                modifier = Modifier
                    .weight(1f)
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 18.dp, vertical = 10.dp),
            ) {
                when (card) {
                    is NewWordCard -> NewWordCardView(card, pinyin)
                    is GrammarCard -> GrammarCardView(card, pinyin)
                    is PronunciationCard -> PronunciationCardView(card, pinyin, state.isAudioLoading, onPlayAudio, onAcknowledge)
                    is ChoiceCard -> ChoiceCardView(
                        card = card,
                        pinyin = pinyin,
                        selectedIndex = selectedIndex,
                        isAnswered = state.isAnswered,
                        isAudioLoading = state.isAudioLoading,
                        onPlayAudio = onPlayAudio,
                        onSelect = { index -> selectedIndex = index; onAnswerChoice(card, index) },
                    )
                    is SentenceBuilderCard -> SentenceBuilderCardView(card, state.isAnswered) { onAnswerBuilder(card, it) }
                    is ReverseBuilderCard -> ReverseBuilderCardView(card, pinyin, state.isAnswered) { onAnswerBuilder(card, it) }
                    is MatchPairsCard -> MatchPairsCardView(card, state.isAnswered) { onAnswerPairs(card, it) }
                    is UnsupportedCard -> UnsupportedCardView(card, onAcknowledge)
                }
                state.audioError?.let { error ->
                    Spacer(Modifier.height(12.dp))
                    Text(
                        text = stringResource(error.messageRes),
                        style = MaterialTheme.typography.bodyMedium,
                        color = PompColors.Flame,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                Spacer(Modifier.height(24.dp))
            }

            FooterBar(state = state, card = card, onAcknowledge = onAcknowledge, onAdvance = onAdvance)
        }

        if (writeTarget != null) {
            WriterButton(
                onClick = { onOpenWriter(writeTarget) },
                modifier = Modifier.align(Alignment.BottomEnd).padding(end = 18.dp, bottom = 152.dp),
            )
        }
    }

    state.writerChar?.let { target ->
        HanziWriterSheet(
            hanzi = target.hanzi,
            pinyin = target.pinyin,
            meaning = target.meaning,
            strokes = state.writerStrokes,
            isLoading = state.isWriterLoading,
            onReplay = { onOpenWriter(target) },
            onDismiss = onCloseWriter,
        )
    }
}

@Composable
private fun WriterButton(onClick: () -> Unit, modifier: Modifier = Modifier) {
    val writerDepth = if (PompColors.IsDark) PompColors.GoldSoft else WriterDepthLight
    Box(modifier = modifier.size(60.dp), contentAlignment = Alignment.TopStart) {
        Box(
            modifier = Modifier
                .size(56.dp)
                .offset(y = 4.dp)
                .clip(CircleShape)
                .background(writerDepth),
        )
        Surface(
            onClick = onClick,
            shape = CircleShape,
            color = PompColors.Gold,
            modifier = Modifier.size(56.dp),
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = Icons.Filled.Edit,
                    contentDescription = stringResource(R.string.lesson_writer_replay),
                    tint = PompColors.PlanOnGold,
                    modifier = Modifier.size(24.dp),
                )
            }
        }
    }
}

private val WriterDepthLight = Color(0xFF9A7420)

@Composable
private fun LessonTopBar(
    progress: Float,
    hearts: Int,
    onOpenPinyinSettings: () -> Unit,
    onExit: () -> Unit,
) {
    val heartColor = if (PompColors.IsDark) PompColors.Flame else PompColors.Cinnabar
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .statusBarsPadding()
            .padding(start = 16.dp, end = 16.dp, top = 14.dp, bottom = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(11.dp),
    ) {
        Surface(
            onClick = onExit,
            shape = CircleShape,
            color = PompColors.PaperRaised,
            border = BorderStroke(1.dp, PompColors.Divider),
            modifier = Modifier.size(30.dp),
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(Icons.Filled.Close, stringResource(R.string.action_close), tint = PompColors.InkSecondary, modifier = Modifier.size(17.dp))
            }
        }

        val animatedProgress by animateFloatAsState(
            targetValue = progress.coerceIn(0f, 1f),
            animationSpec = tween(durationMillis = 300),
            label = "lessonProgress",
        )
        Box(
            modifier = Modifier.weight(1f).height(9.dp).clip(RoundedCornerShape(6.dp)).background(PompColors.Divider),
        ) {
            Box(
                modifier = Modifier.fillMaxWidth(animatedProgress).height(9.dp).clip(RoundedCornerShape(6.dp)).background(PompColors.Cinnabar),
            )
        }

        Surface(onClick = onOpenPinyinSettings, shape = CircleShape, color = Color.Transparent, modifier = Modifier.size(30.dp)) {
            Box(contentAlignment = Alignment.Center) {
                Icon(Icons.Filled.Settings, stringResource(R.string.lesson_pinyin_title), tint = PompColors.InkDisabled, modifier = Modifier.size(17.dp))
            }
        }

        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(3.dp)) {
            Icon(Icons.Filled.Favorite, contentDescription = null, tint = heartColor, modifier = Modifier.size(15.dp))
            Text(
                text = hearts.toString(),
                style = MaterialTheme.typography.labelLarge.copy(fontSize = 15.sp),
                fontWeight = FontWeight.Medium,
                color = heartColor,
            )
        }
    }
}

@Composable
private fun LessonStageLine(index: Int, total: Int, title: String) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(start = 18.dp, end = 18.dp, top = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = "$index / $total",
            style = MaterialTheme.typography.labelSmall.copy(fontSize = 11.sp),
            fontWeight = FontWeight.SemiBold,
            color = PompColors.CinnabarDark,
        )
        Text(
            text = title,
            style = MaterialTheme.typography.labelLarge.copy(fontSize = 12.sp),
            fontWeight = FontWeight.SemiBold,
            color = PompColors.Ink,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
            textAlign = TextAlign.End,
        )
    }
}

@Composable
private fun FooterBar(
    state: LessonUiState,
    card: LessonCard,
    onAcknowledge: () -> Unit,
    onAdvance: () -> Unit,
) {
    val answer = state.answer
    if (answer is AnswerState.Checked) {
        Surface(
            color = if (answer.isCorrect) PompColors.JadeSoft else PompColors.FlameSoft,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(
                modifier = Modifier.navigationBarsPadding().padding(start = 16.dp, end = 16.dp, top = 14.dp, bottom = 18.dp),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = if (answer.isCorrect) Icons.Filled.CheckCircle else Icons.Filled.Cancel,
                        contentDescription = null,
                        tint = if (answer.isCorrect) PompColors.Jade else PompColors.Flame,
                        modifier = Modifier.size(22.dp),
                    )
                    Spacer(Modifier.size(9.dp))
                    Column {
                        Text(
                            text = stringResource(if (answer.isCorrect) R.string.lesson_correct else R.string.lesson_wrong),
                            style = MaterialTheme.typography.titleMedium.copy(fontSize = 15.sp),
                            fontWeight = FontWeight.Medium,
                            color = if (answer.isCorrect) PompColors.Jade else PompColors.Flame,
                        )
                        if (answer.explanation.isNotBlank()) {
                            Text(
                                text = answer.explanation,
                                style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.sp),
                                color = PompColors.InkSecondary,
                            )
                        }
                    }
                }
                Spacer(Modifier.height(10.dp))
                FlowButton(
                    text = stringResource(R.string.lesson_next),
                    color = if (answer.isCorrect) PompColors.Jade else PompColors.Flame,
                    onClick = onAdvance,
                )
            }
        }
        return
    }

    val needsAcknowledge = card is NewWordCard || card is GrammarCard
    if (needsAcknowledge) {
        Box(
            modifier = Modifier.navigationBarsPadding().padding(start = 16.dp, end = 16.dp, bottom = 16.dp),
        ) {
            FlowButton(
                text = stringResource(R.string.lesson_next),
                color = PompColors.Cinnabar,
                shape = RoundedCornerShape(14.dp),
                onClick = onAcknowledge,
            )
        }
    }
}

@Composable
private fun FlowButton(
    text: String,
    color: Color,
    onClick: () -> Unit,
    shape: RoundedCornerShape = RoundedCornerShape(13.dp),
) {
    Surface(onClick = onClick, color = color, shape = shape, modifier = Modifier.fillMaxWidth()) {
        Text(
            text = text,
            style = MaterialTheme.typography.titleMedium.copy(fontSize = 16.sp),
            fontWeight = FontWeight.Medium,
            color = PompColors.Paper,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth().padding(vertical = 14.dp),
        )
    }
}

@Composable
private fun PreviewEndBlock(onExit: () -> Unit) {
    Centered {
        Text(
            text = stringResource(R.string.lesson_preview_over_title),
            style = MaterialTheme.typography.headlineMedium,
            color = PompColors.Ink,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(12.dp))
        Text(
            text = stringResource(R.string.lesson_preview_over_body),
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(24.dp))
        SecondaryAction(stringResource(R.string.action_close), onExit)
    }
}

@Composable
private fun CompletedBlock(
    outcome: LessonOutcome.Completed,
    rankUp: LessonRankUp?,
    onExit: () -> Unit,
) {
    LessonCompletionCelebration(outcome = outcome, rankUp = rankUp, onExit = onExit)
}

@Composable
private fun FailedBlock(
    outcome: LessonOutcome.Failed,
    onRetry: () -> Unit,
    onExit: () -> Unit,
) {
    Centered {
        Text(
            text = stringResource(R.string.lesson_save_failed),
            style = MaterialTheme.typography.titleMedium,
            color = PompColors.Flame,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = (outcome.error as? ApiError.LimitReached)?.limitText ?: stringResource(outcome.error.messageRes),
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(20.dp))
        PrimaryAction(stringResource(R.string.action_retry), onClick = onRetry)
        Spacer(Modifier.height(8.dp))
        SecondaryAction(stringResource(R.string.action_close), onExit)
    }
}
