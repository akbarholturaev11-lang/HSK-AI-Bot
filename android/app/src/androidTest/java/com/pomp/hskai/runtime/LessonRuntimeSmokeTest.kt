package com.pomp.hskai.runtime

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.size
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.feature.lesson.LessonCharacter
import com.pomp.hskai.feature.lesson.LessonCharacterMood
import com.pomp.hskai.feature.lesson.LessonCharacterReaction
import com.pomp.hskai.feature.lesson.LessonCharacterStage
import com.pomp.hskai.feature.limit.LimitGate
import com.pomp.hskai.feature.practice.DrillMode
import com.pomp.hskai.feature.practice.DrillQuestion
import com.pomp.hskai.feature.practice.WordDrillScreen
import com.pomp.hskai.feature.practice.WordDrillUiState
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class LessonRuntimeSmokeTest {

    @get:Rule
    val compose = createComposeRule()

    @Test
    fun every_character_and_loading_animation_composes_on_android() {
        compose.setContent {
            PompHskAiTheme {
                Column {
                    LessonCharacter.entries.forEachIndexed { index, character ->
                        LessonCharacterStage(
                            character = character,
                            mood = if (index == 0) LessonCharacterMood.Loading else LessonCharacterMood.Idle,
                            reaction = if (index == 0) LessonCharacterReaction.Pop else null,
                            reactionKey = index,
                            modifier = Modifier.size(76.dp),
                        )
                    }
                }
            }
        }

        compose.mainClock.advanceTimeBy(1_500)
        compose.waitForIdle()
    }

    @Test
    fun pronunciation_drill_from_the_reported_screen_composes_without_crashing() {
        compose.setContent {
            PompHskAiTheme {
                WordDrillScreen(
                    state = WordDrillUiState(
                        isLoading = false,
                        mode = DrillMode.PRONUNCIATION,
                        questions = listOf(
                            DrillQuestion(
                                hanzi = "胖",
                                pinyin = "pàng",
                                meaning = "фарбеҳ",
                                options = listOf("胖", "好", "学", "你"),
                                isReview = false,
                            ),
                        ),
                    ),
                    limit = LimitGate(),
                    onChoose = {},
                    onSpeak = {},
                    onSkipSpoken = {},
                    onAdvance = {},
                    onRetry = {},
                    onClose = {},
                )
            }
        }

        compose.onNodeWithText("胖").assertIsDisplayed()
        compose.onNodeWithText("pàng").assertIsDisplayed()
        compose.mainClock.advanceTimeBy(1_500)
        compose.waitForIdle()
    }

    @Test
    fun recognition_drill_feedback_composes_with_character_reaction() {
        val question = DrillQuestion(
            hanzi = "学",
            pinyin = "xué",
            meaning = "омӯхтан",
            options = listOf("学", "好", "胖", "你"),
            isReview = false,
        )
        compose.setContent {
            PompHskAiTheme {
                WordDrillScreen(
                    state = WordDrillUiState(
                        isLoading = false,
                        mode = DrillMode.RECOGNITION,
                        questions = listOf(question),
                        selected = "学",
                        isAnswered = true,
                        wasCorrect = true,
                        correctCount = 1,
                    ),
                    limit = LimitGate(),
                    onChoose = {},
                    onSpeak = {},
                    onSkipSpoken = {},
                    onAdvance = {},
                    onRetry = {},
                    onClose = {},
                )
            }
        }

        compose.mainClock.advanceTimeBy(1_000)
        compose.waitForIdle()
    }
}
