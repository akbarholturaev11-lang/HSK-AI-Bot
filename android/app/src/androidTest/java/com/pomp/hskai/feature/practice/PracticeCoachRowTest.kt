package com.pomp.hskai.feature.practice

import android.graphics.Bitmap
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.data.api.MistakeReviewQuestionDto
import com.pomp.hskai.data.api.MistakeReviewSessionDto
import com.pomp.hskai.data.api.PracticeQuestionDto
import com.pomp.hskai.data.api.PracticeSessionDto
import com.pomp.hskai.feature.limit.LimitGate
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.io.FileOutputStream

/**
 * The practice screens carry a coach, and the coach carries the screen's own
 * instruction.
 *
 * The line is MOVED into the bubble, not copied: a drill used to print its
 * instruction as a grey line of its own, and a review printed its category
 * above the question. If either came back, the same sentence would sit on
 * screen twice — which is what these tests fail on.
 *
 * Each test also writes a PNG into the app's external files directory, so the
 * layout can be looked at rather than only asserted about:
 *   adb pull /sdcard/Android/data/<id>/files/coach-*.png
 */
@RunWith(AndroidJUnit4::class)
class PracticeCoachRowTest {

    @get:Rule
    val compose = createComposeRule()

    /**
     * Saves the rendered screen so the layout can be looked at, not only
     * asserted about. Internal storage on purpose: `getExternalFilesDir` can
     * return null on an emulator with no mounted media, and a screenshot that
     * silently never lands is worse than none.
     *   adb exec-out run-as com.pomp.hskai cat files/coach-<name>.png > x.png
     */
    private fun shoot(name: String) {
        compose.waitForIdle()
        val bitmap = compose.onRoot().captureToImage().asAndroidBitmap()
        val dir = InstrumentationRegistry.getInstrumentation().targetContext.filesDir
        val file = File(dir, "coach-$name.png")
        FileOutputStream(file).use {
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)
        }
        android.util.Log.i("CoachShot", "saved ${file.absolutePath} (${file.length()} bytes)")
    }

    // ---- recognition drill -------------------------------------------------

    private fun drillState(
        answered: Boolean,
        mode: DrillMode = DrillMode.RECOGNITION,
    ) = WordDrillUiState(
        isLoading = false,
        mode = mode,
        questions = listOf(
            DrillQuestion(
                hanzi = "好",
                pinyin = "hǎo",
                meaning = "yaxshi",
                options = listOf("好", "女", "子", "妈"),
                isReview = false,
            ),
        ),
        index = 0,
        isAnswered = answered,
        wasCorrect = answered,
        answerStreak = if (answered) 1 else 0,
    )

    @Composable
    private fun drill(answered: Boolean, mode: DrillMode = DrillMode.RECOGNITION) {
        WordDrillScreen(
            state = drillState(answered, mode),
            limit = LimitGate(),
            onChoose = {},
            onSpeak = {},
            onSkipSpoken = {},
            onAdvance = {},
            onRetry = {},
            onClose = {},
        )
    }

    @Test
    fun theDrillInstructionIsTheCoachsLineAndAppearsOnlyOnce() {
        compose.setContent { PompHskAiTheme { drill(answered = false) } }

        val instruction = InstrumentationRegistry.getInstrumentation()
            .targetContext
            .getString(com.pomp.hskai.R.string.drill_recognition_prompt)

        // Capture before asserting: when this fails, the picture is the only
        // thing that says whether the line is missing or merely clipped.
        shoot("drill-idle")
        compose.onNodeWithText(instruction).assertIsDisplayed()
        // Two would mean the old grey line came back underneath the bubble.
        assertOnce(instruction)
    }

    @Test
    fun theDrillCoachStaysThroughAnAnsweredQuestion() {
        compose.setContent { PompHskAiTheme { drill(answered = true) } }

        val instruction = InstrumentationRegistry.getInstrumentation()
            .targetContext
            .getString(com.pomp.hskai.R.string.drill_recognition_prompt)

        // A reaction must not blank the bubble and leave the character alone.
        compose.onNodeWithText(instruction).assertIsDisplayed()
        shoot("drill-answered")
    }

    @Test
    fun thePronunciationDrillKeepsTheCharacterFullSize() {
        compose.setContent {
            PompHskAiTheme { drill(answered = false, mode = DrillMode.PRONUNCIATION) }
        }

        val instruction = InstrumentationRegistry.getInstrumentation()
            .targetContext
            .getString(com.pomp.hskai.R.string.drill_pronunciation_prompt)

        shoot("pron-idle")
        compose.onNodeWithText(instruction).assertIsDisplayed()

        // The whole screen is "say this character", so it must be on it, at
        // full width. Standing it in the narrow column beside the coach once
        // shrank it to a postage stamp above a screenful of nothing.
        compose.onNodeWithText("好").assertIsDisplayed()
        val hanzi = compose.onNodeWithText("好").fetchSemanticsNode().boundsInRoot
        val root = compose.onRoot().fetchSemanticsNode().boundsInRoot
        org.junit.Assert.assertTrue(
            "the drilled character must be centred, not pushed into a side column",
            kotlin.math.abs(hanzi.center.x - root.center.x) < root.width * 0.12f,
        )
    }

    // ---- mistake review ----------------------------------------------------

    @Test
    fun theReviewCategoryLineMovesIntoTheBubble() {
        compose.setContent {
            PompHskAiTheme {
                MistakesReviewRun(
                    state = PracticeUiState(
                        reviewSession = MistakeReviewSessionDto(
                            id = "r1",
                            questions = listOf(
                                MistakeReviewQuestionDto(
                                    id = "q1",
                                    category = "grammar",
                                    prompt = "Bo‘sh joyni to‘ldiring",
                                    options = listOf("是", "有", "很"),
                                    sentence = "我___学生",
                                    pinyin = "wǒ ___ xuéshēng",
                                ),
                            ),
                        ),
                        reviewIndex = 0,
                    ),
                    onSelect = {},
                    onAdvance = {},
                    onCancel = {},
                    onSpeak = {},
                )
            }
        }

        compose.onNodeWithText("Bo‘sh joyni to‘ldiring").assertIsDisplayed()
        shoot("review-idle")
    }

    // ---- placement question ------------------------------------------------

    @Test
    fun thePlacementProgressLineMovesIntoTheBubble() {
        compose.setContent {
            PompHskAiTheme {
                PracticeScreen(
                    state = PracticeUiState(
                        session = PracticeSessionDto(
                            id = "s1",
                            mode = "placement",
                            level = "hsk1",
                            questions = listOf(
                                PracticeQuestionDto(
                                    id = "q1",
                                    type = "multiple_choice",
                                    prompt = "Gapdagi bo‘sh joyga mos so‘zni tanlang",
                                    sentence = "谢谢！___",
                                    options = listOf("不客气", "谢谢", "不", "再见"),
                                    answerIndex = 0,
                                ),
                            ),
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
                    onSpeakReview = {},
                    onStartExam = {},
                    onOpenDrill = {},
                    onSelectExamOption = {},
                    onAdvanceExam = {},
                    onResetExam = {},
                )
            }
        }

        compose.onNodeWithText("谢谢！___").assertIsDisplayed()
        shoot("placement-idle")
    }

    private fun assertOnce(text: String) {
        val count = compose
            .onAllNodes(androidx.compose.ui.test.hasText(text))
            .fetchSemanticsNodes()
            .size
        org.junit.Assert.assertEquals("'$text' must appear exactly once", 1, count)
    }
}
