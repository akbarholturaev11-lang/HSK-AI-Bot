package com.pomp.hskai.feature.practice

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.audio.VoiceRecorder
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.DrillMistakeDto
import com.pomp.hskai.data.api.DrillResultDto
import com.pomp.hskai.data.repository.DictionaryRepository
import com.pomp.hskai.data.repository.FeatureRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/** Which drill is running: pick the character, or say it. */
enum class DrillMode(val feature: String) {
    RECOGNITION("recognition"),
    PRONUNCIATION("pronunciation"),
}

data class WordDrillUiState(
    val isLoading: Boolean = true,
    val mode: DrillMode = DrillMode.RECOGNITION,
    val questions: List<DrillQuestion> = emptyList(),
    val index: Int = 0,
    val selected: String? = null,
    val isAnswered: Boolean = false,
    val wasCorrect: Boolean = false,
    val correctCount: Int = 0,
    /** Pronunciation only: recording, scoring, and the score that came back. */
    val isRecording: Boolean = false,
    val isScoring: Boolean = false,
    val spokenScore: Int? = null,
    val finished: Boolean = false,
    /**
     * The free allowance for this section is spent. Not an error: it is the
     * one place that says what reopens it.
     */
    val limitReached: Boolean = false,
    val limitText: String? = null,
    val resetAt: String? = null,
    val error: ApiError? = null,
) {
    val current: DrillQuestion? get() = questions.getOrNull(index)
    val total: Int get() = questions.size
    val progress: Float get() = if (total == 0) 0f else index.toFloat() / total
}

/**
 * The Mini App's adaptive drill: "Ieroglif tanish" and "Talaffuz mashqi".
 *
 * Android used to build these two sections from the generic MCQ engine, which
 * meant the same learner practised a different set of words on each client and
 * only the Mini App's answers moved the review schedule. This asks the same
 * adviser and reports back to the same schedule.
 */
class WordDrillViewModel(
    private val repository: FeatureRepository,
    private val dictionary: DictionaryRepository,
    private val recorder: VoiceRecorder,
    private val mode: DrillMode,
    private val level: String,
    private val language: AppLanguage,
) : ViewModel() {

    private val _state = MutableStateFlow(WordDrillUiState(mode = mode))
    val state: StateFlow<WordDrillUiState> = _state.asStateFlow()

    private val mistakes = mutableListOf<DrillMistakeDto>()
    private val results = mutableListOf<DrillResultDto>()

    init {
        load()
    }

    /** @param accessRef set when an ad has just reopened the section. */
    /** Trial ochilgach limit bloki yo'qoladi va bo'lim qaytadan so'raladi. */
    fun onAccessChanged() {
        if (!_state.value.limitReached) return
        load()
    }

    fun load(accessRef: String = "") {
        _state.value = WordDrillUiState(isLoading = true, mode = mode)
        mistakes.clear()
        results.clear()
        viewModelScope.launch {
            // The Mini App asks this door first, and so must this client: a
            // free learner gets the section once, and an ad reopens it.
            val gate = repository.drillGate(
                feature = mode.feature,
                ref = "drill:${'$'}{System.currentTimeMillis()}",
                accessRef = accessRef,
            )
            if (gate is ApiResult.Failure) {
                val spent = gate.error as? ApiError.LimitReached
                _state.update {
                    it.copy(
                        isLoading = false,
                        limitReached = spent != null,
                        resetAt = spent?.resetAt,
                        limitText = spent?.limitText,
                        error = if (spent != null) null else gate.error,
                    )
                }
                return@launch
            }
            // The dictionary is the client's own material; an empty cache is
            // the only thing that can stop the drill.
            dictionary.sync(language)
            val pool = WordDrill.pool(dictionary.search("", limit = DICTIONARY_POOL_LIMIT))
            if (pool.size < MIN_POOL) {
                _state.update { it.copy(isLoading = false, error = ApiError.Unknown) }
                return@launch
            }
            val targets = when (
                val words = repository.drillWords(mode.feature, WordDrill.QUESTIONS_PER_DRILL)
            ) {
                // A refused adviser is not a dead drill: the dictionary fills in.
                is ApiResult.Failure -> emptyList()
                is ApiResult.Success -> words.value.words
            }
            val questions = WordDrill.build(targets = targets, pool = pool)
            _state.update {
                it.copy(
                    isLoading = false,
                    questions = questions,
                    error = if (questions.isEmpty()) ApiError.Unknown else null,
                )
            }
        }
    }

    fun choose(option: String) {
        val state = _state.value
        val question = state.current ?: return
        if (state.isAnswered || state.mode != DrillMode.RECOGNITION) return
        val correct = question.isCorrect(option)
        record(question.hanzi, correct, selected = option)
        _state.update {
            it.copy(
                selected = option,
                isAnswered = true,
                wasCorrect = correct,
                correctCount = it.correctCount + if (correct) 1 else 0,
            )
        }
    }

    /** Pronunciation: record for the Mini App's window, then ask for a score. */
    fun speak() {
        val state = _state.value
        val question = state.current ?: return
        if (state.mode != DrillMode.PRONUNCIATION) return
        if (state.isAnswered || state.isRecording || state.isScoring) return

        runCatching { recorder.start() }.onFailure {
            _state.update { it.copy(error = ApiError.Unknown) }
            return
        }
        _state.update { it.copy(isRecording = true, error = null) }
        viewModelScope.launch {
            delay(SPEAKING_WINDOW_MILLIS)
            val recording = runCatching { recorder.stop() }.getOrElse {
                _state.update { it.copy(isRecording = false, error = ApiError.Unknown) }
                return@launch
            }
            _state.update { it.copy(isRecording = false, isScoring = true) }
            when (
                val scored = repository.scorePronunciation(
                    target = question.hanzi,
                    targetPinyin = question.pinyin,
                    language = language.backendCode,
                    level = level,
                    audioDataUrl = recording.dataUrl,
                )
            ) {
                is ApiResult.Success -> {
                    val passed = scored.value.ok && scored.value.score >= PASS_SCORE
                    // The mistake itself is written by `score_pronunciation`;
                    // reporting it again here would duplicate the row.
                    results += DrillResultDto(hanzi = question.hanzi, correct = passed)
                    _state.update {
                        it.copy(
                            isScoring = false,
                            isAnswered = true,
                            wasCorrect = passed,
                            spokenScore = scored.value.score,
                            correctCount = it.correctCount + if (passed) 1 else 0,
                        )
                    }
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isScoring = false, error = scored.error)
                }
            }
        }
    }

    /** "I can't speak right now" — the word is passed over, not marked wrong. */
    fun skipSpoken() {
        if (_state.value.mode != DrillMode.PRONUNCIATION) return
        recorder.cancel()
        _state.update { it.copy(isRecording = false, isScoring = false) }
        advance()
    }

    fun advance() {
        val state = _state.value
        val next = state.index + 1
        if (next >= state.total) {
            finish()
            return
        }
        _state.update {
            it.copy(
                index = next,
                selected = null,
                isAnswered = false,
                wasCorrect = false,
                spokenScore = null,
            )
        }
    }

    private fun record(hanzi: String, correct: Boolean, selected: String) {
        results += DrillResultDto(hanzi = hanzi, correct = correct)
        if (!correct) mistakes += DrillMistakeDto(hanzi = hanzi, selected = selected)
    }

    private fun finish() {
        _state.update { it.copy(finished = true) }
        val reportedMistakes = mistakes.toList()
        val reportedResults = results.toList()
        if (reportedMistakes.isEmpty() && reportedResults.isEmpty()) return
        viewModelScope.launch {
            repository.reportDrill(
                feature = mode.feature,
                level = level,
                language = language.backendCode,
                mistakes = reportedMistakes,
                results = reportedResults,
            )
        }
    }

    override fun onCleared() {
        recorder.cancel()
        super.onCleared()
    }

    class Factory(
        private val repository: FeatureRepository,
        private val dictionary: DictionaryRepository,
        private val recorder: VoiceRecorder,
        private val mode: DrillMode,
        private val level: String,
        private val language: AppLanguage,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = WordDrillViewModel(
            repository,
            dictionary,
            recorder,
            mode,
            level,
            language,
        ) as T
    }

    private companion object {
        const val DICTIONARY_POOL_LIMIT = 400
        const val MIN_POOL = 8
        const val SPEAKING_WINDOW_MILLIS = 2_600L
        const val PASS_SCORE = 60
    }
}
