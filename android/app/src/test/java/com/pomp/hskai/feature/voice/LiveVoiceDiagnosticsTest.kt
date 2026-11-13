package com.pomp.hskai.feature.voice

import com.pomp.hskai.core.diagnostics.Diagnostics
import com.pomp.hskai.core.diagnostics.DiagnosticsKit
import com.pomp.hskai.core.diagnostics.REPORTED_LIVE_REASONS
import java.io.IOException
import kotlinx.coroutines.CompletableDeferred
import okhttp3.Request
import okhttp3.WebSocket
import okio.ByteString
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Before
import org.junit.Test

/** `LiveVoiceSocket.fail` reports client-side reasons once, nothing expected. */
class LiveVoiceDiagnosticsTest {
    private lateinit var kit: DiagnosticsKit

    @Before
    fun install() {
        kit = DiagnosticsKit()
        Diagnostics.reporter = kit.reporter
    }

    @After
    fun uninstall() {
        Diagnostics.reporter = null
    }

    private class FakeSocket(private val queued: Long = 0, private val accepts: Boolean = true) : WebSocket {
        override fun request(): Request = Request.Builder().url("https://example.test/live").build()
        override fun queueSize(): Long = queued
        override fun send(text: String): Boolean = accepts
        override fun send(bytes: ByteString): Boolean = accepts
        override fun close(code: Int, reason: String?): Boolean = true
        override fun cancel() = Unit
    }

    private fun connected(socket: WebSocket = FakeSocket()): AndroidLiveVoiceConnection {
        val connection = AndroidLiveVoiceConnection(CompletableDeferred<Unit>().apply { complete(Unit) })
        connection.attach(socket)
        return connection
    }

    @Test
    fun `an unexpected connection loss is reported once`() {
        val socket = FakeSocket()
        val listener = connected(socket).listener()
        listener.onFailure(socket, IOException("reset"), null)
        listener.onFailure(socket, IOException("again"), null)
        listener.onClosed(socket, 1006, "")
        assertEquals(listOf("voice_practice/live_session_failed/live_connection_lost"), kit.codes())
    }

    @Test
    fun `an oversized message and a failed send are client-side failures`() {
        val socket = FakeSocket()
        connected(socket).listener().onMessage(socket, "x".repeat(256_001))
        connected(FakeSocket(accepts = false)).sendAudio(byteArrayOf(1, 2))
        assertEquals(
            listOf(
                "voice_practice/live_session_failed/live_message_too_large",
                "voice_practice/live_session_failed/live_send_failed",
            ),
            kit.codes(),
        )
    }

    @Test
    fun `a learner close, a connect failure and backpressure are not reported`() {
        val socket = FakeSocket()
        // Not attached, so close() sends no stop frame (org.json is a stub in JVM tests).
        val closing = AndroidLiveVoiceConnection(CompletableDeferred<Unit>().apply { complete(Unit) })
        closing.close()
        closing.listener().onClosed(socket, 1000, "client stop")

        val connecting = AndroidLiveVoiceConnection(CompletableDeferred())
        connecting.listener().onFailure(socket, IOException("no route"), null)

        connected(FakeSocket(queued = Long.MAX_VALUE)).sendAudio(byteArrayOf(1, 2))
        assertEquals(emptyList<String>(), kit.codes())
    }

    @Test
    fun `a late socket failure from the previous account is ignored`() {
        val socket = FakeSocket()
        val listener = connected(socket).listener()
        kit.reporter.clearOwner()
        kit.reporter.bindOwner("device-b")
        listener.onFailure(socket, IOException("reset"), null)
        assertEquals(emptyList<String>(), kit.codes())
    }

    @Test
    fun `server-sent codes are never in the allowlist`() {
        for (code in listOf("live_voice_unavailable", "live_quota_exhausted", "budget_limit", "time_limit",
            "session_limit", "live_connect_failed", "live_network_backpressure", "live_audio_backpressure")) {
            assertFalse(code, code in REPORTED_LIVE_REASONS)
        }
        assertEquals(
            setOf("live_connection_lost", "live_message_invalid", "live_message_too_large", "live_send_failed"),
            REPORTED_LIVE_REASONS.keys,
        )
    }
}
