package com.pomp.hskai.feature.voice

import android.graphics.Bitmap
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.semantics.SemanticsActions
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsOff
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.hasAnyDescendant
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.isDialog
import androidx.compose.ui.test.isToggleable
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performSemanticsAction
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

/**
 * Both voice engines keep the Play AI-content report on V8's AI messages:
 * a long press opens it, user messages have none. No live API call.
 */
@RunWith(AndroidJUnit4::class)
class VoiceAnswerReportTest {
    @get:Rule val compose = createComposeRule()
    private val context = InstrumentationRegistry.getInstrumentation().targetContext

    private val actions = VoiceV8Actions(
        startFromMicrophone = {}, startWithText = {}, toggleRecording = {}, sendText = {},
        endSession = {}, changeTopic = {}, selectRole = {}, cancelRecording = {}, restart = {}, exit = {},
    )

    private fun show(state: () -> VoiceUiState) {
        compose.setContent {
            PompHskAiTheme {
                VoiceV8Screen(
                    state = state(),
                    topicId = VoiceV8Topic.FREE.id,
                    onTopicSelected = {},
                    prefs = VoiceV8Prefs(),
                    onPrefsChange = {},
                    limit = LimitGate(),
                    actions = actions,
                )
            }
        }
        // The transcript is the chat mode's: a tap on the orb opens it.
        compose.onNodeWithContentDescription(context.getString(R.string.hsk_course_voice_v8_orb_label))
            .performSemanticsAction(SemanticsActions.OnClick)
    }

    private fun reportAnswer(live: Boolean, line: VoiceLine) {
        val selectedSession = if (live) "live-report-session" else "turn-report-session"
        val active = mutableStateOf(VoiceUiState(
            isLoading = false, isLive = live, isLiveConnected = live, sessionId = selectedSession,
            lines = listOf(line),
        ))
        show { active.value }
        compose.onNode(
            SemanticsMatcher.keyIsDefined(SemanticsActions.OnLongClick) and hasAnyDescendant(hasText(line.hanzi)),
        ).performSemanticsAction(SemanticsActions.OnLongClick)
        compose.onNodeWithText(context.getString(R.string.assistant_report_answer)).performClick()
        compose.onNode(isDialog()).assertIsDisplayed()
        // The screenshot switch starts off; the V8 mic is toggleable too, so
        // only the dialog's own switch is checked.
        compose.onNode(isToggleable() and hasAnyAncestor(isDialog())).assertIsOff()
        val excerpt = listOf(line.hanzi, line.pinyin, line.text, line.translation, line.correction.orEmpty())
            .filter { it.isNotBlank() }.distinct().joinToString("\n").take(350)
        val expected = context.getString(R.string.assistant_report_prefill, selectedSession, excerpt)
        compose.onNode(hasSetTextAction() and hasAnyAncestor(isDialog())).assert(
            SemanticsMatcher.expectValue(SemanticsProperties.EditableText, AnnotatedString(expected)),
        )

        // A live update or replacement session cannot change a report already opened.
        compose.runOnIdle {
            active.value = active.value.copy(
                sessionId = "replacement-session",
                lines = listOf(VoiceLine(VoiceSpeaker.AI, "Different later answer")),
            )
        }
        compose.onNode(hasSetTextAction() and hasAnyAncestor(isDialog())).assert(
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
        show {
            VoiceUiState(
                isLoading = false, sessionId = "user-only-session",
                lines = listOf(VoiceLine(VoiceSpeaker.USER, "你好")),
            )
        }
        compose.onNodeWithText("你好").assertIsDisplayed()
        // The prompt field's own long press (paste) is not a report action.
        compose.onAllNodes(SemanticsMatcher.keyIsDefined(SemanticsActions.OnLongClick) and !hasSetTextAction())
            .assertCountEquals(0)
    }
}
