package com.pomp.hskai.feature.lesson

import com.pomp.hskai.core.network.ApiError

/**
 * UIUX-008 picture pronunciation deck: the deck's own state while the lesson
 * index stays on its [com.pomp.hskai.domain.model.PictureReviewCard].
 *
 * Nothing here touches hearts, accuracy, streak, mistakes or XP; the lesson
 * moves on only when the deck is empty.
 */
enum class PictureOutcome { PASS, WRONG, SKIP }

sealed interface PicturePhase {
    data object Ask : PicturePhase
    data object Recording : PicturePhase
    data object Scoring : PicturePhase

    /** Scored: the card has flipped and shows the answer. */
    data class Reveal(val passed: Boolean) : PicturePhase

    /** The front card is animating out. */
    data class Leaving(val outcome: PictureOutcome) : PicturePhase
}

data class PictureDeckState(
    /** Indexes into the card's words, front first. */
    val order: List<Int>,
    val tries: Map<Int, Int> = emptyMap(),
    val phase: PicturePhase = PicturePhase.Ask,
    /** The last try was not heard clearly: ask again, no verdict. */
    val unclear: Boolean = false,
    val error: ApiError? = null,
    /** Bumped on every move so the screen can key the next front card. */
    val moves: Int = 0,
) {
    val front: Int? get() = order.firstOrNull()
}

/** A word is asked at most this many times in one deck. */
internal const val PICTURE_MAX_TRIES = 3

/**
 * The queue rule, shared in spirit with the Mini App's `pictureDeckAdvance`:
 * a right or skipped card leaves; a wrong one goes to the back to be asked
 * again, until it has been missed [PICTURE_MAX_TRIES] times.
 */
internal fun PictureDeckState.after(outcome: PictureOutcome): PictureDeckState {
    val front = order.firstOrNull() ?: return this
    val rest = order.drop(1)
    if (outcome != PictureOutcome.WRONG) {
        return copy(order = rest, phase = PicturePhase.Ask, unclear = false, error = null, moves = moves + 1)
    }
    val missed = (tries[front] ?: 0) + 1
    return copy(
        order = if (missed < PICTURE_MAX_TRIES) rest + front else rest,
        tries = tries + (front to missed),
        phase = PicturePhase.Ask,
        unclear = false,
        error = null,
        moves = moves + 1,
    )
}

internal fun ApiError.isPronounceLimit(): Boolean =
    this is ApiError.LimitReached || (this as? ApiError.Server)?.code == "PRONOUNCE_LIMIT_EXCEEDED"
