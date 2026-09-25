package com.pomp.hskai.feature.lesson

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
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
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
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskBrandLoader

/*
 * The lesson's own speech bubble, coach row and buttons for the stage layout:
 * the instruction as a heading, the coach beside what it says, and a solid
 * button with a flat depth under it.
 *
 * They live in the lesson package on purpose. Practice, mistakes and the word
 * drills keep the shared `HskCoachRow` / `HskCoachBeside` until they are moved
 * to this layout too — changing the shared ones would restyle those screens
 * in the same release.
 */

/** Which side the bubble's tail points to: at the coach beside it, or down at the coach under it. */
internal enum class BubbleTail { Start, Bottom }

private val BubbleTailSize = 8.dp
private val BubbleRadius = 16.dp

/**
 * A rounded bubble with a tail, as one outline so the border runs around the
 * tail instead of cutting across its base.
 */
internal class SpeechBubbleShape(
    private val tail: BubbleTail,
    private val radius: Dp = BubbleRadius,
    private val tailSize: Dp = BubbleTailSize,
    /** For [BubbleTail.Bottom]: how far from the start edge the tail sits. */
    private val tailOffset: Dp = 56.dp,
) : Shape {
    override fun createOutline(size: Size, layoutDirection: LayoutDirection, density: Density): Outline {
        val r = with(density) { radius.toPx() }
        val body = Path()
        val tip = Path()
        when (tail) {
            BubbleTail.Start -> {
                val t = with(density) { tailSize.toPx() }.coerceAtMost(size.height / 2f)
                body.addRoundRect(RoundRect(t, 0f, size.width, size.height, CornerRadius(r)))
                val cy = size.height / 2f
                tip.moveTo(t + 1f, cy - t)
                tip.lineTo(0f, cy)
                tip.lineTo(t + 1f, cy + t)
                tip.close()
            }
            BubbleTail.Bottom -> {
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
 * the listening card's speaker, the pronunciation card's phrase.
 */
@Composable
internal fun LessonSpeechBubble(
    tail: BubbleTail,
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    onClickLabel: String? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val shape = remember(tail) { SpeechBubbleShape(tail) }
    val padding = when (tail) {
        BubbleTail.Start -> PaddingValues(start = BubbleTailSize + 14.dp, end = 14.dp, top = 12.dp, bottom = 12.dp)
        BubbleTail.Bottom -> PaddingValues(start = 18.dp, end = 18.dp, top = 12.dp, bottom = 12.dp + BubbleTailSize)
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
internal fun LessonHeading(text: String, modifier: Modifier = Modifier) {
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
internal fun LessonCoachBeside(
    character: LessonCharacter,
    mood: LessonCharacterMood,
    reaction: LessonCharacterReaction?,
    reactionKey: Any?,
    showCharacter: Boolean,
    modifier: Modifier = Modifier,
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
            LessonCharacterStage(
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
            LessonSpeechBubble(
                tail = BubbleTail.Start,
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
internal fun BubbleText(text: String) {
    Text(
        text = text,
        fontSize = 17.sp,
        lineHeight = 24.sp,
        color = PompColors.Ink,
    )
}

/**
 * The lesson's solid button: a flat, darker edge under it instead of a shadow,
 * the way the rest of the stage is drawn. A disabled button drops the edge,
 * so it reads as not pressable before the text is read.
 */
@Composable
internal fun LessonDepthButton(
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
 * The ready answer after a wrong one, said by the AI tutor's avatar. It is the
 * card's own explanation, already in the lesson data: no model is asked, so
 * showing it costs nothing.
 */
@Composable
internal fun ReadyAnswer(text: String, modifier: Modifier = Modifier) {
    Row(
        modifier = modifier.fillMaxWidth(),
        verticalAlignment = Alignment.Top,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier.size(28.dp).clip(RoundedCornerShape(50)).background(PompColors.Cinnabar),
        ) {
            // The same mark the AI chat uses for its own messages.
            Text("AI", color = PompColors.Paper, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
        }
        Surface(
            color = PompColors.PaperRaised,
            shape = RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp, bottomEnd = 20.dp, bottomStart = 6.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, PompColors.Divider),
        ) {
            Text(
                text = text,
                fontSize = 15.sp,
                lineHeight = 21.sp,
                color = PompColors.Ink,
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
            )
        }
    }
}

/** One question the learner can hand to the AI chat with this card as context. */
@Composable
internal fun AskChip(text: String, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(999.dp),
        color = PompColors.PaperRaised,
        border = androidx.compose.foundation.BorderStroke(1.dp, PompColors.Divider),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelLarge,
            color = PompColors.Ink,
            modifier = Modifier.padding(horizontal = 13.dp, vertical = 8.dp),
        )
    }
}
