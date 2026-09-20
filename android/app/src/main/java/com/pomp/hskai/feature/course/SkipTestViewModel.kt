package com.pomp.hskai.feature.course

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.repository.CourseRepository
import com.pomp.hskai.domain.model.ChoiceCard
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlin.random.Random

/**
 * The Mini App's skip-ahead test: a locked lesson opens once the learner has
 * answered a few questions drawn from that lesson's own material.
 *
 * The questions are not invented here. They are the graded cards the lesson
 * already ships, so passing the test means having answered the real thing —
 * and a lesson whose material carries no graded card simply opens, exactly as
 * `buildTestQueue` does when its pool comes back empty.
 */
class SkipTestViewModel(
    private val repository: CourseRepository,
    private val level: String,
    private val language: AppLanguage,
) : ViewModel() {

    private val _state = MutableStateFlow(SkipTestUiState())
    val state: StateFlow<SkipTestUiState> = _state.asStateFlow()

    /** Loads the locked lesson and draws its questions. */
    fun start(lessonOrder: Int) {
        if (_state.value.lessonOrder == lessonOrder && _state.value.questions.isNotEmpty()) return
        _state.value = SkipTestUiState(lessonOrder = lessonOrder, isLoading = true)
        viewModelScope.launch {
            when (val result = repository.lesson(level, lessonOrder, language)) {
                is ApiResult.Success -> {
                    val questions = drawQuestions(
                        cards = result.value.lesson.cards.filterIsInstance<ChoiceCard>(),
                        seed = lessonOrder,
                    )
                    if (questions.isEmpty()) {
                        // Nothing to ask means nothing to prove. The Mini App
                        // unlocks outright here rather than showing an empty
                        // test the learner cannot pass or fail.
                        unlock(score = 100)
                        return@launch
                    }
                    _state.update {
                        it.copy(isLoading = false, questions = questions, index = 0)
                    }
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isLoading = false, error = result.error)
                }
            }
        }
    }

    fun select(optionIndex: Int) {
        val current = _state.value
        val question = current.currentQuestion ?: return
        if (current.selectedIndex != null) return
        val correct = question.isCorrect(optionIndex)
        _state.update {
            it.copy(
                selectedIndex = optionIndex,
                correctCount = it.correctCount + if (correct) 1 else 0,
            )
        }
    }

    fun advance() {
        val current = _state.value
        if (current.selectedIndex == null) return
        if (current.index + 1 < current.questions.size) {
            _state.update { it.copy(index = it.index + 1, selectedIndex = null) }
            return
        }
        _state.update { it.copy(selectedIndex = null, finishedScore = it.score) }
    }

    /**
     * Opens the lesson.
     *
     * Called straight away on a passing score, and only after the learner
     * confirms on a weak one — the confirmation is the Mini App's, and it is
     * the client's to ask because the server opens the lesson either way.
     */
    fun unlock(score: Int = _state.value.score) {
        if (_state.value.isUnlocking) return
        val lessonOrder = _state.value.lessonOrder
        if (lessonOrder <= 0) return
        _state.update { it.copy(isUnlocking = true, error = null) }
        viewModelScope.launch {
            when (val result = repository.unlockLesson(lessonOrder, score)) {
                is ApiResult.Success -> _state.update {
                    it.copy(isUnlocking = false, unlocked = true)
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isUnlocking = false, error = result.error)
                }
            }
        }
    }

    fun dismissError() = _state.update { it.copy(error = null) }

    /**
     * Six questions, shuffled — the Mini App's count and its shuffle.
     *
     * The seed is the lesson order, so re-opening the same locked lesson asks
     * the same questions instead of rerolling until an easy draw appears.
     */
    private fun drawQuestions(cards: List<ChoiceCard>, seed: Int): List<ChoiceCard> =
        cards.shuffled(Random(seed)).take(QUESTION_COUNT)

    class Factory(
        private val repository: CourseRepository,
        private val level: String,
        private val language: AppLanguage,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = SkipTestViewModel(
            repository = repository,
            level = level,
            language = language,
        ) as T
    }

    companion object {
        const val QUESTION_COUNT = 6

        /** Below this the Mini App asks the learner to confirm. */
        const val PASS_PERCENT = 60
    }
}

data class SkipTestUiState(
    val lessonOrder: Int = 0,
    val isLoading: Boolean = false,
    val questions: List<ChoiceCard> = emptyList(),
    val index: Int = 0,
    val selectedIndex: Int? = null,
    val correctCount: Int = 0,
    /** Set once the last question is answered; null while the test runs. */
    val finishedScore: Int? = null,
    val isUnlocking: Boolean = false,
    val unlocked: Boolean = false,
    val error: ApiError? = null,
) {
    val currentQuestion: ChoiceCard? get() = questions.getOrNull(index)

    val isAnswered: Boolean get() = selectedIndex != null

    val isLastQuestion: Boolean get() = index == questions.lastIndex

    /** Percent correct, rounded the way the Mini App rounds it. */
    val score: Int
        get() = if (questions.isEmpty()) 0 else correctCount * 100 / questions.size

    val passed: Boolean get() = (finishedScore ?: score) >= SkipTestViewModel.PASS_PERCENT
}
