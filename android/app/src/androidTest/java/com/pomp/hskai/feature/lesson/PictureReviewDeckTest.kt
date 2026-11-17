package com.pomp.hskai.feature.lesson

import android.graphics.Bitmap
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.settings.PinyinVisibility
import com.pomp.hskai.domain.model.Lesson
import com.pomp.hskai.domain.model.LessonSection
import com.pomp.hskai.domain.model.PictureReviewCard
import com.pomp.hskai.domain.model.PictureWord
import java.io.File
import java.io.FileOutputStream
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * UIUX-008 picture deck on a real device: the answer stays hidden until the
 * server has scored the try, then the card turns over to the hanzi (always),
 * pinyin (by the lesson setting) and the meaning. Screenshots land in the
 * app's files dir as `picture-*.png` for review.
 */
@RunWith(AndroidJUnit4::class)
class PictureReviewDeckTest {
    @get:Rule val compose = createComposeRule()

    private val card = PictureReviewCard(
        materialRef = "lesson:hsk1:5:picture_review",
        words = listOf(
            PictureWord("苹果", "píngguǒ", "olma", "🍎"),
            PictureWord("猫", "māo", "mushuk", "🐈"),
            PictureWord("书", "shū", "kitob", "📕"),
        ),
    )
    private val deck = mutableStateOf(PictureDeckState(order = listOf(0, 1, 2)))
    private val pinyin = mutableStateOf(PinyinVisibility.ALL)
    private var skips = 0
    private var continues = 0

    private fun show() {
        compose.setContent {
            PompHskAiTheme {
                Box(Modifier.fillMaxSize().background(PompColors.Paper).padding(horizontal = 20.dp)) {
                    PictureReviewDeckView(
                        card = card,
                        deck = deck.value,
                        pinyin = pinyin.value,
                        onSpeak = {},
                        onSkip = { skips++ },
                        onContinue = { continues++ },
                    )
                }
            }
        }
    }

    private fun text(id: Int) = InstrumentationRegistry.getInstrumentation().targetContext.getString(id)

    private fun shoot(name: String) {
        compose.waitForIdle()
        val bitmap = compose.onRoot().captureToImage().asAndroidBitmap()
        val dir = InstrumentationRegistry.getInstrumentation().targetContext.filesDir
        FileOutputStream(File(dir, "picture-$name.png")).use {
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)
        }
    }

    @Test
    fun theAnswerStaysHiddenUntilTheTryIsScored() {
        show()
        shoot("ask")

        compose.onNodeWithContentDescription("olma").assertIsDisplayed()
        compose.onNodeWithText(text(R.string.hsk_course_pronunciation_skip)).assertIsDisplayed()
        compose.onNodeWithText("苹果").assertDoesNotExist()
        compose.onNodeWithText("píngguǒ").assertDoesNotExist()

        compose.onNodeWithText(text(R.string.hsk_course_pronunciation_skip)).performClick()
        assertEquals(1, skips)
    }

    @Test
    fun aRightAnswerTurnsTheCardToHanziPinyinAndMeaning() {
        show()
        deck.value = deck.value.copy(phase = PicturePhase.Reveal(passed = true))
        shoot("correct")

        compose.onNodeWithText("苹果").assertIsDisplayed()
        compose.onNodeWithText("píngguǒ").assertIsDisplayed()
        compose.onNodeWithText("olma").assertIsDisplayed()
        compose.onNodeWithText(text(R.string.hsk_course_correct)).assertIsDisplayed()

        // A tap on the revealed card moves on without waiting for the timer.
        compose.onNodeWithText("苹果").performClick()
        assertEquals(1, continues)
    }

    @Test
    fun aWrongAnswerShowsTheAnswerAndRespectsThePinyinSetting() {
        pinyin.value = PinyinVisibility.NEW_WORDS_ONLY
        show()
        deck.value = deck.value.copy(phase = PicturePhase.Reveal(passed = false))
        shoot("wrong")

        compose.onNodeWithText("苹果").assertIsDisplayed()
        compose.onNodeWithText("olma").assertIsDisplayed()
        compose.onNodeWithText("píngguǒ").assertDoesNotExist()
        compose.onNodeWithText(text(R.string.hsk_course_wrong)).assertIsDisplayed()
    }

    @Test
    fun theNextCardComesForwardAfterTheFrontLeaves() {
        show()
        deck.value = deck.value.after(PictureOutcome.PASS)
        shoot("next")

        compose.onNodeWithContentDescription("mushuk").assertIsDisplayed()
        compose.onNodeWithContentDescription("olma").assertDoesNotExist()
    }

    /**
     * The whole lesson screen around the deck, like the Mini App's header: the
     * "3 / 5" counter sits just before the hearts, the section label is
     * centred under the bar, and the microphone and Skip are at the bottom.
     */
    @Test
    fun theLessonHeaderAndTheBottomControlsMatchTheMiniApp() {
        val lesson = Lesson(
            level = "hsk1", order = 5, sourceLesson = 5, part = 1, partCount = 1,
            isCheckpoint = false, title = "5", subtitle = "5",
            sections = listOf(LessonSection(sectionNo = 2, title = "Mashq", purpose = "practice", cards = listOf(card))),
        )
        compose.setContent {
            PompHskAiTheme {
                LessonScreen(
                    state = LessonUiState(
                        isLoading = false, lesson = lesson, cardIndex = 0,
                        completionAllowed = true, pictureDeck = deck.value,
                    ),
                    pinyin = PinyinVisibility.ALL,
                    onAnswerChoice = { _, _ -> }, onAnswerBuilder = { _, _ -> }, onAnswerPairs = {},
                    onAcknowledge = {}, onAdvance = {}, onPlayAudio = {}, onSpeakPronunciation = {},
                    onSkipPronunciation = {}, onRetryCompletion = {}, onOpenPinyinSettings = {},
                    onOpenWriter = {}, onShowWriterCharacter = {}, onCloseWriter = {}, onExit = {},
                    onSpeakPicture = {}, onSkipPicture = { skips++ }, onContinuePicture = {},
                )
            }
        }
        // The full screen has looping coach animations the Compose capture waits
        // on forever; the display itself can still be grabbed.
        // The entry cinematic plays over the first frames of a lesson.
        compose.waitUntil(timeoutMillis = 15_000) {
            compose.onAllNodesWithText(text(R.string.lesson_entry_title)).fetchSemanticsNodes().isEmpty()
        }
        compose.waitForIdle()
        InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()?.let { bitmap ->
            val dir = InstrumentationRegistry.getInstrumentation().targetContext.filesDir
            FileOutputStream(File(dir, "picture-screen.png")).use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
        }

        val root = compose.onRoot().fetchSemanticsNode().boundsInRoot
        val counter = compose.onNodeWithText("1 / 1").assertIsDisplayed().fetchSemanticsNode().boundsInRoot
        val hearts = compose.onNodeWithText("5").assertIsDisplayed().fetchSemanticsNode().boundsInRoot
        assertTrue("counter must sit before the hearts", counter.right <= hearts.left)
        assertTrue("counter must share the hearts' row", kotlin.math.abs(counter.center.y - hearts.center.y) < 24f)

        val label = compose.onNodeWithText(text(R.string.hsk_course_picture_review_label).uppercase())
            .assertIsDisplayed().fetchSemanticsNode().boundsInRoot
        assertTrue("the label is centred", kotlin.math.abs(label.center.x - root.center.x) < 4f)
        assertTrue("the label is under the bar row", label.top >= hearts.bottom)

        val mic = compose.onNodeWithContentDescription(text(R.string.hsk_course_course_voice_inline_a11y_mic))
            .assertIsDisplayed().fetchSemanticsNode().boundsInRoot
        val skip = compose.onNodeWithText(text(R.string.hsk_course_pronunciation_skip))
            .assertIsDisplayed().fetchSemanticsNode().boundsInRoot
        assertTrue("the microphone is centred", kotlin.math.abs(mic.center.x - root.center.x) < 4f)
        assertTrue("the microphone is round", kotlin.math.abs(mic.width - mic.height) < 2f)
        assertTrue("Skip is under the microphone", skip.top > mic.bottom)
        assertTrue("the controls sit in the lower half", mic.center.y > root.height * 0.55f)
    }
}
