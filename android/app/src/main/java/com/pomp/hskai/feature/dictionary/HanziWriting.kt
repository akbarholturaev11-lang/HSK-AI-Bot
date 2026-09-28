package com.pomp.hskai.feature.dictionary

import androidx.compose.ui.geometry.Offset
import com.pomp.hskai.core.hanzi.CharacterStrokes
import com.pomp.hskai.core.hanzi.StrokeMatcher

/**
 * The steps of writing one character by hand.
 *
 * The app writes it first; then the learner writes it three times, each time
 * with less help: over the grey character, with only a dot where the next
 * stroke starts, and from memory.
 */
enum class WritingStage {
    DEMO,
    TRACE,
    HINT,
    MEMORY,
    DONE;

    val round: Int? get() = when (this) {
        TRACE -> 1
        HINT -> 2
        MEMORY -> 3
        else -> null
    }

    /** The whole character is shown in grey to write over. */
    val showsOutline: Boolean get() = this == TRACE

    /** A dot marks where the next stroke starts. */
    val showsStartDot: Boolean get() = this == TRACE || this == HINT

    companion object {
        const val ROUNDS = 3
    }
}

enum class WritingMiss { WRONG, BACKWARDS }

data class WritingUiState(
    val character: String,
    val strokes: CharacterStrokes,
    val stage: WritingStage = WritingStage.DEMO,
    /** How many times the demonstration has played, the first included. */
    val demoPlays: Int = 1,
    /** Changes whenever the demonstration should play from the start. */
    val demoKey: Int = 0,
    /** Strokes already written in the current round. */
    val strokeIndex: Int = 0,
    /** Misses on the stroke being written now. */
    val strokeMisses: Int = 0,
    /** Misses over the whole practice. */
    val totalMistakes: Int = 0,
    val lastMiss: WritingMiss? = null,
    /** Changes on every miss, so the rejected line can flash each time. */
    val missKey: Int = 0,
    /** The stroke being shown as a hint, if any. */
    val hintStroke: Int? = null,
    /** Changes whenever the hint should play again. */
    val hintKey: Int = 0,
) {
    val strokeCount: Int get() = strokes.size

    /** Every stroke of the round is down; the next round starts after a beat. */
    val isRoundComplete: Boolean get() = stage.round != null && strokeIndex >= strokeCount

    val canPlayDemoAgain: Boolean get() = stage == WritingStage.DEMO && demoPlays < MAX_DEMO_PLAYS

    val acceptsStrokes: Boolean get() = stage.round != null && !isRoundComplete

    /** 0..1 across the three rounds. */
    val progress: Float get() {
        val round = stage.round ?: return if (stage == WritingStage.DONE) 1f else 0f
        val within = if (strokeCount == 0) 0f else strokeIndex.toFloat() / strokeCount
        return ((round - 1) + within) / WritingStage.ROUNDS
    }

    companion object {
        const val MAX_DEMO_PLAYS = 3
        /** After this many misses on one stroke, the stroke is shown. */
        const val MISSES_BEFORE_HINT = 3
    }
}

/** Every rule of the practice, kept apart from the screen so it can be tested. */
internal object HanziWriting {

    fun start(character: String, strokes: CharacterStrokes): WritingUiState =
        WritingUiState(character = character, strokes = strokes)

    fun playDemoAgain(state: WritingUiState): WritingUiState {
        if (!state.canPlayDemoAgain) return state
        return state.copy(demoPlays = state.demoPlays + 1, demoKey = state.demoKey + 1)
    }

    fun beginWriting(state: WritingUiState): WritingUiState =
        roundStart(state, WritingStage.TRACE)

    /** [points] are in the character's grid ([com.pomp.hskai.core.hanzi.HanziGrid]). */
    fun submitStroke(state: WritingUiState, points: List<Offset>): WritingUiState {
        if (!state.acceptsStrokes) return state
        val match = StrokeMatcher.match(
            userPoints = points,
            medians = state.strokes.medians,
            strokeIndex = state.strokeIndex,
            outlineVisible = state.stage.showsOutline,
        )
        if (match.isMatch) {
            return state.copy(
                strokeIndex = state.strokeIndex + 1,
                strokeMisses = 0,
                lastMiss = null,
                hintStroke = null,
            )
        }
        // A tap or a speck is not an attempt at a stroke.
        if (points.size < 2) return state
        val misses = state.strokeMisses + 1
        val showHint = misses >= WritingUiState.MISSES_BEFORE_HINT
        return state.copy(
            strokeMisses = misses,
            totalMistakes = state.totalMistakes + 1,
            lastMiss = if (match.isBackwards) WritingMiss.BACKWARDS else WritingMiss.WRONG,
            missKey = state.missKey + 1,
            hintStroke = if (showHint) state.strokeIndex else state.hintStroke,
            hintKey = if (showHint) state.hintKey + 1 else state.hintKey,
        )
    }

    /** Shows the next stroke. Asking is not a mistake. */
    fun hint(state: WritingUiState): WritingUiState {
        if (!state.acceptsStrokes) return state
        return state.copy(hintStroke = state.strokeIndex, hintKey = state.hintKey + 1)
    }

    fun restartRound(state: WritingUiState): WritingUiState {
        val stage = if (state.stage.round != null) state.stage else WritingStage.TRACE
        return roundStart(state, stage)
    }

    /** Called once the finished round has been on screen for a beat. */
    fun nextRound(state: WritingUiState): WritingUiState {
        if (!state.isRoundComplete) return state
        return when (state.stage) {
            WritingStage.TRACE -> roundStart(state, WritingStage.HINT)
            WritingStage.HINT -> roundStart(state, WritingStage.MEMORY)
            else -> state.copy(stage = WritingStage.DONE, lastMiss = null, hintStroke = null)
        }
    }

    /** Practise the same character again from the first round. */
    fun again(state: WritingUiState): WritingUiState =
        roundStart(state.copy(totalMistakes = 0), WritingStage.TRACE)

    private fun roundStart(state: WritingUiState, stage: WritingStage): WritingUiState =
        state.copy(
            stage = stage,
            strokeIndex = 0,
            strokeMisses = 0,
            lastMiss = null,
            hintStroke = null,
        )
}
