package com.pomp.hskai.core.audio

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import android.media.audiofx.AcousticEchoCanceler
import androidx.core.content.ContextCompat
import java.lang.SecurityException
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicLong

interface LiveVoiceAudioEngine {
    fun start(onPcmChunk: (ByteArray) -> Unit)
    fun setMuted(muted: Boolean)
    fun playPcm(pcm: ByteArray): Boolean
    fun clearPlayback()
    fun stop()
}

/** Full-duplex 16 kHz capture and 24 kHz streamed playback for the Live API. */
class AndroidLiveVoiceAudioEngine(context: Context) : LiveVoiceAudioEngine {
    private val appContext = context.applicationContext
    private val audioManager = appContext.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    private val running = AtomicBoolean(false)
    @Volatile private var playbackBuffer = LiveVoicePlaybackBuffer()
    private val audioGeneration = AtomicLong(0)
    @Volatile private var muted = false
    @Volatile private var recorder: AudioRecord? = null
    @Volatile private var player: AudioTrack? = null
    @Volatile private var captureThread: Thread? = null
    @Volatile private var playbackThread: Thread? = null
    @Volatile private var echoCanceler: AcousticEchoCanceler? = null
    private var oldAudioMode: Int = AudioManager.MODE_NORMAL
    private var oldSpeakerphoneOn: Boolean = false
    private var focusRequest: AudioFocusRequest? = null

    @Synchronized
    override fun start(onPcmChunk: (ByteArray) -> Unit) {
        if (!running.compareAndSet(false, true)) return
        val generation = audioGeneration.incrementAndGet()
        try {
            // Each transport owns its queue; a stopped worker cannot take
            // the replacement connection's first PCM chunk.
            val outputBuffer = LiveVoicePlaybackBuffer()
            playbackBuffer = outputBuffer
            if (
                ContextCompat.checkSelfPermission(
                    appContext,
                    Manifest.permission.RECORD_AUDIO,
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                throw SecurityException("RECORD_AUDIO permission is required")
            }
            oldAudioMode = audioManager.mode
            oldSpeakerphoneOn = audioManager.isSpeakerphoneOn
            audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
            audioManager.isSpeakerphoneOn = true
            requestAudioFocus()
            val recordMin = AudioRecord.getMinBufferSize(
                INPUT_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
            )
            val playMin = AudioTrack.getMinBufferSize(
                OUTPUT_RATE,
                AudioFormat.CHANNEL_OUT_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
            )
            check(recordMin > 0 && playMin > 0) { "Device audio format is unavailable" }

            val nextRecorder = AudioRecord(
                MediaRecorder.AudioSource.VOICE_COMMUNICATION,
                INPUT_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                maxOf(recordMin * 2, INPUT_CHUNK_BYTES * 4),
            )
            check(nextRecorder.state == AudioRecord.STATE_INITIALIZED) {
                "Microphone could not be initialized"
            }
            recorder = nextRecorder
            echoCanceler = if (AcousticEchoCanceler.isAvailable()) {
                AcousticEchoCanceler.create(nextRecorder.audioSessionId)?.apply {
                    enabled = true
                }
            } else {
                null
            }

            val attributes = AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                .build()
            val format = AudioFormat.Builder()
                .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                .setSampleRate(OUTPUT_RATE)
                .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                .build()
            val nextPlayer = AudioTrack.Builder()
                .setAudioAttributes(attributes)
                .setAudioFormat(format)
                .setBufferSizeInBytes(maxOf(playMin * 2, OUTPUT_CHUNK_BYTES * 8))
                .setTransferMode(AudioTrack.MODE_STREAM)
                .setPerformanceMode(AudioTrack.PERFORMANCE_MODE_LOW_LATENCY)
                .build()
            check(nextPlayer.state == AudioTrack.STATE_INITIALIZED) {
                "Speaker could not be initialized"
            }
            player = nextPlayer
            nextPlayer.play()
            playbackThread = Thread({ playbackLoop(outputBuffer, generation) }, "hsk-live-voice-playback").apply {
                isDaemon = true
                start()
            }
            nextRecorder.startRecording()
            captureThread = Thread({ captureLoop(nextRecorder, generation, onPcmChunk) }, "hsk-live-voice-capture").apply {
                isDaemon = true
                start()
            }
        } catch (error: Throwable) {
            stop()
            throw error
        }
    }

    override fun setMuted(muted: Boolean) {
        this.muted = muted
    }

    override fun playPcm(pcm: ByteArray): Boolean {
        if (pcm.isEmpty() || !running.get()) return true
        return playbackBuffer.offer(pcm)
    }

    override fun clearPlayback() {
        playbackBuffer.clear()
        player?.let { output ->
            runCatching {
                output.pause()
                output.flush()
                output.play()
            }
        }
    }

    @Synchronized
    override fun stop() {
        running.set(false)
        audioGeneration.incrementAndGet()
        recorder?.let { input ->
            runCatching { input.stop() }
            runCatching { input.release() }
        }
        recorder = null
        captureThread?.interrupt()
        captureThread = null
        playbackBuffer.clear()
        playbackThread?.interrupt()
        playbackThread = null
        player?.let { output ->
            runCatching { output.pause() }
            runCatching { output.flush() }
            runCatching { output.stop() }
            runCatching { output.release() }
        }
        player = null
        echoCanceler?.let { runCatching { it.release() } }
        echoCanceler = null
        focusRequest?.let { audioManager.abandonAudioFocusRequest(it) }
        focusRequest = null
        runCatching { audioManager.isSpeakerphoneOn = oldSpeakerphoneOn }
        runCatching { audioManager.mode = oldAudioMode }
        muted = false
    }

    private fun captureLoop(input: AudioRecord, generation: Long, onPcmChunk: (ByteArray) -> Unit) {
        val buffer = ByteArray(INPUT_CHUNK_BYTES)
        var mutedSilenceFrames = 0
        while (running.get() && generation == audioGeneration.get()) {
            val count = runCatching {
                input.read(buffer, 0, buffer.size, AudioRecord.READ_BLOCKING)
            }.getOrElse { return }
            if (count <= 0 || generation != audioGeneration.get()) return
            when {
                !muted -> {
                    mutedSilenceFrames = 0
                    onPcmChunk(buffer.copyOf(count))
                }
                mutedSilenceFrames < MUTE_TRAILING_FRAMES -> {
                    mutedSilenceFrames++
                    onPcmChunk(ByteArray(count))
                }
            }
        }
    }

    private fun requestAudioFocus() {
        val attributes = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
            .build()
        val request = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
            .setAudioAttributes(attributes)
            .setOnAudioFocusChangeListener { change ->
                when (change) {
                    AudioManager.AUDIOFOCUS_GAIN -> runCatching { player?.setVolume(1f) }
                    // A notification may duck speech; it must not erase the reply.
                    AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK -> runCatching { player?.setVolume(0.25f) }
                    AudioManager.AUDIOFOCUS_LOSS, AudioManager.AUDIOFOCUS_LOSS_TRANSIENT -> clearPlayback()
                }
            }
            .build()
        focusRequest = request
        audioManager.requestAudioFocus(request)
    }

    private fun playbackLoop(buffer: LiveVoicePlaybackBuffer, generation: Long) {
        while (running.get() && generation == audioGeneration.get()) {
            val chunk = try {
                buffer.take()
            } catch (_: InterruptedException) {
                return
            }
            if (generation != audioGeneration.get()) return
            if (!buffer.isCurrent(chunk)) continue

            val output = player ?: return
            var offset = 0
            while (offset < chunk.pcm.size && running.get() && generation == audioGeneration.get()) {
                if (!buffer.isCurrent(chunk)) break
                val count = minOf(OUTPUT_CHUNK_BYTES, chunk.pcm.size - offset)
                val written = runCatching {
                    output.write(chunk.pcm, offset, count, AudioTrack.WRITE_BLOCKING)
                }.getOrElse { return }
                if (written <= 0) break
                offset += written
            }
        }
    }

    private companion object {
        const val INPUT_RATE = 16_000
        const val OUTPUT_RATE = 24_000
        const val INPUT_CHUNK_BYTES = 640 // 20 ms mono PCM16 at 16 kHz
        const val OUTPUT_CHUNK_BYTES = 960 // 20 ms mono PCM16 at 24 kHz
        const val MUTE_TRAILING_FRAMES = 40 // Send 800 ms of silence to close VAD.
    }
}
