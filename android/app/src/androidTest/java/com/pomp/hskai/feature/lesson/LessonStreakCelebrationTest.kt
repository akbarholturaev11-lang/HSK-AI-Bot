package com.pomp.hskai.feature.lesson

import android.content.res.Configuration
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.data.api.CourseGamificationDto
import com.pomp.hskai.data.api.CourseLearningReviewDto
import java.util.Locale
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

    private fun rankedOutcome(updated: Boolean = true, duplicate: Boolean = false) =
        outcome(updated = updated, duplicate = duplicate).copy(
            rankBefore = 14,
            rankAfter = 9,
        )

    private fun waitForText(text: String) {
        compose.waitUntil(timeoutMillis = 10_000) {
            runCatching { compose.onNodeWithText(text).assertIsDisplayed() }.isSuccess
        }
    }

    @Test fun verifiedReviewFitsTheExistingResultWithOneActionInAllLocales() {
        val base = InstrumentationRegistry.getInstrumentation().targetContext
        val language = mutableStateOf("uz")
        val result = outcome(updated = false).copy(
            correct = 3,
            learningResult = LessonLearningResult(
                title = "你好",
                subtitle = "Greetings and introductions",
                review = CourseLearningReviewDto("Hello", "你好！"),
            ),
        )
        var exits = 0
        compose.setContent {
            val tag = language.value
            val localized = remember(tag) {
                base.createConfigurationContext(Configuration(base.resources.configuration).apply {
                    setLocale(Locale.forLanguageTag(tag))
                })
            }
            CompositionLocalProvider(
                LocalContext provides localized,
                LocalConfiguration provides localized.resources.configuration,
            ) {
                PompHskAiTheme {
                    Box(Modifier.width(320.dp)) {
                        LessonCompletionCelebration(result, showTodayPlanHint = true, onExit = { exits++ })
                    }
                }
            }
        }

        for ((index, tag) in listOf("uz", "ru", "tg").withIndex()) {
            compose.runOnIdle { language.value = tag }
            val resources = base.createConfigurationContext(Configuration(base.resources.configuration).apply {
                setLocale(Locale.forLanguageTag(tag))
            }).resources
            val expectedAction = resources.getString(R.string.hsk_course_learning_result_continue)
            waitForText(expectedAction)
            waitForText("你好")
            waitForText("Greetings and introductions")
            waitForText("Hello")
            waitForText("你好！")
            waitForText(resources.getString(R.string.hsk_course_learning_result_review_hint))
            compose.onNodeWithText(resources.getString(R.string.hsk_course_learning_result_next_hint))
                .assertDoesNotExist()
            compose.onAllNodes(hasClickAction()).assertCountEquals(1)
            compose.onNodeWithText(expectedAction).performClick()
            assertEquals(index + 1, exits)
        }
    }

    @Test fun topicOnlyShowsTheDailyPlanCueOnlyWhenItIsAvailable() {
        val showPlan = mutableStateOf(false)
        val result = outcome(updated = false).copy(
            learningResult = LessonLearningResult("你好", "Greetings", review = null),
        )
        compose.setContent {
            PompHskAiTheme {
                LessonCompletionCelebration(result, showTodayPlanHint = showPlan.value, onExit = {})
            }
        }

        val hint = strings.getString(R.string.hsk_course_learning_result_next_hint)
        waitForText("你好")
        compose.onNodeWithText(hint).assertDoesNotExist()
        compose.runOnIdle { showPlan.value = true }
        waitForText(hint)
        compose.onNodeWithText(strings.getString(R.string.hsk_course_learning_result_review)).assertDoesNotExist()
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
    @Test fun confirmedRankUpFollowsStreakBeforeReturningToCourse() {
        var exits = 0
        compose.setContent {
            PompHskAiTheme { LessonCompletionCelebration(rankedOutcome(), onExit = { exits++ }) }
        }
        val next = strings.getString(R.string.lesson_next)
        val days = strings.getString(R.string.lesson_streak_days)
        val rankTitle = strings.getString(R.string.lesson_rank_title)
        val back = strings.getString(R.string.lesson_back_to_course)
        waitForText(next)
        compose.onNodeWithText(next).performClick()
        waitForText(days)
        compose.onNodeWithText(next).performClick()
        waitForText(rankTitle)
        compose.onNodeWithText("#14 → #9").assertIsDisplayed()
        assertEquals(0, exits)
        waitForText(back)
        compose.onNodeWithText(back).performClick()
        assertEquals(1, exits)
    }

    @Test fun confirmedRankUpWithoutStreakStillAppears() {
        var exits = 0
        compose.setContent {
            PompHskAiTheme {
                LessonCompletionCelebration(rankedOutcome(updated = false), onExit = { exits++ })
            }
        }
        val next = strings.getString(R.string.lesson_next)
        val rankTitle = strings.getString(R.string.lesson_rank_title)
        val back = strings.getString(R.string.lesson_back_to_course)
        waitForText(next)
        compose.onNodeWithText(next).performClick()
        waitForText(rankTitle)
        compose.onNodeWithText("#14 → #9").assertIsDisplayed()
        compose.onNodeWithText(back).performClick()
        assertEquals(1, exits)
    }

    @Test fun duplicateCompletionDoesNotReplayRankUp() {
        var exits = 0
        compose.setContent {
            PompHskAiTheme {
                LessonCompletionCelebration(
                    rankedOutcome(updated = false, duplicate = true),
                    onExit = { exits++ },
                )
            }
        }
        val back = strings.getString(R.string.lesson_back_to_course)
        val rankTitle = strings.getString(R.string.lesson_rank_title)
        waitForText(back)
        compose.onNodeWithText(rankTitle).assertDoesNotExist()
        compose.onNodeWithText(back).performClick()
        assertEquals(1, exits)
    }


}
