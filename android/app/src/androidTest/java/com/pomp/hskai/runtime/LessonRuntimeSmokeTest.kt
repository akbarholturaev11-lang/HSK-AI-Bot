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
import com.pomp.hskai.core.settings.PinyinVisibility
import com.pomp.hskai.domain.model.Lesson
import com.pomp.hskai.domain.model.LessonSection
import com.pomp.hskai.domain.model.PronunciationCard
import com.pomp.hskai.feature.lesson.LessonCharacter
import com.pomp.hskai.feature.lesson.LessonCharacterMood
import com.pomp.hskai.feature.lesson.LessonCharacterReaction
import com.pomp.hskai.feature.lesson.LessonCharacterStage
import com.pomp.hskai.feature.lesson.LessonScreen
import com.pomp.hskai.feature.lesson.LessonUiState
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
        compose.mainClock.autoAdvance = false
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
    fun real_lesson_screen_with_pronunciation_card_enters_and_survives_entry_animation() {
        compose.mainClock.autoAdvance = false
        val pronunciation = PronunciationCard(
            materialRef = "lesson:hsk1:1:section:1:card:1",
            phrase = "胖",
            pinyin = "pàng",
            translation = "фарбеҳ",
        )
        val lesson = Lesson(
            level = "hsk1",
            order = 1,
            sourceLesson = 1,
            part = 1,
            partCount = 1,
            isCheckpoint = false,
            title = "Lesson 1",
            subtitle = "",
            sections = listOf(
                LessonSection(
                    sectionNo = 1,
                    title = "Pronunciation",
                    purpose = "practice",
                    cards = listOf(pronunciation),
                ),
            ),
        )

        compose.setContent {
            PompHskAiTheme {
                LessonScreen(
                    state = LessonUiState(
                        isLoading = false,
                        lesson = lesson,
                        completionAllowed = true,
                    ),
                    pinyin = PinyinVisibility.ALL,
                    onAnswerChoice = { _, _ -> },
                    onAnswerBuilder = { _, _ -> },
                    onAnswerPairs = { _, _ -> },
                    onAcknowledge = {},
                    onAdvance = {},
                    onPlayAudio = {},
                    onRetryCompletion = {},
                    onOpenPinyinSettings = {},
                    onOpenWriter = {},
                    onShowWriterCharacter = {},
                    onCloseWriter = {},
                    onExit = {},
                )
            }
        }

        compose.mainClock.advanceTimeBy(1_500)
        compose.onNodeWithText("胖").assertIsDisplayed()
        compose.onNodeWithText("pàng").assertIsDisplayed()
        compose.waitForIdle()
    }

    @Test
    fun pronunciation_drill_from_the_reported_screen_composes_without_crashing() {
        compose.mainClock.autoAdvance = false
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
        compose.mainClock.autoAdvance = false
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
