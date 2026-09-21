package com.pomp.hskai.feature.lesson

import androidx.compose.runtime.Composable
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.ui.Modifier
import com.pomp.hskai.core.design.components.HskCharacter
import com.pomp.hskai.core.design.components.HskCharacterMood
import com.pomp.hskai.core.design.components.HskCharacterReaction
import com.pomp.hskai.core.design.components.HskCharacterStage
import com.pomp.hskai.core.design.components.hskReactionFor
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.ChoiceKind
import com.pomp.hskai.domain.model.GrammarCard
import com.pomp.hskai.domain.model.LessonCard
import com.pomp.hskai.domain.model.MatchPairsCard
import com.pomp.hskai.domain.model.ReverseBuilderCard
import com.pomp.hskai.domain.model.SentenceBuilderCard

/**
 * The lesson's half of the character system: WHICH character a card gets.
 *
 * The cast itself, its moods and its motion live in
 * [com.pomp.hskai.core.design.components.HskCharacterStage] — practice, the
 * mistake review and the word drills draw from the very same renderer, so a
 * retimed jump lands everywhere at once instead of in one screen only.
 *
 * The aliases below keep the lesson's own vocabulary (and its parity test)
 * pointed at the shared types.
 */
internal typealias LessonCharacter = HskCharacter
internal typealias LessonCharacterMood = HskCharacterMood
internal typealias LessonCharacterReaction = HskCharacterReaction

internal fun lessonCharacterFor(card: LessonCard): LessonCharacter = when (card) {
    is GrammarCard -> LessonCharacter.Crane
    is SentenceBuilderCard,
    is ReverseBuilderCard,
    is MatchPairsCard -> LessonCharacter.Monkey
    is ChoiceCard -> when {
        card.isReviewCard -> LessonCharacter.Rabbit
        card.kind == ChoiceKind.GAP_FILL -> LessonCharacter.Crane
        card.kind == ChoiceKind.DIALOG_CLOZE ||
            card.kind == ChoiceKind.QUICK_QUIZ -> LessonCharacter.Monkey
        else -> LessonCharacter.Panda
    }
    else -> LessonCharacter.Panda
}

internal fun lessonReactionFor(
    correct: Boolean,
    hearts: Int,
    streak: Int = 0,
): LessonCharacterReaction = hskReactionFor(correct = correct, hearts = hearts, streak = streak)

/**
 * What the coach is saying on this card.
 *
 * Only [ChoiceCard] carries a real instruction of its own (`title` — "pick
 * the word that fits"), which is the same field the Mini App puts in its
 * `.qq` line. Everything else falls back to the stage title, because a
 * character with an empty bubble is the lone sticker this layout replaced.
 */
internal fun lessonCoachLine(card: LessonCard, fallback: String): String =
    (card as? ChoiceCard)?.title?.ifBlank { fallback } ?: fallback

/**
 * The line the coach is currently saying, so a card does not print it a
 * second time underneath. Read by [com.pomp.hskai.feature.lesson.CardTitle],
 * which is the one place every card type's instruction goes through — far
 * safer than editing each card composable to drop its own title.
 */
internal val LocalLessonCoachLine = compositionLocalOf { "" }

@Composable
internal fun LessonCharacterStage(
    character: LessonCharacter,
    mood: LessonCharacterMood = LessonCharacterMood.Idle,
    reaction: LessonCharacterReaction? = null,
    reactionKey: Any? = null,
    modifier: Modifier = Modifier,
) {
    HskCharacterStage(
        character = character,
        mood = mood,
        reaction = reaction,
        reactionKey = reactionKey,
        modifier = modifier,
    )
}
