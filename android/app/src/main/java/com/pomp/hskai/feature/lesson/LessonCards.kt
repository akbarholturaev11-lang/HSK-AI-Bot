package com.pomp.hskai.feature.lesson

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.VolumeUp
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.core.design.components.HskBubbleTail
import com.pomp.hskai.core.design.components.HskSpeechBubble
import com.pomp.hskai.core.settings.PinyinVisibility
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.ChoiceKind
import com.pomp.hskai.domain.model.GrammarCard
import com.pomp.hskai.domain.model.MatchPairsCard
import com.pomp.hskai.domain.model.NewWordCard
import com.pomp.hskai.domain.model.PronunciationCard
import com.pomp.hskai.domain.model.ReverseBuilderCard
import com.pomp.hskai.domain.model.SentenceBuilderCard
import com.pomp.hskai.domain.model.UnsupportedCard

@Composable
internal fun CardTitle(text: String) {
    if (text.isBlank()) return
    // The coach above the card is already saying this line; printing it here
    // too would put the same sentence on screen twice.
    if (text == LocalLessonCoachLine.current) return
    Text(text = text, style = MaterialTheme.typography.labelLarge, color = PompColors.CinnabarDark)
    Spacer(Modifier.height(8.dp))
}

@Composable
internal fun CardPrompt(text: String) {
    if (text.isBlank()) return
    Text(text = text, style = MaterialTheme.typography.titleLarge, color = PompColors.Ink)
    Spacer(Modifier.height(16.dp))
}

/** `cubic-bezier(.34,1.56,.64,1)` — the Mini App's overshoot on `nwPop`. */
private val NwPop = CubicBezierEasing(0.34f, 1.56f, 0.64f, 1f)

/**
 * The Mini App's `cardWord` celebration, matched beat for beat.
 *
 * A new word is the one moment in a lesson that is pure reward, so it arrives
 * as a card that pops in with sparkles rather than as a line of text: the
 * bordered hanzi plate lands first, the label rises under it, and only after
 * the word has been read aloud does pinyin and meaning slide up. Sizes and
 * colours are `.nw*` in `course-v3.html`; the palette tokens here hold the same
 * hex values, so light mode is identical and dark mode still works.
 */
@Composable
fun NewWordCardView(
    card: NewWordCard,
    pinyin: PinyinVisibility,
    isAudioLoading: Boolean = false,
    onPlayAudio: (String) -> Unit = {},
    onRevealed: () -> Unit = {},
) {
    val haptics = LocalHapticFeedback.current
    val play by rememberUpdatedState(onPlayAudio)
    val revealed = remember(card) { Animatable(0f) }
    var infoOn by remember(card) { mutableStateOf(false) }
    val reveal by rememberUpdatedState(onRevealed)

    LaunchedEffect(card) {
        haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
        revealed.snapTo(0f)
        revealed.animateTo(1f, tween(durationMillis = 500, easing = NwPop))
    }
    // 400ms: the word speaks. 900ms: the meaning opens and the CTA appears —
    // the learner hears it before being asked to move on.
    LaunchedEffect(card) {
        kotlinx.coroutines.delay(400)
        play(card.hanzi)
        kotlinx.coroutines.delay(500)
        infoOn = true
        reveal()
    }

    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
        BoxWithConstraints(modifier = Modifier.fillMaxWidth().padding(top = 22.dp, bottom = 4.dp)) {
            val width = maxWidth
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.fillMaxWidth().align(Alignment.Center),
            ) {
                HanziPlate(hanzi = card.hanzi, progress = revealed.value)
                Spacer(Modifier.height(14.dp))
                NewWordLabel(progress = revealed.value)
            }
            Sparkle(card, Icons.Filled.AutoAwesome, 18.sp, 300, Modifier.align(Alignment.TopStart).offset(x = width * 0.16f, y = 4.dp))
            Sparkle(card, Icons.Filled.Star, 24.sp, 450, Modifier.align(Alignment.TopEnd).offset(x = -width * 0.13f, y = 26.dp))
            Sparkle(card, Icons.Filled.AutoAwesome, 13.sp, 600, Modifier.align(Alignment.BottomStart).offset(x = width * 0.24f, y = -10.dp))
        }
        NewWordInfo(
            card = card,
            pinyin = pinyin,
            visible = infoOn,
            isAudioLoading = isAudioLoading,
            onPlayAudio = { play(card.hanzi) },
        )
    }
}

/** `.nw-card` — white plate, 3px cinnabar edge, flat 6px cinnabar-dark depth. */
@Composable
private fun HanziPlate(hanzi: String, progress: Float) {
    Box(
        modifier = Modifier.graphicsLayer {
            scaleX = 0.3f + 0.7f * progress
            scaleY = 0.3f + 0.7f * progress
            rotationZ = -6f * (1f - progress)
            alpha = progress
        }
    ) {
        Box(
            modifier = Modifier
                .matchParentSize()
                .offset(y = 6.dp)
                .background(PompColors.CinnabarDark, RoundedCornerShape(22.dp))
        )
        Surface(
            color = PompColors.PaperRaised,
            shape = RoundedCornerShape(22.dp),
            border = BorderStroke(3.dp, PompColors.Cinnabar),
        ) {
            Text(
                text = hanzi,
                style = PompTextStyles.hanziLarge.copy(fontSize = 60.sp, lineHeight = 69.sp),
                color = PompColors.Ink,
                modifier = Modifier.padding(horizontal = 42.dp, vertical = 30.dp),
            )
        }
    }
}

/** `.nw-label` — `nwUp`, 450ms on a 250ms delay against the plate's 500ms pop. */
@Composable
private fun NewWordLabel(progress: Float) {
    val own = ((progress - 0.5f) / 0.5f).coerceIn(0f, 1f)
    Text(
        text = stringResource(R.string.lesson_new_word),
        fontSize = 21.sp,
        fontWeight = FontWeight.ExtraBold,
        letterSpacing = 2.sp,
        color = PompColors.Cinnabar,
        modifier = Modifier
            .alpha(own)
            .offset(y = (14 * (1f - own)).dp),
    )
}

/** `.nw-spark` — fades in oversized, then drifts up and out. */
@Composable
private fun Sparkle(
    key: Any,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    size: androidx.compose.ui.unit.TextUnit,
    delayMillis: Int,
    modifier: Modifier = Modifier,
) {
    val t = remember(key) { Animatable(0f) }
    LaunchedEffect(key) {
        t.snapTo(0f)
        kotlinx.coroutines.delay(delayMillis.toLong())
        t.animateTo(1f, tween(durationMillis = 1100, easing = LinearEasing))
    }
    val alpha = if (t.value < 0.4f) t.value / 0.4f else 1f - (t.value - 0.4f) / 0.6f
    val scale = when {
        t.value < 0.4f -> 0.4f + (1.25f - 0.4f) * (t.value / 0.4f)
        else -> 1.25f - (1.25f - 0.7f) * ((t.value - 0.4f) / 0.6f)
    }
    Icon(
        imageVector = icon,
        contentDescription = null,
        tint = PompColors.Gold,
        modifier = modifier
            .size(with(androidx.compose.ui.platform.LocalDensity.current) { size.toDp() })
            .graphicsLayer {
                this.alpha = alpha.coerceIn(0f, 1f)
                scaleX = scale
                scaleY = scale
                translationY = -16.dp.toPx() * ((t.value - 0.4f) / 0.6f).coerceAtLeast(0f)
            },
    )
}

/** `.nw-info` — held back until the word has been heard, then slides up. */
@Composable
private fun NewWordInfo(
    card: NewWordCard,
    pinyin: PinyinVisibility,
    visible: Boolean,
    isAudioLoading: Boolean,
    onPlayAudio: () -> Unit,
) {
    val show = remember(card) { Animatable(0f) }
    LaunchedEffect(visible) {
        if (visible) show.animateTo(1f, tween(durationMillis = 400)) else show.snapTo(0f)
    }
    if (show.value <= 0f) return
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier
            .padding(top = 16.dp)
            .widthIn(max = 330.dp)
            .alpha(show.value)
            .offset(y = (10 * (1f - show.value)).dp),
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(start = 18.dp, end = 18.dp, top = 15.dp, bottom = 16.dp),
        ) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(9.dp, Alignment.CenterHorizontally),
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (pinyin != PinyinVisibility.OFF) {
                    Text(
                        text = card.pinyin,
                        fontSize = 26.sp,
                        lineHeight = 31.sp,
                        fontWeight = FontWeight.Medium,
                        color = PompColors.CinnabarDark,
                    )
                }
                if (card.partOfSpeech.isNotBlank()) {
                    Surface(
                        color = PompColors.Paper,
                        shape = RoundedCornerShape(9.dp),
                        border = BorderStroke(1.dp, PompColors.Divider),
                    ) {
                        Text(
                            text = card.partOfSpeech,
                            fontSize = 11.5.sp,
                            lineHeight = 15.sp,
                            color = PompColors.InkDisabled,
                            modifier = Modifier.padding(horizontal = 9.dp, vertical = 3.dp),
                        )
                    }
                }
            }
            Spacer(Modifier.height(9.dp))
            Box(modifier = Modifier.fillMaxWidth().height(1.dp).background(PompColors.Divider))
            Text(
                text = card.meaning,
                fontSize = 17.sp,
                lineHeight = 25.sp,
                color = PompColors.Ink,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 10.dp),
            )
            Surface(
                color = PompColors.CinnabarSoft,
                shape = RoundedCornerShape(20.dp),
                onClick = onPlayAudio,
                enabled = !isAudioLoading,
                modifier = Modifier.padding(top = 13.dp),
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(7.dp),
                    modifier = Modifier.padding(horizontal = 17.dp, vertical = 9.dp),
                ) {
                    if (isAudioLoading) {
                        CircularProgressIndicator(
                            color = PompColors.CinnabarDark,
                            modifier = Modifier.size(16.dp),
                            strokeWidth = 2.dp,
                        )
                    } else {
                        Icon(
                            Icons.AutoMirrored.Filled.VolumeUp,
                            contentDescription = null,
                            tint = PompColors.CinnabarDark,
                            modifier = Modifier.size(16.dp),
                        )
                    }
                    Text(
                        text = stringResource(R.string.lesson_listen),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Medium,
                        color = PompColors.CinnabarDark,
                    )
                }
            }
        }
    }
}

@Composable
fun GrammarCardView(card: GrammarCard, pinyin: PinyinVisibility) {
    Column {
        CardTitle(card.titleZh.ifBlank { stringResource(R.string.lesson_grammar) })
        Text(text = card.title, style = MaterialTheme.typography.titleLarge, color = PompColors.Ink)
        Spacer(Modifier.height(12.dp))
        Text(text = card.rule, style = MaterialTheme.typography.bodyLarge, color = PompColors.InkSecondary)
        if (card.examples.isNotEmpty()) {
            Spacer(Modifier.height(16.dp))
            card.examples.forEach { example ->
                Surface(
                    color = PompColors.PaperRaised,
                    shape = RoundedCornerShape(12.dp),
                    border = BorderStroke(1.dp, PompColors.Divider),
                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(text = example.hanzi, style = PompTextStyles.hanziMedium, color = PompColors.Ink)
                        if (pinyin == PinyinVisibility.ALL) {
                            Text(text = example.pinyin, style = PompTextStyles.pinyin, color = PompColors.InkSecondary)
                        }
                        Text(text = example.translation, style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
                    }
                }
            }
        }
    }
}

/**
 * Say-it-after-me, in the stage layout: the phrase in a bubble the learner can
 * tap to hear again, the coach under it, and one wide microphone button.
 *
 * [coach] is the lesson's character. It is static here — no idle loop runs
 * while the microphone may be open; only the one-shot reaction to a score does.
 */
@Composable
fun PronunciationCardView(
    card: PronunciationCard,
    pinyin: PinyinVisibility,
    isAudioLoading: Boolean,
    isRecording: Boolean,
    isScoring: Boolean,
    isAnswered: Boolean,
    onPlayAudio: (String) -> Unit,
    onSpeak: () -> Unit,
    onSkip: () -> Unit,
    coach: (@Composable () -> Unit)? = null,
) {
    val context = LocalContext.current
    var permissionDenied by remember { mutableStateOf(false) }
    val permission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        permissionDenied = !granted
        if (granted) onSpeak()
    }
    val micEnabled = !isRecording && !isScoring && !isAnswered
    val canListen = !isRecording && !isScoring && !isAudioLoading
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
        CardTitle(stringResource(R.string.lesson_repeat_after_teacher))
        HskSpeechBubble(
            tail = HskBubbleTail.Bottom,
            onClick = if (canListen) { { onPlayAudio(card.phrase) } } else null,
            onClickLabel = stringResource(R.string.lesson_play_audio),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Box(contentAlignment = Alignment.Center, modifier = Modifier.size(32.dp)) {
                    if (isAudioLoading) {
                        CircularProgressIndicator(
                            color = PompColors.Cinnabar,
                            strokeWidth = 2.dp,
                            modifier = Modifier.size(22.dp),
                        )
                    } else {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.VolumeUp,
                            contentDescription = null,
                            tint = PompColors.Cinnabar,
                            modifier = Modifier.size(30.dp),
                        )
                    }
                }
                Column {
                    Text(text = card.phrase, style = PompTextStyles.hanziMedium, color = PompColors.Ink)
                    if (pinyin == PinyinVisibility.ALL) {
                        Text(
                            text = card.pinyin,
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Medium,
                            color = PompColors.CinnabarDark,
                        )
                    }
                    Text(text = card.translation, style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
                }
            }
        }
        if (coach != null) {
            Spacer(Modifier.height(10.dp))
            coach()
        }
        Spacer(Modifier.height(18.dp))
        val micShape = RoundedCornerShape(20.dp)
        val micColor = if (isRecording) PompColors.CinnabarDark else PompColors.Cinnabar
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
                color = micColor,
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
                isRecording -> stringResource(R.string.foundation_speak_listening)
                isScoring -> stringResource(R.string.foundation_speak_checking)
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
        Spacer(Modifier.height(20.dp))
        // A quiet way out, not a second button competing with the microphone.
        TextButton(onClick = onSkip, enabled = !isRecording && !isScoring) {
            Text(
                text = stringResource(R.string.lesson_cannot_speak_now).uppercase(),
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.sp,
                color = PompColors.InkDisabled,
                textAlign = TextAlign.Center,
            )
        }
    }
}

@Composable
fun ChoiceCardView(
    card: ChoiceCard,
    pinyin: PinyinVisibility,
    selectedIndex: Int?,
    isAnswered: Boolean,
    isAudioLoading: Boolean,
    onPlayAudio: (String) -> Unit,
    onSelect: (Int) -> Unit,
) {
    Column {
        ChoiceCardMaterial(card, pinyin, isAudioLoading, onPlayAudio)
        ChoiceCardOptions(card, selectedIndex, isAnswered, onSelect)
    }
}

/**
 * What the question gives the learner to work on: the sentence, the dialogue,
 * or the speaker when it is a listening question.
 *
 * Kept apart from [ChoiceCardOptions] so the lesson can stand the coach next
 * to the question while the answers keep the full width below — they are the
 * widest thing on the screen and the first to suffer from a narrow column.
 */
@Composable
internal fun ChoiceCardMaterial(
    card: ChoiceCard,
    pinyin: PinyinVisibility,
    isAudioLoading: Boolean,
    onPlayAudio: (String) -> Unit,
) {
    Column {
        CardTitle(card.title)
        when (card.kind) {
            ChoiceKind.LISTENING -> {
                Text(text = stringResource(R.string.lesson_listen_and_choose), style = MaterialTheme.typography.titleLarge, color = PompColors.Ink)
                // The pinyin of what is being said used to sit here whenever the
                // learner had pinyin switched on — which is the answer, written out
                // above the options. The Mini App shows the audio button and nothing
                // else, and a listening question that can be read is not one.
                Spacer(Modifier.height(12.dp))
                AudioAction(isLoading = isAudioLoading, onClick = { onPlayAudio(card.audioText.orEmpty()) })
                Spacer(Modifier.height(16.dp))
            }
            ChoiceKind.GAP_FILL -> {
                CardPrompt(card.prompt)
                card.sentence?.takeIf { it.isNotBlank() }?.let { sentence ->
                    Text(text = sentence, style = PompTextStyles.hanziMedium, color = PompColors.Ink)
                    Spacer(Modifier.height(16.dp))
                }
            }
            ChoiceKind.DIALOG_CLOZE -> {
                CardPrompt(card.prompt.ifBlank { card.title })
                card.lines.forEach { line ->
                    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                        Text(text = "${line.speaker}: ", style = MaterialTheme.typography.bodyLarge, color = PompColors.InkSecondary)
                        Text(
                            text = if (line.isBlank) "＿＿＿" else line.text,
                            style = MaterialTheme.typography.bodyLarge,
                            color = if (line.isBlank) PompColors.CinnabarDark else PompColors.Ink,
                        )
                    }
                }
                Spacer(Modifier.height(16.dp))
            }
            else -> CardPrompt(card.prompt)
        }
    }
}

/** The answers. */
@Composable
internal fun ChoiceCardOptions(
    card: ChoiceCard,
    selectedIndex: Int?,
    isAnswered: Boolean,
    onSelect: (Int) -> Unit,
) {
    Column {
        card.options.forEachIndexed { index, option ->
            OptionRow(
                text = option,
                state = optionState(index, card.correctIndex, selectedIndex, isAnswered),
                enabled = !isAnswered,
                onClick = { onSelect(index) },
                key = "ABCD".getOrNull(index)?.toString().orEmpty(),
            )
        }
    }
}

@Composable
private fun AudioAction(
    isLoading: Boolean,
    enabled: Boolean = true,
    onClick: () -> Unit,
) {
    OutlinedButton(
        onClick = onClick,
        enabled = enabled && !isLoading,
        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
        shape = RoundedCornerShape(14.dp),
    ) {
        if (isLoading) {
            CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp, color = PompColors.Cinnabar)
            Spacer(Modifier.size(10.dp))
        }
        Text(
            text = stringResource(if (isLoading) R.string.lesson_audio_loading else R.string.lesson_play_audio),
            style = MaterialTheme.typography.labelLarge,
            color = PompColors.CinnabarDark,
        )
    }
}

internal enum class OptionState { IDLE, SELECTED_WRONG, CORRECT }

private fun optionState(index: Int, correctIndex: Int, selectedIndex: Int?, isAnswered: Boolean): OptionState = when {
    !isAnswered -> OptionState.IDLE
    index == correctIndex -> OptionState.CORRECT
    index == selectedIndex -> OptionState.SELECTED_WRONG
    else -> OptionState.IDLE
}

@Composable
private fun OptionRow(
    text: String,
    state: OptionState,
    enabled: Boolean,
    onClick: () -> Unit,
    key: String = "",
) {
    val border = when (state) {
        OptionState.IDLE -> PompColors.Divider
        OptionState.CORRECT -> PompColors.Jade
        OptionState.SELECTED_WRONG -> PompColors.Flame
    }
    val background = when (state) {
        OptionState.IDLE -> PompColors.PaperRaised
        OptionState.CORRECT -> PompColors.JadeSoft
        OptionState.SELECTED_WRONG -> PompColors.FlameSoft
    }
    val glyph = when (state) {
        OptionState.IDLE -> ""
        OptionState.CORRECT -> "\u2713"
        OptionState.SELECTED_WRONG -> "\u2715"
    }
    val description = when (state) {
        OptionState.IDLE -> text
        OptionState.CORRECT -> stringResource(R.string.cd_answer_correct, text)
        OptionState.SELECTED_WRONG -> stringResource(R.string.cd_answer_wrong, text)
    }
    val ink = when (state) {
        OptionState.IDLE -> PompColors.Ink
        OptionState.CORRECT -> PompColors.Jade
        OptionState.SELECTED_WRONG -> PompColors.Flame
    }

    Box(modifier = Modifier.fillMaxWidth().padding(top = 5.dp, bottom = 9.dp)) {
        Box(
            modifier = Modifier.matchParentSize().offset(y = 4.dp).clip(RoundedCornerShape(13.dp)).background(PompColors.OptionDepth),
        )
        Surface(
            color = background,
            shape = RoundedCornerShape(13.dp),
            border = BorderStroke(2.dp, border),
            modifier = Modifier.fillMaxWidth().heightIn(min = 54.dp).semantics { contentDescription = description },
            onClick = onClick,
            enabled = enabled,
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 15.dp, vertical = 14.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(11.dp),
            ) {
                if (key.isNotEmpty()) {
                    Surface(
                        shape = RoundedCornerShape(7.dp),
                        color = Color.Transparent,
                        border = BorderStroke(1.5.dp, PompColors.Divider),
                        modifier = Modifier.size(23.dp),
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Text(text = key, style = MaterialTheme.typography.labelSmall.copy(fontSize = 12.sp), color = PompColors.InkDisabled)
                        }
                    }
                }
                Text(text = text, style = MaterialTheme.typography.titleMedium.copy(fontSize = 15.sp), color = ink, modifier = Modifier.weight(1f))
                if (glyph.isNotEmpty()) {
                    Text(text = glyph, style = MaterialTheme.typography.titleMedium, color = border)
                }
            }
        }
    }
}

/**
 * How much of the sentence the learner has to supply.
 *
 * Laying every tile of a seven-token sentence is mostly a memory drill: the
 * grammar point is one or two words, and the rest is typing practice with the
 * thumbs. The sentence is shown already built except for those one or two, so
 * the structure is there to read and the choice is the part being taught.
 *
 * The submitted answer is still the whole sentence, so grading
 * ([SentenceBuilderCard.isCorrect]) and the mistake record are untouched.
 */
private const val MAX_GAPS = 2
private const val MIN_TOKENS_FOR_TWO_GAPS = 5

internal data class GapPlan(val blanks: List<Int>, val bank: List<String>)

/**
 * Chooses the gaps and the tiles offered for them.
 *
 * The bank is the card's own tile list minus one instance of every answer token
 * that stays visible — so what is left is exactly the hidden tokens plus the
 * card's distractors, and a learner choosing between them is choosing between
 * the alternatives the lesson author wrote.
 *
 * Returns null when the card's tiles cannot account for its own answer. That is
 * broken data, and the old build-it-all flow is a safer thing to fall back to
 * than a sentence with a gap nothing can fill.
 */
internal fun planGaps(card: SentenceBuilderCard): GapPlan? {
    val answer = card.answerTokens
    if (answer.size < 2 || card.tokens.isEmpty()) return null
    val gaps = if (answer.size >= MIN_TOKENS_FOR_TWO_GAPS) MAX_GAPS else 1
    // Seeded from the card, so the gaps stay put across recomposition and
    // across a reopened lesson, but differ from card to card.
    val random = kotlin.random.Random(card.materialRef.hashCode())
    val blanks = answer.indices.shuffled(random).take(gaps).sorted()

    val bank = card.tokens.toMutableList()
    answer.forEachIndexed { index, token ->
        if (index !in blanks && !bank.remove(token)) return null
    }
    if (blanks.any { bank.count { tile -> tile == answer[it] } < 1 }) return null
    return GapPlan(blanks = blanks, bank = bank.shuffled(random))
}

@Composable
fun SentenceBuilderCardView(card: SentenceBuilderCard, isAnswered: Boolean, onSubmit: (List<String>) -> Unit) {
    val plan = remember(card) { planGaps(card) }
    if (plan == null) {
        TokenBuilder(
            title = stringResource(R.string.lesson_build_sentence),
            prompt = card.promptSentence,
            tokens = card.tokens,
            isAnswered = isAnswered,
            onSubmit = onSubmit,
        )
        return
    }
    GapBuilder(card = card, plan = plan, isAnswered = isAnswered, onSubmit = onSubmit)
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun GapBuilder(
    card: SentenceBuilderCard,
    plan: GapPlan,
    isAnswered: Boolean,
    onSubmit: (List<String>) -> Unit,
) {
    // Gap position -> index into the bank. Index, not text, so two identical
    // tiles stay distinguishable.
    var filled by remember(card) { mutableStateOf(mapOf<Int, Int>()) }
    val nextGap = plan.blanks.firstOrNull { it !in filled }

    Column {
        CardTitle(stringResource(R.string.lesson_fill_gaps))
        if (card.promptSentence.isNotBlank()) CardPrompt(card.promptSentence)

        Surface(
            color = PompColors.PaperRaised,
            shape = RoundedCornerShape(12.dp),
            border = BorderStroke(1.dp, PompColors.Divider),
            modifier = Modifier.fillMaxWidth().heightIn(min = 64.dp),
        ) {
            FlowRow(
                verticalArrangement = Arrangement.Center,
                modifier = Modifier.padding(10.dp),
            ) {
                card.answerTokens.forEachIndexed { index, token ->
                    if (index !in plan.blanks) {
                        // Already in place: part of the sentence, not a control.
                        Text(
                            text = token,
                            style = PompTextStyles.hanziMedium.copy(fontSize = 22.sp, lineHeight = 30.sp),
                            color = PompColors.Ink,
                            modifier = Modifier.padding(horizontal = 2.dp, vertical = 12.dp),
                        )
                    } else {
                        val bankIndex = filled[index]
                        GapSlot(
                            text = bankIndex?.let { plan.bank[it] },
                            isNext = index == nextGap,
                            enabled = !isAnswered && bankIndex != null,
                            onClick = { filled = filled - index },
                        )
                    }
                }
            }
        }

        Spacer(Modifier.height(16.dp))
        FlowRow {
            plan.bank.indices.filterNot { it in filled.values }.forEach { index ->
                Tile(
                    text = plan.bank[index],
                    enabled = !isAnswered && nextGap != null,
                    onClick = { nextGap?.let { filled = filled + (it to index) } },
                )
            }
        }

        Spacer(Modifier.height(20.dp))
        PrimaryAction(
            text = stringResource(R.string.lesson_check),
            enabled = !isAnswered && filled.size == plan.blanks.size,
            onClick = {
                val built = card.answerTokens.toMutableList()
                filled.forEach { (position, bankIndex) -> built[position] = plan.bank[bankIndex] }
                onSubmit(built)
            },
        )
    }
}

/** One hole in the sentence: outlined while empty, a removable tile once filled. */
@Composable
private fun GapSlot(text: String?, isNext: Boolean, enabled: Boolean, onClick: () -> Unit) {
    Surface(
        color = if (text == null) PompColors.Paper else PompColors.CinnabarSoft,
        shape = RoundedCornerShape(10.dp),
        border = BorderStroke(
            width = if (isNext) 2.dp else 1.dp,
            color = if (text == null && !isNext) PompColors.Divider else PompColors.Cinnabar,
        ),
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier.padding(horizontal = 3.dp, vertical = 6.dp).heightIn(min = 46.dp),
    ) {
        Text(
            text = text ?: "　",
            style = PompTextStyles.hanziMedium.copy(fontSize = 22.sp, lineHeight = 30.sp),
            color = if (text == null) PompColors.InkDisabled else PompColors.CinnabarDark,
            textAlign = TextAlign.Center,
            modifier = Modifier.widthIn(min = 52.dp).padding(horizontal = 10.dp, vertical = 8.dp),
        )
    }
}

@Composable
fun ReverseBuilderCardView(
    card: ReverseBuilderCard,
    pinyin: PinyinVisibility,
    isAnswered: Boolean,
    onSubmit: (List<String>) -> Unit,
) {
    Column {
        Text(text = card.hanzi, style = PompTextStyles.hanziMedium, color = PompColors.Ink)
        if (pinyin == PinyinVisibility.ALL && card.pinyin.isNotBlank()) {
            Text(text = card.pinyin, style = PompTextStyles.pinyin, color = PompColors.InkSecondary)
        }
        Spacer(Modifier.height(12.dp))
        TokenBuilder(
            title = stringResource(R.string.lesson_build_translation),
            prompt = "",
            tokens = card.tokens,
            isAnswered = isAnswered,
            onSubmit = onSubmit,
        )
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun TokenBuilder(
    title: String,
    prompt: String,
    tokens: List<String>,
    isAnswered: Boolean,
    onSubmit: (List<String>) -> Unit,
) {
    var chosen by remember(tokens) { mutableStateOf(listOf<Int>()) }
    Column {
        CardTitle(title)
        if (prompt.isNotBlank()) CardPrompt(prompt)
        Surface(
            color = PompColors.PaperRaised,
            shape = RoundedCornerShape(12.dp),
            border = BorderStroke(1.dp, PompColors.Divider),
            modifier = Modifier.fillMaxWidth().heightIn(min = 64.dp),
        ) {
            FlowRow(modifier = Modifier.padding(10.dp)) {
                chosen.forEach { index ->
                    Tile(text = tokens[index], enabled = !isAnswered, onClick = { chosen = chosen - index })
                }
            }
        }
        Spacer(Modifier.height(16.dp))
        FlowRow {
            tokens.indices.filterNot { it in chosen }.forEach { index ->
                Tile(text = tokens[index], enabled = !isAnswered, onClick = { chosen = chosen + index })
            }
        }
        Spacer(Modifier.height(20.dp))
        PrimaryAction(
            text = stringResource(R.string.lesson_check),
            enabled = !isAnswered && chosen.isNotEmpty(),
            onClick = { onSubmit(chosen.map { tokens[it] }) },
        )
    }
}

@Composable
private fun Tile(text: String, enabled: Boolean, onClick: () -> Unit) {
    Surface(
        color = if (PompColors.IsDark) PompColors.OptionDepth else PompColors.Paper,
        shape = RoundedCornerShape(10.dp),
        border = BorderStroke(1.dp, PompColors.Cinnabar),
        // A tile that cannot be tapped must not keep looking tappable. With
        // both gaps full the bank is inert until a slot is freed, and without
        // this the learner taps a live-looking tile and nothing happens.
        modifier = Modifier
            .padding(4.dp)
            .heightIn(min = 48.dp)
            .alpha(if (enabled) 1f else 0.4f),
        onClick = onClick,
        enabled = enabled,
    ) {
        Text(text = text, style = MaterialTheme.typography.titleMedium, color = PompColors.Ink, modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp))
    }
}

/** What a pair cell is doing right now, mirroring `.pcell` / `.sel` / `.ok`. */
private enum class PairState { IDLE, SELECTED, MATCHED }

/**
 * `.pcell` from `course-v3.html`.
 *
 * The Android tile never showed a selection at all: tapping a hanzi left the
 * cell exactly as it was, so there was no way to tell what the second tap would
 * be matched against. Idle is a neutral edge, the picked cell turns cinnabar,
 * and a solved pair goes jade and fades back.
 */
@Composable
private fun PairCell(
    text: String,
    state: PairState,
    small: Boolean,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    val border = when (state) {
        PairState.IDLE -> PompColors.Divider
        PairState.SELECTED -> PompColors.Cinnabar
        PairState.MATCHED -> PompColors.Jade
    }
    val background = when (state) {
        PairState.IDLE -> PompColors.PaperRaised
        PairState.SELECTED -> PompColors.CinnabarSoft
        PairState.MATCHED -> PompColors.JadeSoft
    }
    val ink = when (state) {
        PairState.IDLE -> PompColors.Ink
        PairState.SELECTED -> PompColors.CinnabarDark
        PairState.MATCHED -> PompColors.Jade
    }
    val shape = RoundedCornerShape(14.dp)
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 4.dp)
            // `.pcell.ok{opacity:.7}` — a solved pair steps back without leaving.
            .alpha(if (state == PairState.MATCHED) 0.7f else 1f),
    ) {
        // The same flat edge the answer buttons stand on.
        Box(
            modifier = Modifier
                .matchParentSize()
                .offset(y = 4.dp)
                .clip(shape)
                .background(if (state == PairState.IDLE) PompColors.OptionDepth else border),
        )
        Surface(
            color = background,
            shape = shape,
            border = BorderStroke(2.dp, border),
            onClick = onClick,
            enabled = enabled,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Box(contentAlignment = Alignment.Center, modifier = Modifier.heightIn(min = 76.dp)) {
                Text(
                    text = text,
                    style = if (small) {
                        MaterialTheme.typography.bodyMedium.copy(fontSize = 15.sp, lineHeight = 20.sp)
                    } else {
                        PompTextStyles.hanziMedium.copy(fontSize = 24.sp, lineHeight = 30.sp)
                    },
                    color = ink,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 13.dp),
                )
            }
        }
    }
}

@Composable
fun MatchPairsCardView(card: MatchPairsCard, isAnswered: Boolean, onFinished: (List<Pair<Int, Int>>) -> Unit) {
    val rightOrder = remember(card) { card.pairs.indices.shuffled() }
    var selectedLeft by remember(card) { mutableStateOf<Int?>(null) }
    var matched by remember(card) { mutableStateOf(setOf<Int>()) }
    var wrongAttempts by remember(card) { mutableStateOf(listOf<Pair<Int, Int>>()) }
    val haptics = LocalHapticFeedback.current

    fun cellState(index: Int, isLeft: Boolean) = when {
        index in matched -> PairState.MATCHED
        isLeft && selectedLeft == index -> PairState.SELECTED
        else -> PairState.IDLE
    }

    // The instruction («Juftlarni moslang») is the lesson's heading now.
    Column(modifier = Modifier.fillMaxWidth()) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(
                verticalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.weight(1f),
            ) {
                card.pairs.forEachIndexed { index, pair ->
                    PairCell(
                        text = pair.first,
                        state = cellState(index, isLeft = true),
                        small = false,
                        enabled = !isAnswered && index !in matched,
                        onClick = { selectedLeft = index },
                    )
                }
            }
            Column(
                verticalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.weight(1f),
            ) {
                rightOrder.forEach { index ->
                    PairCell(
                        text = card.pairs[index].second,
                        state = cellState(index, isLeft = false),
                        small = true,
                        enabled = !isAnswered && index !in matched,
                        onClick = {
                            // A right cell does nothing until a hanzi is picked,
                            // exactly as `window._mR` bails on `selL === null`.
                            val left = selectedLeft ?: return@PairCell
                            if (left == index) {
                                matched = matched + index
                                haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                if (matched.size == card.pairs.size) onFinished(wrongAttempts)
                            } else {
                                wrongAttempts = wrongAttempts + (left to index)
                                haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                            }
                            selectedLeft = null
                        },
                    )
                }
            }
        }
    }
}

@Composable
fun UnsupportedCardView(card: UnsupportedCard, onSkip: () -> Unit) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(text = stringResource(R.string.lesson_card_unsupported), style = MaterialTheme.typography.titleMedium, color = PompColors.Ink, textAlign = TextAlign.Center)
        Spacer(Modifier.height(8.dp))
        Text(text = stringResource(R.string.lesson_card_unsupported_hint), style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary, textAlign = TextAlign.Center)
        Spacer(Modifier.height(20.dp))
        SecondaryAction(text = stringResource(R.string.lesson_skip_card), onClick = onSkip)
    }
}
