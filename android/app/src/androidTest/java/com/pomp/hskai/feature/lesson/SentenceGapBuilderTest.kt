package com.pomp.hskai.feature.lesson

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.domain.model.SentenceBuilderCard
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * The gap card end to end: the sentence arrives built except for its gaps, the
 * bank fills them, and what leaves for grading is still the whole sentence.
 */
@RunWith(AndroidJUnit4::class)
class SentenceGapBuilderTest {

    @get:Rule
    val compose = createComposeRule()

    private val answer = listOf("你", "女儿", "的", "房间", "真", "漂亮", "啊")

    private val card = SentenceBuilderCard(
        materialRef = "v3-part:hsk2:4:1",
        promptSentence = "Qizingizning xonasi haqiqatan chiroyli!",
        tokens = answer + listOf("千", "手表"),
        answerTokens = answer,
        explanation = "",
    )

    private val plan = requireNotNull(planGaps(card))
    private var submitted: List<String>? = null

    private fun render() {
        compose.setContent {
            PompHskAiTheme {
                SentenceBuilderCardView(
                    card = card,
                    isAnswered = false,
                    onSubmit = { submitted = it },
                )
            }
        }
    }

    @Test
    fun the_sentence_arrives_already_built_around_its_gaps() {
        render()

        // Everything not hidden is on screen without the learner doing anything.
        answer.forEachIndexed { index, token ->
            if (index !in plan.blanks) compose.onNodeWithText(token).assertIsDisplayed()
        }
        // And the check is refused until the gaps are dealt with.
        compose.onNodeWithText("Tekshirish").assertIsNotEnabled()
    }

    @Test
    fun filling_the_gaps_submits_the_whole_sentence_for_grading() {
        render()

        // The bank holds duplicates of nothing here, so tapping by text is
        // unambiguous and fills the gaps left to right.
        plan.blanks.forEach { position ->
            compose.onNodeWithText(answer[position]).performClick()
        }

        compose.onNodeWithText("Tekshirish").assertIsEnabled().performClick()

        assertEquals(answer, submitted)
    }

    @Test
    fun a_distractor_reaches_the_grader_as_the_wrong_sentence() {
        render()

        compose.onNodeWithText("千").performClick()
        plan.blanks.drop(1).forEach { compose.onNodeWithText(answer[it]).performClick() }

        compose.onNodeWithText("Tekshirish").performClick()

        val built = requireNotNull(submitted)
        assertEquals(answer.size, built.size)
        assertEquals("千", built[plan.blanks.first()])
        assertEquals(false, card.isCorrect(built))
    }

    @Test
    fun a_filled_gap_can_be_emptied_again() {
        render()

        val first = plan.blanks.first()
        compose.onNodeWithText(answer[first]).performClick()
        compose.onNodeWithText("Tekshirish").assertIsNotEnabled()

        // Tapping the filled slot returns the tile to the bank.
        compose.onNodeWithText(answer[first]).performClick()

        plan.blanks.forEach { compose.onNodeWithText(answer[it]).performClick() }
        compose.onNodeWithText("Tekshirish").assertIsEnabled().performClick()
        assertEquals(answer, submitted)
    }
}
