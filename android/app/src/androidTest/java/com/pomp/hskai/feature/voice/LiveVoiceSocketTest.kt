package com.pomp.hskai.feature.voice

import androidx.test.ext.junit.runners.AndroidJUnit4
import java.io.IOException
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import okhttp3.Request
import okhttp3.WebSocket
import okio.ByteString
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/** Exercises the Android JSON/socket callbacks, including intentional and provider closes. */
@RunWith(AndroidJUnit4::class)
class LiveVoiceSocketTest {
    private class Socket : WebSocket {
        var closes = 0
        override fun request() = Request.Builder().url("https://example.com/voice").build()
        override fun queueSize() = 0L
        override fun send(text: String) = true
        override fun send(bytes: ByteString) = true
        override fun close(code: Int, reason: String?): Boolean { closes++; return true }
        override fun cancel() = Unit
    }

    private fun readyConnection(): Pair<AndroidLiveVoiceConnection, Socket> {
        val connection = AndroidLiveVoiceConnection(CompletableDeferred())
        val socket = Socket()
        connection.attach(socket)
        connection.listener().onMessage(socket, """{"type":"ready","max_seconds":180}""")
        return connection to socket
    }

    @Test fun deliberateCloseAndLateSocketCallbacksNeverReportConnectionLoss() = runBlocking {
        val (connection, socket) = readyConnection()
        connection.close(); connection.close()
        connection.listener().onClosed(socket, 1000, "client stop")
        connection.listener().onFailure(socket, IOException("closed"), null)
        assertEquals(emptyList<LiveVoiceEvent>(), connection.events.replayCache)
        assertEquals(1, socket.closes)
    }

    @Test fun failureAndFollowingClosePublishOnlyOneFailure() = runBlocking {
        val (connection, socket) = readyConnection()
        val received = mutableListOf<LiveVoiceEvent>()
        val collector = launch(start = CoroutineStart.UNDISPATCHED) { connection.events.collect { received += it } }
        connection.listener().onFailure(socket, IOException("network"), null)
        connection.listener().onClosed(socket, 1006, "lost")
        kotlinx.coroutines.yield()
        assertEquals(listOf(LiveVoiceEvent.Failed("live_connection_lost")), received)
        collector.cancelAndJoin(); connection.close()
    }

    @Test fun providerLimitsRemainTerminalAfterTheSocketCloses() = runBlocking {
        for (reason in listOf("budget_limit", "time_limit", "session_limit")) {
            val (connection, socket) = readyConnection()
            connection.listener().onMessage(socket, """{"type":"$reason"}""")
            connection.listener().onClosed(socket, 1000, "limit reached")
            assertEquals(listOf(LiveVoiceEvent.Terminal(reason)), connection.events.replayCache)
            connection.close()
        }
    }

    @Test fun closingWhileWaitingForReadyCompletesTheWait() = runBlocking {
        val ready = CompletableDeferred<Unit>()
        val connection = AndroidLiveVoiceConnection(ready)
        connection.attach(Socket()); connection.close()
        assertTrue(ready.isCompleted && ready.isCancelled)
    }

    @Test fun aFullAudioEventQueueCannotSwallowTheBudgetLimit() = runBlocking {
        val (connection, socket) = readyConnection()
        val resumeCollector = CompletableDeferred<Unit>()
        val firstReceived = CompletableDeferred<Unit>()
        val terminalReceived = CompletableDeferred<LiveVoiceEvent>()
        val collector = launch(start = CoroutineStart.UNDISPATCHED) {
            connection.events.collect { event ->
                if (!firstReceived.isCompleted) {
                    firstReceived.complete(Unit)
                    resumeCollector.await()
                }
                if (event is LiveVoiceEvent.Terminal) terminalReceived.complete(event)
            }
        }
        try {
            val listener = connection.listener()
            listener.onMessage(socket, """{"type":"interrupted"}""")
            firstReceived.await()
            // Replay + extra buffer = 257 events while the consumer is paused.
            repeat(257) { listener.onMessage(socket, """{"type":"audio","data":"AAE="}""") }
            listener.onMessage(socket, """{"type":"budget_limit"}""")
            listener.onClosed(socket, 1000, "budget reached")
            resumeCollector.complete(Unit)
            assertEquals(LiveVoiceEvent.Terminal("budget_limit"), withTimeout(5_000) { terminalReceived.await() })
        } finally { collector.cancelAndJoin(); connection.close() }
    }
}
