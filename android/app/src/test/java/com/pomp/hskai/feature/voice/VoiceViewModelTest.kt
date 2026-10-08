package com.pomp.hskai.feature.voice

import com.pomp.hskai.core.audio.LiveVoiceAudioEngine
import com.pomp.hskai.core.audio.VoiceRecorder
import com.pomp.hskai.core.audio.VoiceRecording
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidFeatureApi
import com.pomp.hskai.data.api.VoiceEndResponse
import com.pomp.hskai.data.api.VoiceStartResponse
import com.pomp.hskai.data.api.VoiceStatusResponse
import com.pomp.hskai.data.repository.FeatureRepository
import java.io.IOException
import java.lang.reflect.Proxy
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class VoiceViewModelTest {
    private val dispatcher = StandardTestDispatcher()
    @Before fun setUp() { Dispatchers.setMain(dispatcher) }
    @After fun tearDown() { Dispatchers.resetMain() }

    private class Connection : LiveVoiceConnection {
        override val events = MutableSharedFlow<LiveVoiceEvent>(extraBufferCapacity = 16)
        override val maxSeconds = 180
        var closes = 0
        override fun sendAudio(pcm: ByteArray) = Unit
        override fun sendText(text: String) = Unit
        override fun setMuted(muted: Boolean) = Unit
        override fun close() {
            closes++
            // Emulate the old socket reporting its deliberate close as loss.
            events.tryEmit(LiveVoiceEvent.Failed("live_connection_lost"))
        }
    }

    private class Audio : LiveVoiceAudioEngine {
        var starts = 0
        var playing = false
        override fun start(onPcmChunk: (ByteArray) -> Unit) { starts++; playing = true }
        override fun setMuted(muted: Boolean) = Unit
        override fun playPcm(pcm: ByteArray) = true
        override fun clearPlayback() = Unit
        override fun stop() { playing = false }
    }

    private class Recorder : VoiceRecorder {
        override val isRecording = false
        override fun start() = Unit
        override suspend fun stop() = VoiceRecording("", 0)
        override fun cancel() = Unit
    }

    private inner class Fixture {
        val first = Connection()
        val audio = Audio()
        var connections = 0
        var statusCalls = 0
        var starts = 0
        var ends = 0
        var startFails = false
        var connect: suspend (Int) -> LiveVoiceConnection = { first }
        // Only Voice methods may be called; unrelated API methods fail loudly.
        private val api = Proxy.newProxyInstance(
            AndroidFeatureApi::class.java.classLoader,
            arrayOf(AndroidFeatureApi::class.java),
        ) { _, method, _ ->
            when (method.name) {
                "voiceStatus" -> {
                    statusCalls++
                    Response.success(VoiceStatusResponse(ok = true, liveAvailable = true, remainingVoiceLimit = 3))
                }
                "voiceStart" -> {
                    starts++
                    check(!startFails) { "fixture unavailable" }
                    Response.success(VoiceStartResponse(ok = true, sessionId = "owned-session", mode = "live"))
                }
                "voiceEnd" -> { ends++; Response.success(VoiceEndResponse(ok = true)) }
                else -> error("Unexpected API call: ${method.name}")
            }
        } as AndroidFeatureApi
        val vm = VoiceViewModel(
            FeatureRepository(api, accessToken = { ApiResult.Success("test-token") }), Recorder(),
            liveVoiceGateway = object : LiveVoiceGateway {
                override suspend fun connect(sessionId: String): LiveVoiceConnection {
                    assertEquals("owned-session", sessionId)
                    return connect(++connections)
                }
            },
            liveVoiceAudioEngine = audio, liveIoDispatcher = dispatcher,
        )
    }

    @Test fun deliberateCloseAndLateEventsProduceOnlyOneReconnect() = runTest(dispatcher) {
        val f = Fixture()
        val replacement = Connection()
        f.connect = { if (it == 1) f.first else replacement }
        try {
            f.vm.ensureStatusLoaded(); runCurrent()
            f.vm.startSession("hsk1", "uz"); runCurrent()
            f.first.events.tryEmit(LiveVoiceEvent.Failed("live_connection_lost")); runCurrent()
            advanceTimeBy(1_300); runCurrent()
            f.first.events.tryEmit(LiveVoiceEvent.Failed("live_connection_lost")); runCurrent()
            assertEquals(2, f.connections)
            assertEquals(1, f.first.closes)
            assertTrue(f.vm.state.value.isLiveConnected)
            assertNull(f.vm.state.value.error)
        } finally { f.vm.reset() }
    }

    @Test fun endingDuringReconnectDoesNotReopenTheMicrophone() = runTest(dispatcher) {
        val f = Fixture()
        try {
            f.vm.ensureStatusLoaded(); runCurrent()
            f.vm.startSession("hsk1", "uz"); runCurrent()
            f.first.events.tryEmit(LiveVoiceEvent.Failed("live_connection_lost")); runCurrent()
            f.vm.endSession(); runCurrent()
            advanceTimeBy(5_000); runCurrent()
            assertEquals(1, f.connections)
            assertEquals(1, f.ends)
            assertFalse(f.audio.playing)
            assertNotNull(f.vm.state.value.result)
        } finally { f.vm.reset() }
    }

    @Test fun endingDuringPendingConnectionCannotResurrectTheCall() = runTest(dispatcher) {
        val f = Fixture()
        val pending = CompletableDeferred<LiveVoiceConnection>()
        f.connect = { pending.await() }
        try {
            f.vm.ensureStatusLoaded(); runCurrent()
            f.vm.startSession("hsk1", "uz"); runCurrent()
            f.vm.endSession(); runCurrent()
            pending.complete(Connection()); runCurrent()
            assertEquals(0, f.audio.starts)
            assertEquals(1, f.ends)
            assertNull(f.vm.state.value.sessionId)
        } finally { f.vm.reset() }
    }

    @Test fun aFailedReconnectRetriesWithoutStartingANewConversation() = runTest(dispatcher) {
        val f = Fixture()
        val initial = Connection()
        f.connect = { when (it) { 1 -> initial; 2 -> throw IOException("live_connect_failed"); else -> Connection() } }
        try {
            f.vm.ensureStatusLoaded(); runCurrent()
            f.vm.startSession("hsk1", "uz"); runCurrent()
            initial.events.tryEmit(LiveVoiceEvent.Failed("live_connection_lost")); runCurrent()
            advanceTimeBy(1_300); runCurrent()
            advanceTimeBy(2_500); runCurrent()
            assertEquals(3, f.connections)
            assertEquals(1, f.starts)
            assertTrue(f.vm.state.value.isLiveConnected)
        } finally { f.vm.reset() }
    }

    @Test fun budgetLimitEndsTheCallWithoutRetryOrFallback() = runTest(dispatcher) {
        val f = Fixture()
        try {
            f.vm.ensureStatusLoaded(); runCurrent()
            f.vm.startSession("hsk1", "uz"); runCurrent()
            f.first.events.tryEmit(LiveVoiceEvent.Terminal("budget_limit")); runCurrent()
            advanceTimeBy(5_000); runCurrent()
            assertEquals(1, f.connections)
            assertEquals(1, f.starts)
            assertEquals(1, f.ends)
            assertNotNull(f.vm.state.value.result)
        } finally { f.vm.reset() }
    }

    @Test fun reconnectAfterACompletedTurnIsBoundedAndKeepsTheConversation() = runTest(dispatcher) {
        val f = Fixture()
        f.connect = { if (it == 1) f.first else throw IOException("live_connect_failed") }
        try {
            f.vm.ensureStatusLoaded(); runCurrent()
            f.vm.startSession("hsk1", "uz"); runCurrent()
            f.first.events.tryEmit(LiveVoiceEvent.TurnComplete(LiveVoiceTurn(
                transcription = "你好", chineseReply = "你好！", pinyin = "nǐ hǎo", translation = "salom",
                correction = null, suggestions = emptyList(), remainingLimit = 3,
                turnCount = 8, maxDialogs = 0, shouldEnd = false,
            ))); runCurrent()
            assertTrue(f.vm.state.value.hasSession)
            f.first.events.tryEmit(LiveVoiceEvent.Failed("live_connection_lost")); runCurrent()
            advanceTimeBy(10_000); runCurrent()
            assertEquals(4, f.connections)
            assertEquals(1, f.starts)
            assertEquals(0, f.ends)
            assertEquals(8, f.vm.state.value.turnCount)
            assertEquals("owned-session", f.vm.state.value.sessionId)
            assertFalse(f.vm.state.value.isLiveConnecting)
            assertTrue(f.vm.state.value.error is ApiError.Server)
            advanceTimeBy(10_000); runCurrent()
            assertEquals(4, f.connections)
        } finally { f.vm.reset() }
    }

    @Test fun aSessionExpiredDuringConnectEndsWithoutRetrying() = runTest(dispatcher) {
        val f = Fixture()
        f.connect = { throw IOException("live_session_expired") }
        try {
            f.vm.ensureStatusLoaded(); runCurrent()
            f.vm.startSession("hsk1", "uz"); runCurrent()
            advanceTimeBy(10_000); runCurrent()
            assertEquals(1, f.connections)
            assertEquals(1, f.starts)
            assertEquals(1, f.ends)
            assertNotNull(f.vm.state.value.result)
        } finally { f.vm.reset() }
    }

    @Test fun reopeningTheVoiceTabRefreshesAStaleError() = runTest(dispatcher) {
        val f = Fixture()
        f.startFails = true
        try {
            f.vm.ensureStatusLoaded(); runCurrent()
            f.vm.startSession("hsk1", "uz"); runCurrent()
            assertEquals(ApiError.Unknown, f.vm.state.value.error)
            assertEquals(1, f.statusCalls)
            f.vm.ensureStatusLoaded(); runCurrent()
            assertEquals(2, f.statusCalls)
            assertNull(f.vm.state.value.error)
            assertEquals(3, f.vm.state.value.remainingLimit)
        } finally { f.vm.reset() }
    }
}
