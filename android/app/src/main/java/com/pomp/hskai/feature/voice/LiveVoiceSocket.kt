package com.pomp.hskai.feature.voice

import android.util.Base64
import com.pomp.hskai.BuildConfig
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.VoiceSuggestionDto
import java.io.IOException
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.withTimeout
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import org.json.JSONObject

data class LiveVoiceTurn(
    val transcription: String,
    val chineseReply: String,
    val pinyin: String,
    val translation: String,
    val correction: String?,
    val suggestions: List<VoiceSuggestionDto>,
    val remainingLimit: Int,
    val turnCount: Int,
    val maxDialogs: Int,
    val shouldEnd: Boolean,
)

sealed interface LiveVoiceEvent {
    data class Audio(val pcm: ByteArray) : LiveVoiceEvent
    data class TurnComplete(val turn: LiveVoiceTurn) : LiveVoiceEvent
    data object Interrupted : LiveVoiceEvent
    data class Terminal(val reason: String) : LiveVoiceEvent
    data class Failed(val reason: String) : LiveVoiceEvent
}

interface LiveVoiceConnection {
    val events: kotlinx.coroutines.flow.SharedFlow<LiveVoiceEvent>
    val maxSeconds: Int
    fun sendAudio(pcm: ByteArray)
    fun sendText(text: String)
    fun setMuted(muted: Boolean)
    fun close()
}

interface LiveVoiceGateway {
    suspend fun connect(sessionId: String): LiveVoiceConnection
}

/** Native Android client for the authenticated backend WebSocket relay. */
class AndroidLiveVoiceGateway(
    private val client: OkHttpClient,
    private val accessToken: suspend () -> ApiResult<String>,
    private val onSessionExpired: suspend () -> Unit,
) : LiveVoiceGateway {
    override suspend fun connect(sessionId: String): LiveVoiceConnection {
        val token = when (val result = accessToken()) {
            is ApiResult.Success -> result.value
            is ApiResult.Failure -> {
                if (result.error is ApiError.SessionExpired) onSessionExpired()
                throw IOException("Android session is unavailable")
            }
        }
        val base = requireNotNull(BuildConfig.API_ORIGIN.toHttpUrlOrNull()) {
            "Invalid API origin"
        }
        require(base.scheme == "https") { "Live Voice requires HTTPS" }
        val httpUrl = base.newBuilder()
            .addPathSegments("api/v3/android/voice/live")
            .addQueryParameter("session_id", sessionId)
            .build()
        val url = httpUrl.toString().replaceFirst("https://", "wss://")
        val ready = CompletableDeferred<Unit>()
        val connection = AndroidLiveVoiceConnection(ready)
        val request = Request.Builder()
            .url(url)
            .header("Authorization", "Bearer $token")
            .build()
        connection.attach(client.newWebSocket(request, connection.listener()))
        return try {
            withTimeout(15_000) { ready.await() }
            connection
        } catch (error: Exception) {
            connection.close()
            throw error
        }
    }
}

private class AndroidLiveVoiceConnection(
    private val ready: CompletableDeferred<Unit>,
) : LiveVoiceConnection {
    private val mutableEvents = MutableSharedFlow<LiveVoiceEvent>(replay = 1, extraBufferCapacity = 96)
    override val events = mutableEvents.asSharedFlow()
    @Volatile private var socket: WebSocket? = null
    @Volatile private var muted = false
    @Volatile override var maxSeconds: Int = 180
        private set

    fun attach(value: WebSocket) {
        socket = value
    }

    fun listener() = object : WebSocketListener() {
        override fun onMessage(webSocket: WebSocket, text: String) {
            if (text.length > 256_000) {
                fail("live_message_too_large")
                webSocket.cancel()
                return
            }
            runCatching { JSONObject(text) }
                .onSuccess(::handleMessage)
                .onFailure {
                    fail("live_message_invalid")
                    webSocket.cancel()
                }
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
            val reason = if (!ready.isCompleted) "live_connect_failed" else "live_connection_lost"
            if (!ready.isCompleted) ready.completeExceptionally(IOException(reason, t))
            fail(reason)
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            if (!ready.isCompleted) {
                ready.completeExceptionally(IOException("Live Voice closed"))
            } else {
                fail("live_connection_lost")
            }
        }
    }

    override fun sendAudio(pcm: ByteArray) {
        if (muted || pcm.isEmpty()) return
        val current = socket ?: return
        if (current.queueSize() > MAX_QUEUED_AUDIO_BYTES) {
            fail("live_network_backpressure")
            current.cancel()
            return
        }
        if (!current.send(ByteString.of(*pcm))) fail("live_send_failed")
    }

    override fun sendText(text: String) {
        val value = text.trim().take(200)
        if (value.isEmpty()) return
        val payload = JSONObject().put("type", "text").put("text", value).toString()
        if (socket?.send(payload) != true) fail("live_send_failed")
    }

    override fun setMuted(muted: Boolean) {
        this.muted = muted
    }

    override fun close() {
        socket?.send(JSONObject().put("type", "stop").toString())
        socket?.close(1000, "client stop")
        socket = null
    }

    private fun handleMessage(message: JSONObject) {
        when (val type = message.optString("type")) {
            "ready" -> {
                maxSeconds = message.optInt("max_seconds", 180).coerceIn(1, 180)
                ready.complete(Unit)
            }
            "audio" -> {
                val encoded = message.optString("data")
                val pcm = runCatching { Base64.decode(encoded, Base64.DEFAULT) }.getOrDefault(byteArrayOf())
                if (pcm.isNotEmpty() && !mutableEvents.tryEmit(LiveVoiceEvent.Audio(pcm))) {
                    fail("live_audio_backpressure")
                    socket?.cancel()
                }
            }
            "interrupted" -> mutableEvents.tryEmit(LiveVoiceEvent.Interrupted)
            "turn_complete" -> mutableEvents.tryEmit(LiveVoiceEvent.TurnComplete(message.toTurn()))
            "budget_limit", "time_limit", "session_limit" ->
                mutableEvents.tryEmit(LiveVoiceEvent.Terminal(type))
            "error" -> {
                val code = message.optString("code").ifBlank { "live_voice_unavailable" }
                if (!ready.isCompleted) ready.completeExceptionally(IOException(code))
                fail(code)
            }
            "pong" -> Unit
        }
    }

    private fun JSONObject.toTurn(): LiveVoiceTurn {
        val rawSuggestions = optJSONArray("suggestions")
        val suggestions = buildList {
            if (rawSuggestions != null) {
                for (index in 0 until rawSuggestions.length()) {
                    val item = rawSuggestions.optJSONObject(index) ?: continue
                    add(
                        VoiceSuggestionDto(
                            hanzi = item.optString("zh"),
                            pinyin = item.optString("pinyin"),
                            translation = item.optString("translation"),
                        ),
                    )
                }
            }
        }
        return LiveVoiceTurn(
            transcription = optString("transcription"),
            chineseReply = optString("chinese_reply"),
            pinyin = optString("pinyin"),
            translation = optString("translation"),
            correction = optString("correction").takeIf { it.isNotBlank() && it != "null" },
            suggestions = suggestions,
            remainingLimit = optInt("remaining_limit"),
            turnCount = optInt("turn_count"),
            maxDialogs = optInt("max_dialogs", 7),
            shouldEnd = optBoolean("session_should_end"),
        )
    }

    private fun fail(reason: String) {
        mutableEvents.tryEmit(LiveVoiceEvent.Failed(reason))
    }

    private companion object {
        const val MAX_QUEUED_AUDIO_BYTES = 64_000L
    }
}
