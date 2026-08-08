package com.pomp.hskai.feature.lesson

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.CourseMistakeDto
import com.pomp.hskai.data.repository.CourseRepository
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.Lesson
import com.pomp.hskai.domain.model.LessonCard
import com.pomp.hskai.domain.model.MatchPairsCard
import com.pomp.hskai.domain.model.ReverseBuilderCard
import com.pomp.hskai.domain.model.SentenceBuilderCard
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/** What the learner has done with the card currently on screen. */
sealed interface AnswerState {
    data object Unanswered : AnswerState
    data class Checked(val isCorrect: Boolean, val explanation: String) : AnswerState
}

sealed interface LessonOutcome {
    data object InProgress : LessonOutcome

    /** Finished and reported. [duplicate] means the server had it already. */
    data class Completed(
        val correct: Int,
        val graded: Int,
        val duplicate: Boolean,
    ) : LessonOutcome

    /** The free half-preview ran out. Completion is not possible. */
    data object PreviewExhausted : LessonOutcome

    data class Failed(val error: ApiError) : LessonOutcome
}

data class LessonUiState(
    val isLoading: Boolean = true,
    val lesson: Lesson? = null,
    val cardIndex: Int = 0,
    val answer: AnswerState = AnswerState.Unanswered,
    val correctCount: Int = 0,
    val gradedAnswered: Int = 0,
    val isSubmitting: Boolean = false,
    val outcome: LessonOutcome = LessonOutcome.InProgress,
    val error: ApiError? = null,
) {
    val cards: List<LessonCard> get() = lesson?.cards.orEmpty()
    val currentCard: LessonCard? get() = cards.getOrNull(cardIndex)
    val totalCards: Int get() = cards.size

    /** 0..1, for the progress bar. */
    val progress: Float
        get() = if (totalCards == 0) 0f else cardIndex.toFloat() / totalCards

    val isAnswered: Boolean get() = answer is AnswerState.Checked
}

/**
 * Runs one mini-lesson.
 *
 * Grading happens locally so feedback is instant, exactly as on the Mini App
 * and the desktop client. It is not the source of truth: only `material_ref`
 * plus the learner's raw selection is reported, and the server rebuilds the
 * question and decides what was actually wrong.
 */
class LessonViewModel(
    private val repository: CourseRepository,
    private val level: String,
    private val lessonOrder: Int,
    private val language: AppLanguage,
    private val isHalfPreview: Boolean,
    /**
     * Stable for the whole attempt. A retry after a dropped connection reuses
     * it, so the server recognises the completion instead of awarding twice.
     */
    private val eventId: String = CourseRepository.newEventId(),
) : ViewModel() {

    private val _state = MutableStateFlow(LessonUiState())
    val state: StateFlow<LessonUiState> = _state.asStateFlow()

    private val mistakes = mutableListOf<CourseMistakeDto>()

    init {
        load()
    }

    fun load() {
        _state.update { it.copy(isLoading = true, error = null) }
        viewModelScope.launch {
            when (val result = repository.lesson(level, lessonOrder, language)) {
                is ApiResult.Success -> _state.value = LessonUiState(
                    isLoading = false,
                    lesson = result.value,
                )

                is ApiResult.Failure -> _state.update {
                    it.copy(isLoading = false, error = result.error)
                }
            }
        }
    }

    /**
     * The card index at which a free half preview stops.
     *
     * Mirrors Course v3 exactly: `max(1, floor(cards / 2))`.
     */
    private fun previewStopIndex(): Int {
        val total = _state.value.totalCards
        return maxOf(1, total / 2)
    }

    fun answerChoice(card: ChoiceCard, selectedIndex: Int) {
        if (_state.value.isAnswered) return
        val correct = card.isCorrect(selectedIndex)
        if (!correct) {
            mistakes += CourseMistakeDto(
                materialRef = card.materialRef,
                selectedIndex = selectedIndex,
            )
        }
        record(correct, card.explanation)
    }

    fun answerBuilder(card: LessonCard, built: List<String>) {
        if (_state.value.isAnswered) return
        val (correct, explanation) = when (card) {
            is SentenceBuilderCard -> card.isCorrect(built) to card.explanation
            is ReverseBuilderCard -> card.isCorrect(built) to card.explanation
            else -> return
        }
        if (!correct) {
            mistakes += CourseMistakeDto(
                materialRef = card.materialRef,
                selectedTokens = built,
            )
        }
        record(correct, explanation)
    }

    fun answerMatchPairs(card: MatchPairsCard, wrongAttempts: List<Pair<Int, Int>>) {
        if (_state.value.isAnswered) return
        wrongAttempts.forEach { (left, right) ->
            mistakes += CourseMistakeDto(
                materialRef = card.materialRef,
                selectedLeftIndex = left,
                selectedRightIndex = right,
            )
        }
        record(wrongAttempts.isEmpty(), card.explanation)
    }

    /** New word, grammar, pronunciation and unsupported cards just advance. */
    fun acknowledge() {
        if (_state.value.isAnswered) return
        advance()
    }

    private fun record(correct: Boolean, explanation: String) {
        _state.update {
            it.copy(
                answer = AnswerState.Checked(correct, explanation),
                correctCount = it.correctCount + if (correct) 1 else 0,
                gradedAnswered = it.gradedAnswered + 1,
            )
        }
    }

    /** Moves past the feedback bar to the next card, or finishes the lesson. */
    fun advance() {
        val current = _state.value
        val next = current.cardIndex + 1

        if (isHalfPreview && next >= previewStopIndex() && next < current.totalCards) {
            // The preview stops mid-lesson and cannot complete it. The server
            // would reject the completion anyway; not sending it keeps the
            // attempt clean.
            _state.update {
                it.copy(
                    answer = AnswerState.Unanswered,
                    outcome = LessonOutcome.PreviewExhausted,
                )
            }
            return
        }

        if (next >= current.totalCards) {
            finish()
            return
        }

        _state.update { it.copy(cardIndex = next, answer = AnswerState.Unanswered) }
    }

    private fun finish() {
        if (_state.value.isSubmitting) return
        _state.update { it.copy(isSubmitting = true, error = null) }
        viewModelScope.launch {
            val result = repository.completeLesson(
                lessonOrder = lessonOrder,
                eventId = eventId,
                mistakes = mistakes.toList(),
            )
            _state.update { current ->
                when (result) {
                    is ApiResult.Success -> current.copy(
                        isSubmitting = false,
                        outcome = LessonOutcome.Completed(
                            correct = current.correctCount,
                            graded = current.gradedAnswered,
                            duplicate = result.value.duplicate,
                        ),
                    )

                    is ApiResult.Failure -> current.copy(
                        isSubmitting = false,
                        outcome = LessonOutcome.Failed(result.error),
                        error = result.error,
                    )
                }
            }
        }
    }

    /** Retries a failed completion with the same event id. */
    fun retryCompletion() {
        _state.update { it.copy(outcome = LessonOutcome.InProgress) }
        finish()
    }

    class Factory(
        private val repository: CourseRepository,
        private val level: String,
        private val lessonOrder: Int,
        private val language: AppLanguage,
        private val isHalfPreview: Boolean,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = LessonViewModel(
            repository = repository,
            level = level,
            lessonOrder = lessonOrder,
            language = language,
            isHalfPreview = isHalfPreview,
        ) as T
    }
}
