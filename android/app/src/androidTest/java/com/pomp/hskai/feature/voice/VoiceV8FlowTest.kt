package com.pomp.hskai.feature.voice

import android.Manifest
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.data.api.VoiceStatusResponse
import com.pomp.hskai.data.api.VoiceSuggestionDto
import com.pomp.hskai.data.api.VoiceWordDto
import com.pomp.hskai.feature.limit.LimitGate
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** «Начать разговор» starts the call; a spent allowance leaves; «+» offers what to say. */
@RunWith(AndroidJUnit4::class)
class VoiceV8FlowTest {
    @get:Rule val compose = createComposeRule()
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context = instrumentation.targetContext
    private val status = VoiceStatusResponse(ok = true, remainingVoiceLimit = 3)

    private var starts = 0
    private var exits = 0
    private val sent = mutableListOf<String>()

    private val actions = VoiceV8Actions(
        startFromMicrophone = { starts++ },
        startWithText = {},
        toggleRecording = {},
        sendText = { sent += it },
        endSession = {},
        changeTopic = {},
        selectRole = {},
        cancelRecording = {},
        restart = {},
        exit = { exits++ },
    )

    private fun setV8(state: VoiceUiState) {
        compose.setContent {
            PompHskAiTheme {
                VoiceV8Screen(
                    state = state,
                    topicId = VoiceV8Topic.FREE.id,
                    onTopicSelected = {},
                    prefs = VoiceV8Prefs(),
                    onPrefsChange = {},
                    limit = LimitGate(),
                    actions = actions,
                )
            }
        }
    }

    @Test fun openingTheCallStartsItWithoutAMicTap() {
        instrumentation.uiAutomation.grantRuntimePermission(context.packageName, Manifest.permission.RECORD_AUDIO)
        setV8(VoiceUiState(status = status, isLoading = false, remainingLimit = 3))
        compose.runOnIdle { assertEquals(1, starts) }
    }

    @Test fun aSpentAllowanceNeverStartsAndXLeavesAtOnce() {
        setV8(
            VoiceUiState(
                status = status.copy(remainingVoiceLimit = 0),
                isLoading = false,
                remainingLimit = 0,
            ),
        )
        compose.runOnIdle { assertEquals(0, starts) }
        compose.onNodeWithContentDescription(context.getString(R.string.hsk_course_voice_v8_end_label))
            .performClick()
        compose.onNodeWithText(context.getString(R.string.hsk_course_voice_v8_end_title)).assertDoesNotExist()
        compose.runOnIdle { assertEquals(1, exits) }
    }

    @Test fun plusOffersLessonWordsSuggestionsAndExamples() {
        setV8(
            VoiceUiState(
                status = status,
                isLoading = false,
                remainingLimit = 3,
                sessionId = "open-session",
                lessonWords = listOf(VoiceWordDto(hanzi = "学生", pinyin = "xuésheng", meaning = "talaba")),
                reviewWords = listOf(VoiceWordDto(hanzi = "老师", pinyin = "lǎoshī", meaning = "o'qituvchi")),
                suggestions = listOf(
                    VoiceSuggestionDto(hanzi = "你好，我是学生", pinyin = "nǐ hǎo, wǒ shì xuésheng", translation = "Salom"),
                ),
            ),
        )
        compose.onNodeWithContentDescription(context.getString(R.string.hsk_course_voice_page_hint_title))
            .performClick()
        compose.onNodeWithText("学生").assertIsDisplayed()
        compose.onNodeWithText("老师").assertIsDisplayed()
        compose.onNodeWithText(context.getString(R.string.hsk_course_voice_v8_example1_label)).assertExists()
        compose.onNodeWithText("你好，我是学生").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(listOf("你好，我是学生"), sent) }
    }
}
