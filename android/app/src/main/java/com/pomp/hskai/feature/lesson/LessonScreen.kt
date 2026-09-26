package com.pomp.hskai.feature.lesson

import com.pomp.hskai.core.network.ApiError

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.keyframes
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
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
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.PI
import kotlin.math.sin
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskBrandLoader
import com.pomp.hskai.core.design.components.HskBubbleText
import com.pomp.hskai.core.design.components.HskDepthButton
import com.pomp.hskai.core.design.components.HskStageCoach
import com.pomp.hskai.core.design.components.HskStageHeading
import com.pomp.hskai.core.design.components.HskStageProgress
import com.pomp.hskai.core.design.components.HskGlassButton
import com.pomp.hskai.core.design.components.HskGlassIconButton
import com.pomp.hskai.core.design.components.HskPrimaryButton
import com.pomp.hskai.core.design.components.HskSceneBackground
import com.pomp.hskai.core.design.components.rememberExitGuard
import com.pomp.hskai.core.settings.PinyinVisibility
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.ChoiceKind
import com.pomp.hskai.domain.model.GrammarCard
import com.pomp.hskai.domain.model.LessonCard
import com.pomp.hskai.domain.model.MatchPairsCard
import com.pomp.hskai.domain.model.NewWordCard
import com.pomp.hskai.domain.model.PronunciationCard
import com.pomp.hskai.domain.model.ReverseBuilderCard
import com.pomp.hskai.domain.model.SentenceBuilderCard
import com.pomp.hskai.domain.model.UnsupportedCard
import com.pomp.hskai.feature.limit.LimitGate
import com.pomp.hskai.feature.limit.SectionLimitOverlay

@Composable
internal fun PrimaryAction(
    text: String,
    onClick: () -> Unit,
    enabled: Boolean = true,
) {
    HskPrimaryButton(
        text = text,
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
internal fun SecondaryAction(text: String, onClick: () -> Unit) {
    HskGlassButton(
        text = text,
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
    )
}

/**
 * [onAskAssistant] hands a question to the AI chat together with the ready
 * answer the lesson already showed. Null hides the questions — the chat is
 * switched off, or there is no chat on this screen.
 */
@Composable
fun LessonScreen(
    state: LessonUiState,
    limit: LimitGate? = null,
    pinyin: PinyinVisibility,
    onAnswerChoice: (ChoiceCard, Int) -> Unit,
    onAnswerBuilder: (LessonCard, List<String>) -> Unit,
    onAnswerPairs: (MatchPairsCard) -> Unit,
    onAcknowledge: () -> Unit,
    onAdvance: () -> Unit,
    onPlayAudio: (String) -> Unit,
    onSpeakPronunciation: () -> Unit,
    onSkipPronunciation: () -> Unit,
    onRetryCompletion: () -> Unit,
    onOpenPinyinSettings: () -> Unit,
    onOpenWriter: (WriterTarget) -> Unit,
    onShowWriterCharacter: (Int) -> Unit,
    onCloseWriter: () -> Unit,
    onExit: () -> Unit,
    onAskAssistant: ((question: String, readyAnswer: String) -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    val outcome = state.outcome
    // Mid-lesson, the ✕ and the phone's back both ask before leaving; the back
    // used to close the whole app from here. Loaders, errors, the limit block
    // and the celebration are not a lesson in progress and just leave.
    val requestExit = rememberExitGuard(
        running = !state.isLoading &&
            state.lesson != null &&
            outcome is LessonOutcome.InProgress &&
            state.error !is ApiError.LimitReached,
        title = R.string.lesson_exit_title,
        body = R.string.lesson_exit_body,
        onExit = onExit,
    )
    Box(modifier = modifier.fillMaxSize()) {
        Surface(modifier = Modifier.fillMaxSize(), color = PompColors.Paper) {
            when {
                state.isLoading -> Centered { HskBrandLoader() }
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
                outcome is LessonOutcome.Completed ->
                    CompletedBlock(
                        outcome = outcome,
                        isCheckpoint = state.lesson?.isCheckpoint == true,
                        rankBoard = state.rankBoard,
                        onExit = onExit,
                    )
                outcome is LessonOutcome.Failed -> FailedBlock(outcome, onRetryCompletion, onExit)
                else -> Box(modifier = Modifier.fillMaxSize()) {
                    // The faded ink landscape sits under the cards only; the
                    // loader, the errors and the celebration keep their own ground.
                    HskSceneBackground(Modifier.fillMaxSize())
                    LessonBody(
                        state = state,
                        pinyin = pinyin,
                        onAnswerChoice = onAnswerChoice,
                        onAnswerBuilder = onAnswerBuilder,
                        onAnswerPairs = onAnswerPairs,
                        onAcknowledge = onAcknowledge,
                        onAdvance = onAdvance,
                        onPlayAudio = onPlayAudio,
                        onSpeakPronunciation = onSpeakPronunciation,
                        onSkipPronunciation = onSkipPronunciation,
                        onOpenPinyinSettings = onOpenPinyinSettings,
                        onOpenWriter = onOpenWriter,
                        onShowWriterCharacter = onShowWriterCharacter,
                        onCloseWriter = onCloseWriter,
                        onExit = requestExit,
                        onAskAssistant = onAskAssistant,
                    )
                }
            }
        }

        /* Chegara tugaganda dars ustida AMALIY blok chiqadi — quruq matn
           emas, `LimitGate` bergan trial/obuna tugmalari bilan. Kurs
           xaritasi, Mashq va AI Voice bir xil `SectionLimitOverlay` ni
           ko'rsatadi; dars ham shundan chetda qolmasin.

           Ilgari bu blok `LessonLimitCompat.kt` dagi bir xil nomli ikkinchi
           `LessonScreen` da edi. Ikkita bir xil nomli composable — tuzoq:
           chaqiruvga yangi parametr qo'shilishi bilan Kotlin ikkinchisini
           tanlab qo'ydi va blok jim yo'qoldi. Shuning uchun u shu yerda. */
        val spent = state.error as? ApiError.LimitReached
        if (spent != null && limit != null) {
            SectionLimitOverlay(
                sectionTitle = stringResource(R.string.nav_course),
                sourceKey = "course_lesson_limit",
                limit = limit,
                reason = spent.limitText ?: stringResource(R.string.limit_lesson_reason),
                // Qachon ochilishini server aytadi, bu yerda hisoblanmaydi.
                resetAt = spent.resetAt,
                onClose = onExit,
            )
        }
    }
}

/**
 * Same banner, same words the Kurs map shows when it is running on the phone's
 * own copy. A lesson opened offline can be read but not finished, so saying so
 * once at the top beats letting the completion button fail unexplained.
 */
@Composable
private fun StaleBanner() {
    Surface(
        color = PompColors.GoldSoft,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
    ) {
        Text(
            stringResource(R.string.today_stale),
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.Ink,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
        )
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

/**
 * The instruction a card puts at the top of the screen, or null when the card
 * keeps the coach above it instead (teaching cards and the builders, whose
 * own instruction sits inside them).
 */
@Composable
private fun lessonHeading(card: LessonCard, section: String): String? {
    val listenTitle = stringResource(R.string.lesson_listen_and_choose)
    val repeatTitle = stringResource(R.string.lesson_repeat_after_teacher)
    val pairsTitle = stringResource(R.string.lesson_match_pairs)
    return when (card) {
        is ChoiceCard -> card.title.ifBlank { if (card.kind == ChoiceKind.LISTENING) listenTitle else section }
        is PronunciationCard -> repeatTitle
        is MatchPairsCard -> pairsTitle
        else -> null
    }
}

@Composable
private fun LessonBody(
    state: LessonUiState,
    pinyin: PinyinVisibility,
    onAnswerChoice: (ChoiceCard, Int) -> Unit,
    onAnswerBuilder: (LessonCard, List<String>) -> Unit,
    onAnswerPairs: (MatchPairsCard) -> Unit,
    onAcknowledge: () -> Unit,
    onAdvance: () -> Unit,
    onPlayAudio: (String) -> Unit,
    onSpeakPronunciation: () -> Unit,
    onSkipPronunciation: () -> Unit,
    onOpenPinyinSettings: () -> Unit,
    onOpenWriter: (WriterTarget) -> Unit,
    onShowWriterCharacter: (Int) -> Unit,
    onCloseWriter: () -> Unit,
    onExit: () -> Unit,
    onAskAssistant: ((question: String, readyAnswer: String) -> Unit)?,
) {
    val haptics = LocalHapticFeedback.current
    val card = state.currentCard ?: return
    // A question is answered in two steps: a tap only picks, Tekshirish checks.
    var selectedIndex by remember(state.cardIndex) { mutableStateOf<Int?>(null) }

    LaunchedEffect(state.answer, state.cardIndex) {
        val answer = state.answer
        if (answer is AnswerState.Checked) {
            haptics.performHapticFeedback(
                if (answer.isCorrect) HapticFeedbackType.LongPress else HapticFeedbackType.TextHandleMove
            )
        }
    }

    // The new-word card hides the CTA until it has opened, the way `cardWord`
    // keeps `#f-cta` hidden for its first 900ms. Reset per card.
    var newWordOpen by remember(state.cardIndex) { mutableStateOf(false) }

    val writeTarget = state.writeTarget
    // The footer grows with the explanation it carries, so a pencil pinned at a
    // fixed height from the bottom sat on top of the answer whenever the answer
    // had much to say. It is measured instead.
    val density = LocalDensity.current
    var footerHeight by remember { mutableStateOf(0.dp) }

    val lessonEntryKey = state.lesson?.let { it.level to it.order }
    var entryVisible by remember(lessonEntryKey) { mutableStateOf(true) }
    val entryAlpha = remember(lessonEntryKey) { Animatable(1f) }
    LaunchedEffect(lessonEntryKey) {
        if (lessonEntryKey == null) return@LaunchedEffect
        delay(720)
        entryAlpha.animateTo(0f, tween(durationMillis = 360))
        entryVisible = false
    }

    // A voice card speaks as it arrives, the way the Mini App's `cardChoice`
    // (listening) and `cardPron` do: the teacher is heard first, without a tap.
    // It waits for the entry curtain, so the first card is not spoken unseen.
    val play by rememberUpdatedState(onPlayAudio)
    LaunchedEffect(state.cardIndex, entryVisible) {
        if (entryVisible || state.isAnswered) return@LaunchedEffect
        val spoken = when (card) {
            is ChoiceCard -> card.audioText.takeIf { card.kind == ChoiceKind.LISTENING }
            is PronunciationCard -> card.phrase
            else -> null
        }
        if (spoken.isNullOrBlank()) return@LaunchedEffect
        delay(VOICE_CARD_SPEAK_DELAY_MILLIS)
        play(spoken)
    }

    Box(modifier = Modifier.fillMaxSize()) {
        Column(modifier = Modifier.fillMaxSize()) {
            LessonTopBar(
                progress = state.progress,
                hearts = state.hearts,
                onOpenPinyinSettings = onOpenPinyinSettings,
                onExit = onExit,
            )
            if (state.isStale) StaleBanner()

            val checked = state.answer as? AnswerState.Checked
            val coachCharacter = if (
                checked != null &&
                !checked.isCorrect &&
                state.hearts == 1
            ) {
                LessonCharacter.Rabbit
            } else {
                lessonCharacterFor(card)
            }
            val coachReaction = checked?.let {
                lessonReactionFor(
                    correct = it.isCorrect,
                    hearts = state.hearts,
                    streak = state.answerStreak,
                )
            }
            val coachMood = when {
                checked == null -> LessonCharacterMood.Idle
                !checked.isCorrect && state.hearts == 1 -> LessonCharacterMood.OneHeart
                checked.isCorrect -> LessonCharacterMood.Correct
                else -> LessonCharacterMood.Wrong
            }
            val reactionKey = state.cardIndex to checked?.isCorrect
            // The coach says the card's own instruction instead of standing
            // alone beside a name tag.
            val coachLine = lessonCoachLine(card, state.currentSectionTitle)
            // A question, the pronunciation card and the pairs put their
            // instruction at the top as the screen's heading, the stage layout;
            // the coach then says the material, not the instruction.
            val heading = lessonHeading(card, state.currentSectionTitle)
            // The entry cinematic is already a character on screen. Composing
            // the coach underneath it means two character compositions alive at
            // once (origin/main ff230ab7); the slot is held open so nothing
            // jumps when the cinematic ends.
            val coachReady = !entryVisible

            if (heading != null) HskStageHeading(heading)

            // Teaching cards and the builders keep the coach above: there is
            // nothing to stand beside. The pairs keep the whole width for the grid.
            val coachAbove = card !is ChoiceCard && card !is PronunciationCard && card !is MatchPairsCard
            if (coachAbove) {
                HskStageCoach(
                    character = coachCharacter,
                    mood = coachMood,
                    reaction = coachReaction,
                    reactionKey = reactionKey,
                    showCharacter = coachReady,
                    showBubble = coachLine.isNotBlank(),
                    characterSize = 88.dp,
                    modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 10.dp),
                ) {
                    HskBubbleText(coachLine)
                }
            }

            // Longer decks still scroll. A question stands the coach at the top
            // and its answers at the bottom; every other card sits in the middle.
            BoxWithConstraints(modifier = Modifier.weight(1f).fillMaxWidth()) {
              val viewport = maxHeight
              CompositionLocalProvider(LocalLessonCoachLine provides (heading ?: coachLine)) {
              Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
                    .heightIn(min = viewport)
                    .padding(start = 16.dp, end = 16.dp, top = 14.dp, bottom = 20.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = if (card is ChoiceCard) Arrangement.SpaceBetween else Arrangement.Center,
              ) {
                when (card) {
                    is ChoiceCard -> {
                        val listening = card.kind == ChoiceKind.LISTENING
                        HskStageCoach(
                            character = coachCharacter,
                            mood = coachMood,
                            reaction = coachReaction,
                            reactionKey = reactionKey,
                            showCharacter = coachReady,
                            // The listening bubble is the speaker: tap it to hear again.
                            onBubbleClick = if (listening && !state.isAudioLoading) {
                                { onPlayAudio(card.audioText.orEmpty()) }
                            } else {
                                null
                            },
                            onBubbleClickLabel = if (listening) stringResource(R.string.lesson_play_audio) else null,
                        ) {
                            LessonChoiceMaterial(card = card, isAudioLoading = state.isAudioLoading)
                        }
                        Column(modifier = Modifier.fillMaxWidth().padding(top = 20.dp)) {
                            LessonChoiceOptions(
                                card = card,
                                selectedIndex = selectedIndex,
                                isAnswered = state.isAnswered,
                                onSelect = { index -> selectedIndex = index },
                            )
                            LessonCardErrors(state)
                        }
                    }
                    is PronunciationCard -> {
                        PronunciationCardView(
                            card = card,
                            pinyin = pinyin,
                            isAudioLoading = state.isAudioLoading,
                            isRecording = state.isPronunciationRecording,
                            isScoring = state.isPronunciationScoring,
                            isAnswered = state.isAnswered,
                            onPlayAudio = onPlayAudio,
                            onSpeak = onSpeakPronunciation,
                            onSkip = onSkipPronunciation,
                            coach = {
                                val stage = Modifier.size(width = 150.dp, height = 165.dp)
                                if (coachReady) {
                                    LessonCharacterStage(
                                        character = coachCharacter,
                                        mood = coachMood,
                                        reaction = coachReaction,
                                        reactionKey = reactionKey,
                                        modifier = stage,
                                    )
                                } else {
                                    Spacer(stage)
                                }
                            },
                        )
                        LessonCardErrors(state)
                    }
                    is NewWordCard -> {
                        NewWordCardView(
                            card = card,
                            pinyin = pinyin,
                            isAudioLoading = state.isAudioLoading,
                            onPlayAudio = onPlayAudio,
                            onRevealed = { newWordOpen = true },
                        )
                        LessonCardErrors(state)
                    }
                    is GrammarCard -> {
                        GrammarCardView(card, pinyin)
                        LessonCardErrors(state)
                    }
                    is SentenceBuilderCard -> {
                        SentenceBuilderCardView(card, state.isAnswered) { onAnswerBuilder(card, it) }
                        LessonCardErrors(state)
                    }
                    is ReverseBuilderCard -> {
                        ReverseBuilderCardView(card, pinyin, state.isAnswered) { onAnswerBuilder(card, it) }
                        LessonCardErrors(state)
                    }
                    is MatchPairsCard -> {
                        MatchPairsCardView(card, state.isAnswered) { onAnswerPairs(card) }
                        LessonCardErrors(state)
                    }
                    is UnsupportedCard -> {
                        UnsupportedCardView(card, onAcknowledge)
                        LessonCardErrors(state)
                    }
                }
              }
              }
            }

            Box(
                modifier = Modifier.onSizeChanged { size ->
                    footerHeight = with(density) { size.height.toDp() }
                },
            ) {
                FooterBar(
                    state = state,
                    card = card,
                    selectedChoice = selectedIndex,
                    acknowledgeReady = card !is NewWordCard || newWordOpen,
                    onCheckChoice = {
                        val index = selectedIndex
                        if (card is ChoiceCard && index != null) onAnswerChoice(card, index)
                    },
                    onAcknowledge = onAcknowledge,
                    onAdvance = onAdvance,
                    onAskAssistant = onAskAssistant,
                )
            }
        }

        if (entryVisible && lessonEntryKey != null) {
            LessonEntryOverlay(
                alpha = entryAlpha.value,
                key = lessonEntryKey,
            )
        }

        if (writeTarget != null) {
            WriterButton(
                onClick = { onOpenWriter(writeTarget) },
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(end = 18.dp, bottom = footerHeight + WriterButtonGap),
            )
        }
    }

    state.writerChar?.let { target ->
        HanziWriterSheet(
            hanzi = target.hanzi,
            pinyin = target.pinyin,
            meaning = target.meaning,
            characters = target.characters,
            index = state.writerIndex,
            strokes = state.writerStrokes,
            isLoading = state.isWriterLoading,
            onShowCharacter = onShowWriterCharacter,
            onReplay = { onShowWriterCharacter(state.writerIndex) },
            onDismiss = onCloseWriter,
        )
    }
}

/** Audio and microphone failures, said under the card they happened on. */
@Composable
private fun LessonCardErrors(state: LessonUiState) {
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
    state.pronunciationError?.let { error ->
        Spacer(Modifier.height(12.dp))
        Text(
            text = stringResource(error.messageRes),
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.Flame,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
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

/** How far the pencil floats above whatever the footer currently is. */
private val WriterButtonGap = 16.dp

/** Between the Mini App's 250 ms (listening) and 350 ms (say-after-me). */
private const val VOICE_CARD_SPEAK_DELAY_MILLIS = 300L

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
            .padding(start = 8.dp, end = 16.dp, top = 8.dp, bottom = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        HskGlassIconButton(
            icon = Icons.Filled.Close,
            contentDescription = stringResource(R.string.action_close),
            onClick = onExit,
            size = 40.dp,
            iconSize = 24.dp,
            tint = PompColors.InkSecondary,
        )

        HskStageProgress(progress = progress, modifier = Modifier.weight(1f))

        HskGlassIconButton(
            icon = Icons.Filled.Settings,
            contentDescription = stringResource(R.string.lesson_pinyin_title),
            onClick = onOpenPinyinSettings,
            size = 40.dp,
            iconSize = 22.dp,
            tint = PompColors.InkDisabled,
        )

        AnimatedHeartCounter(
            hearts = hearts,
            heartColor = heartColor,
        )
    }
}

@Composable
private fun AnimatedHeartCounter(
    hearts: Int,
    heartColor: Color,
) {
    var previous by remember { mutableStateOf(hearts) }
    val scale = remember { Animatable(1f) }
    val rotation = remember { Animatable(0f) }
    val alpha = remember { Animatable(1f) }
    val glow = remember { Animatable(0f) }

    LaunchedEffect(hearts) {
        if (hearts < previous) {
            scale.snapTo(1f)
            rotation.snapTo(0f)
            alpha.snapTo(1f)
            glow.snapTo(0f)
            when (hearts) {
                1 -> coroutineScope {
                    launch {
                        scale.animateTo(
                            1f,
                            keyframes {
                                durationMillis = 2200
                                1f at 0
                                1.16f at 550
                                1f at 1100
                                1.16f at 1650
                                1f at 2200
                            },
                        )
                    }
                    launch {
                        glow.animateTo(
                            0f,
                            keyframes {
                                durationMillis = 2200
                                0f at 0
                                .45f at 550
                                0f at 1100
                                .45f at 1650
                                0f at 2200
                            },
                        )
                    }
                }
                0 -> coroutineScope {
                    launch {
                        scale.animateTo(
                            1f,
                            keyframes {
                                durationMillis = 500
                                1f at 0
                                .88f at 200
                                1f at 500
                            },
                        )
                    }
                    launch {
                        alpha.animateTo(
                            1f,
                            keyframes {
                                durationMillis = 500
                                1f at 0
                                .70f at 200
                                1f at 500
                            },
                        )
                    }
                }
                else -> coroutineScope {
                    launch {
                        scale.animateTo(
                            1f,
                            keyframes {
                                durationMillis = 420
                                1f at 0
                                1.18f at 126
                                1f at 420
                            },
                        )
                    }
                    launch {
                        rotation.animateTo(
                            0f,
                            keyframes {
                                durationMillis = 420
                                0f at 0
                                -8f at 126
                                0f at 420
                            },
                        )
                    }
                }
            }
        }
        previous = hearts
    }

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        modifier = Modifier.graphicsLayer { this.alpha = alpha.value },
    ) {
        Box(
            modifier = Modifier.size(28.dp),
            contentAlignment = Alignment.Center,
        ) {
            if (glow.value > 0f) {
                Canvas(Modifier.fillMaxSize()) {
                    drawCircle(
                        color = PompColors.Cinnabar.copy(alpha = glow.value),
                        radius = size.minDimension * .48f,
                    )
                }
            }
            Icon(
                Icons.Filled.Favorite,
                contentDescription = null,
                tint = heartColor,
                modifier = Modifier
                    .size(22.dp)
                    .graphicsLayer {
                        scaleX = scale.value
                        scaleY = scale.value
                        rotationZ = rotation.value
                    },
            )
        }
        Text(
            text = hearts.toString(),
            style = MaterialTheme.typography.labelLarge.copy(fontSize = 17.sp),
            fontWeight = FontWeight.Bold,
            color = heartColor,
        )
    }
}

@Composable
private fun LessonEntryOverlay(
    alpha: Float,
    key: Any,
) {
    val phase by rememberInfiniteTransition(label = "lesson-entry-dots").animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 900),
            repeatMode = RepeatMode.Restart,
        ),
        label = "lesson-entry-dot-phase",
    )
    Surface(
        color = PompColors.Paper,
        modifier = Modifier
            .fillMaxSize()
            .graphicsLayer {
                this.alpha = alpha
                scaleX = 1f + (1f - alpha) * .012f
                scaleY = 1f + (1f - alpha) * .012f
            },
    ) {
        Column(
            modifier = Modifier.fillMaxSize().padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            LessonCharacterStage(
                character = LessonCharacter.Panda,
                mood = LessonCharacterMood.Loading,
                reaction = LessonCharacterReaction.Pop,
                reactionKey = key,
                modifier = Modifier.size(width = 148.dp, height = 164.dp),
            )
            Spacer(Modifier.height(9.dp))
            Text(
                text = stringResource(R.string.lesson_entry_title),
                style = MaterialTheme.typography.labelLarge.copy(fontSize = 14.sp),
                fontWeight = FontWeight.Bold,
                color = PompColors.Ink,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = stringResource(R.string.lesson_entry_subtitle),
                style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.sp),
                color = PompColors.InkSecondary,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(10.dp))
            Canvas(Modifier.size(width = 42.dp, height = 12.dp)) {
                repeat(3) { index ->
                    val local = ((phase + index * .22f) % 1f)
                    val wave = ((sin(local * 2f * PI).toFloat() + 1f) / 2f)
                    drawCircle(
                        color = PompColors.Cinnabar.copy(alpha = .35f + wave * .65f),
                        radius = 2.5.dp.toPx(),
                        center = Offset(
                            x = 7.dp.toPx() + index * 14.dp.toPx(),
                            y = size.height / 2f - wave * 2.dp.toPx(),
                        ),
                    )
                }
            }
        }
    }
}

/**
 * The bottom of the lesson: Tekshirish on a question until it is checked,
 * Davom etish on a teaching card, and after a check the result panel.
 */
@Composable
private fun FooterBar(
    state: LessonUiState,
    card: LessonCard,
    selectedChoice: Int?,
    acknowledgeReady: Boolean,
    onCheckChoice: () -> Unit,
    onAcknowledge: () -> Unit,
    onAdvance: () -> Unit,
    onAskAssistant: ((question: String, readyAnswer: String) -> Unit)?,
) {
    val answer = state.answer
    if (answer is AnswerState.Checked) {
        FeedbackPanel(
            answer = answer,
            card = card,
            submitting = state.isSubmitting,
            onAdvance = onAdvance,
            onAskAssistant = onAskAssistant,
        )
        return
    }

    val footer = Modifier.navigationBarsPadding().padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 16.dp)
    when {
        card is ChoiceCard -> Box(modifier = footer) {
            HskDepthButton(
                text = stringResource(R.string.lesson_check),
                color = PompColors.Cinnabar,
                onClick = onCheckChoice,
                enabled = selectedChoice != null,
            )
        }
        (card is NewWordCard || card is GrammarCard) && acknowledgeReady -> Box(modifier = footer) {
            HskDepthButton(
                text = stringResource(R.string.lesson_next),
                color = PompColors.Cinnabar,
                onClick = onAcknowledge,
            )
        }
    }
}

/**
 * The result of a check. A wrong answer on a graded card also gets the ready
 * answer — the card's own explanation, said by the AI tutor's avatar — and two
 * questions the learner can take to the AI chat. The ready answer asks no
 * model; only a question the learner taps does, so a lesson full of mistakes
 * does not spend AI on its own.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun FeedbackPanel(
    answer: AnswerState.Checked,
    card: LessonCard,
    submitting: Boolean,
    onAdvance: () -> Unit,
    onAskAssistant: ((question: String, readyAnswer: String) -> Unit)?,
) {
    val accent = if (answer.isCorrect) PompColors.Jade else PompColors.Flame
    // A pronunciation score is not an answer the chat can explain.
    val offerHelp = !answer.isCorrect && card !is PronunciationCard
    Surface(
        color = if (answer.isCorrect) PompColors.JadeSoft else PompColors.FlameSoft,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.navigationBarsPadding().padding(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 16.dp),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Icon(
                    imageVector = if (answer.isCorrect) Icons.Filled.CheckCircle else Icons.Filled.Cancel,
                    contentDescription = null,
                    tint = accent,
                    modifier = Modifier.size(30.dp),
                )
                Text(
                    text = stringResource(if (answer.isCorrect) R.string.lesson_correct else R.string.lesson_wrong),
                    fontSize = 22.sp,
                    lineHeight = 28.sp,
                    fontWeight = FontWeight.Bold,
                    color = accent,
                )
            }
            if (offerHelp) {
                if (answer.explanation.isNotBlank()) {
                    ReadyAnswer(text = answer.explanation, modifier = Modifier.padding(top = 12.dp))
                }
                if (onAskAssistant != null) {
                    val mistake = stringResource(R.string.assistant_mistake)
                    val example = stringResource(R.string.assistant_example)
                    FlowRow(
                        modifier = Modifier.padding(start = 36.dp, top = 10.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        AskChip(text = mistake, onClick = { onAskAssistant(mistake, answer.explanation) })
                        AskChip(text = example, onClick = { onAskAssistant(example, answer.explanation) })
                    }
                }
            } else if (answer.explanation.isNotBlank()) {
                Text(
                    text = answer.explanation,
                    fontSize = 14.sp,
                    lineHeight = 20.sp,
                    color = PompColors.InkSecondary,
                    modifier = Modifier.padding(top = 6.dp),
                )
            }
            Spacer(Modifier.height(14.dp))
            HskDepthButton(
                text = stringResource(R.string.lesson_next),
                color = accent,
                onClick = onAdvance,
                enabled = !submitting,
                loading = submitting,
            )
        }
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
    isCheckpoint: Boolean,
    rankBoard: LessonRankBoard?,
    onExit: () -> Unit,
) {
    LessonCompletionCelebration(
        outcome = outcome,
        isCheckpoint = isCheckpoint,
        rankBoard = rankBoard,
        onExit = onExit,
    )
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
