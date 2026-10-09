package com.pomp.hskai.feature.voice

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.R
import com.pomp.hskai.core.audio.LiveVoiceAudioEngine
import com.pomp.hskai.core.audio.LessonAudioPlayer
import com.pomp.hskai.core.audio.VoiceRecorder
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.VoiceEndResponse
import com.pomp.hskai.data.api.VoiceStatusResponse
import com.pomp.hskai.data.api.VoiceMessageResponse
import com.pomp.hskai.data.api.VoiceSuggestionDto
import com.pomp.hskai.data.api.VoiceWordDto
import com.pomp.hskai.data.repository.CourseRepository
import com.pomp.hskai.data.repository.FeatureRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class VoiceRoleSpec(
    val id: String,
    val titleRes: Int,
    val bodyRes: Int,
    val glyph: String,
)

data class VoiceLine(
    val speaker: VoiceSpeaker,
    val text: String,
    val hanzi: String = "",
    val pinyin: String = "",
    val translation: String = "",
    val correction: String? = null,
)

enum class VoiceSpeaker { USER, AI }

data class VoiceUiState(
    val status: VoiceStatusResponse? = null,
    val isLoading: Boolean = true,
    val isStarting: Boolean = false,
    val isRecording: Boolean = false,
    val isSending: Boolean = false,
    val isLive: Boolean = false,
    val isLiveConnecting: Boolean = false,
    val isLiveConnected: Boolean = false,
    val isLiveMuted: Boolean = false,
    val liveSecondsRemaining: Int? = null,
    val isAiSpeaking: Boolean = false,
    val usedTurnFallback: Boolean = false,
    val selectedRole: String = "friend",
    val sessionId: String? = null,
    val remainingLimit: Int = 0,
    val turnCount: Int = 0,
    val maxDialogs: Int = 0,
    val lines: List<VoiceLine> = emptyList(),
    val result: VoiceEndResponse? = null,
    val error: ApiError? = null,
    /**
     * Material for the Mini App's "Nima deyish?" sheet: the words of the
     * lesson this conversation is built on, the words due for review, and the
     * phrases the AI itself proposed for this turn.
     */
    val lessonWords: List<VoiceWordDto> = emptyList(),
    val reviewWords: List<VoiceWordDto> = emptyList(),
    val suggestions: List<VoiceSuggestionDto> = emptyList(),
) {
    val hasSession: Boolean get() = sessionId != null && result == null

    /** True while the learner may answer — the mic and the keyboard agree. */
    val canAnswer: Boolean get() = hasSession && !isSending && !isStarting
}

class VoiceViewModel(
    private val repository: FeatureRepository,
    private val recorder: VoiceRecorder,
    /** Speaks the partner's replies; a silent voice practice is not one. */
    private val courseRepository: CourseRepository? = null,
    private val audioPlayer: LessonAudioPlayer? = null,
    private val liveVoiceGateway: LiveVoiceGateway? = null,
    private val liveVoiceAudioEngine: LiveVoiceAudioEngine? = null,
    private val liveIoDispatcher: CoroutineDispatcher = Dispatchers.IO,
) : ViewModel() {

    private var speakJob: Job? = null
    private var liveEventsJob: Job? = null
    private var liveTimerJob: Job? = null
    private var liveConnectJob: Job? = null
    private var liveReconnectJob: Job? = null
    private var liveConnection: LiveVoiceConnection? = null
    private val liveAudioLifecycleLock = Any()
    @Volatile private var liveGeneration = 0L
    private var lastLiveLevel = "hsk1"
    private var lastLiveLanguage = "uz"
    private var liveReconnectAttempts = 0
    private var fallbackNoticePending = false
    private var slowSpeech: Boolean = false
    private var courseLevel: String? = null
    private var courseGeneration = 0L
    private var sessionGeneration = 0L
    private var endingGeneration: Long? = null

    /** Follows the learner's "slow speech" setting for the next reply. */
    fun setSlowSpeech(slow: Boolean) {
        slowSpeech = slow
    }

    /**
     * Reads one Chinese reply aloud.
     *
     * The Mini App's panda speaks every turn — hearing the answer is most of
     * the exercise. A failure here is silent on purpose: a missing voice must
     * not interrupt the conversation.
     */
    private fun speak(text: String) {
        val phrase = text.trim()
        if (phrase.isEmpty()) return
        val course = courseRepository ?: return
        val player = audioPlayer ?: return
        val generation = sessionGeneration
        speakJob?.cancel()
        speakJob = viewModelScope.launch {
            when (val audio = course.ttsAudio(phrase)) {
                is ApiResult.Success -> runCatching {
                    if (generation == sessionGeneration) {
                        player.play(audio.value, if (slowSpeech) SLOW_SPEECH_RATE else 1f)
                    }
                }

                is ApiResult.Failure -> Unit
            }
        }
    }

    private val _state = MutableStateFlow(VoiceUiState())
    val state: StateFlow<VoiceUiState> = _state.asStateFlow()
    private var statusLoaded = false
    private var statusLoadInFlight = false

    /** First Voice-tab entry owns the initial status request, not app startup. */
    fun ensureStatusLoaded() {
        if (!statusLoadInFlight && (!statusLoaded || (!_state.value.hasSession && _state.value.error != null))) {
            loadStatus()
        }
    }

    /** Access changes refresh Voice only after Voice has actually been opened. */
    fun refreshStatusIfLoaded() {
        if (statusLoaded || statusLoadInFlight) {
            courseGeneration++
            statusLoadInFlight = false
            loadStatus()
        }
    }

    /** A confirmed course change cannot keep a conversation from the old level. */
    fun onCourseChanged(level: String) {
        val previousLevel = courseLevel
        courseLevel = level
        if (previousLevel == null || previousLevel == level) return
        val current = _state.value
        val refreshStatus = statusLoaded || statusLoadInFlight
        courseGeneration++
        statusLoadInFlight = false
        invalidateSession()
        lastLiveLevel = level
        _state.value = VoiceUiState(
            status = current.status,
            isLoading = !statusLoaded,
            selectedRole = current.selectedRole,
            remainingLimit = current.status?.remainingVoiceLimit ?: 0,
        )
        current.sessionId?.let(::closeAbandonedSession)
        if (refreshStatus) loadStatus()
    }

    private fun invalidateSession() {
        sessionGeneration++
        endingGeneration = null
        speakJob?.cancel()
        speakJob = null
        audioPlayer?.release()
        recorder.cancel()
        disconnectLiveTransport()
        fallbackNoticePending = false
        liveReconnectAttempts = 0
    }

    private fun closeAbandonedSession(sessionId: String) {
        viewModelScope.launch { repository.voiceEnd(sessionId) }
    }

    private fun ownsSession(generation: Long, sessionId: String): Boolean =
        generation == sessionGeneration && _state.value.sessionId == sessionId

    override fun onCleared() {
        courseGeneration++
        invalidateSession()
    }

    fun loadStatus() {
        if (statusLoadInFlight) return
        val generation = courseGeneration
        statusLoadInFlight = true
        _state.update { it.copy(isLoading = true, error = null) }
        viewModelScope.launch {
            try {
            when (val result = repository.voiceStatus()) {
                is ApiResult.Success -> {
                    if (generation != courseGeneration) return@launch
                    statusLoaded = true
                    _state.update {
                        it.copy(
                            isLoading = false,
                            status = result.value,
                            remainingLimit = result.value.remainingVoiceLimit,
                        )
                    }
                }

                is ApiResult.Failure -> if (generation == courseGeneration) _state.update {
                    it.copy(isLoading = false, error = result.error)
                }
            }
            } finally {
                if (generation == courseGeneration) statusLoadInFlight = false
            }
        }
    }

    fun selectRole(role: String) {
        if (_state.value.hasSession) return
        _state.update { it.copy(selectedRole = role) }
    }

    fun startSession(level: String, language: String, preferLive: Boolean = true) {
        if (_state.value.isStarting || _state.value.hasSession) return
        if (courseLevel != null && courseLevel != level) return
        if (courseLevel == null) courseLevel = level
        val generation = ++sessionGeneration
        val role = _state.value.selectedRole
        lastLiveLevel = level
        lastLiveLanguage = language
        liveReconnectAttempts = 0
        val mode = if (preferLive && _state.value.status?.liveAvailable == true) "live" else "turn"
        _state.update { it.copy(isStarting = true, error = null, result = null) }
        viewModelScope.launch {
            when (
                val result = repository.voiceStart(
                    role = role,
                    level = level,
                    language = language,
                    mode = mode,
                )
            ) {
                is ApiResult.Success -> {
                    if (generation != sessionGeneration) {
                        closeAbandonedSession(result.value.sessionId)
                        return@launch
                    }
                    val opening = result.value.openingMessage
                    _state.update {
                        it.copy(
                            isStarting = false,
                            sessionId = result.value.sessionId,
                            isLive = result.value.mode == "live",
                            isLiveConnecting = result.value.mode == "live",
                            isLiveConnected = false,
                            isLiveMuted = false,
                            isAiSpeaking = false,
                            usedTurnFallback = fallbackNoticePending,
                            remainingLimit = result.value.remainingLimit,
                            maxDialogs = result.value.maxDialogs,
                            turnCount = 0,
                            lessonWords = result.value.courseContext.words,
                            reviewWords = result.value.courseContext.reviewWords,
                            suggestions = opening.suggestions,
                            lines = listOf(
                                VoiceLine(
                                    speaker = VoiceSpeaker.AI,
                                    text = opening.translation,
                                    hanzi = opening.chineseReply,
                                    pinyin = opening.pinyin,
                                    translation = opening.translation,
                                    correction = opening.correction,
                                )
                            ),
                        )
                    }
                    if (result.value.mode == "live") {
                        connectLiveSession(result.value.sessionId)
                    } else {
                        fallbackNoticePending = false
                        speak(opening.chineseReply)
                    }
                }

                is ApiResult.Failure -> {
                    if (generation != sessionGeneration) return@launch
                    if (mode == "live") {
                        fallbackNoticePending = true
                        _state.update { it.copy(isStarting = false, error = null) }
                        startSession(level, language, preferLive = false)
                    } else {
                        fallbackNoticePending = false
                        _state.update { it.copy(isStarting = false, error = result.error) }
                    }
                }
            }
        }
    }

    fun toggleRecording() {
        val current = _state.value
        if (current.isLive) {
            toggleLiveMute(current)
            return
        }
        if (!current.hasSession || current.isSending) return
        if (!current.isRecording) {
            runCatching { recorder.start() }.fold(
                onSuccess = {
                    _state.update { it.copy(isRecording = true, error = null) }
                },
                onFailure = {
                    _state.update { it.copy(error = ApiError.Unknown) }
                },
            )
            return
        }
        val sessionId = current.sessionId ?: return
        val generation = sessionGeneration
        viewModelScope.launch {
            if (!ownsSession(generation, sessionId)) return@launch
            _state.update { it.copy(isRecording = false, isSending = true, error = null) }
            val recording = runCatching { recorder.stop() }.getOrElse {
                if (!ownsSession(generation, sessionId)) return@launch
                _state.update { state ->
                    state.copy(isSending = false, error = ApiError.Unknown)
                }
                return@launch
            }
            if (!ownsSession(generation, sessionId)) return@launch
            applyTurn(repository.voiceMessage(sessionId, recording.dataUrl), generation, sessionId)
        }
    }

    /**
     * A typed turn, from the keyboard beside the microphone.
     *
     * It costs a dialogue turn exactly as speaking does — the limit is about
     * the conversation, not about how the answer was produced.
     */
    fun sendTypedMessage(text: String) {
        val trimmed = text.trim()
        val current = _state.value
        if (trimmed.isEmpty() || !current.canAnswer) return
        val sessionId = current.sessionId ?: return
        val generation = sessionGeneration
        if (current.isLive) {
            val connection = liveConnection ?: return
            connection.setMuted(true)
            liveVoiceAudioEngine?.setMuted(true)
            connection.sendText(trimmed)
            _state.update { it.copy(isSending = true, isLiveMuted = true, isRecording = false, error = null) }
            return
        }
        recorder.cancel()
        _state.update { it.copy(isRecording = false, isSending = true, error = null) }
        viewModelScope.launch {
            if (!ownsSession(generation, sessionId)) return@launch
            applyTurn(repository.voiceTypedMessage(sessionId, trimmed), generation, sessionId)
        }
    }

    private fun connectLiveSession(sessionId: String, allowTurnFallback: Boolean = true) {
        if (!_state.value.isLive || _state.value.sessionId != sessionId || liveConnectJob?.isActive == true) return
        val gateway = liveVoiceGateway
        val audioEngine = liveVoiceAudioEngine
        if (gateway == null || audioEngine == null) {
            fallbackToTurnBased(sessionId)
            return
        }
        val generation = ++liveGeneration
        liveConnectJob = viewModelScope.launch {
            try {
                val connection = gateway.connect(sessionId)
                if (generation != liveGeneration || _state.value.sessionId != sessionId) {
                    connection.close()
                    return@launch
                }
                liveConnection = connection
                startLiveTimer(connection.maxSeconds)
                liveEventsJob?.cancel()
                liveEventsJob = launch {
                    connection.events.collect { event ->
                        if (liveConnection === connection && generation == liveGeneration) handleLiveEvent(event)
                    }
                }
                withContext(liveIoDispatcher) {
                    synchronized(liveAudioLifecycleLock) {
                        if (generation == liveGeneration) {
                            audioEngine.start { chunk ->
                                if (generation == liveGeneration) connection.sendAudio(chunk)
                            }
                        }
                    }
                }
                if (generation != liveGeneration || _state.value.sessionId != sessionId) return@launch
                connection.setMuted(false)
                audioEngine.setMuted(false)
                _state.update {
                    it.copy(
                        isLiveConnecting = false,
                        isLiveConnected = true,
                        isLiveMuted = false,
                        isRecording = true,
                    )
                }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Exception) {
                if (generation == liveGeneration) {
                    recoverLiveConnection(error.message ?: "live_connect_failed", allowTurnFallback)
                }
            } finally {
                if (generation == liveGeneration) liveConnectJob = null
            }
        }
    }

    private fun disconnectLiveTransport(keepTimer: Boolean = false) {
        liveGeneration++
        liveConnectJob?.cancel()
        liveConnectJob = null
        liveReconnectJob?.cancel()
        liveReconnectJob = null
        liveEventsJob?.cancel()
        liveEventsJob = null
        val connection = liveConnection
        liveConnection = null
        connection?.close()
        synchronized(liveAudioLifecycleLock) { liveVoiceAudioEngine?.stop() }
        if (!keepTimer) {
            liveTimerJob?.cancel()
            liveTimerJob = null
        }
    }

    private fun recoverLiveConnection(reason: String, allowTurnFallback: Boolean = true) {
        val current = _state.value
        if (!current.isLive || !current.hasSession) return
        val sessionId = current.sessionId ?: return
        disconnectLiveTransport(keepTimer = true)
        _state.update {
            it.copy(isRecording = false, isLiveConnected = false, isAiSpeaking = false, isSending = false)
        }
        if (reason in LIVE_TERMINAL_REASONS) {
            endSession()
            return
        }
        if (liveReconnectAttempts < MAX_LIVE_RECONNECTS) {
            liveReconnectAttempts++
            val generation = liveGeneration
            val retryDelay = LIVE_RECONNECT_DELAY_MS * liveReconnectAttempts
            _state.update { it.copy(isLiveConnecting = true, error = null) }
            liveReconnectJob = viewModelScope.launch {
                delay(retryDelay)
                if (generation == liveGeneration && _state.value.sessionId == sessionId && _state.value.isLive) {
                    liveReconnectJob = null
                    connectLiveSession(sessionId, allowTurnFallback)
                }
            }
        } else if (allowTurnFallback && current.turnCount == 0) {
            disconnectLiveTransport()
            fallbackToTurnBased(sessionId)
        } else {
            liveTimerJob?.cancel()
            liveTimerJob = null
            val error = ApiError.fromCode(reason).takeUnless { it == ApiError.Unknown }
                ?: ApiError.Server(reason, R.string.error_voice_unavailable)
            _state.update { it.copy(isLiveConnecting = false, error = error) }
        }
    }

    private fun fallbackToTurnBased(liveSessionId: String) {
        val generation = ++sessionGeneration
        val role = _state.value.selectedRole
        val level = lastLiveLevel
        val language = lastLiveLanguage
        disconnectLiveTransport()
        _state.update {
            it.copy(
                isLive = false,
                isLiveConnecting = false,
                isLiveConnected = false,
                isRecording = false,
                isLiveMuted = false,
                liveSecondsRemaining = null,
                isAiSpeaking = false,
                isStarting = true,
            )
        }
        viewModelScope.launch {
            repository.voiceEnd(liveSessionId)
            if (!ownsSession(generation, liveSessionId)) return@launch
            when (
                val fallback = repository.voiceStart(
                    role = role,
                    level = level,
                    language = language,
                    mode = "turn",
                )
            ) {
                is ApiResult.Success -> {
                    if (!ownsSession(generation, liveSessionId)) {
                        closeAbandonedSession(fallback.value.sessionId)
                        return@launch
                    }
                    val response = fallback.value
                    val opening = response.openingMessage
                    _state.update {
                        it.copy(
                            isStarting = false,
                            isLive = false,
                            isLiveConnecting = false,
                            isLiveConnected = false,
                            isRecording = false,
                            isSending = false,
                            sessionId = response.sessionId,
                            turnCount = 0,
                            maxDialogs = response.maxDialogs,
                            lessonWords = response.courseContext.words,
                            reviewWords = response.courseContext.reviewWords,
                            suggestions = opening.suggestions,
                            usedTurnFallback = true,
                            lines = listOf(
                                VoiceLine(
                                    speaker = VoiceSpeaker.AI,
                                    text = opening.translation,
                                    hanzi = opening.chineseReply,
                                    pinyin = opening.pinyin,
                                    translation = opening.translation,
                                ),
                            ),
                        )
                    }
                    speak(opening.chineseReply)
                }
                is ApiResult.Failure -> if (ownsSession(generation, liveSessionId)) _state.update {
                    it.copy(isStarting = false, sessionId = null, error = fallback.error)
                }
            }
        }
    }

    private fun toggleLiveMute(current: VoiceUiState) {
        if (current.isLiveConnecting) return
        if (!current.isLiveConnected) {
            current.sessionId?.let { connectLiveSession(it, allowTurnFallback = current.turnCount == 0) }
            return
        }
        val muted = !current.isLiveMuted
        liveConnection?.setMuted(muted)
        liveVoiceAudioEngine?.setMuted(muted)
        _state.update {
            it.copy(
                isLiveMuted = muted,
                isRecording = !muted,
                error = null,
            )
        }
    }

    private fun startLiveTimer(seconds: Int) {
        liveTimerJob?.cancel()
        liveTimerJob = viewModelScope.launch {
            var remaining = seconds.coerceAtLeast(0)
            _state.update { it.copy(liveSecondsRemaining = remaining) }
            while (remaining > 0) {
                delay(1_000)
                remaining = (remaining - 1).coerceAtLeast(0)
                _state.update { it.copy(liveSecondsRemaining = remaining) }
            }
        }
    }

    private suspend fun handleLiveEvent(event: LiveVoiceEvent) {
        val generation = liveGeneration
        when (event) {
            is LiveVoiceEvent.Audio -> {
                _state.update { it.copy(isAiSpeaking = true) }
                val engine = liveVoiceAudioEngine
                if (engine != null) {
                    val queued = withContext(liveIoDispatcher) {
                        synchronized(liveAudioLifecycleLock) {
                            if (generation == liveGeneration) engine.playPcm(event.pcm) else true
                        }
                    }
                    if (generation != liveGeneration) return
                    if (!queued) {
                        handleLiveEvent(LiveVoiceEvent.Failed("live_playback_backpressure"))
                    }
                }
            }
            LiveVoiceEvent.Interrupted -> {
                liveVoiceAudioEngine?.let { engine ->
                    withContext(liveIoDispatcher) {
                        synchronized(liveAudioLifecycleLock) {
                            if (generation == liveGeneration) engine.clearPlayback()
                        }
                    }
                }
                if (generation != liveGeneration) return
                _state.update { it.copy(isAiSpeaking = false) }
            }
            is LiveVoiceEvent.TurnComplete -> {
                val turn = event.turn
                liveReconnectAttempts = 0
                liveConnection?.setMuted(false)
                liveVoiceAudioEngine?.setMuted(false)
                _state.update {
                    it.copy(
                        isSending = false,
                        isRecording = true,
                        isLiveMuted = false,
                        isAiSpeaking = false,
                        turnCount = turn.turnCount,
                        maxDialogs = turn.maxDialogs,
                        remainingLimit = turn.remainingLimit,
                        suggestions = turn.suggestions.ifEmpty { it.suggestions },
                        lines = it.lines + listOf(
                            VoiceLine(speaker = VoiceSpeaker.USER, text = turn.transcription),
                            VoiceLine(
                                speaker = VoiceSpeaker.AI,
                                text = turn.translation.ifBlank { turn.chineseReply },
                                hanzi = turn.chineseReply,
                                pinyin = turn.pinyin,
                                translation = turn.translation,
                                correction = turn.correction,
                            ),
                        ),
                    )
                }
                if (turn.shouldEnd) endSession()
            }
            is LiveVoiceEvent.Terminal -> {
                when (event.reason) {
                    "session_limit" -> endSession()
                    "budget_limit", "time_limit" -> {
                        disconnectLiveTransport()
                        _state.update {
                            it.copy(
                                isRecording = false,
                                isLiveConnected = false,
                                isLiveConnecting = false,
                                isAiSpeaking = false,
                                isSending = false,
                            )
                        }
                        endSession()
                    }
                }
            }
            is LiveVoiceEvent.Failed -> {
                recoverLiveConnection(event.reason, allowTurnFallback = _state.value.turnCount == 0)
            }
        }
    }

    private fun applyTurn(result: ApiResult<VoiceMessageResponse>, generation: Long, sessionId: String) {
        if (!ownsSession(generation, sessionId)) return
        when (result) {
            is ApiResult.Success -> {
                val response = result.value
                _state.update {
                    it.copy(
                        isSending = false,
                        turnCount = response.turnCount,
                        maxDialogs = response.maxDialogs,
                        remainingLimit = response.remainingLimit,
                        // Fresh phrases arrive with every reply; an empty list
                        // keeps the previous ones rather than emptying the
                        // sheet mid-conversation.
                        suggestions = response.suggestions.ifEmpty { it.suggestions },
                        lines = it.lines + listOf(
                            VoiceLine(
                                speaker = VoiceSpeaker.USER,
                                text = response.transcription,
                            ),
                            VoiceLine(
                                speaker = VoiceSpeaker.AI,
                                text = response.translation,
                                hanzi = response.chineseReply,
                                pinyin = response.pinyin,
                                translation = response.translation,
                                correction = response.correction,
                            ),
                        ),
                    )
                }
                speak(response.chineseReply)
                if (response.sessionShouldEnd) {
                    endSession()
                }
            }

            is ApiResult.Failure -> _state.update {
                it.copy(isSending = false, error = result.error)
            }
        }
    }

    fun endSession() {
        if (endingGeneration == sessionGeneration) return
        val sessionId = _state.value.sessionId
        invalidateSession()
        if (sessionId == null) {
            _state.update { it.copy(isStarting = false, isSending = false, isRecording = false) }
            return
        }
        val generation = sessionGeneration
        endingGeneration = generation
        _state.update {
            it.copy(
                isStarting = false,
                isRecording = false,
                isLiveConnecting = false,
                isLiveConnected = false,
                isAiSpeaking = false,
                isSending = true,
                error = null,
            )
        }
        viewModelScope.launch {
            val result = repository.voiceEnd(sessionId)
            if (!ownsSession(generation, sessionId)) return@launch
            endingGeneration = null
            when (result) {
                is ApiResult.Success -> _state.update {
                    it.copy(
                        isSending = false,
                        result = result.value,
                        sessionId = null,
                        isLive = false,
                        isLiveConnecting = false,
                        isLiveConnected = false,
                        isLiveMuted = false,
                        liveSecondsRemaining = null,
                        isAiSpeaking = false,
                    )
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isSending = false, error = result.error)
                }
            }
        }
    }

    /**
     * Mini App `VOICE.swap()`: the partner defines the whole dialogue, so
     * changing it closes the current conversation on the server and opens a
     * fresh one instead of continuing with a different voice mid-way.
     */
    fun swapPartner(role: String, level: String, language: String) {
        if (_state.value.isSending || _state.value.isStarting) return
        val previousSession = _state.value.sessionId
        invalidateSession()
        val generation = sessionGeneration
        _state.update {
            it.copy(
                selectedRole = role,
                sessionId = null,
                isRecording = false,
                isLive = false,
                isLiveConnecting = false,
                isLiveConnected = false,
                isLiveMuted = false,
                liveSecondsRemaining = null,
                isAiSpeaking = false,
                lines = emptyList(),
                turnCount = 0,
                result = null,
                error = null,
            )
        }
        viewModelScope.launch {
            if (previousSession != null) repository.voiceEnd(previousSession)
            if (generation == sessionGeneration) startSession(level, language)
        }
    }

    fun reset() {
        courseGeneration++
        statusLoadInFlight = false
        invalidateSession()
        _state.update {
            VoiceUiState(
                status = it.status,
                isLoading = false,
                selectedRole = it.selectedRole,
                remainingLimit = it.status?.remainingVoiceLimit ?: 0,
            )
        }
        loadStatus()
    }

    class Factory(
        private val repository: FeatureRepository,
        private val recorder: VoiceRecorder,
        private val courseRepository: CourseRepository? = null,
        private val audioPlayer: LessonAudioPlayer? = null,
        private val liveVoiceGateway: LiveVoiceGateway? = null,
        private val liveVoiceAudioEngine: LiveVoiceAudioEngine? = null,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            VoiceViewModel(
                repository,
                recorder,
                courseRepository,
                audioPlayer,
                liveVoiceGateway,
                liveVoiceAudioEngine,
            ) as T
    }

    private companion object {
        /** The Mini App's `playbackRate` for slow speech. */
        const val SLOW_SPEECH_RATE = 0.75f
        const val MAX_LIVE_RECONNECTS = 3
        const val LIVE_RECONNECT_DELAY_MS = 1_200L
        val LIVE_TERMINAL_REASONS = setOf(
            "budget_limit", "time_limit", "live_session_expired", "LIMIT_EXCEEDED",
            "SESSION_EXPIRED", "SESSION_ENDED", "SESSION_NOT_FOUND",
        )
    }
}
