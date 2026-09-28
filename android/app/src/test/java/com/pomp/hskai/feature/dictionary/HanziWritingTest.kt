package com.pomp.hskai.feature.dictionary

import com.pomp.hskai.core.hanzi.CharacterStrokes
import com.pomp.hskai.core.hanzi.StrokeMatcherTest.Companion.bundledMedians
import com.pomp.hskai.core.hanzi.StrokeMatcherTest.Companion.finger
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class HanziWritingTest {

    private val medians = bundledMedians('好')
    private val strokes = CharacterStrokes(outlines = medians.map { "M 0 0 Z" }, medians = medians)

    private fun writeRound(state: WritingUiState): WritingUiState =
        medians.indices.fold(state) { current, index -> HanziWriting.submitStroke(current, finger(medians[index], index)) }

    @Test
    fun `the demonstration can be replayed at most three times`() {
        var state = HanziWriting.start("好", strokes)
        assertEquals(WritingStage.DEMO, state.stage)
        assertFalse(state.acceptsStrokes)

        repeat(5) { state = HanziWriting.playDemoAgain(state) }

        assertEquals(WritingUiState.MAX_DEMO_PLAYS, state.demoPlays)
        assertFalse(state.canPlayDemoAgain)
    }

    @Test
    fun `three clean rounds take the learner from tracing to done`() {
        var state = HanziWriting.beginWriting(HanziWriting.start("好", strokes))
        val stages = mutableListOf(state.stage)

        repeat(WritingStage.ROUNDS) {
            state = writeRound(state)
            assertTrue(state.isRoundComplete)
            assertFalse("no strokes between rounds", state.acceptsStrokes)
            state = HanziWriting.nextRound(state)
            stages += state.stage
        }

        assertEquals(
            listOf(WritingStage.TRACE, WritingStage.HINT, WritingStage.MEMORY, WritingStage.DONE),
            stages,
        )
        assertEquals(0, state.totalMistakes)
        assertEquals(1f, state.progress)
    }

    @Test
    fun `a wrong stroke is a mistake and the third shows the stroke`() {
        var state = HanziWriting.beginWriting(HanziWriting.start("好", strokes))
        val wrong = finger(medians.last(), 9)

        state = HanziWriting.submitStroke(state, wrong)
        assertEquals(WritingMiss.WRONG, state.lastMiss)
        assertEquals(1, state.totalMistakes)
        assertNull(state.hintStroke)

        state = HanziWriting.submitStroke(HanziWriting.submitStroke(state, wrong), wrong)
        assertEquals(3, state.strokeMisses)
        assertEquals(0, state.hintStroke)
        assertEquals(0, state.strokeIndex)

        state = HanziWriting.submitStroke(state, finger(medians[0], 0))
        assertEquals(1, state.strokeIndex)
        assertEquals(0, state.strokeMisses)
        assertNull("the hint goes once the stroke is written", state.hintStroke)
        assertNull(state.lastMiss)
        assertEquals(3, state.totalMistakes)
    }

    @Test
    fun `a backwards stroke is told apart from a wrong one`() {
        val state = HanziWriting.submitStroke(
            HanziWriting.beginWriting(HanziWriting.start("好", strokes)),
            finger(medians[0], 2).asReversed(),
        )

        assertEquals(WritingMiss.BACKWARDS, state.lastMiss)
    }

    @Test
    fun `asking for the next stroke is not a mistake`() {
        val state = HanziWriting.hint(HanziWriting.beginWriting(HanziWriting.start("好", strokes)))

        assertEquals(0, state.hintStroke)
        assertEquals(0, state.totalMistakes)
    }

    @Test
    fun `restarting a round keeps the round and clears its strokes`() {
        var state = HanziWriting.beginWriting(HanziWriting.start("好", strokes))
        state = HanziWriting.submitStroke(state, finger(medians[0], 0))
        state = HanziWriting.submitStroke(state, finger(medians[1], 1))

        state = HanziWriting.restartRound(state)

        assertEquals(WritingStage.TRACE, state.stage)
        assertEquals(0, state.strokeIndex)
    }

    @Test
    fun `progress runs across the three rounds`() {
        var state = HanziWriting.beginWriting(HanziWriting.start("好", strokes))
        assertEquals(0f, state.progress)

        state = HanziWriting.nextRound(writeRound(state))

        assertEquals(WritingStage.HINT, state.stage)
        assertEquals(1f / 3f, state.progress, 0.001f)
    }

    @Test
    fun `writing again starts over with a clean slate`() {
        var state = HanziWriting.beginWriting(HanziWriting.start("好", strokes))
        state = HanziWriting.submitStroke(state, finger(medians.last(), 4))

        state = HanziWriting.again(state)

        assertEquals(WritingStage.TRACE, state.stage)
        assertEquals(0, state.totalMistakes)
    }
}
