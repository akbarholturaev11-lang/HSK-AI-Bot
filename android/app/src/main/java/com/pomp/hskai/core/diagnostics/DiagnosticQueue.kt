package com.pomp.hskai.core.diagnostics

import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import kotlinx.serialization.json.Json

/** Byte storage for the queue and the crash record. */
interface DiagnosticFileStore {
    fun read(): ByteArray?
    fun write(bytes: ByteArray)
    fun delete()
}

/**
 * Write-to-temp, fsync, rename — the same guarantee as `android.util.AtomicFile`
 * (a reader sees the old or the new file, never half of one), in plain Java I/O
 * so the queue logic runs in JVM tests. Lives in `noBackupFilesDir`.
 */
class AtomicDiagnosticFile(private val file: File) : DiagnosticFileStore {
    private val temp get() = File(file.parentFile, file.name + ".tmp")

    override fun read(): ByteArray? = if (file.isFile) file.readBytes() else null

    override fun write(bytes: ByteArray) {
        file.parentFile?.mkdirs()
        val temp = temp
        FileOutputStream(temp).use { out ->
            out.write(bytes)
            out.fd.sync()
        }
        if (!temp.renameTo(file)) {
            file.delete()
            if (!temp.renameTo(file)) {
                temp.delete()
                throw IOException("diagnostic file write failed")
            }
        }
    }

    override fun delete() {
        file.delete()
        temp.delete()
    }
}

/**
 * The owner-bound event queue (design D5): at most [maxEvents], each kept for
 * [ttlMillis]. Events dropped for the cap or the TTL are replaced by one
 * content-free `monitoring/queue_dropped` event. Thread-safe.
 */
class DiagnosticQueue(
    private val store: DiagnosticFileStore,
    private val json: Json,
    private val clock: () -> Long = System::currentTimeMillis,
    private val maxEvents: Int = MAX_EVENTS,
    private val ttlMillis: Long = TTL_MILLIS,
) {
    private val lock = Any()

    /** Adds [entry]; [dropMarker] builds the `queue_dropped` event for an owner. */
    fun enqueue(entry: QueuedDiagnostic, dropMarker: (owner: String) -> QueuedDiagnostic) = synchronized(lock) {
        val now = clock()
        val all = load()
        val live = all.filter { it.isLive(now) }.toMutableList()
        var dropped = all.size - live.size
        live += entry
        dropped += trim(live)
        if (dropped > 0 && live.none { it.isDropMarker() && it.owner == entry.owner }) {
            live += dropMarker(entry.owner)
            trim(live)
        }
        save(live)
    }

    /** The oldest live events of [owner], at most [limit]. */
    fun forOwner(owner: String, limit: Int): List<QueuedDiagnostic> = synchronized(lock) {
        val now = clock()
        load().filter { it.owner == owner && it.isLive(now) }.take(limit)
    }

    fun remove(eventIds: Set<String>) = synchronized(lock) {
        val all = load()
        val kept = all.filterNot { it.event.eventId in eventIds }
        if (kept.size != all.size) save(kept)
    }

    /**
     * Binds the queue to [owner]: events queued before sign-in (owner "") are
     * adopted, every other owner's events are purged (an account switch).
     */
    fun bind(owner: String) = synchronized(lock) {
        val all = load()
        val kept = all.filter { it.owner == owner || it.owner.isEmpty() }.map {
            if (it.owner.isEmpty()) it.copy(owner = owner) else it
        }
        if (kept != all) save(kept)
    }

    fun purge() = synchronized(lock) { store.delete() }

    fun purgeOwner(owner: String) = retain { it.owner != owner }

    fun keepPreSignIn() = retain { it.owner.isEmpty() }

    private fun retain(keep: (QueuedDiagnostic) -> Boolean) = synchronized(lock) {
        val all = load()
        val kept = all.filter(keep)
        if (kept.size != all.size) save(kept)
    }

    fun size(): Int = synchronized(lock) { load().size }

    private fun QueuedDiagnostic.isLive(now: Long) = queuedAt <= now && now - queuedAt < ttlMillis

    /** Drops the oldest events beyond the cap, keeping drop markers. */
    private fun trim(entries: MutableList<QueuedDiagnostic>): Int {
        var dropped = 0
        while (entries.size > maxEvents) {
            val index = entries.indexOfFirst { !it.isDropMarker() }.takeIf { it >= 0 } ?: 0
            entries.removeAt(index)
            dropped++
        }
        return dropped
    }

    private fun load(): List<QueuedDiagnostic> = try {
        store.read()?.let { json.decodeFromString(DiagnosticQueueFile.serializer(), it.decodeToString()).entries }.orEmpty()
    } catch (_: Exception) {
        // A corrupt queue is content-free and expendable: start over.
        runCatching { store.delete() }
        emptyList()
    }

    private fun save(entries: List<QueuedDiagnostic>) {
        if (entries.isEmpty()) store.delete()
        else store.write(json.encodeToString(DiagnosticQueueFile.serializer(), DiagnosticQueueFile(entries)).encodeToByteArray())
    }

    companion object {
        const val MAX_EVENTS = 50
        const val TTL_MILLIS = 72L * 60 * 60 * 1000
    }
}

internal fun QueuedDiagnostic.isDropMarker() = event.failureCode == DiagFailure.QUEUE_DROPPED.code
