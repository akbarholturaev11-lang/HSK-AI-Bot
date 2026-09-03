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

data class DictionaryUiState(
    val isLoading: Boolean = true,
    val query: String = "",
    val words: List<DictionaryWord> = emptyList(),
    val total: Int = 0,
    val error: ApiError? = null,
) {
    /** Nothing stored and nothing to show: the only true empty state. */
    val isUnavailable: Boolean get() = !isLoading && total == 0
}

class DictionaryViewModel(
    private val repository: DictionaryRepository,
    private val language: AppLanguage,
) : ViewModel() {

    private val _state = MutableStateFlow(DictionaryUiState())
    val state: StateFlow<DictionaryUiState> = _state.asStateFlow()

    private var searchJob: Job? = null

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
    }
}
