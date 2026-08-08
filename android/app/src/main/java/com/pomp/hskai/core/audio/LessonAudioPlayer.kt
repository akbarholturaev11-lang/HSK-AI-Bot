package com.pomp.hskai.core.audio

import android.content.Context
import android.media.AudioAttributes
import android.media.MediaPlayer
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext

/** Small injectable boundary so lesson audio stays testable without Android. */
interface LessonAudioPlayer {
    suspend fun play(mp3: ByteArray)
    fun release()
}

/** Plays a server-verified MP3 from the private app cache. */
class AndroidLessonAudioPlayer(context: Context) : LessonAudioPlayer {

    private val cacheDir = File(context.applicationContext.cacheDir, "lesson_audio")
    private var player: MediaPlayer? = null
    private var currentFile: File? = null

    override suspend fun play(mp3: ByteArray) {
        require(mp3.isNotEmpty()) { "Empty lesson audio" }
        val file = withContext(Dispatchers.IO) {
            cacheDir.mkdirs()
            File.createTempFile("lesson-", ".mp3", cacheDir).also { it.writeBytes(mp3) }
        }

        withContext(Dispatchers.Main.immediate) {
            stopCurrent()
            suspendCancellableCoroutine { continuation ->
                val next = MediaPlayer()
                player = next
                currentFile = file
                next.setAudioAttributes(
                    AudioAttributes.Builder()
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .build()
                )
                next.setOnPreparedListener { ready ->
                    runCatching { ready.start() }
                        .onSuccess { continuation.resumeWith(Result.success(Unit)) }
                        .onFailure { error ->
                            stopIfCurrent(ready)
                            continuation.resumeWith(Result.failure(error))
                        }
                }
                next.setOnCompletionListener(::stopIfCurrent)
                next.setOnErrorListener { failed, _, _ ->
                    stopIfCurrent(failed)
                    if (continuation.isActive) {
                        continuation.resumeWith(
                            Result.failure(IllegalStateException("Lesson audio playback failed"))
                        )
                    }
                    true
                }
                continuation.invokeOnCancellation { stopIfCurrent(next) }
                runCatching {
                    next.setDataSource(file.absolutePath)
                    next.prepareAsync()
                }.onFailure { error ->
                    stopIfCurrent(next)
                    if (continuation.isActive) {
                        continuation.resumeWith(Result.failure(error))
                    }
                }
            }
        }
    }

    override fun release() = stopCurrent()

    private fun stopIfCurrent(candidate: MediaPlayer) {
        if (player === candidate) stopCurrent() else runCatching { candidate.release() }
    }

    private fun stopCurrent() {
        val old = player
        player = null
        runCatching { old?.stop() }
        runCatching { old?.release() }
        currentFile?.delete()
        currentFile = null
    }
}
