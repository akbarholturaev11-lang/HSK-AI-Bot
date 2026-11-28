package com.pomp.hskai.feature.lesson

import android.graphics.Bitmap
import android.content.res.Configuration
import android.view.KeyEvent
import androidx.activity.ComponentActivity
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.onAllNodesWithContentDescription
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.PinyinPicker
import com.pomp.hskai.data.api.AdaptiveItemDto
import com.pomp.hskai.data.api.MistakeReviewQuestionDto
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.settings.PinyinVisibility
import com.pomp.hskai.core.settings.LessonResumePoint
import com.pomp.hskai.domain.model.Lesson
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.ChoiceKind
import com.pomp.hskai.domain.model.LessonSection
import com.pomp.hskai.domain.model.PictureReviewCard
import com.pomp.hskai.domain.model.PictureWord
import java.io.File
import java.io.FileOutputStream
import java.util.Locale
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.After
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
    @get:Rule val compose = createAndroidComposeRule<ComponentActivity>()
    private var originalConfiguration: Configuration? = null

    @After @Suppress("DEPRECATION") fun restoreHostConfiguration() {
        originalConfiguration?.let { original ->
            InstrumentationRegistry.getInstrumentation().runOnMainSync {
                compose.activity.resources.updateConfiguration(original, compose.activity.resources.displayMetrics)
            }
        }
    }

    @Test fun accountReplacementFencesLateResumeWritesAndCompletionClears() = runBlocking {
        val app = InstrumentationRegistry.getInstrumentation().targetContext.applicationContext as HskAiApplication
        check(app.packageName.endsWith(".qa"))
        val settings = app.appSettings
        val old = settings.sessionLessonResumeStore()
        val before = LessonResumePoint(3, "lesson:hsk1:1:section:2:card:1")
        val after = LessonResumePoint(1, "lesson:hsk1:1:section:1:card:2")
        try {
            old.setLessonResumePoint("resume_qa", 1, before)
            settings.clearLessonResumePositions()
            val current = settings.sessionLessonResumeStore()
            assertEquals(LessonResumePoint(0), current.lessonResumePoint("resume_qa", 1))
            current.setLessonResumePoint("resume_qa", 1, after)
            old.setLessonResumePoint("resume_qa", 1, before)
            old.clearLessonResume("resume_qa", 1)
            assertEquals(after, current.lessonResumePoint("resume_qa", 1))
            assertEquals(LessonResumePoint(0), old.lessonResumePoint("resume_qa", 1))
        } finally { settings.clearLessonResumePositions() }
    }

    @Test fun persistedResumeKeepsMaterialAndClearsLegacyReferences() = runBlocking {
        val app = InstrumentationRegistry.getInstrumentation().targetContext.applicationContext as HskAiApplication
        val store = app.appSettings
        val point = LessonResumePoint(3, "lesson:hsk1:1:section:2:card:1")
        try {
            store.setLessonResumePoint("resume_qa", 1, point)
            assertEquals(point, store.lessonResumePoint("resume_qa", 1))
            assertEquals(3, store.lessonResumeIndex("resume_qa", 1))
            store.setLessonResumeIndex("resume_qa", 1, 2)
            assertEquals(LessonResumePoint(2), store.lessonResumePoint("resume_qa", 1))
            store.clearLessonResume("resume_qa", 1)
            assertEquals(LessonResumePoint(0), store.lessonResumePoint("resume_qa", 1))
        } finally {
            store.clearLessonResume("resume_qa", 1)
        }
    }

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

    @Test fun pictureLessonSettingsOwnTheHeaderAndGuardExit() = verifyLessonSettings("uz", picture = true)

    @Test fun ordinaryLessonSettingsOwnTheHeaderAndGuardExit() = verifyLessonSettings("ru")

    @Test fun adaptiveLessonSettingsOwnTheHeaderAndGuardExit() = verifyLessonSettings("tg", adaptive = true)

    @Suppress("DEPRECATION")
    private fun verifyLessonSettings(language: String, picture: Boolean = false, adaptive: Boolean = false) {
        val base = compose.activity
        val choice = ChoiceCard("lesson:hsk1:5:section:2:card:1", ChoiceKind.MEANING,
            "你好", "你好", listOf("salom", "xayr"), 0, "你好")
        val lesson = Lesson(
            level = "hsk1", order = 5, sourceLesson = 5, part = 1, partCount = 1,
            isCheckpoint = false, title = "5", subtitle = "5",
            sections = listOf(LessonSection(2, "Mashq", "practice", listOf(if (picture) card else choice))),
        )
        val state = LessonUiState(isLoading = false, lesson = lesson,
            pictureDeck = if (picture) deck.value else null,
            adaptive = if (adaptive) AdaptiveReviewState(
                1, AdaptiveItemDto(id = "review-1", question = MistakeReviewQuestionDto(
                    id = "question-1", format = "meaning_choice", prompt = "你好", options = listOf("salom", "xayr"))),
            ) else null,
        )
        val configuration = Configuration(base.resources.configuration).apply { setLocale(Locale.forLanguageTag(language)) }
        // Native modal windows read their host's resources. LocalContext alone
        // only localizes the parent composition, not the dialog window.
        originalConfiguration = Configuration(base.resources.configuration)
        InstrumentationRegistry.getInstrumentation().runOnMainSync {
            base.resources.updateConfiguration(configuration, base.resources.displayMetrics)
        }
        val localized = base
        val heading = localized.getString(R.string.hsk_course_lesson_settings_title)
        val pinyinHeading = localized.getString(R.string.hsk_course_pinyin_settings_h)
        val off = localized.getString(R.string.hsk_course_pinyin_settings_off)
        val exit = localized.getString(R.string.hsk_course_lesson_settings_exit)
        val confirm = localized.getString(R.string.lesson_exit_title)
        val open = mutableStateOf(false)
        val selected = mutableStateOf(PinyinVisibility.ALL)
        var exits = 0
        compose.setContent {
            CompositionLocalProvider(LocalConfiguration provides configuration) {
                PompHskAiTheme {
                    LessonScreen(
                        state = state, pinyin = selected.value,
                        onAnswerChoice = { _, _ -> }, onAnswerBuilder = { _, _ -> }, onAnswerPairs = {},
                        onAcknowledge = {}, onAdvance = {}, onPlayAudio = {}, onSpeakPronunciation = {},
                        onSkipPronunciation = {}, onRetryCompletion = {}, onOpenPinyinSettings = { open.value = true },
                        onOpenWriter = {}, onShowWriterCharacter = {}, onCloseWriter = {}, onExit = { exits++ },
                        settingsSheet = { guardedExit ->
                            if (open.value) PinyinPicker(selected.value,
                                onPick = { selected.value = it; open.value = false }, onDismiss = { open.value = false },
                                onExit = { open.value = false; guardedExit() })
                        },
                    )
                }
            }
        }
        compose.waitUntil(timeoutMillis = 15_000) {
            compose.onAllNodesWithText(localized.getString(R.string.lesson_entry_title)).fetchSemanticsNodes().isEmpty()
        }
        compose.onAllNodesWithContentDescription(heading).assertCountEquals(1)
        compose.onAllNodesWithContentDescription(localized.getString(R.string.hsk_common_action_close)).assertCountEquals(0)
        if (picture) compose.onRoot().captureToImage().asAndroidBitmap().let { image ->
            FileOutputStream(File(base.filesDir, "lesson-header-settings.png")).use {
                image.compress(Bitmap.CompressFormat.PNG, 100, it)
            }
        }
        fun openSettings() {
            compose.onNodeWithContentDescription(heading).assertIsDisplayed().performClick()
            // A modal window is measured and animated after the click.
            try {
                compose.waitUntil(timeoutMillis = 10_000) {
                    runCatching {
                        compose.onNodeWithText(pinyinHeading).assertIsDisplayed()
                        compose.onNodeWithText(exit).assertIsDisplayed()
                    }.isSuccess
                }
            } catch (error: Throwable) {
                InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()?.let { image ->
                    FileOutputStream(File(base.filesDir, "lesson-settings-failed-$language.png")).use {
                        image.compress(Bitmap.CompressFormat.PNG, 100, it)
                    }
                }
                throw error
            }
        }
        openSettings()
        assertTrue(compose.onNodeWithText(exit).fetchSemanticsNode().boundsInRoot.top >=
            compose.onNodeWithText(off).fetchSemanticsNode().boundsInRoot.bottom)
        InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()?.let { image ->
            FileOutputStream(File(base.filesDir, "lesson-settings-$language.png")).use {
                image.compress(Bitmap.CompressFormat.PNG, 100, it)
            }
        }
        // The sheet owns a separate focused window. Espresso's root picker
        // waits for the obscured Activity on headless API 35; deliver the real
        // hardware Back to Android's focused window. Instrumentation supplies
        // the keyboard source and FLAG_FROM_SYSTEM required for system Back;
        // raw UiAutomation key events do not normalize those fields.
        InstrumentationRegistry.getInstrumentation().sendKeyDownUpSync(KeyEvent.KEYCODE_BACK)
        compose.waitUntil(timeoutMillis = 5_000) {
            compose.onAllNodesWithText(exit).fetchSemanticsNodes().isEmpty()
        }
        compose.onNodeWithText(exit).assertDoesNotExist()
        compose.onNodeWithContentDescription(heading).assertIsDisplayed()
        compose.onNodeWithText(confirm).assertDoesNotExist()
        compose.runOnIdle { assertEquals(0, exits) }
        openSettings()
        compose.onNodeWithText(off).performClick()
        compose.runOnIdle { assertEquals(PinyinVisibility.OFF, selected.value) }
        openSettings()
        compose.onNodeWithText(exit).performClick()
        compose.onNodeWithText(confirm).assertIsDisplayed()
        compose.runOnIdle { assertEquals(0, exits) }
        compose.onNodeWithText(localized.getString(R.string.hsk_common_action_continue)).performClick()
        openSettings()
        compose.onNodeWithText(exit).performClick()
        compose.onNodeWithText(localized.getString(R.string.hsk_common_action_exit)).performClick()
        compose.runOnIdle { assertEquals(1, exits) }
    }

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
