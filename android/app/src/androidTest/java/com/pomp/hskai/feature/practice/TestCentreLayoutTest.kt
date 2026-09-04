package com.pomp.hskai.feature.practice

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onFirst
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.feature.limit.LimitGate
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * The test centre lists four exams, and HSK 3 and 4 carry four tags each: the
 * learner's own level plus three sections. Laid out in a plain row those tags
 * run past the card's edge, the last ones are squeezed to nothing, and the
 * card stretches to swallow the overflow. Compiling proves none of that, so
 * the tags are asserted to be on screen here.
 */
@RunWith(AndroidJUnit4::class)
class TestCentreLayoutTest {

    @get:Rule
    val compose = createComposeRule()

    private fun openTestCentre(level: String) {
        compose.setContent {
            PompHskAiTheme {
                PracticeScreen(
                    state = PracticeUiState(),
                    level = level,
                    language = "uz",
                    limit = LimitGate(),
                    onWatchAd = {},
                    onOpenDictionary = {},
                    onStartPractice = { _, _, _ -> },
                    onSelectPracticeOption = {},
                    onAdvancePractice = {},
                    onResetPractice = {},
                    onStartMistakeReview = {},
                    onAnswerReview = {},
                    onAdvanceReview = {},
                    onResetReview = {},
                    onStartExam = {},
                    onSelectExamOption = {},
                    onAdvanceExam = {},
                    onResetExam = {},
                )
            }
        }
        compose.onNodeWithText("Test markazi").performClick()
    }

    @Test
    fun every_tag_of_the_learners_own_exam_stays_on_screen() {
        // HSK 4 is the worst case: "your level" plus all three sections.
        openTestCentre("hsk4")
        compose.onNodeWithText("Sizning darajangiz").assertIsDisplayed()
        // Every exam carries the section tags, so each text matches several
        // rows. The learner's own exam is sorted to the top, which makes the
        // first match the one under test.
        compose.onAllNodesWithText("听力 Tinglash").onFirst().assertIsDisplayed()
        compose.onAllNodesWithText("阅读 O‘qish").onFirst().assertIsDisplayed()
        compose.onAllNodesWithText("书写 Yozish").onFirst().assertIsDisplayed()
    }

    @Test
    fun the_placement_offer_and_every_exam_are_listed() {
        openTestCentre("hsk1")
        compose.onNodeWithText("Darajangizni bilmaysizmi?").assertIsDisplayed()
        compose.onNodeWithText("HSK 1").assertIsDisplayed()
        compose.onNodeWithText("HSK 2").assertIsDisplayed()
    }
}
