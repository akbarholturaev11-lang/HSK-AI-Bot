package com.pomp.hskai.feature.rating

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.ChallengeAnswerDto
import com.pomp.hskai.data.api.ChallengeQuestionDto
import com.pomp.hskai.data.repository.FeatureRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ChallengeRunUiState(
    val isLoading: Boolean = true,
    val questions: List<ChallengeQuestionDto> = emptyList(),
    val index: Int = 0,
    val selected: Int? = null,
    val isSubmitting: Boolean = false,
    val finished: Boolean = false,
    val error: ApiError? = null,
) {
    val current: ChallengeQuestionDto? get() = questions.getOrNull(index)
    val total: Int get() = questions.size
    val progress: Float get() = if (total == 0) 0f else index.toFloat() / total
}

/**
 * One side of a duel.
 *
 * Both learners answer the same frozen set and the server compares the two
 * scores, so nothing here decides who won — it only collects answers and
 * hands them over. The right answer is never sent to the client, which is why
 * there is no per-question feedback: the result is the whole point.
 */
class ChallengeRunViewModel(
    private val repository: FeatureRepository,
    private val challengeId: Int,
) : ViewModel() {

    private val _state = MutableStateFlow(ChallengeRunUiState())
    val state: StateFlow<ChallengeRunUiState> = _state.asStateFlow()

    private val answers = mutableListOf<ChallengeAnswerDto>()
    private val startedAtMillis = System.currentTimeMillis()

    init {
        load()
    }

    fun load() {
        _state.value = ChallengeRunUiState(isLoading = true)
        answers.clear()
        viewModelScope.launch {
            when (val result = repository.startChallenge(challengeId)) {
                is ApiResult.Success -> {
                    val questions = result.value.session.questions.filter {
                        it.id.isNotBlank() && it.options.size >= 2
                    }
                    _state.update {
                        it.copy(
                            isLoading = false,
                            questions = questions,
                            error = if (questions.isEmpty()) ApiError.Unknown else null,
                        )
                    }
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isLoading = false, error = result.error)
                }
            }
        }
    }

    fun select(index: Int) {
        val state = _state.value
        val question = state.current ?: return
        if (state.isSubmitting || index !in question.options.indices) return
        _state.update { it.copy(selected = index) }
    }

    fun advance() {
        val state = _state.value
        val question = state.current ?: return
        val chosen = state.selected ?: return
        answers += ChallengeAnswerDto(questionId = question.id, selectedIndex = chosen)

        val next = state.index + 1
        if (next < state.total) {
            _state.update { it.copy(index = next, selected = null) }
            return
        }
        submit()
    }

    private fun submit() {
        _state.update { it.copy(isSubmitting = true, error = null) }
        viewModelScope.launch {
            val seconds = ((System.currentTimeMillis() - startedAtMillis) / 1000).toInt()
            when (
                val result = repository.submitChallenge(
                    challengeId = challengeId,
                    answers = answers.toList(),
                    durationSeconds = seconds.coerceIn(0, 7200),
                )
            ) {
                is ApiResult.Success -> _state.update {
                    it.copy(isSubmitting = false, finished = true)
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isSubmitting = false, error = result.error)
                }
            }
        }
    }

    class Factory(
        private val repository: FeatureRepository,
        private val challengeId: Int,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            ChallengeRunViewModel(repository, challengeId) as T
    }
}
