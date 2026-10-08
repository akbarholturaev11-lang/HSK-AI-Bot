package com.pomp.hskai.core.audio

import java.util.concurrent.ArrayBlockingQueue

/** PCM may arrive faster than it can be spoken; keep a bounded reply queue. */
internal class LiveVoicePlaybackBuffer {
    data class Chunk(val pcm: ByteArray, val generation: Long)

    private val queue = ArrayBlockingQueue<Chunk>(600)
    private val lock = Any()
    private var queuedBytes = 0
    @Volatile private var generation = 0L

    fun offer(pcm: ByteArray): Boolean = synchronized(lock) {
        if (queuedBytes + pcm.size > MAX_BYTES) return false
        if (!queue.offer(Chunk(pcm.copyOf(), generation))) return false
        queuedBytes += pcm.size
        true
    }

    fun take(): Chunk {
        val chunk = queue.take()
        synchronized(lock) {
            if (isCurrent(chunk)) queuedBytes -= chunk.pcm.size
        }
        return chunk
    }

    fun isCurrent(chunk: Chunk): Boolean = chunk.generation == generation

    fun clear() = synchronized(lock) {
        generation++
        queue.clear()
        queuedBytes = 0
    }

    private companion object {
        // 12 seconds at 24 kHz PCM16 mono, under 600 KB. This is capacity,
        // not a startup delay: the player consumes the first chunk at once.
        const val MAX_BYTES = 24_000 * 2 * 12
    }
}
