package com.pomp.hskai.feature.voice

import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.espresso.Espresso.pressBack
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.data.api.VoiceStatusResponse
import com.pomp.hskai.feature.limit.LimitGate
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** System Back must use the same exit action as the call's Close button. */
@RunWith(AndroidJUnit4::class)
class VoiceScreenBackTest {
    @get:Rule val compose = createComposeRule()

    private fun backExits(initial: VoiceUiState) {
        val state = mutableStateOf(initial)
        var ends = 0
        compose.setContent {
            PompHskAiTheme {
                VoiceScreen(
                    state = state.value,
                    level = "hsk1",
                    language = "uz",
                    limit = LimitGate(),
                    subtitlesOn = true,
                    slowSpeech = false,
                    onToggleSubtitles = {},
                    onToggleSlowSpeech = {},
                    onSelectRole = {},
                    onStartSession = { _, _, _ -> },
                    onToggleRecording = {},
                    onSendText = {},
                    onEndSession = {
                        ends++
                        state.value = VoiceUiState(status = initial.status, isLoading = false)
                    },
                    onSwapPartner = {},
                    onReset = {},
                )
            }
        }
        compose.waitForIdle()
        pressBack()
        compose.runOnIdle { assertEquals(1, ends) }
    }

    @Test fun backCancelsAPendingStartBeforeASessionExists() = backExits(VoiceUiState(
        status = VoiceStatusResponse(ok = true, remainingVoiceLimit = 3),
        isLoading = false,
        isStarting = true,
    ))

    @Test fun backExitsAnActiveCallWhileTheTurnIsSending() = backExits(VoiceUiState(
        status = VoiceStatusResponse(ok = true, remainingVoiceLimit = 3),
        isLoading = false,
        sessionId = "sending-session",
        isSending = true,
        lines = listOf(VoiceLine(VoiceSpeaker.AI, "Salom", hanzi = "你好", pinyin = "nǐ hǎo")),
    ))

    @Test fun replacingVoiceWithAnotherScreenCancelsAnActiveOrPendingCallOnly() {
        val visible = mutableStateOf(true)
        val state = mutableStateOf(VoiceUiState(
            status = VoiceStatusResponse(ok = true, remainingVoiceLimit = 3), isLoading = false,
        ))
        var ends = 0
        compose.setContent {
            PompHskAiTheme {
                if (visible.value) VoiceScreen(
                    state = state.value,
                    level = "hsk1",
                    language = "uz",
                    limit = LimitGate(),
                    subtitlesOn = true,
                    slowSpeech = false,
                    onToggleSubtitles = {},
                    onToggleSlowSpeech = {},
                    onSelectRole = {},
                    onStartSession = { _, _, _ -> },
                    onToggleRecording = {},
                    onSendText = {},
                    onEndSession = { ends++ },
                    onSwapPartner = {},
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
