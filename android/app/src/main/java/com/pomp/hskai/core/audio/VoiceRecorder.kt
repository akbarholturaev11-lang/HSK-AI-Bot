package com.pomp.hskai.core.audio

import android.content.Context
import android.media.MediaRecorder
import android.util.Base64
import java.io.File
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

interface VoiceRecorder {
    val isRecording: Boolean
    fun start()
    suspend fun stop(): VoiceRecording
    fun cancel()
}

data class VoiceRecording(
    val dataUrl: String,
    val bytes: Int,
)

class AndroidVoiceRecorder(
    context: Context,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
) : VoiceRecorder {

    private val appContext = context.applicationContext
    private var recorder: MediaRecorder? = null
    private var outputFile: File? = null

    override val isRecording: Boolean
        get() = recorder != null

    @Suppress("DEPRECATION")
    override fun start() {
        if (recorder != null) return
        val file = File.createTempFile("voice-", ".m4a", appContext.cacheDir)
        val nextRecorder = MediaRecorder()
        nextRecorder.setAudioSource(MediaRecorder.AudioSource.MIC)
        nextRecorder.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
        nextRecorder.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
        nextRecorder.setAudioEncodingBitRate(96_000)
        nextRecorder.setAudioSamplingRate(44_100)
        nextRecorder.setOutputFile(file.absolutePath)
        nextRecorder.prepare()
        nextRecorder.start()
        outputFile = file
        recorder = nextRecorder
    }

    override suspend fun stop(): VoiceRecording = withContext(ioDispatcher) {
        val active = recorder ?: throw IllegalStateException("Recorder is not active")
        val file = outputFile ?: throw IllegalStateException("Recording file is missing")
        var stopFailure: Throwable? = null
        try {
            active.stop()
        } catch (error: Throwable) {
            stopFailure = error
        } finally {
            active.release()
            recorder = null
            outputFile = null
        }
        if (stopFailure != null) {
            file.delete()
            throw IllegalStateException("Recording could not be stopped", stopFailure)
        }
        val bytes = file.readBytes()
        file.delete()
        if (bytes.isEmpty() || bytes.size > MAX_AUDIO_BYTES) {
            throw IllegalStateException("Recording is empty or too large")
        }
        VoiceRecording(
            dataUrl = "data:audio/mp4;base64," +
                Base64.encodeToString(bytes, Base64.NO_WRAP),
            bytes = bytes.size,
        )
    }

    override fun cancel() {
        val active = recorder
        recorder = null
        runCatching { active?.stop() }
        runCatching { active?.release() }
        outputFile?.delete()
        outputFile = null
    }

    private companion object {
        const val MAX_AUDIO_BYTES = 5 * 1024 * 1024
    }
}
