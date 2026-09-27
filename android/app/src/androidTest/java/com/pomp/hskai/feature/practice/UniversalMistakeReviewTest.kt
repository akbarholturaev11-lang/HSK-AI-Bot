package com.pomp.hskai.feature.practice

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.data.api.MistakeReviewQuestionDto
import com.pomp.hskai.data.api.MistakeReviewSessionDto
import com.pomp.hskai.data.api.MistakeSummaryDto
import com.pomp.hskai.data.api.MistakeTargetDto
import com.pomp.hskai.data.api.MistakesOverviewResponse
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * The universal mistake review: sentence building from tiles, and the list
 * of targets with their three-exercise progress and the category scope.
 */
@RunWith(AndroidJUnit4::class)
class UniversalMistakeReviewTest {

    @get:Rule
    val compose = createComposeRule()

    // HskDepthButton draws its label in capitals.
    private val CHECK = "TEKSHIRISH"

    private val builder = MistakeReviewQuestionDto(
        id = "t:1:sentence_builder",
        category = "grammar",
        prompt = "Gapni tuzing: «Men talabaman.»",
        format = "sentence_builder",
        tokens = listOf("学生", "我", "是"),
    )

    private fun openBuilder(onSubmit: (List<String>) -> Unit) {
        compose.setContent {
            PompHskAiTheme {
                MistakesReviewRun(
                    state = PracticeUiState(
                        reviewSession = MistakeReviewSessionDto(id = "s1", questions = listOf(builder)),
                    ),
                    onSelect = {},
                    onAdvance = {},
                    onCancel = {},
                    onSpeak = {},
                    onSubmitTokens = onSubmit,
                )
            }
        }
    }

    @Test
    fun a_sentence_is_built_from_the_tiles_and_sent_in_the_laid_order() {
        val sent = mutableListOf<List<String>>()
        openBuilder { sent += it }

        compose.onNodeWithText(CHECK).assertIsNotEnabled()
        compose.onNodeWithText("我").performClick()
        compose.onNodeWithText("是").performClick()
        compose.onNodeWithText(CHECK).assertIsNotEnabled()
        compose.onNodeWithText("学生").performClick()
        compose.onNodeWithText(CHECK).assertIsEnabled().performClick()

        assertEquals(listOf(listOf("我", "是", "学生")), sent)
    }

    @Test
    fun a_laid_tile_goes_back_to_the_bank_when_tapped() {
        val sent = mutableListOf<List<String>>()
        openBuilder { sent += it }

        compose.onNodeWithText("是").performClick()
        compose.onNodeWithText("我").performClick()
        // Lift 是 (first laid) back, then lay it after 我.
        compose.onNodeWithText("是").performClick()
        compose.onNodeWithText("是").performClick()
        compose.onNodeWithText("学生").performClick()
        compose.onNodeWithText(CHECK).performClick()

        assertEquals(listOf(listOf("我", "是", "学生")), sent)
    }

    @Test
    fun the_list_shows_each_target_with_its_progress_and_scopes_the_review() {
        val picked = mutableListOf<String>()
        compose.setContent {
            PompHskAiTheme {
                MistakesOverviewScreen(
                    state = PracticeUiState(
                        mistakeCategory = "grammar",
                        mistakes = MistakesOverviewResponse(
                            ok = true,
                            summary = MistakeSummaryDto(total = 2, categories = mapOf("word" to 1, "grammar" to 1)),
                            targets = listOf(
                                MistakeTargetDto(
                                    id = 1, category = "grammar", kind = "sentence", zh = "我是学生。",
                                    pinyin = "wǒ shì xuésheng", translation = "Men talabaman.",
                                    wrong = "我是学生吗", passed = 1, required = 3, sources = listOf("voice"),
                                ),
                                MistakeTargetDto(
                                    id = 2, category = "word", kind = "word", zh = "你", pinyin = "nǐ",
                                    meaning = "sen", required = 3, sources = listOf("lesson"),
                                ),
                            ),
                        ),
                    ),
                    onBack = {},
                    onStartReview = {},
                    onReload = {},
                    onSelectCategory = { picked += it },
                )
            }
        }

        // The chip picked in the view model scopes both the list and the CTA.
        compose.onNodeWithText("Grammatika bo'yicha takrorlash").assertIsDisplayed()
        compose.onNodeWithText("Xatolar: 1 · har biri 3 xil mashqda").assertIsDisplayed()
        compose.onNodeWithText("我是学生。").assertIsDisplayed()
        compose.onNodeWithText("Men talabaman.").assertIsDisplayed()
        compose.onNodeWithText("✗ 我是学生吗").assertIsDisplayed()
        compose.onNodeWithContentDescription("1 / 3 mashq bajarildi").assertIsDisplayed()
        assertEquals(0, compose.onAllNodesWithText("你").fetchSemanticsNodes().size)

        compose.onNode(hasText("So'zlar · 1")).performClick()
        assertEquals(listOf("word"), picked)
    }
}
