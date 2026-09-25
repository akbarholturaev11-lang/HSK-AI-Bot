package com.pomp.hskai.feature.lesson

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.VolumeUp
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.ChoiceKind

/*
 * A lesson question in the stage layout: the instruction is the screen's
 * heading, the coach says the material in its bubble, and the answers are
 * full-width, centred buttons. Picking one only selects it; the lesson's
 * Tekshirish button checks it.
 *
 * The course skip test still draws [ChoiceCardView], which answers on the
 * first tap. It is a separate screen and keeps its own behaviour until it is
 * moved over deliberately.
 */

/** What the coach says on a question card: the material the learner works on. */
@Composable
internal fun LessonChoiceMaterial(card: ChoiceCard, isAudioLoading: Boolean) {
    when (card.kind) {
        // A listening question that can be read is not one: the bubble is the
        // speaker and nothing else, as on the Mini App.
        ChoiceKind.LISTENING -> ListeningPrompt(isAudioLoading = isAudioLoading)
        ChoiceKind.GAP_FILL -> {
            if (card.prompt.isNotBlank()) BubbleText(card.prompt)
            card.sentence?.takeIf { it.isNotBlank() }?.let { sentence ->
                Spacer(Modifier.height(8.dp))
                Text(
                    text = sentence,
                    style = PompTextStyles.hanziMedium.copy(fontSize = 24.sp, lineHeight = 32.sp),
                    color = PompColors.Ink,
                )
            }
        }
        ChoiceKind.DIALOG_CLOZE -> {
            // The heading already says the instruction; do not repeat it.
            card.prompt.takeIf { it.isNotBlank() && it != LocalLessonCoachLine.current }?.let {
                BubbleText(it)
                Spacer(Modifier.height(6.dp))
            }
            card.lines.forEach { line ->
                Row(modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp)) {
                    Text(
                        text = "${line.speaker}: ",
                        fontSize = 15.sp,
                        lineHeight = 22.sp,
                        color = PompColors.InkSecondary,
                    )
                    Text(
                        text = if (line.isBlank) "＿＿＿" else line.text,
                        fontSize = 15.sp,
                        lineHeight = 22.sp,
                        color = if (line.isBlank) PompColors.CinnabarDark else PompColors.Ink,
                    )
                }
            }
        }
        else -> BubbleText(card.prompt.ifBlank { card.title })
    }
}

/** The speaker and a still waveform; the whole bubble around it plays the audio. */
@Composable
private fun ListeningPrompt(isAudioLoading: Boolean) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
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
        Waveform(Modifier.width(112.dp).height(30.dp))
    }
}

/** Bar heights out of 32, the shape of a short spoken phrase. */
private val WaveBars = floatArrayOf(6f, 10f, 16f, 24f, 18f, 28f, 12f, 20f, 26f, 14f, 22f, 10f, 16f, 8f)

@Composable
private fun Waveform(modifier: Modifier) {
    val color = PompColors.Cinnabar.copy(alpha = 0.7f)
    Canvas(modifier) {
        val bar = size.width / (WaveBars.size * 2 - 1)
        WaveBars.forEachIndexed { index, value ->
            val height = size.height * value / 32f
            drawRoundRect(
                color = color,
                topLeft = Offset(index * bar * 2f, (size.height - height) / 2f),
                size = Size(bar, height),
                cornerRadius = CornerRadius(bar / 2f),
            )
        }
    }
}

internal enum class LessonOptionState { IDLE, SELECTED, CORRECT, WRONG }

/** Before the check only the pick is lit; after it, the right answer and the wrong pick. */
internal fun lessonOptionState(
    index: Int,
    correctIndex: Int,
    selectedIndex: Int?,
    isAnswered: Boolean,
): LessonOptionState = when {
    !isAnswered -> if (index == selectedIndex) LessonOptionState.SELECTED else LessonOptionState.IDLE
    index == correctIndex -> LessonOptionState.CORRECT
    index == selectedIndex -> LessonOptionState.WRONG
    else -> LessonOptionState.IDLE
}

@Composable
internal fun LessonChoiceOptions(
    card: ChoiceCard,
    selectedIndex: Int?,
    isAnswered: Boolean,
    onSelect: (Int) -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        card.options.forEachIndexed { index, option ->
            LessonOptionRow(
                text = option,
                state = lessonOptionState(index, card.correctIndex, selectedIndex, isAnswered),
                enabled = !isAnswered,
                onClick = { onSelect(index) },
            )
        }
    }
}

@Composable
private fun LessonOptionRow(
    text: String,
    state: LessonOptionState,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    val border = when (state) {
        LessonOptionState.IDLE -> PompColors.Divider
        LessonOptionState.SELECTED -> PompColors.Cinnabar
        LessonOptionState.CORRECT -> PompColors.Jade
        LessonOptionState.WRONG -> PompColors.Flame
    }
    val background = when (state) {
        LessonOptionState.IDLE -> PompColors.PaperRaised
        LessonOptionState.SELECTED -> PompColors.CinnabarSoft
        LessonOptionState.CORRECT -> PompColors.JadeSoft
        LessonOptionState.WRONG -> PompColors.FlameSoft
    }
    val ink = when (state) {
        LessonOptionState.IDLE -> PompColors.Ink
        LessonOptionState.SELECTED -> PompColors.CinnabarDark
        LessonOptionState.CORRECT -> PompColors.Jade
        LessonOptionState.WRONG -> PompColors.Flame
    }
    val description = when (state) {
        LessonOptionState.CORRECT -> stringResource(R.string.cd_answer_correct, text)
        LessonOptionState.WRONG -> stringResource(R.string.cd_answer_wrong, text)
        else -> text
    }
    val shape = RoundedCornerShape(14.dp)
    Box(modifier = Modifier.fillMaxWidth().padding(bottom = 4.dp)) {
        // The flat edge under the button: neutral while idle, the state's own colour once lit.
        Box(
            modifier = Modifier
                .matchParentSize()
                .offset(y = 4.dp)
                .clip(shape)
                .background(if (state == LessonOptionState.IDLE) PompColors.OptionDepth else border),
        )
        Surface(
            onClick = onClick,
            enabled = enabled,
            color = background,
            shape = shape,
            border = BorderStroke(2.dp, border),
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 58.dp)
                .semantics {
                    contentDescription = description
                    selected = state == LessonOptionState.SELECTED
                },
        ) {
            Box(contentAlignment = Alignment.Center, modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) {
                Text(
                    text = text,
                    style = if (text.hasHanzi()) {
                        PompTextStyles.hanziMedium.copy(fontSize = 24.sp, lineHeight = 32.sp)
                    } else {
                        MaterialTheme.typography.titleMedium.copy(fontSize = 17.sp)
                    },
                    color = ink,
                    textAlign = TextAlign.Center,
                )
            }
        }
    }
}

/** Hanzi get the serif face; pinyin and translations stay in the text face. */
private fun String.hasHanzi(): Boolean =
    any { it.code in 0x3400..0x9FFF || it.code in 0xF900..0xFAFF }
