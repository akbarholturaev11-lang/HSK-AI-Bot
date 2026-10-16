package com.pomp.hskai.feature.practice

import android.graphics.Bitmap
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.navigation.MainScaffold
import com.pomp.hskai.core.navigation.MainTab
import com.pomp.hskai.data.api.MistakeReviewQuestionDto
import com.pomp.hskai.data.api.MistakeReviewSessionDto
import com.pomp.hskai.data.api.PracticeCompleteResponse
import com.pomp.hskai.feature.assistant.AssistantBinding
import com.pomp.hskai.feature.assistant.LocalAssistant
import com.pomp.hskai.feature.assistant.ScreenRegistry
import com.pomp.hskai.feature.limit.LimitGate
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Render the attempt inside the floating tab scaffold, where the overlap occurred. */
@RunWith(AndroidJUnit4::class)
class PracticeImmersiveLayoutTest {
    @get:Rule val compose = createComposeRule()
    private val context = InstrumentationRegistry.getInstrumentation().targetContext
    private val registry = ScreenRegistry()

    private fun capture(name: String) {
        compose.mainClock.advanceTimeBy(500)
        compose.waitForIdle()
        val image = compose.onRoot().captureToImage().asAndroidBitmap()
        File(context.getExternalFilesDir(null), "ui-fix-$name.png").outputStream().use {
            image.compress(Bitmap.CompressFormat.PNG, 100, it)
        }
    }

    private fun render(initial: PracticeUiState) {
        val active = mutableStateOf(initial)
        val binding = AssistantBinding(
            registry, (context.applicationContext as HskAiApplication).assistant, {}, { _, _ -> },
        )
        compose.setContent {
            CompositionLocalProvider(LocalAssistant provides binding) {
                PompHskAiTheme {
                    MainScaffold(
                        selectedTab = MainTab.PRACTICE,
                        onTabSelected = {},
                        bottomBarVisible = !active.value.isImmersive,
                    ) { _, modifier ->
                        PracticeScreen(
                            state = active.value, level = "hsk1", language = "ru", limit = LimitGate(),
                            onOpenDictionary = {}, onStartPractice = { _, _, _ -> },
                            onSelectPracticeOption = {}, onAdvancePractice = {},
                            onResetPractice = { active.value = PracticeUiState() },
                            onStartMistakeReview = {}, onAnswerReview = {}, onAdvanceReview = {},
                            onResetReview = { active.value = PracticeUiState() }, onSpeakReview = {},
                            onStartExam = {}, onOpenDrill = {}, onSelectExamOption = {},
                            onAdvanceExam = {}, onResetExam = { active.value = PracticeUiState() },
                            modifier = modifier,
                        )
                    }
                }
            }
        }
    }

    private fun assertImmersive() {
        compose.onNodeWithText(context.getString(R.string.nav_profile)).assertDoesNotExist()
        compose.runOnIdle { assertFalse(registry.current!!.showsButton) }
    }

    @Test fun mistakeReviewKeepsTheQuestionAndCheckButtonClearOfNavigation() {
        render(PracticeUiState(reviewSession = MistakeReviewSessionDto(
            id = "fixture-review",
            questions = listOf(MistakeReviewQuestionDto(
                id = "q1", category = "word", prompt = "Выберите значение",
                sentence = "你", pinyin = "nǐ", options = listOf("ты", "он"),
            )),
        )))
        compose.onNodeWithText("你").assertIsDisplayed()
        assertImmersive()
        capture("review")
    }

    @Test fun streakContinuationIsReachableAndRestoresNavigationWhenFinished() {
        render(PracticeUiState(result = PracticeCompleteResponse(
            ok = true, score = 9, total = 10, percent = 90,
            reward = buildJsonObject {
                put("awarded_xp", 15); put("streak", 2); put("streak_updated", true)
            },
        )))
        val next = context.getString(R.string.lesson_next)
        compose.onNodeWithText(next).performScrollTo().assertIsDisplayed().performClick()
        compose.waitUntil(timeoutMillis = 15_000) {
            runCatching {
                compose.onNodeWithText(context.getString(R.string.lesson_streak_days)).assertIsDisplayed()
            }.isSuccess
        }
        assertImmersive()
        capture("streak")
        compose.onNodeWithText(next).assertIsDisplayed().performClick()
        compose.onNodeWithText(context.getString(R.string.nav_profile)).assertIsDisplayed()
        compose.runOnIdle { assertTrue(registry.current!!.showsButton) }
        capture("return-home")
    }
}
