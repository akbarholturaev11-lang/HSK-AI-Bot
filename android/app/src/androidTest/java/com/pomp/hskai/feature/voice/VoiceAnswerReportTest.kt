package com.pomp.hskai.feature.voice

import android.graphics.Bitmap
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsOff
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.isDialog
import androidx.compose.ui.test.isToggleable
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.text.AnnotatedString
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.feature.limit.LimitGate
import java.io.File
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Both voice engines use the same selected-answer reporting UI. No live API call. */
@RunWith(AndroidJUnit4::class)
class VoiceAnswerReportTest {
    @get:Rule val compose = createComposeRule()
    private val context = InstrumentationRegistry.getInstrumentation().targetContext

    private fun reportAnswer(live: Boolean, line: VoiceLine) {
        val selectedSession = if (live) "live-report-session" else "turn-report-session"
        val active = mutableStateOf(VoiceUiState(
            isLoading = false, isLive = live, sessionId = selectedSession,
            lines = listOf(line),
        ))
        compose.setContent {
            PompHskAiTheme {
                VoiceScreen(
                    state = active.value, level = "hsk1", language = "uz", limit = LimitGate(),
                    subtitlesOn = true, slowSpeech = false, onToggleSubtitles = {},
                    onToggleSlowSpeech = {}, onSelectRole = {}, onStartSession = { _, _, _ -> },
                    onToggleRecording = {}, onSendText = {}, onEndSession = {}, onSwapPartner = {},
                    onReset = {},
                )
            }
        }
        compose.onNodeWithContentDescription(context.getString(R.string.assistant_more_actions))
            .assertIsDisplayed().performClick()
        compose.onNodeWithText(context.getString(R.string.assistant_report_answer)).performClick()
        compose.onNode(isDialog()).assertIsDisplayed()
        compose.onNode(isToggleable()).assertIsOff()
        val excerpt = listOf(line.hanzi, line.pinyin, line.text, line.translation, line.correction.orEmpty())
            .filter { it.isNotBlank() }.distinct().joinToString("\n").take(350)
        val expected = context.getString(R.string.assistant_report_prefill, selectedSession, excerpt)
        compose.onNode(hasSetTextAction()).assert(
            SemanticsMatcher.expectValue(SemanticsProperties.EditableText, AnnotatedString(expected)),
        )

        // A live update or replacement session cannot change a report already opened.
        compose.runOnIdle {
            active.value = active.value.copy(
                sessionId = "replacement-session",
                lines = listOf(VoiceLine(VoiceSpeaker.AI, "Different later answer")),
            )
        }
        compose.onNode(hasSetTextAction()).assert(
            SemanticsMatcher.expectValue(SemanticsProperties.EditableText, AnnotatedString(expected)),
        )
        val image = compose.onNode(isDialog()).captureToImage().asAndroidBitmap()
        File(context.getExternalFilesDir(null), "voice-report-${if (live) "live" else "turn"}.png")
            .outputStream().use { image.compress(Bitmap.CompressFormat.PNG, 100, it) }
        compose.onNodeWithText(context.getString(R.string.hsk_common_action_close)).performClick()
        compose.onNode(isDialog()).assertDoesNotExist()
    }

    @Test fun turnVoiceReportsTheSelectedAnswerWithoutAnAutomaticScreenshot() = reportAnswer(
        live = false,
        line = VoiceLine(VoiceSpeaker.AI, "Salom", hanzi = "你好", pinyin = "nǐ hǎo", translation = "Salom"),
    )

    @Test fun liveVoiceReportsHanziEvenWhenOtherAnswerFieldsAreBlank() = reportAnswer(
        live = true,
        line = VoiceLine(VoiceSpeaker.AI, "", hanzi = "你好"),
    )

    @Test fun userMessagesDoNotOfferAnAiContentReportAction() {
        compose.setContent {
            PompHskAiTheme {
                VoiceBubble(VoiceLine(VoiceSpeaker.USER, "你好"), onReport = { error("User content") })
            }
        }
        compose.onNodeWithContentDescription(context.getString(R.string.assistant_more_actions))
            .assertDoesNotExist()
    }
}
