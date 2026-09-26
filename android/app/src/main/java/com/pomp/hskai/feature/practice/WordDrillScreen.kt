package com.pomp.hskai.feature.practice

import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.asPaddingValues
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.TextButton
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import com.pomp.hskai.core.design.components.HskAnswerOption
import com.pomp.hskai.core.design.components.HskBubbleTail
import com.pomp.hskai.core.design.components.HskCharacterStage
import com.pomp.hskai.core.design.components.HskSceneBackground
import com.pomp.hskai.core.design.components.HskSpeechBubble
import com.pomp.hskai.core.design.components.HskStageCoach
import com.pomp.hskai.core.design.components.HskStageHeading
import com.pomp.hskai.core.design.components.hskOptionState
import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.core.design.components.HskBrandLoader
import com.pomp.hskai.core.design.components.HskCoachBeside
import com.pomp.hskai.core.design.components.HskCoachRow
import com.pomp.hskai.core.design.components.HskGlassIconButton
import com.pomp.hskai.core.design.components.HskGlassSurface
import com.pomp.hskai.core.design.components.HskPrimaryButton
import com.pomp.hskai.core.design.components.hskReactionFor
import com.pomp.hskai.feature.assistant.AssistantScreen
import com.pomp.hskai.feature.assistant.wordDrillAssistantContext
import com.pomp.hskai.feature.limit.LimitGate
import com.pomp.hskai.feature.limit.SectionLimitOverlay

/**
 * The Mini App's adaptive drill screen.
 *
 * Recognition asks the learner to find the character behind a pinyin and a
 * meaning; pronunciation shows the character and listens. Both draw their
 * words from the same adviser, so the review schedule sees every answer.
 */
@Composable
fun WordDrillScreen(
    state: WordDrillUiState,
    limit: LimitGate,
    onChoose: (String) -> Unit,
    onSpeak: () -> Unit,
    onSkipSpoken: () -> Unit,
    onAdvance: () -> Unit,
    onRetry: () -> Unit,
    onClose: () -> Unit,
) {
    AssistantScreen(wordDrillAssistantContext(state), bottomBar = false)
    Surface(modifier = Modifier.fillMaxSize(), color = PompColors.Paper) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding(),
        ) {
            // The result opens with its own clip and has no bar over it.
            if (!state.finished) PracticeStageTopBar(progress = state.progress, onClose = onClose)

            when {
                state.isLoading -> Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) { HskBrandLoader() }

                state.limitReached -> SectionLimitOverlay(
                    sectionTitle = stringResource(
                        if (state.mode == DrillMode.RECOGNITION) {
                            R.string.practice_characters_title
                        } else {
                            R.string.practice_pronunciation_row_title
                        }
                    ),
                    limit = limit,
                    reason = state.limitText ?: stringResource(R.string.limit_practice_reason),
                    resetAt = state.resetAt,
                    onClose = onClose,
                )

                state.finished -> DrillSummary(
                    mode = state.mode,
                    correct = state.correctCount,
                    total = state.total,
                    onDone = onClose,
                )

                state.current == null -> DrillEmpty(onRetry = onRetry, onClose = onClose)

                else -> DrillQuestionBody(
                    state = state,
                    question = state.current!!,
                    onChoose = onChoose,
                    onSpeak = onSpeak,
                    onSkipSpoken = onSkipSpoken,
                    onAdvance = onAdvance,
                )
            }
        }
    }
}

/**
 * One drill question in the lesson's stage layout, over the faded landscape.
 *
 * Recognition stands the coach beside the word's sound and meaning and puts
 * the four characters under it; a tap picks, Tekshirish checks. Pronunciation
 * is the lesson's pronunciation card: the character in the coach's bubble,
 * the coach, and a wide microphone.
 */
@Composable
private fun DrillQuestionBody(
    state: WordDrillUiState,
    question: DrillQuestion,
    onChoose: (String) -> Unit,
    onSpeak: () -> Unit,
    onSkipSpoken: () -> Unit,
    onAdvance: () -> Unit,
) {
    val recognition = state.mode == DrillMode.RECOGNITION
    var picked by remember(state.index) { mutableStateOf<String?>(null) }
    val character = drillCharacterFor(state.mode)
    val mood = practiceMoodFor(if (state.isAnswered) state.wasCorrect else null)
    val reaction = if (state.isAnswered) {
        hskReactionFor(correct = state.wasCorrect, streak = state.answerStreak)
    } else {
        null
    }
    val reactionKey = state.index to state.isAnswered
    // A full-screen route: the footer only has the gesture bar to clear.
    val bottomInset = WindowInsets.navigationBars.asPaddingValues().calculateBottomPadding()

    Box(modifier = Modifier.fillMaxSize()) {
        HskSceneBackground(Modifier.fillMaxSize())
        Column(modifier = Modifier.fillMaxSize()) {
            HskStageHeading(
                stringResource(
                    if (recognition) R.string.drill_recognition_prompt else R.string.drill_pronunciation_prompt
                )
            )
            BoxWithConstraints(modifier = Modifier.weight(1f).fillMaxWidth()) {
                val viewport = maxHeight
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .verticalScroll(rememberScrollState())
                        .heightIn(min = viewport)
                        .padding(start = 16.dp, end = 16.dp, top = 14.dp, bottom = 20.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = if (recognition) Arrangement.SpaceBetween else Arrangement.Center,
                ) {
                    if (recognition) {
                        HskStageCoach(
                            character = character,
                            mood = mood,
                            reaction = reaction,
                            reactionKey = reactionKey,
                        ) {
                            // The word to find, by its sound and its meaning.
                            Text(
                                text = question.pinyin,
                                style = PompTextStyles.pinyin.copy(fontSize = 17.sp),
                                fontWeight = FontWeight.Medium,
                                color = PompColors.CinnabarDark,
                            )
                            Spacer(Modifier.height(4.dp))
                            Text(
                                text = question.meaning,
                                style = MaterialTheme.typography.titleMedium.copy(fontSize = 16.sp),
                                color = PompColors.Ink,
                            )
                        }
                        RecognitionOptions(
                            state = state,
                            question = question,
                            picked = picked,
                            onPick = { picked = it },
                        )
                    } else {
                        PronunciationStage(
                            state = state,
                            question = question,
                            coach = {
                                HskCharacterStage(
                                    character = character,
                                    mood = mood,
                                    reaction = reaction,
                                    reactionKey = reactionKey,
                                    modifier = Modifier.size(width = 150.dp, height = 165.dp),
                                )
                            },
                            onSpeak = onSpeak,
                            onSkipSpoken = onSkipSpoken,
                        )
                    }
                    state.error?.let { error ->
                        PracticeErrorPill(stringResource(error.messageRes), Modifier.padding(top = 12.dp))
                    }
                }
            }
            when {
                state.isAnswered -> PracticeFeedbackPanel(
                    isCorrect = state.wasCorrect,
                    verdictSuffix = state.spokenScore?.let { " $it%" }.orEmpty(),
                    lines = if (state.wasCorrect) emptyList() else listOf("${question.hanzi} · ${question.pinyin}"),
                    continueText = stringResource(R.string.lesson_next),
                    loading = false,
                    onContinue = onAdvance,
                    bottomInset = bottomInset,
                )
                recognition -> PracticeCheckFooter(
                    enabled = picked != null,
                    onCheck = { picked?.let(onChoose) },
                    bottomInset = bottomInset,
                )
            }
        }
    }
}

/** The four characters, two by two: the grid keeps them large enough to tell apart. */
@Composable
private fun RecognitionOptions(
    state: WordDrillUiState,
    question: DrillQuestion,
    picked: String?,
    onPick: (String) -> Unit,
) {
    val correctIndex = question.options.indexOf(question.hanzi)
    val chosen = if (state.isAnswered) state.selected else picked
    val chosenIndex = chosen?.let { question.options.indexOf(it) }?.takeIf { it >= 0 }
    Column(
        modifier = Modifier.fillMaxWidth().padding(top = 20.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        question.options.chunked(2).forEachIndexed { row, pair ->
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                pair.forEachIndexed { column, option ->
                    val index = row * 2 + column
                    HskAnswerOption(
                        text = option,
                        state = hskOptionState(
                            index = index,
                            correctIndex = correctIndex,
                            selectedIndex = chosenIndex,
                            isAnswered = state.isAnswered,
                        ),
                        enabled = !state.isAnswered,
                        onClick = { onPick(option) },
                        modifier = Modifier.weight(1f),
                        minHeight = 76.dp,
                        hanziSize = 32.sp,
                    )
                }
            }
        }
    }
}

/**
 * The lesson's pronunciation card for a drilled character: what to say in the
 * coach's bubble, the coach under it, a wide microphone, and a quiet way out.
 */
@Composable
private fun PronunciationStage(
    state: WordDrillUiState,
    question: DrillQuestion,
    coach: @Composable () -> Unit,
    onSpeak: () -> Unit,
    onSkipSpoken: () -> Unit,
) {
    val context = LocalContext.current
    var permissionDenied by remember { mutableStateOf(false) }
    val permission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        permissionDenied = !granted
        if (granted) onSpeak()
    }
    val micEnabled = !state.isRecording && !state.isScoring && !state.isAnswered

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        HskSpeechBubble(tail = HskBubbleTail.Bottom) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = question.hanzi,
                    style = PompTextStyles.hanziLarge,
                    color = PompColors.Ink,
                )
                Text(
                    text = question.pinyin,
                    style = PompTextStyles.pinyin.copy(fontSize = 17.sp),
                    fontWeight = FontWeight.Medium,
                    color = PompColors.CinnabarDark,
                    textAlign = TextAlign.Center,
                )
                Text(
                    text = question.meaning,
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                    textAlign = TextAlign.Center,
                )
            }
        }
        Spacer(Modifier.height(10.dp))
        coach()
        Spacer(Modifier.height(18.dp))
        val micShape = RoundedCornerShape(20.dp)
        Box(modifier = Modifier.padding(bottom = 6.dp)) {
            Box(
                modifier = Modifier
                    .matchParentSize()
                    .offset(y = 6.dp)
                    .clip(micShape)
                    .background(if (micEnabled) PompColors.CinnabarDark else PompColors.Divider),
            )
            Surface(
                onClick = {
                    val granted = ContextCompat.checkSelfPermission(
                        context,
                        Manifest.permission.RECORD_AUDIO,
                    ) == PackageManager.PERMISSION_GRANTED
                    if (granted) {
                        permissionDenied = false
                        onSpeak()
                    } else {
                        permission.launch(Manifest.permission.RECORD_AUDIO)
                    }
                },
                enabled = micEnabled,
                shape = micShape,
                color = if (state.isRecording) PompColors.CinnabarDark else PompColors.Cinnabar,
                modifier = Modifier.size(width = 208.dp, height = 80.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = Icons.Filled.Mic,
                        contentDescription = stringResource(R.string.voice_a11y_mic),
                        tint = PompColors.Paper,
                        modifier = Modifier.size(36.dp),
                    )
                }
            }
        }
        Spacer(Modifier.height(9.dp))
        Text(
            text = when {
                state.isRecording -> stringResource(R.string.foundation_speak_listening)
                state.isScoring -> stringResource(R.string.foundation_speak_checking)
                else -> stringResource(R.string.foundation_speak_check)
            },
            style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.sp),
            color = PompColors.InkDisabled,
            textAlign = TextAlign.Center,
        )
        if (permissionDenied) {
            Spacer(Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.lesson_microphone_permission_required),
                style = MaterialTheme.typography.bodySmall,
                color = PompColors.Flame,
                textAlign = TextAlign.Center,
            )
        }
        if (!state.isAnswered) {
            Spacer(Modifier.height(20.dp))
            // A quiet way out, not a second button competing with the microphone.
            TextButton(onClick = onSkipSpoken, enabled = !state.isRecording && !state.isScoring) {
                Text(
                    text = stringResource(R.string.foundation_speak_skip),
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.sp,
                    color = PompColors.InkDisabled,
                    textAlign = TextAlign.Center,
                )
            }
        }
    }
}

@Composable
private fun DrillSummary(mode: DrillMode, correct: Int, total: Int, onDone: () -> Unit) {
    val outcome = drillCompletionOutcome(
        kind = if (mode == DrillMode.RECOGNITION) {
            PracticeCompletionKind.RECOGNITION
        } else {
            PracticeCompletionKind.PRONUNCIATION
        },
        correct = correct,
        total = total,
    )
    PracticeCompletionClip(outcome = outcome) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .navigationBarsPadding()
                .padding(24.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            PracticeCompletionHero(outcome = outcome)
            Spacer(Modifier.height(24.dp))
            Surface(
                onClick = onDone,
                color = PompColors.Cinnabar,
                shape = RoundedCornerShape(14.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    text = stringResource(R.string.action_close),
                    style = MaterialTheme.typography.titleMedium,
                    color = PompColors.Paper,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 15.dp),
                )
            }
        }
    }
}

@Composable
private fun DrillEmpty(onRetry: () -> Unit, onClose: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = stringResource(R.string.error_unknown),
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(16.dp))
        HskPrimaryButton(
            text = stringResource(R.string.action_retry),
            onClick = onRetry,
        )
        Spacer(Modifier.height(10.dp))
        Text(
            text = stringResource(R.string.action_close),
            style = MaterialTheme.typography.labelLarge,
            color = PompColors.InkDisabled,
            modifier = Modifier
                .clickable(onClick = onClose)
                .padding(8.dp),
        )
    }
}
