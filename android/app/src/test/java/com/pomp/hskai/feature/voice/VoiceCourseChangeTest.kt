package com.pomp.hskai.feature.voice

import com.pomp.hskai.core.audio.LiveVoiceAudioEngine
import com.pomp.hskai.core.audio.VoiceRecorder
import com.pomp.hskai.core.audio.VoiceRecording
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidFeatureApi
import com.pomp.hskai.data.api.VoiceEndRequest
import com.pomp.hskai.data.api.VoiceEndResponse
import com.pomp.hskai.data.api.VoiceMessageRequest
import com.pomp.hskai.data.api.VoiceMessageResponse
import com.pomp.hskai.data.api.VoiceStartRequest
import com.pomp.hskai.data.api.VoiceStartResponse
import com.pomp.hskai.data.api.VoiceStatusResponse
import com.pomp.hskai.data.repository.FeatureRepository
import java.lang.reflect.Proxy
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import kotlin.coroutines.Continuation
import kotlin.coroutines.intrinsics.startCoroutineUninterceptedOrReturn
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.asCoroutineDispatcher
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

/** Delayed network/recorder replies may never restore an abandoned course call. */
@OptIn(ExperimentalCoroutinesApi::class)
class VoiceCourseChangeTest {
    private val dispatcher = StandardTestDispatcher()
    @Before fun setUp() = Dispatchers.setMain(dispatcher)
    @After fun tearDown() = Dispatchers.resetMain()

    private class Recorder : VoiceRecorder {
        private var recording = false
        override val isRecording get() = recording
        var stopped: CompletableDeferred<VoiceRecording>? = null
        override fun start() { recording = true }
        override suspend fun stop(): VoiceRecording {
            recording = false
            return stopped?.await() ?: VoiceRecording("data:audio/mp4;base64,TEST", 4)
        }
        override fun cancel() { recording = false }
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

    private class Connection : LiveVoiceConnection {
        override val events = MutableSharedFlow<LiveVoiceEvent>(extraBufferCapacity = 4)
        override val maxSeconds = 180
        var closes = 0
        override fun sendAudio(pcm: ByteArray) = Unit
        override fun sendText(text: String) = Unit
        override fun setMuted(muted: Boolean) = Unit
        override fun close() { closes++ }
    }

    private inner class Fixture(
        gatewayAvailable: Boolean = true,
        audioEngine: LiveVoiceAudioEngine? = null,
        ioDispatcher: CoroutineDispatcher = dispatcher,
    ) {
        val recorder = Recorder()
        val audio = Audio()
        val connection = Connection()
        val statuses = ArrayDeque<CompletableDeferred<Response<VoiceStatusResponse>>>()
        val starts = ArrayDeque<CompletableDeferred<Response<VoiceStartResponse>>>()
        val turns = ArrayDeque<CompletableDeferred<Response<VoiceMessageResponse>>>()
        val ends = ArrayDeque<CompletableDeferred<Response<VoiceEndResponse>>>()
        val startRequests = mutableListOf<VoiceStartRequest>()
        val turnRequests = mutableListOf<VoiceMessageRequest>()
        val ended = mutableListOf<String>()
        var statusCalls = 0
        var liveAvailable = false

        @Suppress("UNCHECKED_CAST")
        private fun <T> respond(reply: CompletableDeferred<T>, args: Array<out Any>?): Any? =
            (suspend { reply.await() }).startCoroutineUninterceptedOrReturn(args!!.last() as Continuation<T>)

        private val api = Proxy.newProxyInstance(
            AndroidFeatureApi::class.java.classLoader, arrayOf(AndroidFeatureApi::class.java),
        ) { _, method, args ->
            when (method.name) {
                "voiceStatus" -> {
                    statusCalls++
                    if (statuses.isEmpty()) Response.success(VoiceStatusResponse(
                        ok = true, liveAvailable = liveAvailable, remainingVoiceLimit = 3,
                    )) else respond(statuses.removeFirst(), args)
                }
                "voiceStart" -> {
                    val request = args!![1] as VoiceStartRequest
                    startRequests += request
                    if (starts.isEmpty()) Response.success(VoiceStartResponse(
                        ok = true, sessionId = "session-${startRequests.size}", mode = request.mode ?: "turn",
                    )) else respond(starts.removeFirst(), args)
                }
                "voiceMessage" -> {
                    turnRequests += args!![1] as VoiceMessageRequest
                    respond(turns.removeFirst(), args)
                }
                "voiceEnd" -> {
                    ended += (args!![1] as VoiceEndRequest).sessionId
                    if (ends.isEmpty()) Response.success(VoiceEndResponse(ok = true))
                    else respond(ends.removeFirst(), args)
                }
                else -> error("Unexpected API call: ${method.name}")
            }
        } as AndroidFeatureApi

        val vm = VoiceViewModel(
            FeatureRepository(api, { ApiResult.Success("test-token") }), recorder,
            liveVoiceGateway = if (gatewayAvailable) object : LiveVoiceGateway {
                override suspend fun connect(sessionId: String): LiveVoiceConnection = connection
            } else null,
            liveVoiceAudioEngine = audioEngine ?: audio,
            liveIoDispatcher = ioDispatcher,
        ).also { it.onCourseChanged("hsk1") }

        fun startTurn() { vm.startSession("hsk1", "uz", preferLive = false) }
    }

    @Test fun unopenedVoiceKeepsStatusLazyAndRefusesTheOldPermissionCallback() = runTest(dispatcher) {
        val f = Fixture()
        f.vm.onCourseChanged("nhsk3")
        f.vm.startSession("hsk1", "uz")
        runCurrent()
        assertEquals(0, f.statusCalls)
        assertTrue(f.startRequests.isEmpty())
        f.vm.ensureStatusLoaded()
        runCurrent()
        assertEquals(1, f.statusCalls)
    }

    @Test fun oldStatusCannotReplaceTheRefreshForTheNewCourse() = runTest(dispatcher) {
        val f = Fixture()
        val old = CompletableDeferred<Response<VoiceStatusResponse>>()
        val fresh = CompletableDeferred<Response<VoiceStatusResponse>>()
        f.statuses.add(old)
        f.vm.ensureStatusLoaded()
        runCurrent()
        f.statuses.add(fresh)
        f.vm.onCourseChanged("nhsk3")
        runCurrent()
        fresh.complete(Response.success(VoiceStatusResponse(ok = true, level = "nhsk3", remainingVoiceLimit = 7)))
        runCurrent()
        old.complete(Response.success(VoiceStatusResponse(ok = true, level = "hsk1", remainingVoiceLimit = 1)))
        runCurrent()
        assertEquals("nhsk3", f.vm.state.value.status!!.level)
        assertEquals(7, f.vm.state.value.remainingLimit)
        f.vm.ensureStatusLoaded()
        runCurrent()
        assertEquals(2, f.statusCalls)
    }

    @Test fun courseChangeStopsLiveAudioAndRejectsOldSocketEvents() = runTest(dispatcher) {
        val f = Fixture()
        f.liveAvailable = true
        f.vm.ensureStatusLoaded()
        runCurrent()
        f.vm.startSession("hsk1", "uz")
        runCurrent()
        assertTrue(f.audio.playing)
        f.vm.onCourseChanged("nhsk3")
        runCurrent()
        f.connection.events.tryEmit(LiveVoiceEvent.Failed("live_connection_lost"))
        advanceTimeBy(2_000)
        runCurrent()
        assertFalse(f.audio.playing)
        assertFalse(f.vm.state.value.isRecording)
        assertNull(f.vm.state.value.sessionId)
        assertNull(f.vm.state.value.liveSecondsRemaining)
        assertTrue(f.vm.state.value.lines.isEmpty())
        assertEquals(1, f.connection.closes)
        assertEquals(listOf("session-1"), f.ended)
        assertEquals(1, f.startRequests.size)
    }

    @Test fun paymentRefreshSupersedesAnInFlightBlockedStatusResponse() = runTest(dispatcher) {
        val f = Fixture()
        val blocked = CompletableDeferred<Response<VoiceStatusResponse>>()
        val paid = CompletableDeferred<Response<VoiceStatusResponse>>()
        f.statuses.add(blocked)
        f.vm.ensureStatusLoaded()
        runCurrent()
        f.statuses.add(paid)
        f.vm.refreshStatusIfLoaded()
        runCurrent()
        paid.complete(Response.success(VoiceStatusResponse(ok = true, isPaid = true, remainingVoiceLimit = 20)))
        runCurrent()
        blocked.complete(Response.success(VoiceStatusResponse(ok = true, remainingVoiceLimit = 0)))
        runCurrent()
        assertTrue(f.vm.state.value.status!!.isPaid)
        assertEquals(20, f.vm.state.value.remainingLimit)
        assertFalse(f.vm.state.value.isLoading)
        assertEquals(2, f.statusCalls)
    }

    @Test fun courseResetSerializesStopWithAnAlreadyDispatchedAudioStart() = runTest(dispatcher) {
        val startEntered = CountDownLatch(1)
        val finishStart = CountDownLatch(1)
        var playing = false
        val engine = object : LiveVoiceAudioEngine {
            override fun start(onPcmChunk: (ByteArray) -> Unit) {
                startEntered.countDown()
                check(finishStart.await(5, TimeUnit.SECONDS)) { "audio start barrier timed out" }
                playing = true
            }
            override fun setMuted(muted: Boolean) = Unit
            override fun playPcm(pcm: ByteArray) = true
            override fun clearPlayback() = Unit
            override fun stop() { playing = false }
        }
        val io = Executors.newSingleThreadExecutor().asCoroutineDispatcher()
        val f = Fixture(audioEngine = engine, ioDispatcher = io)
        f.liveAvailable = true
        var changer: Thread? = null
        try {
            f.vm.ensureStatusLoaded()
            runCurrent()
            f.vm.startSession("hsk1", "uz")
            runCurrent()
            assertTrue(startEntered.await(5, TimeUnit.SECONDS))
            val reset = Thread { f.vm.onCourseChanged("nhsk3") }
            changer = reset
            reset.start()
            val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(2)
            while (reset.isAlive && reset.state != Thread.State.BLOCKED && System.nanoTime() < deadline) {
                Thread.yield()
            }
            // Without ownership around start+stop, reset finishes first and
            // the abandoned IO start subsequently reopens the microphone.
            assertEquals(Thread.State.BLOCKED, reset.state)
            finishStart.countDown()
            reset.join(5_000)
            assertFalse(reset.isAlive)
            runCurrent()
            assertFalse(playing)
            assertNull(f.vm.state.value.sessionId)
            assertFalse(f.vm.state.value.isRecording)
        } finally {
            finishStart.countDown()
            changer?.join(5_000)
            f.vm.endSession()
            io.close()
        }
    }

    @Test fun oldStartCannotReplaceANewCourseCallOrOpenTheMicrophone() = runTest(dispatcher) {
        val f = Fixture()
        val old = CompletableDeferred<Response<VoiceStartResponse>>()
        f.starts.add(old)
        f.startTurn()
        runCurrent()
        f.vm.onCourseChanged("nhsk3")
        f.vm.startSession("nhsk3", "uz", preferLive = false)
        runCurrent()
        old.complete(Response.success(VoiceStartResponse(ok = true, sessionId = "old-session", mode = "live")))
        runCurrent()
        assertEquals("session-2", f.vm.state.value.sessionId)
        assertEquals(0, f.audio.starts)
        assertEquals(listOf("old-session"), f.ended)
        assertFalse(f.vm.state.value.isStarting)
    }

    @Test fun endingAPendingStartCannotResurrectTheCall() = runTest(dispatcher) {
        val f = Fixture()
        val old = CompletableDeferred<Response<VoiceStartResponse>>()
        f.starts.add(old)
        f.startTurn()
        runCurrent()
        f.vm.endSession()
        assertFalse(f.vm.state.value.isStarting)
        old.complete(Response.success(VoiceStartResponse(ok = true, sessionId = "late-session", mode = "live")))
        runCurrent()
        assertNull(f.vm.state.value.sessionId)
        assertEquals(0, f.audio.starts)
        assertEquals(listOf("late-session"), f.ended)
    }

    @Test fun lateTurnCannotEndOrAddLinesToANewCourseCall() = runTest(dispatcher) {
        val f = Fixture()
        f.startTurn()
        runCurrent()
        val old = CompletableDeferred<Response<VoiceMessageResponse>>()
        f.turns.add(old)
        f.vm.sendTypedMessage("你好")
        runCurrent()
        f.vm.onCourseChanged("nhsk3")
        f.vm.startSession("nhsk3", "uz", preferLive = false)
        runCurrent()
        old.complete(Response.success(VoiceMessageResponse(ok = true, turnCount = 9, sessionShouldEnd = true)))
        runCurrent()
        assertEquals("session-2", f.vm.state.value.sessionId)
        assertEquals(0, f.vm.state.value.turnCount)
        assertEquals(1, f.vm.state.value.lines.size)
        assertFalse(f.vm.state.value.isSending)
        assertEquals(listOf("session-1"), f.ended)
    }

    @Test fun endingWhileATurnIsSendingStillStopsTheCall() = runTest(dispatcher) {
        val f = Fixture()
        f.startTurn()
        runCurrent()
        val old = CompletableDeferred<Response<VoiceMessageResponse>>()
        f.turns.add(old)
        f.vm.sendTypedMessage("你好")
        runCurrent()
        f.vm.endSession()
        runCurrent()
        old.complete(Response.success(VoiceMessageResponse(ok = true, turnCount = 9)))
        runCurrent()
        assertEquals(listOf("session-1"), f.ended)
        assertNotNull(f.vm.state.value.result)
        assertNull(f.vm.state.value.sessionId)
        assertEquals(0, f.vm.state.value.turnCount)
    }

    @Test fun lateEndCannotReplaceANewCourseConversationWithOldResults() = runTest(dispatcher) {
        val f = Fixture()
        f.startTurn()
        runCurrent()
        val old = CompletableDeferred<Response<VoiceEndResponse>>()
        f.ends.add(old)
        f.vm.endSession()
        runCurrent()
        f.vm.onCourseChanged("nhsk3")
        f.vm.startSession("nhsk3", "uz", preferLive = false)
        runCurrent()
        old.complete(Response.success(VoiceEndResponse(ok = true)))
        runCurrent()
        assertEquals("session-2", f.vm.state.value.sessionId)
        assertNull(f.vm.state.value.result)
        assertFalse(f.vm.state.value.isSending)
    }

    @Test fun changedCourseStopsAFallbackWaitingForTheOldSessionToEnd() = runTest(dispatcher) {
        val f = Fixture(gatewayAvailable = false)
        f.liveAvailable = true
        f.vm.ensureStatusLoaded()
        runCurrent()
        val old = CompletableDeferred<Response<VoiceEndResponse>>()
        f.ends.add(old)
        f.vm.startSession("hsk1", "uz")
        runCurrent()
        assertTrue(f.vm.state.value.isStarting)
        f.vm.onCourseChanged("nhsk3")
        f.vm.startSession("nhsk3", "uz", preferLive = false)
        runCurrent()
        old.complete(Response.success(VoiceEndResponse(ok = true)))
        runCurrent()
        assertEquals(2, f.startRequests.size)
        assertEquals("session-2", f.vm.state.value.sessionId)
    }

    @Test fun changedCourseRejectsALateFallbackStartResponse() = runTest(dispatcher) {
        val f = Fixture(gatewayAvailable = false)
        f.liveAvailable = true
        f.vm.ensureStatusLoaded()
        runCurrent()
        val old = CompletableDeferred<Response<VoiceStartResponse>>()
        f.starts.add(CompletableDeferred(Response.success(VoiceStartResponse(
            ok = true, sessionId = "old-live", mode = "live",
        ))))
        f.starts.add(old)
        f.vm.startSession("hsk1", "uz")
        runCurrent()
        f.vm.onCourseChanged("nhsk3")
        f.vm.startSession("nhsk3", "uz", preferLive = false)
        runCurrent()
        old.complete(Response.success(VoiceStartResponse(ok = true, sessionId = "old-fallback")))
        runCurrent()
        assertEquals("session-3", f.vm.state.value.sessionId)
        assertFalse(f.vm.state.value.usedTurnFallback)
        assertTrue("old-fallback" in f.ended)
    }

    @Test fun oldRecordingCannotUploadIntoANewCourseConversation() = runTest(dispatcher) {
        val f = Fixture()
        f.startTurn()
        runCurrent()
        val old = CompletableDeferred<VoiceRecording>()
        f.recorder.stopped = old
        f.vm.toggleRecording()
        assertTrue(f.recorder.isRecording)
        f.vm.toggleRecording()
        runCurrent()
        f.vm.onCourseChanged("nhsk3")
        f.vm.startSession("nhsk3", "uz", preferLive = false)
        runCurrent()
        old.complete(VoiceRecording("data:audio/mp4;base64,OLD", 3))
        runCurrent()
        assertFalse(f.recorder.isRecording)
        assertTrue(f.turnRequests.isEmpty())
        assertEquals("session-2", f.vm.state.value.sessionId)
        assertFalse(f.vm.state.value.isSending)
    }

    @Test fun aDelayedPartnerSwapCannotStartThePreviousCourseAgain() = runTest(dispatcher) {
        val f = Fixture()
        f.startTurn()
        runCurrent()
        val old = CompletableDeferred<Response<VoiceEndResponse>>()
        f.ends.add(old)
        f.vm.swapPartner("teacher_li", "hsk1", "uz")
        runCurrent()
        f.vm.onCourseChanged("nhsk3")
        f.vm.startSession("nhsk3", "uz", preferLive = false)
        runCurrent()
        old.complete(Response.success(VoiceEndResponse(ok = true)))
        runCurrent()
        assertEquals(2, f.startRequests.size)
        assertEquals("session-2", f.vm.state.value.sessionId)
    }
}
