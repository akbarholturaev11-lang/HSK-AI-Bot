package com.pomp.hskai.feature.voice

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.audio.VoiceRecorder
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.VoiceEndResponse
import com.pomp.hskai.data.api.VoiceStatusResponse
import com.pomp.hskai.data.api.VoiceMessageResponse
import com.pomp.hskai.data.api.VoiceSuggestionDto
import com.pomp.hskai.data.api.VoiceWordDto
import com.pomp.hskai.data.repository.FeatureRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

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
    val selectedRole: String = "friend",
    val sessionId: String? = null,
    val remainingLimit: Int = 0,
    val turnCount: Int = 0,
    val maxDialogs: Int = 7,
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
) : ViewModel() {

    private val _state = MutableStateFlow(VoiceUiState())
    val state: StateFlow<VoiceUiState> = _state.asStateFlow()

    init {
        loadStatus()
    }

    override fun onCleared() {
        recorder.cancel()
    }

    fun loadStatus() {
        _state.update { it.copy(isLoading = true, error = null) }
        viewModelScope.launch {
            when (val result = repository.voiceStatus()) {
                is ApiResult.Success -> _state.update {
                    it.copy(
                        isLoading = false,
                        status = result.value,
                        remainingLimit = result.value.remainingVoiceLimit,
                    )
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isLoading = false, error = result.error)
                }
            }
        }
    }

    fun selectRole(role: String) {
        if (_state.value.hasSession) return
        _state.update { it.copy(selectedRole = role) }
    }

    fun startSession(level: String, language: String) {
        if (_state.value.isStarting || _state.value.hasSession) return
        _state.update { it.copy(isStarting = true, error = null, result = null) }
        viewModelScope.launch {
            when (
                val result = repository.voiceStart(
                    role = _state.value.selectedRole,
                    level = level,
                    language = language,
                )
            ) {
                is ApiResult.Success -> {
                    val opening = result.value.openingMessage
                    _state.update {
                        it.copy(
                            isStarting = false,
                            sessionId = result.value.sessionId,
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
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isStarting = false, error = result.error)
                }
            }
        }
    }

    fun toggleRecording() {
        val current = _state.value
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
        viewModelScope.launch {
            _state.update { it.copy(isRecording = false, isSending = true, error = null) }
            val recording = runCatching { recorder.stop() }.getOrElse {
                _state.update { state ->
                    state.copy(isSending = false, error = ApiError.Unknown)
                }
                return@launch
            }
            val sessionId = _state.value.sessionId ?: return@launch
            applyTurn(repository.voiceMessage(sessionId, recording.dataUrl))
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
        recorder.cancel()
        _state.update { it.copy(isRecording = false, isSending = true, error = null) }
        viewModelScope.launch {
            applyTurn(repository.voiceTypedMessage(sessionId, trimmed))
        }
    }

    private fun applyTurn(result: ApiResult<VoiceMessageResponse>) {
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
        val sessionId = _state.value.sessionId ?: return
        if (_state.value.isSending) return
        recorder.cancel()
        _state.update { it.copy(isRecording = false, isSending = true, error = null) }
        viewModelScope.launch {
            when (val result = repository.voiceEnd(sessionId)) {
                is ApiResult.Success -> _state.update {
                    it.copy(
                        isSending = false,
                        result = result.value,
                        sessionId = null,
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
        recorder.cancel()
        _state.update {
            it.copy(
                selectedRole = role,
                sessionId = null,
                isRecording = false,
                lines = emptyList(),
                turnCount = 0,
                result = null,
                error = null,
            )
        }
        viewModelScope.launch {
            if (previousSession != null) repository.voiceEnd(previousSession)
            startSession(level, language)
        }
    }

    fun reset() {
        recorder.cancel()
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
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            VoiceViewModel(repository, recorder) as T
    }
}
