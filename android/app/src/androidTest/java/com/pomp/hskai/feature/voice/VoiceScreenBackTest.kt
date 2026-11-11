package com.pomp.hskai.feature.voice

import androidx.activity.OnBackPressedDispatcherOwner
import androidx.activity.compose.LocalOnBackPressedDispatcherOwner
import androidx.compose.runtime.mutableStateOf
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
import com.pomp.hskai.feature.limit.LimitGate
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** System Back leaves AI Voice the same way the V8 screen's own controls do. */
@RunWith(AndroidJUnit4::class)
class VoiceScreenBackTest {
    @get:Rule val compose = createComposeRule()
    private val context = InstrumentationRegistry.getInstrumentation().targetContext
    private val status = VoiceStatusResponse(ok = true, remainingVoiceLimit = 3)

    private fun actions(onExit: () -> Unit = {}, onEnd: () -> Unit = {}, onRestart: () -> Unit = {}) = VoiceV8Actions(
        startFromMicrophone = {},
        startWithText = {},
        toggleRecording = {},
        sendText = {},
        endSession = onEnd,
        changeTopic = {},
        selectRole = {},
        cancelRecording = {},
        restart = onRestart,
        exit = onExit,
    )

    private var backOwner: OnBackPressedDispatcherOwner? = null

    private fun pressBack() {
        // Exercise the actual Compose BackHandler dispatcher, not Espresso's
        // focus-sensitive root picker (which fails on headless CI emulators).
        compose.runOnIdle { checkNotNull(backOwner).onBackPressedDispatcher.onBackPressed() }
    }

    private fun setV8(state: VoiceUiState, actions: VoiceV8Actions) {
        compose.setContent {
            backOwner = LocalOnBackPressedDispatcherOwner.current
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

    @Test fun backCancelsAPendingStartBeforeASessionExists() {
        val state = mutableStateOf(VoiceUiState(status = status, isLoading = false, isStarting = true))
        var ends = 0
        compose.setContent {
            backOwner = LocalOnBackPressedDispatcherOwner.current
            PompHskAiTheme {
                VoiceScreen(
                    state = state.value,
                    level = "hsk1",
                    language = "uz",
                    limit = LimitGate(),
                    onSelectRole = {},
                    onOpenVoice = {},
                    onEndSession = {
                        ends++
                        state.value = VoiceUiState(status = status, isLoading = false)
                    },
                    onReset = {},
                )
            }
        }
        pressBack()
        compose.runOnIdle { assertEquals(1, ends) }
    }

    @Test fun backLeavesTheConversationWhileATurnIsSending() {
        var exits = 0
        setV8(
            VoiceUiState(
                status = status,
                isLoading = false,
                sessionId = "sending-session",
                isSending = true,
                lines = listOf(VoiceLine(VoiceSpeaker.AI, "Salom", hanzi = "你好", pinyin = "nǐ hǎo")),
            ),
            actions(onExit = { exits++ }),
        )
        pressBack()
        compose.runOnIdle { assertEquals(1, exits) }
    }

    @Test fun backClosesTheEndDialogBeforeLeaving() {
        var exits = 0
        var ends = 0
        setV8(
            VoiceUiState(status = status, isLoading = false, sessionId = "open-session"),
            actions(onExit = { exits++ }, onEnd = { ends++ }),
        )
        compose.onNodeWithContentDescription(context.getString(R.string.hsk_course_voice_v8_end_label))
            .performClick()
        compose.onNodeWithText(context.getString(R.string.hsk_course_voice_v8_end_title)).assertIsDisplayed()
        pressBack()
        compose.onNodeWithText(context.getString(R.string.hsk_course_voice_v8_end_title)).assertDoesNotExist()
        compose.runOnIdle {
            assertEquals(0, exits)
            assertEquals(0, ends)
        }
        pressBack()
        compose.runOnIdle { assertEquals(1, exits) }
    }

    @Test fun endingKeepsTheConversationAndOffersRestartOrExit() {
        var exits = 0
        var ends = 0
        var restarts = 0
        setV8(
            VoiceUiState(
                status = status,
                isLoading = false,
                sessionId = "open-session",
                lines = listOf(
                    VoiceLine(VoiceSpeaker.USER, "我是学生"),
                    VoiceLine(VoiceSpeaker.AI, "Zo'r", hanzi = "很好", translation = "Zo'r"),
                ),
            ),
            actions(onExit = { exits++ }, onEnd = { ends++ }, onRestart = { restarts++ }),
        )
        compose.onNodeWithContentDescription(context.getString(R.string.hsk_course_voice_v8_end_label))
            .performClick()
        compose.onNodeWithText(context.getString(R.string.hsk_course_voice_v8_end_confirm)).performClick()
        compose.runOnIdle { assertEquals(1, ends) }
        compose.onNodeWithText("我是学生").assertIsDisplayed()
        compose.onNodeWithText("很好").assertIsDisplayed()
        compose.onNodeWithText(context.getString(R.string.hsk_course_voice_v8_status_end)).assertIsDisplayed()
        compose.onNodeWithText(context.getString(R.string.hsk_course_voice_v8_restart)).assertIsDisplayed()
        compose.onNodeWithText(context.getString(R.string.hsk_course_voice_page_exit)).assertIsDisplayed()
            .performClick()
        compose.runOnIdle {
            assertEquals(1, exits)
            assertEquals(0, restarts)
            assertEquals(1, ends)
        }
    }

    @Test fun replacingVoiceWithAnotherScreenCancelsAnActiveOrPendingCallOnly() {
        val visible = mutableStateOf(true)
        val state = mutableStateOf(VoiceUiState(status = status, isLoading = false))
        var ends = 0
        compose.setContent {
            PompHskAiTheme {
                if (visible.value) VoiceScreen(
                    state = state.value,
                    level = "hsk1",
                    language = "uz",
                    limit = LimitGate(),
                    onSelectRole = {},
                    onOpenVoice = {},
                    onEndSession = { ends++ },
                    onReset = {},
                )
            }
        }
        compose.runOnIdle { visible.value = false }
        compose.runOnIdle { assertEquals(0, ends) }
        compose.runOnIdle {
            state.value = state.value.copy(isStarting = true)
            visible.value = true
        }
        compose.runOnIdle { visible.value = false }
        compose.runOnIdle { assertEquals(1, ends) }
        compose.runOnIdle {
            state.value = state.value.copy(isStarting = false, sessionId = "active-session")
            visible.value = true
        }
        compose.runOnIdle { visible.value = false }
        compose.runOnIdle { assertEquals(2, ends) }
    }
}
