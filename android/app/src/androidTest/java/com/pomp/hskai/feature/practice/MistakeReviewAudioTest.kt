package com.pomp.hskai.feature.practice

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.data.api.MistakeReviewQuestionDto
import com.pomp.hskai.data.api.MistakeReviewSessionDto
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * The listening speaker used to drive the phone's own `TextToSpeech`, which is
 * silent on a phone with no Chinese voice installed — most of them here. It now
 * asks the caller, which reaches the same server voice the lesson uses. Nothing
 * about that is visible to the compiler, so the wiring is asserted here.
 */
@RunWith(AndroidJUnit4::class)
class MistakeReviewAudioTest {

    @get:Rule
    val compose = createComposeRule()

    private val listen = "Talaffuzni eshitish"

    private val question = MistakeReviewQuestionDto(
        id = "q1",
        category = "word",
        prompt = "Nima eshitdingiz?",
        options = listOf("你好", "谢谢"),
        audioText = "你好",
        pinyin = "nǐ hǎo",
    )

    private fun openReview(
        isAudioLoading: Boolean = false,
        audioError: ApiError? = null,
        onSpeak: (String) -> Unit = {},
    ) {
        compose.setContent {
            PompHskAiTheme {
                MistakesReviewRun(
                    state = PracticeUiState(
                        reviewSession = MistakeReviewSessionDto(id = "s1", questions = listOf(question)),
                        isReviewAudioLoading = isAudioLoading,
                        reviewAudioError = audioError,
                    ),
                    onSelect = {},
                    onAdvance = {},
                    onCancel = {},
                    onSpeak = onSpeak,
                )
            }
        }
    }

    @Test
    fun the_speaker_asks_the_server_for_the_questions_audio() {
        val spoken = mutableListOf<String>()
        openReview(isAudioLoading = false) { spoken += it }

        compose.onNodeWithContentDescription(listen).assertIsDisplayed().performClick()

        assertEquals(listOf("你好"), spoken)
    }

    @Test
    fun the_speaker_is_busy_while_the_audio_is_still_loading() {
        val spoken = mutableListOf<String>()
        openReview(isAudioLoading = true) { spoken += it }

        // The icon gives way to the spinner, so there is no speaker to tap and
        // an impatient learner cannot queue a second download.
        val speakers = compose.onAllNodes(hasContentDescription(listen)).fetchSemanticsNodes()
        assertEquals(0, speakers.size)
        assertEquals(emptyList<String>(), spoken)
    }

    @Test
    fun a_failed_download_says_so_instead_of_playing_nothing() {
        openReview(audioError = ApiError.Offline)

        compose.onNodeWithText("Internet aloqasi yo'q. Ulanishni tekshiring.").assertIsDisplayed()
    }
}
