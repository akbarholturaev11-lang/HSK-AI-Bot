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
import androidx.compose.ui.text.style.TextOverflow
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
import com.pomp.hskai.core.design.components.HskCoachRow
import com.pomp.hskai.core.design.components.HskGlassButton
import com.pomp.hskai.core.design.components.HskGlassIconButton
import com.pomp.hskai.core.design.components.HskPrimaryButton
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
    onShowWriterCharacter: (Int) -> Unit,
    onCloseWriter: () -> Unit,
    onExit: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val outcome = state.outcome
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
                    onShowWriterCharacter = onShowWriterCharacter,
                    onCloseWriter = onCloseWriter,
                    onExit = onExit,
                )
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
    onShowWriterCharacter: (Int) -> Unit,
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
            // The coach says the card's own instruction instead of standing
            // alone beside a name tag. `CardTitle` reads the same line out of
            // LocalLessonCoachLine and skips it, so it is moved, not doubled.
            val coachLine = lessonCoachLine(card, state.currentSectionTitle)
            HskCoachRow(
                character = coachCharacter,
                mood = coachMood,
                reaction = coachReaction,
                reactionKey = state.cardIndex to checked?.isCorrect,
                text = coachLine,
                modifier = Modifier.padding(horizontal = 18.dp),
            )

            // The card sits in the middle of the free space instead of clinging to
            // the top-left corner; longer decks still scroll normally.
            BoxWithConstraints(modifier = Modifier.weight(1f).fillMaxWidth()) {
              val viewport = maxHeight
              CompositionLocalProvider(LocalLessonCoachLine provides coachLine) {
              Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
                    .heightIn(min = viewport)
                    .padding(horizontal = 18.dp, vertical = 10.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
              ) {
                when (card) {
                    is NewWordCard -> NewWordCardView(
                        card = card,
                        pinyin = pinyin,
                        isAudioLoading = state.isAudioLoading,
                        onPlayAudio = onPlayAudio,
                        onRevealed = { newWordOpen = true },
                    )
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
                    acknowledgeReady = card !is NewWordCard || newWordOpen,
                    onAcknowledge = onAcknowledge,
                    onAdvance = onAdvance,
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
        HskGlassIconButton(
            icon = Icons.Filled.Close,
            contentDescription = stringResource(R.string.action_close),
            onClick = onExit,
            size = 30.dp,
            iconSize = 17.dp,
            tint = PompColors.InkSecondary,
        )

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

        HskGlassIconButton(
            icon = Icons.Filled.Settings,
            contentDescription = stringResource(R.string.lesson_pinyin_title),
            onClick = onOpenPinyinSettings,
            size = 30.dp,
            iconSize = 17.dp,
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
        horizontalArrangement = Arrangement.spacedBy(3.dp),
        modifier = Modifier.graphicsLayer { this.alpha = alpha.value },
    ) {
        Box(
            modifier = Modifier.size(21.dp),
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
                    .size(15.dp)
                    .graphicsLayer {
                        scaleX = scale.value
                        scaleY = scale.value
                        rotationZ = rotation.value
                    },
            )
        }
        Text(
            text = hearts.toString(),
            style = MaterialTheme.typography.labelLarge.copy(fontSize = 15.sp),
            fontWeight = FontWeight.Medium,
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
    acknowledgeReady: Boolean,
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
                    // The persistent coach above owns the feedback reaction.
                    // Do not draw a second legacy panda in the footer.
                    Column(modifier = Modifier.weight(1f)) {
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
    if (needsAcknowledge && acknowledgeReady) {
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
