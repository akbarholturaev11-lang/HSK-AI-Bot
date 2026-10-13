package com.pomp.hskai.core.audio

import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

/**
 * Lesson pronunciations already obtained from the server.
 *
 * These are shared course materials, not session secrets. Saving them in the
 * app's filesDir makes them available offline even after Android clears its
 * disposable cacheDir or the learner signs out. App uninstall / Clear Storage
 * still removes private app files.
 */
interface TtsCache {
    suspend fun read(key: String): ByteArray?
    suspend fun write(key: String, audio: ByteArray)
    /** Explicit, user-requested deletion only; never called by logout. */
    suspend fun clear()
}

/**
 * Permanent, append-only pronunciation library.
 *
 * Unlike an LRU cache, no phrase is automatically evicted and a previously
 * downloaded phrase is never overwritten. A file remains available for as long
 * as the user keeps the app's data and the device storage remains intact.
 *
 * On first access, existing MP3s from the old cacheDir/tts are migrated into
 * filesDir before Android can purge them. Migration is idempotent and only
 * deletes legacy files after a complete persistent copy exists.
 */
class DiskTtsCache(
    private val dir: File,
    private val legacyDir: File? = null,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
) : TtsCache {

    private val writeLock = Mutex()
    private var legacyMigrationDone = false

    override suspend fun read(key: String): ByteArray? = withContext(ioDispatcher) {
        migrateLegacyEntries()
        runCatching {
            val file = File(dir, persistentFileName(key))
            if (!file.isFile) return@runCatching null
            file.readBytes().takeIf { it.isNotEmpty() }
        }.getOrNull()
    }

    override suspend fun write(key: String, audio: ByteArray) {
        if (audio.isEmpty() || audio.size > MAX_SINGLE_AUDIO_BYTES) return
        withContext(ioDispatcher) {
            migrateLegacyEntries()
            writeLock.withLock {
                runCatching {
                    dir.mkdirs()
                    val target = File(dir, persistentFileName(key))
                    if (!target.isFile || target.length() == 0L) {
                        storeAtomically(target, audio)
                    }
                }
            }
        }
    }

    /**
     * Only explicit "delete downloaded pronunciations" features should use
     * this. Repository clearCache() must NOT touch the audio library.
     */
    override suspend fun clear() {
        withContext(ioDispatcher) {
            writeLock.withLock {
                runCatching {
                    dir.listFiles()?.filter { it.isFile && it.name.endsWith(".audio") }
                        ?.forEach { it.delete() }
                }
            }
        }
    }

    private suspend fun migrateLegacyEntries() {
        if (legacyMigrationDone) return
        writeLock.withLock {
            if (legacyMigrationDone) return@withLock
            val old = legacyDir
            if (old == null || !old.isDirectory) {
                legacyMigrationDone = true
                return@withLock
            }
            val result = runCatching {
                dir.mkdirs()
                if (!dir.isDirectory) error("Cannot create persistent audio directory")
                old.listFiles().orEmpty().filter { file ->
                    file.isFile && LEGACY_NAME.matches(file.name) && file.length() > 0
                }.forEach { source ->
                    val target = File(dir, source.name.removeSuffix(".mp3") + ".audio")
                    if (!target.isFile || target.length() == 0L) {
                        storeAtomically(target, source.readBytes())
                    }
                    if (target.isFile && target.length() == source.length()) {
                        source.delete()
                    }
                }
            }
            // Retry migration on the next access after a disk IO failure.
            legacyMigrationDone = result.isSuccess
        }
    }

    private fun storeAtomically(target: File, bytes: ByteArray) {
        val temporary = File.createTempFile("lesson-tts-", ".part", dir)
        try {
            FileOutputStream(temporary).use { stream ->
                stream.write(bytes)
                stream.fd.sync()
            }
            if (!temporary.renameTo(target)) error("Audio persistence rename failed")
        } finally {
            temporary.delete()
        }
    }

    private fun digest(key: String): String {
        val hash = MessageDigest.getInstance("SHA-256").digest(key.toByteArray(Charsets.UTF_8))
        return hash.joinToString(separator = "") { "%02x".format(it) }
    }

    private fun persistentFileName(key: String) = digest(key) + ".audio"

    private companion object {
        private const val MAX_SINGLE_AUDIO_BYTES = 16 * 1024 * 1024
        private val LEGACY_NAME = Regex("[0-9a-f]{64}\\.mp3")
    }
}
