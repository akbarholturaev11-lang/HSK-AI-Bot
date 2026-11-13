package com.pomp.hskai.core.diagnostics

import java.io.File
import java.nio.file.Files
import kotlinx.coroutines.test.runTest
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.Response

/** Queue cap and TTL, the drop marker, owner binding and the uploader's answers. */
class DiagnosticQueueTest {
    private fun DiagnosticsKit.lessonFailure() =
        reporter.report(DiagFeature.LESSONS, DiagFailure.API_5XX, DiagSite.LESSON_OPEN)

    @Test
    fun `the cap keeps the newest events and one drop marker`() {
        val kit = DiagnosticsKit()
        repeat(DiagnosticQueue.MAX_EVENTS + 7) {
            kit.clock.now += 1
            kit.lessonFailure()
        }
        val codes = kit.codes()
        assertEquals(DiagnosticQueue.MAX_EVENTS, codes.size)
        assertEquals(1, codes.count { it == "monitoring/queue_dropped/queue" })
    }

    @Test
    fun `expired events are dropped and replaced by one marker`() {
        val kit = DiagnosticsKit()
        kit.lessonFailure()
        kit.lessonFailure()
        kit.clock.now += DiagnosticQueue.TTL_MILLIS
        kit.reporter.report(DiagFeature.PRACTICE, DiagFailure.API_DECODE, DiagSite.PRACTICE)
        assertEquals(listOf("practice/api_decode/practice", "monitoring/queue_dropped/queue"), kit.codes())
    }

    @Test
    fun `an account switch purges the queue and sign-in adopts pre-sign-in events`() {
        val kit = DiagnosticsKit(owner = null)
        kit.lessonFailure()
        kit.reporter.bindOwner(OWNER)
        assertEquals(1, kit.codes(OWNER).size)
        kit.reporter.bindOwner("device-b")
        assertEquals(0, kit.queue.size())
        kit.lessonFailure()
        kit.reporter.clearOwner()
        assertEquals(0, kit.queue.size())
    }

    @Test
    fun `a paused intake stops queueing until the pause ends`() {
        val kit = DiagnosticsKit()
        kit.state.pausedUntil = kit.clock.now + 1_000
        kit.lessonFailure()
        assertEquals(0, kit.queue.size())
        kit.clock.now += 1_000
        kit.lessonFailure()
        assertEquals(1, kit.queue.size())
    }

    @Test
    fun `a corrupt queue starts over and the atomic file round-trips`() {
        val kit = DiagnosticsKit()
        kit.store.bytes = "not json".encodeToByteArray()
        assertEquals(0, kit.queue.size())
        val dir = Files.createTempDirectory("diag").toFile()
        val file = AtomicDiagnosticFile(File(dir, "queue.json"))
        file.write("one".encodeToByteArray())
        file.write("two".encodeToByteArray())
        assertEquals("two", file.read()!!.decodeToString())
        assertFalse(File(dir, "queue.json.tmp").exists())
        file.delete()
        assertEquals(null, file.read())
        dir.deleteRecursively()
    }

    private fun response(code: Int, paused: Boolean = false): Response<DiagnosticIntakeResponse> =
        if (code in 200..299) Response.success(code, DiagnosticIntakeResponse(accepted = 1, paused = paused))
        else Response.error(code, """{"ok":false}""".toResponseBody("application/json".toMediaType()))

    private fun uploader(kit: DiagnosticsKit, answer: () -> Response<DiagnosticIntakeResponse>, sent: MutableList<DiagnosticBatchDto>) =
        DiagnosticUploader(kit.queue, kit.state, token = { "token" }, send = { bearer, batch ->
            assertEquals("Bearer token", bearer)
            sent += batch
            answer()
        }, clock = kit.clock::read)

    @Test
    fun `a 2xx removes the batch and 401 or 403 drops the queue`() = runTest {
        val kit = DiagnosticsKit()
        repeat(3) { kit.lessonFailure() }
        val sent = mutableListOf<DiagnosticBatchDto>()
        assertEquals(FlushOutcome.DONE, uploader(kit, { response(200) }, sent).flush())
        assertEquals(DIAG_SCHEMA, sent.single().schema)
        assertEquals(3, sent.single().events.size)
        assertEquals(0, kit.queue.size())
        for (code in listOf(401, 403)) {
            kit.lessonFailure()
            assertEquals(FlushOutcome.DROPPED, uploader(kit, { response(code) }, mutableListOf()).flush())
            assertEquals(0, kit.queue.size())
        }
    }

    @Test
    fun `a 5xx or a transport error is retried and other 4xx drop the batch`() = runTest {
        val kit = DiagnosticsKit()
        kit.lessonFailure()
        assertEquals(FlushOutcome.RETRY, uploader(kit, { response(503) }, mutableListOf()).flush())
        assertEquals(FlushOutcome.RETRY, uploader(kit, { throw java.io.IOException("offline") }, mutableListOf()).flush())
        assertEquals(1, kit.queue.size())
        assertEquals(FlushOutcome.DONE, uploader(kit, { response(422) }, mutableListOf()).flush())
        assertEquals(0, kit.queue.size())
    }

    @Test
    fun `a paused answer pauses reporting for a day and empties the queue`() = runTest {
        val kit = DiagnosticsKit()
        kit.lessonFailure()
        uploader(kit, { response(200, paused = true) }, mutableListOf()).flush()
        assertEquals(kit.clock.now + DiagnosticUploader.PAUSE_MILLIS, kit.state.pausedUntil)
        kit.lessonFailure()
        assertEquals(0, kit.queue.size())
    }

    @Test
    fun `nothing is sent without an owner or a token`() = runTest {
        val kit = DiagnosticsKit(owner = null)
        kit.lessonFailure()
        val sent = mutableListOf<DiagnosticBatchDto>()
        assertEquals(FlushOutcome.DONE, uploader(kit, { response(200) }, sent).flush())
        assertTrue(sent.isEmpty())
    }

    @Test
    fun `backoff gives up after three attempts`() {
        assertTrue(shouldRetryFlush(FlushOutcome.RETRY, 0))
        assertTrue(shouldRetryFlush(FlushOutcome.RETRY, 1))
        assertFalse(shouldRetryFlush(FlushOutcome.RETRY, 2))
        assertFalse(shouldRetryFlush(FlushOutcome.DONE, 0))
        assertFalse(shouldRetryFlush(FlushOutcome.DROPPED, 0))
    }
}
