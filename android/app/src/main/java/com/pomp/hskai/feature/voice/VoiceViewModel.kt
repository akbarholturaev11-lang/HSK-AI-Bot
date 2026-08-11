package com.pomp.hskai.feature.voice

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.audio.VoiceRecorder
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.VoiceEndResponse
import com.pomp.hskai.data.api.VoiceStatusResponse
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
) {
    val hasSession: Boolean get() = sessionId != null && result == null
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
            when (val result = repository.voiceMessage(sessionId, recording.dataUrl)) {
                is ApiResult.Success -> {
                    val response = result.value
                    _state.update {
                        it.copy(
                            isSending = false,
                            turnCount = response.turnCount,
                            maxDialogs = response.maxDialogs,
                            remainingLimit = response.remainingLimit,
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
