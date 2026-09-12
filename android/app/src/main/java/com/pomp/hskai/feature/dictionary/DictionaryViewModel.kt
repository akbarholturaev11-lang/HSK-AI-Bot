package com.pomp.hskai.feature.dictionary

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.repository.DictionaryRepository
import com.pomp.hskai.data.repository.DictionaryWord
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * Detail-screen actions are carried with the state so the old four-argument
 * DictionaryScreen call site can stay source-compatible while the native
 * dictionary grows into the Mini App detail flow. This is session-local: the
 * controller is the DictionaryViewModel that owns this exact state.
 */
interface DictionaryController {
    fun openWord(word: DictionaryWord)
    fun closeWord()
    fun previousCharacter()
    fun nextCharacter()
    fun previousStroke()
    fun nextStroke()
    fun playStrokeOrder()
    fun pauseStrokeOrder()
    fun nextWord()
}

data class DictionaryUiState(
    val isLoading: Boolean = true,
    val query: String = "",
    val words: List<DictionaryWord> = emptyList(),
    val total: Int = 0,
    val error: ApiError? = null,
    val selectedWord: DictionaryWord? = null,
    val characters: List<String> = emptyList(),
    val characterIndex: Int = 0,
    val strokes: List<String> = emptyList(),
    val isStrokeLoading: Boolean = false,
    val strokeError: ApiError? = null,
    val visibleStrokeCount: Int = 0,
    val strokeReplayKey: Int = 0,
    val isStrokePlaying: Boolean = false,
    val controller: DictionaryController? = null,
) {
    val isUnavailable: Boolean get() = !isLoading && total == 0
    val currentCharacter: String? get() = characters.getOrNull(characterIndex)
    val strokeCount: Int get() = strokes.size
    val hasPreviousCharacter: Boolean get() = characterIndex > 0
    val hasNextCharacter: Boolean get() = characterIndex < characters.lastIndex
}

class DictionaryViewModel(
    private val repository: DictionaryRepository,
    private val language: AppLanguage,
) : ViewModel(), DictionaryController {

    private val _state = MutableStateFlow(DictionaryUiState())
    val state: StateFlow<DictionaryUiState> = _state.asStateFlow()

    private var searchJob: Job? = null
    private var strokeJob: Job? = null
    private var playJob: Job? = null
    private var fullWords: List<DictionaryWord> = emptyList()

    init {
        _state.update { it.copy(controller = this) }
        load()
    }

    fun load() {
        _state.update { it.copy(isLoading = true, error = null) }
        viewModelScope.launch {
            when (val result = repository.sync(language)) {
                is ApiResult.Success -> {
                    _state.update { it.copy(total = result.value) }
                    fullWords = repository.search("")
                    runSearch(_state.value.query)
                    _state.update { it.copy(isLoading = false) }
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isLoading = false, error = result.error)
                }
            }
        }
    }

    fun onQueryChange(query: String) {
        _state.update { it.copy(query = query) }
        searchJob?.cancel()
        searchJob = viewModelScope.launch {
            delay(SEARCH_DEBOUNCE_MS)
            runSearch(query)
        }
    }

    override fun openWord(word: DictionaryWord) {
        val chars = word.hanzi
            .filter { it in '\u4E00'..'\u9FFF' }
            .map { it.toString() }
            .ifEmpty { listOf(word.hanzi) }
        stopPlayback()
        _state.update {
            it.copy(
                selectedWord = word,
                characters = chars,
                characterIndex = 0,
                strokes = emptyList(),
                visibleStrokeCount = 0,
                strokeError = null,
            )
        }
        loadCurrentCharacter()
    }

    override fun closeWord() {
        strokeJob?.cancel()
        stopPlayback()
        _state.update {
            it.copy(
                selectedWord = null,
                characters = emptyList(),
                characterIndex = 0,
                strokes = emptyList(),
                isStrokeLoading = false,
                strokeError = null,
                visibleStrokeCount = 0,
            )
        }
    }

    override fun previousCharacter() = moveCharacter(-1)
    override fun nextCharacter() = moveCharacter(1)

    override fun previousStroke() {
        stopPlayback()
        _state.update {
            it.copy(visibleStrokeCount = (it.visibleStrokeCount - 1).coerceAtLeast(0))
        }
    }

    override fun nextStroke() {
        stopPlayback()
        _state.update {
            it.copy(visibleStrokeCount = (it.visibleStrokeCount + 1).coerceAtMost(it.strokes.size))
        }
    }

    override fun playStrokeOrder() {
        val count = _state.value.strokes.size
        if (count == 0) return
        playJob?.cancel()
        val replay = _state.value.strokeReplayKey + 1
        _state.update {
            it.copy(
                visibleStrokeCount = 0,
                strokeReplayKey = replay,
                isStrokePlaying = true,
            )
        }
        playJob = viewModelScope.launch {
            delay(count * STROKE_STEP_MS + PLAY_END_PADDING_MS)
            _state.update {
                if (it.strokeReplayKey == replay) {
                    it.copy(visibleStrokeCount = it.strokes.size, isStrokePlaying = false)
                } else it
            }
        }
    }

    override fun pauseStrokeOrder() {
        if (!_state.value.isStrokePlaying) return
        playJob?.cancel()
        // Compose's compact writer animation is all-or-nothing. Pausing returns
        // to the last explicit step instead of inventing a half stroke.
        _state.update { it.copy(isStrokePlaying = false) }
    }

    override fun nextWord() {
        val current = _state.value.selectedWord ?: return
        val index = fullWords.indexOfFirst { it.hanzi == current.hanzi }
        if (index >= 0 && index < fullWords.lastIndex) openWord(fullWords[index + 1])
    }

    private fun moveCharacter(delta: Int) {
        val next = (_state.value.characterIndex + delta)
        if (next !in _state.value.characters.indices) return
        stopPlayback()
        _state.update {
            it.copy(
                characterIndex = next,
                strokes = emptyList(),
                visibleStrokeCount = 0,
                strokeError = null,
            )
        }
        loadCurrentCharacter()
    }

    private fun loadCurrentCharacter() {
        val char = _state.value.currentCharacter ?: return
        strokeJob?.cancel()
        _state.update { it.copy(isStrokeLoading = true, strokeError = null) }
        strokeJob = viewModelScope.launch {
            when (val result = repository.strokes(char)) {
                is ApiResult.Success -> {
                    _state.update {
                        if (it.currentCharacter == char) {
                            it.copy(
                                strokes = result.value,
                                isStrokeLoading = false,
                                visibleStrokeCount = 0,
                                strokeError = null,
                            )
                        } else it
                    }
                    playStrokeOrder()
                }
                is ApiResult.Failure -> _state.update {
                    if (it.currentCharacter == char) {
                        it.copy(isStrokeLoading = false, strokeError = result.error)
                    } else it
                }
            }
        }
    }

    private fun stopPlayback() {
        playJob?.cancel()
        _state.update { it.copy(isStrokePlaying = false) }
    }

    private suspend fun runSearch(query: String) {
        val results = repository.search(query)
        _state.update { it.copy(words = results) }
    }

    class Factory(
        private val repository: DictionaryRepository,
        private val language: AppLanguage,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            DictionaryViewModel(repository, language) as T
    }

    private companion object {
        const val SEARCH_DEBOUNCE_MS = 180L
        const val STROKE_STEP_MS = 420L
        const val PLAY_END_PADDING_MS = 80L
    }
}
