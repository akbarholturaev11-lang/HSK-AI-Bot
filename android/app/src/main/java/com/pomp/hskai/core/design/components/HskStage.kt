package com.pomp.hskai.core.design.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.RoundRect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Outline
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathOperation
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles

/*
 * The stage layout a question is drawn in, shared by the lesson and the
 * practice screens: the instruction as a heading, the coach beside what it
 * says, full-width answers, and a solid button with a flat depth under it.
 *
 * It started in the lesson package and moved here when practice took the
 * same layout, for the reason the cast moved (`HskCharacters.kt`): two copies
 * of one screen style drift apart the moment one of them is retouched.
 */

/** Which side the bubble's tail points to: at the coach beside it, or down at the coach under it. */
internal enum class HskBubbleTail { Start, Bottom }

private val BubbleTailSize = 8.dp
private val BubbleRadius = 16.dp

/**
 * A rounded bubble with a tail, as one outline so the border runs around the
 * tail instead of cutting across its base.
 */
internal class HskSpeechBubbleShape(
    private val tail: HskBubbleTail,
    private val radius: Dp = BubbleRadius,
    private val tailSize: Dp = BubbleTailSize,
    /** For [HskBubbleTail.Bottom]: how far from the start edge the tail sits. */
    private val tailOffset: Dp = 56.dp,
) : Shape {
    override fun createOutline(size: Size, layoutDirection: LayoutDirection, density: Density): Outline {
        val r = with(density) { radius.toPx() }
        val body = Path()
        val tip = Path()
        when (tail) {
            HskBubbleTail.Start -> {
                val t = with(density) { tailSize.toPx() }.coerceAtMost(size.height / 2f)
                body.addRoundRect(RoundRect(t, 0f, size.width, size.height, CornerRadius(r)))
                val cy = size.height / 2f
                tip.moveTo(t + 1f, cy - t)
                tip.lineTo(0f, cy)
                tip.lineTo(t + 1f, cy + t)
                tip.close()
            }
            HskBubbleTail.Bottom -> {
                val t = with(density) { tailSize.toPx() }.coerceAtMost(size.width / 4f)
                body.addRoundRect(RoundRect(0f, 0f, size.width, size.height - t, CornerRadius(r)))
                val cx = with(density) { tailOffset.toPx() }
                    .coerceIn(r + t, (size.width - r - t).coerceAtLeast(r + t))
                tip.moveTo(cx - t, size.height - t - 1f)
                tip.lineTo(cx, size.height)
                tip.lineTo(cx + t, size.height - t - 1f)
                tip.close()
            }
        }
        val outline = Path()
        outline.op(body, tip, PathOperation.Union)
        return Outline.Generic(outline)
    }
}

/**
 * What the coach is saying. [onClick] makes the whole bubble the control —
 * a listening question's speaker, a pronunciation card's phrase.
 */
@Composable
internal fun HskSpeechBubble(
    tail: HskBubbleTail,
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    onClickLabel: String? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val shape = remember(tail) { HskSpeechBubbleShape(tail) }
    val padding = when (tail) {
        HskBubbleTail.Start -> PaddingValues(start = BubbleTailSize + 14.dp, end = 14.dp, top = 12.dp, bottom = 12.dp)
        HskBubbleTail.Bottom -> PaddingValues(start = 18.dp, end = 18.dp, top = 12.dp, bottom = 12.dp + BubbleTailSize)
    }
    val clickable = if (onClick != null) {
        Modifier.clickable(onClickLabel = onClickLabel, role = Role.Button, onClick = onClick)
    } else {
        Modifier
    }
    Column(
        modifier = modifier
            .clip(shape)
            .background(PompColors.PaperRaised, shape)
            .border(2.dp, PompColors.Divider, shape)
            .then(clickable)
            .padding(padding),
        content = content,
    )
}

/** The instruction, as the screen's heading. */
@Composable
internal fun HskStageHeading(text: String, modifier: Modifier = Modifier) {
    if (text.isBlank()) return
    Text(
        text = text,
        fontSize = 22.sp,
        lineHeight = 28.sp,
        fontWeight = FontWeight.Bold,
        color = PompColors.Ink,
        modifier = modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, top = 14.dp),
    )
}

/**
 * The coach standing beside what it says: a question's material, a word's
 * meaning. The character stays outside any clipping box so a jump or a
 * celebration is never cut at its edge.
 */
@Composable
internal fun HskStageCoach(
    character: HskCharacter,
    mood: HskCharacterMood,
    reaction: HskCharacterReaction?,
    reactionKey: Any?,
    modifier: Modifier = Modifier,
    /** False keeps the slot open without drawing the character (the lesson's entry scene). */
    showCharacter: Boolean = true,
    /** False leaves the character alone: a bubble with nothing in it is worse than none. */
    showBubble: Boolean = true,
    characterSize: Dp = 124.dp,
    onBubbleClick: (() -> Unit)? = null,
    onBubbleClickLabel: String? = null,
    bubble: @Composable ColumnScope.() -> Unit,
) {
    // The cast is drawn on a 100×110 box; keep it so the character is never stretched.
    val stageWidth = characterSize
    val stageHeight = characterSize * 1.1f
    Row(
        modifier = modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (showCharacter) {
            HskCharacterStage(
                character = character,
                mood = mood,
                reaction = reaction,
                reactionKey = reactionKey,
                modifier = Modifier.size(width = stageWidth, height = stageHeight),
            )
        } else {
            // The slot stays open so nothing jumps when the entry scene ends.
            Spacer(Modifier.size(width = stageWidth, height = stageHeight))
        }
        if (showBubble) {
            HskSpeechBubble(
                tail = HskBubbleTail.Start,
                modifier = Modifier.weight(1f),
                onClick = onBubbleClick,
                onClickLabel = onBubbleClickLabel,
                content = bubble,
            )
        }
    }
}

/** A plain line said by the coach, sized for the bubble. */
@Composable
internal fun HskBubbleText(text: String) {
    Text(
        text = text,
        fontSize = 17.sp,
        lineHeight = 24.sp,
        color = PompColors.Ink,
    )
}

/**
 * The stage's solid button: a flat, darker edge under it instead of a shadow,
 * the way the rest of the stage is drawn. A disabled button drops the edge,
 * so it reads as not pressable before the text is read.
 */
@Composable
internal fun HskDepthButton(
    text: String,
    color: Color,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    loading: Boolean = false,
) {
    val shape = RoundedCornerShape(14.dp)
    val live = enabled || loading
    Box(modifier = modifier.fillMaxWidth().padding(bottom = if (live) 4.dp else 0.dp)) {
        if (live) {
            Box(
                modifier = Modifier
                    .matchParentSize()
                    .offset(y = 4.dp)
                    .clip(shape)
                    .background(lerp(color, Color.Black, 0.22f)),
            )
        }
        Surface(
            onClick = onClick,
            enabled = enabled && !loading,
            color = if (live) color else PompColors.Divider,
            shape = shape,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth().height(52.dp)) {
                if (loading) {
                    HskBrandLoader(compact = true)
                } else {
                    Text(
                        text = text.uppercase(),
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.sp,
                        color = if (live) PompColors.Paper else PompColors.InkDisabled,
                        textAlign = TextAlign.Center,
                    )
                }
            }
        }
    }
}

/**
 * The stage's progress tube. A soft highlight runs along the top of the fill,
 * so it reads as a filled tube rather than a flat stripe.
 */
@Composable
internal fun HskStageProgress(progress: Float, modifier: Modifier = Modifier) {
    val animated by animateFloatAsState(
        targetValue = progress.coerceIn(0f, 1f),
        animationSpec = tween(durationMillis = 300),
        label = "stage-progress",
    )
    Box(
        modifier = modifier.height(16.dp).clip(RoundedCornerShape(8.dp)).background(PompColors.Divider),
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(animated)
                .fillMaxHeight()
                .clip(RoundedCornerShape(8.dp))
                .background(PompColors.Cinnabar),
        ) {
            if (animated > 0.06f) {
                Box(
                    modifier = Modifier
                        .padding(start = 8.dp, end = 8.dp, top = 4.dp)
                        .fillMaxWidth()
                        .height(4.dp)
                        .clip(RoundedCornerShape(2.dp))
                        .background(Color.White.copy(alpha = 0.3f)),
                )
            }
        }
    }
}

/** How an answer is lit. */
internal enum class HskOptionState { IDLE, SELECTED, CORRECT, WRONG }

/** Before the check only the pick is lit; after it, the right answer and the wrong pick. */
internal fun hskOptionState(
    index: Int,
    correctIndex: Int,
    selectedIndex: Int?,
    isAnswered: Boolean,
): HskOptionState = when {
    !isAnswered -> if (index == selectedIndex) HskOptionState.SELECTED else HskOptionState.IDLE
    index == correctIndex -> HskOptionState.CORRECT
    index == selectedIndex -> HskOptionState.WRONG
    else -> HskOptionState.IDLE
}

/**
 * One answer: a full-width, centred button with a flat depth under it. There
 * is no A/B/C — the answer is the button. [hanziSize] is the serif size used
 * when the answer is written in characters.
 */
@Composable
internal fun HskAnswerOption(
    text: String,
    state: HskOptionState,
    enabled: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    minHeight: Dp = 58.dp,
    hanziSize: TextUnit = 24.sp,
) {
    val border = when (state) {
        HskOptionState.IDLE -> PompColors.Divider
        HskOptionState.SELECTED -> PompColors.Cinnabar
        HskOptionState.CORRECT -> PompColors.Jade
        HskOptionState.WRONG -> PompColors.Flame
    }
    val background = when (state) {
        HskOptionState.IDLE -> PompColors.PaperRaised
        HskOptionState.SELECTED -> PompColors.CinnabarSoft
        HskOptionState.CORRECT -> PompColors.JadeSoft
        HskOptionState.WRONG -> PompColors.FlameSoft
    }
    val ink = when (state) {
        HskOptionState.IDLE -> PompColors.Ink
        HskOptionState.SELECTED -> PompColors.CinnabarDark
        HskOptionState.CORRECT -> PompColors.Jade
        HskOptionState.WRONG -> PompColors.Flame
    }
    val description = when (state) {
        HskOptionState.CORRECT -> stringResource(R.string.cd_answer_correct, text)
        HskOptionState.WRONG -> stringResource(R.string.cd_answer_wrong, text)
        else -> text
    }
    val shape = RoundedCornerShape(14.dp)
    Box(modifier = modifier.fillMaxWidth().padding(bottom = 4.dp)) {
        // The flat edge under the button: neutral while idle, the state's own colour once lit.
        Box(
            modifier = Modifier
                .matchParentSize()
                .offset(y = 4.dp)
                .clip(shape)
                .background(if (state == HskOptionState.IDLE) PompColors.OptionDepth else border),
        )
        Surface(
            onClick = onClick,
            enabled = enabled,
            color = background,
            shape = shape,
            border = BorderStroke(2.dp, border),
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = minHeight)
                .semantics {
                    contentDescription = description
                    selected = state == HskOptionState.SELECTED
                },
        ) {
            Box(contentAlignment = Alignment.Center, modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) {
                Text(
                    text = text,
                    style = if (text.hasHanzi()) {
                        PompTextStyles.hanziMedium.copy(fontSize = hanziSize, lineHeight = hanziSize * 1.34f)
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
