package com.pomp.hskai.core.diagnostics

import java.lang.IndexOutOfBoundsException
import java.lang.NullPointerException
import java.lang.OutOfMemoryError
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/** Crash records (no network, previous handler runs) and exit reasons (once). */
class CrashAndExitDiagnosticsTest {
    private var original: Thread.UncaughtExceptionHandler? = null

    @Before
    fun keepHandler() {
        original = Thread.getDefaultUncaughtExceptionHandler()
    }

    @After
    fun restoreHandler() {
        Thread.setDefaultUncaughtExceptionHandler(original)
    }

    @Test
    fun `a crash writes a small record and the previous handler still runs`() {
        val kit = DiagnosticsKit()
        val crashStore = MemoryStore()
        var delegated: Throwable? = null
        Thread.setDefaultUncaughtExceptionHandler { _, error -> delegated = error }
        val recorder = CrashRecorder(crashStore, testJson, kit.state, feature = { DiagFeature.LESSONS }, clock = kit.clock::read)
        recorder.install()
        recorder.install() // idempotent: never wraps itself
        val crash = IllegalStateException("secret learner text")
        Thread.getDefaultUncaughtExceptionHandler()!!.uncaughtException(Thread.currentThread(), crash)
        assertSame(crash, delegated)
        val bytes = crashStore.bytes!!
        assertTrue(bytes.size <= CrashRecorder.MAX_RECORD_BYTES)
        assertTrue("secret" !in bytes.decodeToString())

        recorder.collect(kit.reporter)
        assertEquals(listOf("lessons/crash_uncaught/exc_state"), kit.codes())
        assertEquals("state", kit.events().single().category)
        assertNull(crashStore.bytes)
        assertEquals(kit.clock.now, kit.state.lastCrashAt)
    }

    @Test
    fun `another account's crash record is dropped`() {
        val kit = DiagnosticsKit()
        val crashStore = MemoryStore()
        val recorder = CrashRecorder(crashStore, testJson, kit.state, clock = kit.clock::read)
        recorder.record(NullPointerException())
        kit.state.owner = "device-b"
        recorder.collect(kit.reporter)
        assertEquals(0, kit.queue.size())
        assertNull(crashStore.bytes)
    }

    @Test
    fun `crash buckets never use the message`() {
        assertEquals(DiagSite.EXC_MEMORY, crashBucket(OutOfMemoryError()).first)
        assertEquals(DiagSite.EXC_SERIALIZATION, crashBucket(kotlinx.serialization.SerializationException("x")).first)
        assertEquals(DiagSite.EXC_ARGUMENT, crashBucket(IllegalArgumentException()).first)
        assertEquals(DiagSite.EXC_INDEX, crashBucket(IndexOutOfBoundsException()).first)
        assertEquals(DiagSite.EXC_OTHER, crashBucket(Exception()).first)
    }

    @Test
    fun `exit reasons map crash, native crash and ANR, each once`() {
        val kit = DiagnosticsKit()
        kit.state.lastExitSeen = START - 10_000
        val exits = listOf(
            ExitRecord(ExitReasons.REASON_ANR, START - 5_000),
            ExitRecord(ExitReasons.REASON_CRASH_NATIVE, START - 4_000),
            ExitRecord(ExitReasons.REASON_CRASH, START - 3_000),
            ExitRecord(1, START - 2_000), // exit self: not a failure
            ExitRecord(ExitReasons.REASON_ANR, START - 20_000), // already seen
        )
        ExitReasons.report(exits, kit.state, kit.reporter, START)
        ExitReasons.report(exits, kit.state, kit.reporter, START)
        assertEquals(
            listOf("app_shell/anr/process", "app_shell/crash_native/process", "app_shell/crash_uncaught/process"),
            kit.codes(),
        )
        assertEquals(START - 2_000, kit.state.lastExitSeen)
    }

    @Test
    fun `a JVM crash already recorded is not reported again as an exit reason`() {
        val reported = ExitReasons.select(
            listOf(ExitRecord(ExitReasons.REASON_CRASH, START + 5_000)), lastSeen = START, lastCrashAt = START + 4_000,
        )
        assertEquals(emptyList<Pair<DiagFailure, Long>>(), reported)
    }

    @Test
    fun `the first run only sets the mark`() {
        val kit = DiagnosticsKit()
        ExitReasons.report(listOf(ExitRecord(ExitReasons.REASON_ANR, START - 1)), kit.state, kit.reporter, START)
        assertEquals(0, kit.queue.size())
        assertEquals(START - 1, kit.state.lastExitSeen)
    }
}
