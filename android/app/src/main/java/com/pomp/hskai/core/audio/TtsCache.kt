package com.pomp.hskai.core.audio

import java.io.File
import java.security.MessageDigest
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

/**
 * Pronunciation audio the server has already produced for a phrase.
 *
 * The Mini App keeps fetched TTS in a blob cache, so the second tap on a
 * speaker plays instantly; Android re-downloaded the same MP3 on every tap.
 * Nothing here is private or account-scoped — it is the course's own Chinese,
 * byte-identical for every learner — so the ordinary app cache directory is
 * the right home for it.
 */
interface TtsCache {
    suspend fun read(key: String): ByteArray?
    suspend fun write(key: String, audio: ByteArray)
    suspend fun clear()
}

/**
 * A size-capped least-recently-used cache on disk.
 *
 * Recency is the file's own modification time, stamped on every read, so a
 * phrase the learner keeps replaying outlives one they met once. Every
 * operation swallows its own IO failure: a cache that cannot be read or
 * written must degrade to a plain download, never to a broken speaker.
 */
class DiskTtsCache(
    private val dir: File,
    private val maxBytes: Long = DEFAULT_MAX_BYTES,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
    private val now: () -> Long = System::currentTimeMillis,
) : TtsCache {

    private val writeLock = Mutex()

    override suspend fun read(key: String): ByteArray? = withContext(ioDispatcher) {
        val file = File(dir, fileName(key))
        runCatching {
            if (!file.isFile) return@runCatching null
            val bytes = file.readBytes()
            if (bytes.isEmpty()) {
                file.delete()
                return@runCatching null
            }
            file.setLastModified(now())
            bytes
        }.getOrNull()
    }

    override suspend fun write(key: String, audio: ByteArray) {
        if (audio.isEmpty() || audio.size > maxBytes) return
        withContext(ioDispatcher) {
            writeLock.withLock {
                runCatching {
                    dir.mkdirs()
                    val target = File(dir, fileName(key))
                    // Written aside and renamed, so a cancelled write can never
                    // leave a half MP3 under a key a later read would trust.
                    val staging = File(dir, target.name + ".part")
                    staging.writeBytes(audio)
                    if (target.exists()) target.delete()
                    if (!staging.renameTo(target)) staging.delete() else target.setLastModified(now())
                    trim()
                }
            }
        }
    }

    override suspend fun clear() {
        withContext(ioDispatcher) {
            writeLock.withLock {
                runCatching { dir.listFiles()?.forEach { it.delete() } }
            }
        }
    }

    /** Drops the least recently used files until the directory is under cap. */
    private fun trim() {
        val files = dir.listFiles()?.filter { it.isFile } ?: return
        var total = files.sumOf { it.length() }
        if (total <= maxBytes) return
        files.sortedBy { it.lastModified() }.forEach { file ->
            if (total <= maxBytes) return
            val size = file.length()
            if (file.delete()) total -= size
        }
    }

    private fun fileName(key: String): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(key.toByteArray())
        return digest.joinToString(separator = "") { "%02x".format(it) } + ".mp3"
    }

    private companion object {
        /** Roughly a few hundred short phrases; a card's audio is ~10-30 KB. */
        const val DEFAULT_MAX_BYTES = 24L * 1024 * 1024
    }
}
