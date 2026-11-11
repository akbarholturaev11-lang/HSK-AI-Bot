package com.pomp.hskai.feature.voice

import com.pomp.hskai.R
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.data.api.VoiceStatusResponse
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** The line under the V8 orb follows the PWA's `setState()` states. */
class VoiceV8StatusTest {
    private val free = VoiceStatusResponse(ok = true, remainingVoiceLimit = 3, liveAvailable = true)
    private val idle = VoiceUiState(status = free, isLoading = false, remainingLimit = 3)
    private val live = idle.copy(sessionId = "s", isLive = true, isLiveConnected = true)
    private val turn = idle.copy(sessionId = "s")

    private fun of(state: VoiceUiState, micDenied: Boolean = false, ended: Boolean = false) =
        voiceV8Status(state, micDenied, ended).status

    @Test fun beforeASessionTheOrbIsReadyOrConnecting() {
        assertEquals(VoiceV8Status.READY, of(idle))
        assertEquals(VoiceV8Status.CONNECT, of(idle.copy(isStarting = true)))
        assertEquals(VoiceV8Status.CONNECT, of(VoiceUiState(isLoading = true)))
    }

    @Test fun anExhaustedFreeAllowanceSaysSoButNotForPro() {
        val spent = idle.copy(status = free.copy(remainingVoiceLimit = 0), remainingLimit = 0)
        val line = voiceV8Status(spent, micDenied = false, ended = false)
        assertEquals(VoiceV8Status.FAIL, line.status)
        assertEquals(R.string.hsk_course_voice_v8_no_quota, line.messageRes)
        val pro = spent.copy(status = spent.status!!.copy(isPaid = true))
        assertEquals(VoiceV8Status.READY, of(pro))
    }

    @Test fun liveStatesFollowTheSocket() {
        assertEquals(VoiceV8Status.LISTENING, of(live))
        assertEquals(VoiceV8Status.SPEAKING, of(live.copy(isAiSpeaking = true)))
        assertEquals(VoiceV8Status.THINKING, of(live.copy(isSending = true)))
        assertEquals(VoiceV8Status.READY, of(live.copy(isLiveMuted = true)))
        assertEquals(VoiceV8Status.CONNECT, of(live.copy(isLiveConnected = false, isLiveConnecting = true)))
        assertEquals(
            VoiceV8Status.RECONNECT,
            of(live.copy(isLiveConnected = false, isLiveConnecting = true, isLiveReconnecting = true)),
        )
    }

    @Test fun turnStatesFollowTheRecorderAndThePlayer() {
        assertEquals(VoiceV8Status.READY, of(turn))
        assertEquals(VoiceV8Status.RECORDING, of(turn.copy(isRecording = true)))
        assertEquals(VoiceV8Status.THINKING, of(turn.copy(isSending = true)))
        assertEquals(VoiceV8Status.SPEAKING, of(turn.copy(turnCount = 1, isReplyPlaying = true)))
        assertEquals(VoiceV8Status.TURN, of(turn.copy(turnCount = 1)))
        assertEquals(VoiceV8Status.TURN, of(turn.copy(usedTurnFallback = true)))
    }

    @Test fun errorsMicAndEndTakePrecedence() {
        assertEquals(VoiceV8Status.END, of(live, micDenied = true, ended = true))
        assertEquals(VoiceV8Status.MIC, of(live, micDenied = true))
        assertEquals(VoiceV8Status.OFFLINE, of(live.copy(error = ApiError.Offline)))
        assertEquals(VoiceV8Status.SLOW, of(live.copy(error = ApiError.Timeout)))
        assertEquals(VoiceV8Status.LOGIN, of(live.copy(error = ApiError.SessionExpired)))
        assertEquals(VoiceV8Status.FAIL, of(live.copy(error = ApiError.Unknown)))
        assertEquals(VoiceV8Status.FAIL, of(idle.copy(error = ApiError.LimitReached(resetAt = null, messageRes = 0))))
        // A too-short recording is a toast, not a failure: the turn goes on.
        val short = turn.copy(turnCount = 1, error = ApiError.Server("TRANSCRIPTION_EMPTY", 0))
        assertEquals(VoiceV8Status.TURN, of(short))
        assertTrue(VoiceV8Status.OFFLINE.urgent)
        assertTrue(!VoiceV8Status.LISTENING.urgent)
    }

    @Test fun messagesPutTheCorrectionUnderTheLearnersLineAndSkipBlanks() {
        val messages = voiceV8Messages(listOf(
            VoiceLine(VoiceSpeaker.AI, ""),
            VoiceLine(VoiceSpeaker.USER, "我是学生"),
            VoiceLine(VoiceSpeaker.AI, "Zo'r", hanzi = "很好", pinyin = "hěn hǎo", translation = "Zo'r", correction = "我是学生。"),
            VoiceLine(VoiceSpeaker.AI, "Salom"),
        ))
        assertEquals(3, messages.size)
        assertEquals("我是学生。", messages[0].correction)
        assertEquals("很好", messages[1].text)
        assertEquals("hěn hǎo", messages[1].pinyin)
        assertEquals("Zo'r", messages[1].translation)
        // A line with no Chinese is shown as is, with no separate translation.
        assertEquals("Salom", messages[2].text)
        assertEquals("", messages[2].translation)
        assertNull(messages[0].source)
    }

    @Test fun topicsMapToTheBackendPartners() {
        assertEquals(VoiceV8Topic.HSK, VoiceV8Topic.forRole("teacher_li"))
        assertEquals(VoiceV8Topic.FREE, VoiceV8Topic.forRole("seller"))
        assertEquals(VoiceV8Topic.FREE, VoiceV8Topic.of("missing"))
        val roles = setOf("friend", "teacher_li", "seller", "classmate", "manager_wang", "roommate")
        assertTrue(VoiceV8Topic.entries.all { it.role in roles })
    }
}
