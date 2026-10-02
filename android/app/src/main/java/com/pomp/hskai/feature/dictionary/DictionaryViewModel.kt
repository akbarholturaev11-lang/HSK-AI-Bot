package com.pomp.hskai.feature.dictionary

import androidx.compose.ui.geometry.Offset
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.hanzi.CharacterStrokes
import com.pomp.hskai.core.audio.LessonAudioPlayer
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.repository.CharacterBreakdown
import com.pomp.hskai.data.repository.DictionaryInsightsSource
import com.pomp.hskai.data.repository.DictionaryRepository
import com.pomp.hskai.data.repository.DictionaryWord
import com.pomp.hskai.data.repository.CourseRepository
import com.pomp.hskai.data.repository.ExampleSentence
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
    val versionFilter: String = "all",
    val levelFilter: String = "all",
    val words: List<DictionaryWord> = emptyList(),
    val total: Int = 0,
    val error: ApiError? = null,
    val selectedWord: DictionaryWord? = null,
    val characters: List<String> = emptyList(),
    val characterIndex: Int = 0,
    val strokes: CharacterStrokes = CharacterStrokes.EMPTY,
    val isStrokeLoading: Boolean = false,
    val strokeError: ApiError? = null,
    /** Null means full autoplay; otherwise it is the number of visible strokes. */
    val visibleStrokeCount: Int? = null,
    val replayKey: Int = 0,
    val isAudioLoading: Boolean = false,
    val audioError: ApiError? = null,
    /** Real sentences using the selected word. */
    val examples: List<ExampleSentence> = emptyList(),
    /** What each character of the selected word is made of, in order. */
    val breakdowns: List<CharacterBreakdown> = emptyList(),
    val isInsightsLoading: Boolean = false,
    /** The handwriting practice, while it is open. */
    val writing: WritingUiState? = null,
    /** Entries last opened from a search, newest first; shown when the search box is focused. */
    val history: List<DictionaryWord> = emptyList(),
) {
    /** Nothing stored and nothing to show: the only true empty state. */
    val isUnavailable: Boolean get() = !isLoading && total == 0
    val currentCharacter: String? get() = characters.getOrNull(characterIndex)

    private val selectedIndex: Int get() = words.indexOfFirst { it.hanzi == selectedWord?.hanzi }
    val previousWord: DictionaryWord? get() = selectedIndex.takeIf { it > 0 }?.let { words[it - 1] }
    val nextWord: DictionaryWord? get() = selectedIndex.takeIf { it >= 0 }?.let { words.getOrNull(it + 1) }
    val hasNextCharacter: Boolean get() = characterIndex < characters.lastIndex

    /** Writing needs the brush's route, not only the finished shape. */
    val canWrite: Boolean get() = strokes.isNotEmpty() && strokes.medians.size == strokes.size
}

class DictionaryViewModel(
    private val repository: DictionaryRepository,
    private val courseRepository: CourseRepository,
    private val audioPlayer: LessonAudioPlayer,
    private val language: AppLanguage,
    private val insights: DictionaryInsightsSource? = null,
    private val readHistory: suspend () -> List<String> = { emptyList() },
    private val writeHistory: suspend (List<String>) -> Unit = {},
) : ViewModel() {

    private val _state = MutableStateFlow(DictionaryUiState())
    val state: StateFlow<DictionaryUiState> = _state.asStateFlow()

    private var searchJob: Job? = null
    private var strokeJob: Job? = null
    private var audioJob: Job? = null
    private var insightJob: Job? = null
    private var roundJob: Job? = null

    /** Every entry by its characters, so the history can be shown in the current language. */
    private var entries: Map<String, DictionaryWord> = emptyMap()
    private var historyKeys: List<String> = emptyList()

    init {
        load()
    }

    fun load() {
        _state.update { it.copy(isLoading = true, error = null) }
        viewModelScope.launch {
            // The words on the device are shown first. The server is asked
            // afterwards and only replaces the list if it has a newer one, so
            // no connection — or a slow one — never holds the dictionary up.
            historyKeys = runCatching { readHistory() }.getOrDefault(emptyList())
            val stored = repository.prepare(language)
            if (stored > 0) {
                _state.update { it.copy(total = stored) }
                refreshEntries()
                runSearch(_state.value.query)
                _state.update { it.copy(isLoading = false) }
            }
            when (val result = repository.sync(language)) {
                is ApiResult.Success -> {
                    _state.update { it.copy(total = result.value) }
                    refreshEntries()
                    runSearch(_state.value.query)
                    _state.update { it.copy(isLoading = false) }
                }

                is ApiResult.Failure -> _state.update {
                    if (stored > 0) it.copy(isLoading = false)
                    else it.copy(isLoading = false, error = result.error)
                }
            }
        }
    }

    fun setActiveCourseLevel(level: String) {
        val normalized = level.trim().lowercase()
        val version = if (normalized.startsWith("nhsk")) "hsk30" else "hsk20"
        val levelFilter = when {
            normalized.startsWith("nhsk") -> {
                val band = normalized.filter { it.isDigit() }.toIntOrNull()?.coerceIn(1, 3) ?: 1
                "nhsk$band"
            }
            normalized.startsWith("hsk") -> {
                val band = normalized.filter { it.isDigit() }.toIntOrNull()?.coerceIn(1, 4) ?: 1
                "hsk$band"
            }
            else -> "hsk1"
        }
        val current = _state.value
        if (current.versionFilter == version && current.levelFilter == levelFilter) return
        _state.update { it.copy(versionFilter = version, levelFilter = levelFilter) }
        viewModelScope.launch { runSearch(_state.value.query) }
    }

    fun selectVersionFilter(filter: String) {
        if (filter !in VERSION_FILTERS) return
        val current = _state.value
        val nextLevel = when (filter) {
            "hsk20" -> current.levelFilter.takeIf { it in HSK20_LEVEL_FILTERS } ?: "all"
            "hsk30" -> current.levelFilter.takeIf { it in HSK30_LEVEL_FILTERS } ?: "all"
            else -> current.levelFilter
        }
        _state.update { it.copy(versionFilter = filter, levelFilter = nextLevel) }
        viewModelScope.launch { runSearch(_state.value.query) }
    }

    fun selectLevelFilter(filter: String) {
        if (filter !in LEVEL_FILTERS) return
        _state.update { it.copy(levelFilter = filter) }
        viewModelScope.launch { runSearch(_state.value.query) }
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

    /**
     * Opens an entry tapped in the list. One found by searching is what the
     * learner was looking for, so it goes into the history; one picked while
     * browsing the plain list does not.
     */
    fun openWord(word: DictionaryWord) {
        if (_state.value.query.isNotBlank()) addToHistory(word)
        showWord(word)
    }

    /** Opens an entry from the history, which moves it back to the top. */
    fun openRecent(word: DictionaryWord) {
        addToHistory(word)
        showWord(word)
    }

    private fun addToHistory(word: DictionaryWord) {
        historyKeys = DictionaryHistory.record(historyKeys, word.hanzi)
        publishHistory()
        val saved = historyKeys
        viewModelScope.launch { runCatching { writeHistory(saved) } }
    }

    private fun publishHistory() {
        _state.update { current -> current.copy(history = historyKeys.mapNotNull(entries::get)) }
    }

    private suspend fun refreshEntries() {
        entries = repository.search("").associateBy { it.hanzi }
        publishHistory()
    }

    private fun showWord(word: DictionaryWord) {
        val characters = word.hanzi.codePoints()
            .toArray()
            .map { String(Character.toChars(it)) }
            .filter { it.any(Char::isHanzi) }
        audioJob?.cancel()
        _state.update {
            it.copy(
                selectedWord = word,
                characters = characters,
                characterIndex = 0,
                strokes = CharacterStrokes.EMPTY,
                strokeError = null,
                visibleStrokeCount = null,
                examples = emptyList(),
                breakdowns = emptyList(),
                isInsightsLoading = insights != null,
                writing = null,
                isAudioLoading = false,
            )
        }
        loadCurrentCharacter()
        loadInsights(word, characters)
    }

    fun previousWord() = moveWord(-1)
    fun nextWord() = moveWord(1)

    private fun moveWord(offset: Int) {
        val current = _state.value
        val next = if (offset < 0) current.previousWord else current.nextWord
        // Stepping through the list is browsing, not searching.
        next?.let(::showWord)
    }

    fun closeWord() {
        strokeJob?.cancel()
        audioJob?.cancel()
        insightJob?.cancel()
        roundJob?.cancel()
        audioPlayer.release()
        _state.update {
            it.copy(
                selectedWord = null,
                characters = emptyList(),
                strokes = CharacterStrokes.EMPTY,
                isStrokeLoading = false,
                isAudioLoading = false,
                examples = emptyList(),
                breakdowns = emptyList(),
                isInsightsLoading = false,
                writing = null,
            )
        }
    }

    fun previousCharacter() = moveCharacter(-1)
    fun nextCharacter() = moveCharacter(1)

    private fun moveCharacter(offset: Int, thenWrite: Boolean = false) {
        val current = _state.value
        val next = (current.characterIndex + offset).coerceIn(0, current.characters.lastIndex)
        if (next == current.characterIndex) return
        _state.update { it.copy(characterIndex = next, visibleStrokeCount = null, writing = null) }
        loadCurrentCharacter(thenWrite)
    }

    /** Writes the character stroke by stroke in the big card. */
    fun playStrokeOrder() {
        if (_state.value.strokes.isEmpty()) return
        _state.update { it.copy(visibleStrokeCount = null, replayKey = it.replayKey + 1) }
    }

    private fun loadCurrentCharacter(thenWrite: Boolean = false) {
        val character = _state.value.currentCharacter ?: return
        strokeJob?.cancel()
        _state.update {
            it.copy(isStrokeLoading = true, strokes = CharacterStrokes.EMPTY, strokeError = null)
        }
        strokeJob = viewModelScope.launch {
            when (val result = courseRepository.strokes(character)) {
                is ApiResult.Failure -> _state.update {
                    it.copy(isStrokeLoading = false, strokeError = result.error)
                }
                is ApiResult.Success -> {
                    _state.update {
                        it.copy(
                            isStrokeLoading = false,
                            strokes = result.value,
                            // The card shows the finished character; the
                            // stroke order plays when it is asked for.
                            visibleStrokeCount = result.value.size,
                        )
                    }
                    if (thenWrite) startWriting()
                }
            }
        }
    }

    private fun loadInsights(word: DictionaryWord, characters: List<String>) {
        val source = insights ?: return
        insightJob?.cancel()
        insightJob = viewModelScope.launch {
            val examples = source.examples(word.hanzi, language)
            val breakdowns = characters.distinct().mapNotNull { source.breakdown(it, language) }
            _state.update {
                if (it.selectedWord?.hanzi != word.hanzi) it
                else it.copy(
                    examples = examples,
                    breakdowns = breakdowns,
                    isInsightsLoading = false,
                )
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

    // --- handwriting practice ---

    fun startWriting() {
        val current = _state.value
        val character = current.currentCharacter ?: return
        if (!current.canWrite) return
        roundJob?.cancel()
        _state.update { it.copy(writing = HanziWriting.start(character, current.strokes)) }
    }

    fun closeWriting() {
        roundJob?.cancel()
        _state.update { it.copy(writing = null) }
    }

    fun playWritingDemoAgain() = updateWriting(HanziWriting::playDemoAgain)
    fun beginWriting() = updateWriting(HanziWriting::beginWriting)
    fun showWritingHint() = updateWriting(HanziWriting::hint)
    fun restartWritingRound() = updateWriting(HanziWriting::restartRound)
    fun writeAgain() = updateWriting(HanziWriting::again)

    /** [points] are in the character's grid, as the writing canvas reports them. */
    fun submitWritingStroke(points: List<Offset>) {
        updateWriting { HanziWriting.submitStroke(it, points) }
        val writing = _state.value.writing ?: return
        if (!writing.isRoundComplete) return
        roundJob?.cancel()
        roundJob = viewModelScope.launch {
            // The finished character stays on screen for a beat before the
            // next round clears it; otherwise the last stroke never shows.
            delay(ROUND_PAUSE_MS)
            updateWriting(HanziWriting::nextRound)
        }
    }

    /** From the finished practice straight to the word's next character. */
    fun writeNextCharacter() {
        if (!_state.value.hasNextCharacter) return
        roundJob?.cancel()
        moveCharacter(1, thenWrite = true)
    }

    private fun updateWriting(change: (WritingUiState) -> WritingUiState) {
        _state.update { current -> current.writing?.let { current.copy(writing = change(it)) } ?: current }
    }

    private suspend fun runSearch(query: String) {
        val current = _state.value
        val results = repository.search(query).filter { word ->
            dictionaryWordMatches(
                word = word,
                versionFilter = current.versionFilter,
                levelFilter = current.levelFilter,
            )
        }
        _state.update { it.copy(words = results) }
    }

    class Factory(
        private val repository: DictionaryRepository,
        private val courseRepository: CourseRepository,
        private val audioPlayer: LessonAudioPlayer,
        private val language: AppLanguage,
        private val insights: DictionaryInsightsSource? = null,
        private val readHistory: suspend () -> List<String> = { emptyList() },
        private val writeHistory: suspend (List<String>) -> Unit = {},
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            DictionaryViewModel(
                repository,
                courseRepository,
                audioPlayer,
                language,
                insights,
                readHistory,
                writeHistory,
            ) as T
    }

    override fun onCleared() {
        audioPlayer.release()
        super.onCleared()
    }

    private companion object {
        const val SEARCH_DEBOUNCE_MS = 180L
        const val ROUND_PAUSE_MS = 650L
        val VERSION_FILTERS = setOf("all", "hsk20", "hsk30")
        val HSK20_LEVEL_FILTERS = setOf("all", "hsk1", "hsk2", "hsk3", "hsk4")
        val HSK30_LEVEL_FILTERS = setOf("all", "nhsk1", "nhsk2", "nhsk3")
        val LEVEL_FILTERS = HSK20_LEVEL_FILTERS + HSK30_LEVEL_FILTERS
    }
}

internal fun dictionaryWordMatches(
    word: DictionaryWord,
    versionFilter: String,
    levelFilter: String,
): Boolean {
    val tags = word.level.split("|")
        .map { it.trim().lowercase() }
        .filter(String::isNotBlank)
    val versionMatches = when (versionFilter) {
        "hsk20" -> tags.any { it.startsWith("hsk") }
        "hsk30" -> tags.any { Regex("^n[1-3]$").matches(it) }
        else -> true
    }
    if (!versionMatches) return false
    return when (levelFilter) {
        "hsk1", "hsk2", "hsk3", "hsk4" -> tags.any { it == levelFilter }
        "nhsk1", "nhsk2", "nhsk3" -> tags.any { it == "n" + levelFilter.takeLast(1) }
        else -> true
    }
}

private fun Char.isHanzi(): Boolean = this in '一'..'鿿'
