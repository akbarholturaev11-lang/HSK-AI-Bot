package com.pomp.hskai.feature.dictionary

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.audio.LessonAudioPlayer
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.repository.DictionaryRepository
import com.pomp.hskai.data.repository.DictionaryWord
import com.pomp.hskai.data.repository.CourseRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

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
    /** Null means full autoplay; otherwise it is the number of visible strokes. */
    val visibleStrokeCount: Int? = null,
    val replayKey: Int = 0,
    val isAudioLoading: Boolean = false,
    val audioError: ApiError? = null,
) {
    /** Nothing stored and nothing to show: the only true empty state. */
    val isUnavailable: Boolean get() = !isLoading && total == 0
    val currentCharacter: String? get() = characters.getOrNull(characterIndex)
}

class DictionaryViewModel(
    private val repository: DictionaryRepository,
    private val courseRepository: CourseRepository,
    private val audioPlayer: LessonAudioPlayer,
    private val language: AppLanguage,
) : ViewModel() {

    private val _state = MutableStateFlow(DictionaryUiState())
    val state: StateFlow<DictionaryUiState> = _state.asStateFlow()

    private var searchJob: Job? = null
    private var strokeJob: Job? = null
    private var audioJob: Job? = null

    init {
        load()
    }

    fun load() {
        _state.update { it.copy(isLoading = true, error = null) }
        viewModelScope.launch {
            when (val result = repository.sync(language)) {
                is ApiResult.Success -> {
                    _state.update { it.copy(total = result.value) }
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
            // Typing a word should not run a query per keystroke against a
            // 1200-row table; the last keystroke is the one that matters.
            delay(SEARCH_DEBOUNCE_MS)
            runSearch(query)
        }
    }

    fun openWord(word: DictionaryWord) {
        val characters = word.hanzi.codePoints()
            .toArray()
            .map { String(Character.toChars(it)) }
        _state.update {
            it.copy(
                selectedWord = word,
                characters = characters,
                characterIndex = 0,
                strokes = emptyList(),
                strokeError = null,
                visibleStrokeCount = null,
            )
        }
        loadCurrentCharacter()
    }

    fun previousWord() = moveWord(-1)
    fun nextWord() = moveWord(1)

    private fun moveWord(offset: Int) {
        val current = _state.value
        val index = current.words.indexOfFirst { it.hanzi == current.selectedWord?.hanzi }
        if (index < 0) return
        current.words.getOrNull(index + offset)?.let(::openWord)
    }

    fun closeWord() {
        strokeJob?.cancel()
        audioJob?.cancel()
        audioPlayer.release()
        _state.update {
            it.copy(
                selectedWord = null,
                characters = emptyList(),
                strokes = emptyList(),
                isStrokeLoading = false,
                isAudioLoading = false,
            )
        }
    }

    fun previousCharacter() = moveCharacter(-1)
    fun nextCharacter() = moveCharacter(1)

    private fun moveCharacter(offset: Int) {
        val current = _state.value
        val next = (current.characterIndex + offset).coerceIn(0, current.characters.lastIndex)
        if (next == current.characterIndex) return
        _state.update { it.copy(characterIndex = next, visibleStrokeCount = null) }
        loadCurrentCharacter()
    }

    fun replayStrokes() {
        _state.update { it.copy(visibleStrokeCount = null, replayKey = it.replayKey + 1) }
    }

    fun previousStroke() {
        _state.update { current ->
            val shown = current.visibleStrokeCount ?: current.strokes.size
            current.copy(visibleStrokeCount = (shown - 1).coerceAtLeast(0))
        }
    }

    fun nextStroke() {
        _state.update { current ->
            val shown = current.visibleStrokeCount ?: 0
            current.copy(visibleStrokeCount = (shown + 1).coerceAtMost(current.strokes.size))
        }
    }

    private fun loadCurrentCharacter() {
        val character = _state.value.currentCharacter ?: return
        strokeJob?.cancel()
        _state.update {
            it.copy(isStrokeLoading = true, strokes = emptyList(), strokeError = null)
        }
        strokeJob = viewModelScope.launch {
            when (val result = courseRepository.strokes(character)) {
                is ApiResult.Failure -> _state.update {
                    it.copy(isStrokeLoading = false, strokeError = result.error)
                }
                is ApiResult.Success -> _state.update {
                    it.copy(
                        isStrokeLoading = false,
                        strokes = result.value,
                        visibleStrokeCount = null,
                        replayKey = it.replayKey + 1,
                    )
                }
            }
        }
    }

    fun playAudio() {
        val text = _state.value.selectedWord?.hanzi.orEmpty()
        if (text.isBlank() || _state.value.isAudioLoading) return
        audioJob?.cancel()
        _state.update { it.copy(isAudioLoading = true, audioError = null) }
        audioJob = viewModelScope.launch {
            when (val result = courseRepository.ttsAudio(text)) {
                is ApiResult.Failure -> _state.update {
                    it.copy(isAudioLoading = false, audioError = result.error)
                }
                is ApiResult.Success -> runCatching { audioPlayer.play(result.value) }.fold(
                    onSuccess = { _state.update { it.copy(isAudioLoading = false) } },
                    onFailure = { _state.update { it.copy(isAudioLoading = false, audioError = ApiError.Unknown) } },
                )
            }
        }
    }

    private suspend fun runSearch(query: String) {
        val results = repository.search(query)
        _state.update { it.copy(words = results) }
    }

    class Factory(
        private val repository: DictionaryRepository,
        private val courseRepository: CourseRepository,
        private val audioPlayer: LessonAudioPlayer,
        private val language: AppLanguage,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            DictionaryViewModel(repository, courseRepository, audioPlayer, language) as T
    }

    override fun onCleared() {
        audioPlayer.release()
        super.onCleared()
    }

    private companion object {
        const val SEARCH_DEBOUNCE_MS = 180L
    }
}
