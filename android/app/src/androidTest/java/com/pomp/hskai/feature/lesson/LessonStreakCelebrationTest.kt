package com.pomp.hskai.feature.lesson

import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.data.api.CourseGamificationDto
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class LessonStreakCelebrationTest {
    @get:Rule val compose = createComposeRule()
    private val strings = InstrumentationRegistry.getInstrumentation().targetContext.resources

    private fun outcome(updated: Boolean = true, duplicate: Boolean = false, snapshotDuplicate: Boolean = false) =
        LessonOutcome.Completed(
            correct = 4, graded = 4, duplicate = duplicate,
            gamification = CourseGamificationDto(
                awardedXp = 20, streak = 6, previousStreak = 5,
                streakUpdated = updated, duplicate = snapshotDuplicate,
                localDate = "2026-10-08", weekStart = "2026-10-05",
                weekActivityDates = listOf("2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08"),
            ),
        )

    private fun waitForText(text: String) {
        compose.waitUntil(timeoutMillis = 10_000) {
            runCatching { compose.onNodeWithText(text).assertIsDisplayed() }.isSuccess
        }
    }

    @Test fun freshCheckpointStreakFollowsTheResultBeforeReturningToCourse() {
        var exits = 0
        compose.setContent {
            PompHskAiTheme { LessonCompletionCelebration(outcome(), isCheckpoint = true, onExit = { exits++ }) }
        }
        val next = strings.getString(R.string.lesson_next)
        val days = strings.getString(R.string.lesson_streak_days)
        val back = strings.getString(R.string.lesson_back_to_course)
        waitForText(next)
        compose.onNodeWithText(days).assertDoesNotExist()
        compose.onNodeWithText(next).performClick()
        waitForText(days)
        compose.onNodeWithText("6").assertIsDisplayed()
        assertEquals(0, exits)
        waitForText(back)
        compose.onNodeWithText(back).performClick()
        assertEquals(1, exits)
    }

    @Test fun sameDayAndDuplicateCompletionsDoNotReplayTheStreak() {
        val cases = listOf(outcome(updated = false), outcome(duplicate = true), outcome(snapshotDuplicate = true))
        val active = mutableStateOf(cases.first())
        var exits = 0
        compose.setContent {
            PompHskAiTheme { LessonCompletionCelebration(active.value, onExit = { exits++ }) }
        }
        val back = strings.getString(R.string.lesson_back_to_course)
        val days = strings.getString(R.string.lesson_streak_days)
        cases.forEachIndexed { index, value ->
            compose.runOnIdle { active.value = value }
            waitForText(back)
            compose.onNodeWithText(days).assertDoesNotExist()
            compose.onNodeWithText(back).performClick()
            assertEquals(index + 1, exits)
        }
    }
}
