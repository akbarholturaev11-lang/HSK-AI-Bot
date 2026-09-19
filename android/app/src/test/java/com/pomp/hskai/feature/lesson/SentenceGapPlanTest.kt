package com.pomp.hskai.feature.lesson

import com.pomp.hskai.domain.model.SentenceBuilderCard
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * `Gapni tuzing` made the learner lay all nine tiles of a sentence they had
 * just been shown. The grammar point is one or two words; the rest was thumb
 * work. The card now arrives built except for those, and this covers the part
 * that decides which — above all that the bank can always fill the gaps it
 * leaves, because a gap with no tile for it is an unanswerable card.
 */
class SentenceGapPlanTest {

    private fun card(
        answer: List<String>,
        tokens: List<String>,
        ref: String = "v3-part:hsk2:4:1",
    ) = SentenceBuilderCard(
        materialRef = ref,
        promptSentence = "Qizingizning xonasi haqiqatan chiroyli!",
        tokens = tokens,
        answerTokens = answer,
        explanation = "",
    )

    private val answer = listOf("你", "女儿", "的", "房间", "真", "漂亮", "啊")
    private val bank = answer + listOf("千", "手表")

    @Test
    fun `a long sentence keeps two gaps and shows the rest`() {
        val plan = requireNotNull(planGaps(card(answer, bank)))

        assertEquals(2, plan.blanks.size)
        assertEquals(plan.blanks.sorted(), plan.blanks)
        assertTrue(plan.blanks.all { it in answer.indices })
    }

    @Test
    fun `a short sentence keeps one gap`() {
        val short = listOf("你", "好", "吗")
        val plan = requireNotNull(planGaps(card(short, short + "千")))

        assertEquals(1, plan.blanks.size)
    }

    /** The whole card is unanswerable if a gap has no tile that fits it. */
    @Test
    fun `every gap has its own answer waiting in the bank`() {
        val plan = requireNotNull(planGaps(card(answer, bank)))

        val remaining = plan.bank.toMutableList()
        plan.blanks.forEach { position ->
            assertTrue(
                "no tile left for gap at $position (${answer[position]})",
                remaining.remove(answer[position]),
            )
        }
    }

    @Test
    fun `the bank is the hidden words plus the card's own distractors`() {
        val plan = requireNotNull(planGaps(card(answer, bank)))

        val expected = (plan.blanks.map { answer[it] } + listOf("千", "手表")).sorted()
        assertEquals(expected, plan.bank.sorted())
    }

    @Test
    fun `filling every gap correctly rebuilds the sentence the grader expects`() {
        val subject = card(answer, bank)
        val plan = requireNotNull(planGaps(subject))

        val built = answer.toMutableList()
        plan.blanks.forEach { built[it] = answer[it] }

        assertTrue(subject.isCorrect(built))
    }

    @Test
    fun `a wrong tile in a gap is still graded wrong`() {
        val subject = card(answer, bank)
        val plan = requireNotNull(planGaps(subject))

        val built = answer.toMutableList()
        built[plan.blanks.first()] = "千"

        assertTrue(!subject.isCorrect(built))
    }

    /** Gaps must not wander between recompositions, or a filled slot moves. */
    @Test
    fun `the same card always gets the same gaps`() {
        val first = requireNotNull(planGaps(card(answer, bank)))
        val second = requireNotNull(planGaps(card(answer, bank)))

        assertEquals(first.blanks, second.blanks)
        assertEquals(first.bank, second.bank)
    }

    @Test
    fun `different cards do not all blank the same position`() {
        val plans = (1..12).map {
            requireNotNull(planGaps(card(answer, bank, ref = "v3-part:hsk2:4:$it")))
        }

        assertTrue(plans.map { it.blanks }.distinct().size > 1)
    }

    /** Broken data falls back to the old build-it-all card, never to a dead gap. */
    @Test
    fun `tiles that cannot account for the answer refuse the gap plan`() {
        assertNull(planGaps(card(answer, tokens = listOf("千", "手表"))))
    }

    @Test
    fun `a card with no tiles refuses the gap plan`() {
        assertNull(planGaps(card(answer, tokens = emptyList())))
    }

    @Test
    fun `a one word answer refuses the gap plan`() {
        assertNull(planGaps(card(listOf("你"), listOf("你", "千"))))
    }

    /** Duplicated words must not be consumed twice while building the bank. */
    @Test
    fun `a repeated word leaves the right tiles behind`() {
        val repeated = listOf("我", "的", "书", "和", "他", "的", "书")
        val plan = planGaps(card(repeated, repeated + "千"))

        assertNotNull(plan)
        val remaining = requireNotNull(plan).bank.toMutableList()
        plan.blanks.forEach { assertTrue(remaining.remove(repeated[it])) }
    }
}
