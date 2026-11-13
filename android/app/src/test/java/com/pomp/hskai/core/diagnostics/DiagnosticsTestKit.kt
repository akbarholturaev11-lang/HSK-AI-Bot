package com.pomp.hskai.core.diagnostics

import java.util.concurrent.Executor
import kotlinx.serialization.json.Json

internal class MemoryStore : DiagnosticFileStore {
    var bytes: ByteArray? = null
    override fun read(): ByteArray? = bytes
    override fun write(bytes: ByteArray) {
        this.bytes = bytes
    }
    override fun delete() {
        bytes = null
    }
}

internal class MemoryState(
    override var owner: String? = OWNER,
    override var pausedUntil: Long = 0L,
    override var lastExitSeen: Long = 0L,
    override var lastCrashAt: Long = 0L,
) : DiagnosticState

internal class TestClock(var now: Long = START) {
    fun read(): Long = now
}

internal const val OWNER = "device-a"
internal const val START = 1_790_000_000_000L
internal val testJson = Json { ignoreUnknownKeys = true; explicitNulls = false }

/** Queue, state, clock and a reporter that writes synchronously. */
internal class DiagnosticsKit(owner: String? = OWNER) {
    val clock = TestClock()
    val store = MemoryStore()
    val state = MemoryState(owner = owner)
    val queue = DiagnosticQueue(store, testJson, clock::read)
    val reporter = DiagnosticReporter(
        queue = queue,
        state = state,
        appVersion = "1.8.0",
        build = 40,
        channel = "play",
        executor = Executor { it.run() },
        clock = clock::read,
    )

    fun events(owner: String = state.owner.orEmpty()): List<DiagnosticEventDto> =
        queue.forOwner(owner, 1_000).map { it.event }

    fun codes(owner: String = state.owner.orEmpty()): List<String> =
        events(owner).map { "${it.featureCode}/${it.failureCode}/${it.siteCode}" }
}
