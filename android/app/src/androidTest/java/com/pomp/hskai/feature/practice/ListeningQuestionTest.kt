package com.pomp.hskai.feature.practice

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.data.api.PracticeQuestionDto
import com.pomp.hskai.data.api.PracticeSessionDto
import com.pomp.hskai.feature.limit.LimitGate
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * A listening question must be heard, not read.
 *
 * `QuestionText` used to print `audioText` whenever `sentence` was empty —
 * which is exactly when the question is a listening one. The screen then said
 * "Eshiting va to'g'ri javobni tanlang" with 您 written above the options: the
 * answer, in full, for a question about hearing it. The same fallback left a
 * sentence-less question with nothing on screen at all.
 */
@RunWith(AndroidJUnit4::class)
class ListeningQuestionTest {

    @get:Rule
    val compose = createComposeRule()

    private val spoken = mutableListOf<String>()

    private fun runPractice(question: PracticeQuestionDto) {
        compose.setContent {
            PompHskAiTheme {
                PracticeScreen(
                    state = PracticeUiState(
                        session = PracticeSessionDto(
                            id = "s1",
                            mode = "drill",
                            level = "hsk1",
                            questions = listOf(question),
                        ),
                    ),
                    level = "hsk1",
                    language = "uz",
                    limit = LimitGate(),
                    onOpenDictionary = {},
                    onStartPractice = { _, _, _ -> },
                    onSelectPracticeOption = {},
                    onAdvancePractice = {},
                    onResetPractice = {},
                    onStartMistakeReview = {},
                    onAnswerReview = {},
                    onAdvanceReview = {},
                    onResetReview = {},
                    onSpeakReview = { spoken += it },
                    onStartExam = {},
                    onOpenDrill = {},
                    onSelectExamOption = {},
                    onAdvanceExam = {},
                    onResetExam = {},
                )
            }
        }
    }

    private fun listening() = PracticeQuestionDto(
        id = "q1",
        type = "listening_choice",
        prompt = "Eshiting va to‘g‘ri javobni tanlang",
        sentence = "",
        audioText = "您",
        options = listOf("你", "好", "您", "你们"),
        answerIndex = 2,
    )

    @Test
    fun theAnswerIsNotPrintedAboveTheOptions() {
        runPractice(listening())

        compose.onNodeWithText("Eshiting va to‘g‘ri javobni tanlang").assertIsDisplayed()
        // 您 is one of the options, so it is on screen once. Two would mean it
        // is also printed as the question — which is the bug.
        assertEquals(1, compose.onAllNodesWithTextCount("您"))
    }

    @Test
    fun aSpeakerIsOfferedInstead() {
        runPractice(listening())
        compose.onNodeWithContentDescription("Talaffuzni eshitish").assertIsDisplayed()
    }

    @Test
    fun itIsSpokenWithoutBeingAskedFor() {
        runPractice(listening())
        compose.waitForIdle()
        assertEquals(listOf("您"), spoken)
    }

    @Test
    fun aWrittenQuestionIsStillWrittenAndNotSpoken() {
        runPractice(
            PracticeQuestionDto(
                id = "q2",
                type = "multiple_choice",
                prompt = "Gapdagi bo‘sh joyga mos so‘zni tanlang",
                sentence = "谢谢！___",
                audioText = "",
                options = listOf("不客气", "谢谢", "不", "再见"),
                answerIndex = 0,
            )
        )

        compose.onNodeWithText("谢谢！___").assertIsDisplayed()
        compose.waitForIdle()
        assertEquals(emptyList<String>(), spoken)
    }
}

/** Counts matches without failing when there are none. */
private fun androidx.compose.ui.test.junit4.ComposeContentTestRule.onAllNodesWithTextCount(
    text: String,
): Int = onAllNodes(androidx.compose.ui.test.hasText(text)).fetchSemanticsNodes().size
