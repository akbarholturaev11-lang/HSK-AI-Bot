package com.pomp.hskai.feature.lesson

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.audio.LessonAudioPlayer
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.settings.LessonResumeStore
import com.pomp.hskai.data.api.CourseGamificationDto
import com.pomp.hskai.data.api.CourseMistakeDto
import com.pomp.hskai.data.repository.CourseRepository
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.PronunciationCard
import com.pomp.hskai.domain.model.NewWordCard
import com.pomp.hskai.domain.model.ChoiceKind
import com.pomp.hskai.domain.model.Lesson
import com.pomp.hskai.domain.model.LessonCard
import com.pomp.hskai.domain.model.MatchPairsCard
import com.pomp.hskai.domain.model.ReverseBuilderCard
import com.pomp.hskai.domain.model.SentenceBuilderCard
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.Job
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
        /** Mini App parity signals: XP, streak, league and reward chest state. */
        val gamification: CourseGamificationDto,
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
    val previewCardLimit: Int = 0,
    val completionAllowed: Boolean = false,
    val completionError: String? = null,
    val isAudioLoading: Boolean = false,
    val audioError: ApiError? = null,
    val outcome: LessonOutcome = LessonOutcome.InProgress,
    val error: ApiError? = null,
    /**
     * The Mini App's five hearts. A wrong answer costs one and the count is
     * shown in the lesson header. It never ends the lesson — the learner is
     * here to learn, not to lose — but it makes a careless streak visible.
     */
    val hearts: Int = MAX_HEARTS,
    /** Stroke outlines for the character the pencil is showing, if any. */
    val writerChar: WriterTarget? = null,
    val writerStrokes: List<String>? = null,
    val isWriterLoading: Boolean = false,
) {
    val cards: List<LessonCard> get() = lesson?.cards.orEmpty()
    val currentCard: LessonCard? get() = cards.getOrNull(cardIndex)
    val totalCards: Int get() = cards.size

    /** 0..1, for the progress bar. */
    val progress: Float
        get() = if (totalCards == 0) 0f else cardIndex.toFloat() / totalCards

    val isAnswered: Boolean get() = answer is AnswerState.Checked

    /**
     * The Mini App's `.fstage` label — which part of the lesson this card
     * belongs to. Cards are flattened for the flow, so the section is found by
     * counting rather than stored on the card.
     */
    val currentSectionTitle: String
        get() {
            var start = 0
            for (section in lesson?.sections.orEmpty()) {
                val end = start + section.cards.size
                if (cardIndex < end) return section.title
                start = end
            }
            return ""
        }

    /**
     * The character the pencil offers on this card, mirroring the Mini App's
     * `setWriteBtn`: the word being taught, the phrase being said, or the
     * sentence being heard. Cards that teach no single character show none.
     */
    val writeTarget: WriterTarget?
        get() = when (val card = currentCard) {
            is NewWordCard -> WriterTarget(card.hanzi, card.pinyin, card.meaning)
            is PronunciationCard -> WriterTarget(card.phrase, card.pinyin, card.translation)
            is ChoiceCard -> card.audioText
                ?.takeIf { it.isNotBlank() && card.kind == ChoiceKind.LISTENING }
                ?.let { WriterTarget(it, card.audioPinyin.orEmpty(), "") }

            else -> null
        }

    companion object {
        const val MAX_HEARTS = 5
    }
}

/** What the writing sheet is about to show. */
data class WriterTarget(
    val hanzi: String,
    val pinyin: String,
    val meaning: String,
)

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
    private val audioPlayer: LessonAudioPlayer,
    private val level: String,
    private val lessonOrder: Int,
    private val language: AppLanguage,
    /** Set when an ad opened this premium lesson; the server re-checks it. */
    private val accessRef: String = "",
    /** Absent in tests, where there is no device storage to resume from. */
    private val resumeStore: LessonResumeStore? = null,
    /**
     * A new id is created only when [beginAttempt] receives a new launch key.
     * Completion retries inside that attempt keep the same id. Trailing, so a
     * lambda argument cannot land on another parameter by accident.
     */
    private val eventIdFactory: () -> String = CourseRepository::newEventId,
) : ViewModel() {

    private val _state = MutableStateFlow(LessonUiState())
    val state: StateFlow<LessonUiState> = _state.asStateFlow()

    private val mistakes = mutableListOf<CourseMistakeDto>()
    private var activeAttemptKey: String? = null
    private var eventId: String = ""
    private var loadGeneration: Long = 0
    private var audioJob: Job? = null

    /**
     * Starts exactly one clean attempt for a UI launch.
     *
     * The ViewModel can survive after the lesson composable leaves the screen;
     * the opaque launch key prevents an old outcome/event id from resurfacing
     * when the same lesson is opened again.
     */
    fun beginAttempt(attemptKey: String) {
        if (attemptKey.isBlank() || activeAttemptKey == attemptKey) return
        stopAudio()
        activeAttemptKey = attemptKey
        eventId = eventIdFactory()
        mistakes.clear()
        _state.value = LessonUiState()
        load()
    }

    /** Invalidates pending work and playback when the lesson leaves the screen. */
    fun endAttempt(attemptKey: String) {
        if (activeAttemptKey != attemptKey) return
        activeAttemptKey = null
        loadGeneration++
        stopAudio()
        _state.update { it.copy(isAudioLoading = false, audioError = null) }
    }

    fun load() {
        if (activeAttemptKey == null) return
        val generation = ++loadGeneration
        _state.update { it.copy(isLoading = true, error = null) }
        viewModelScope.launch {
            when (val result = repository.lesson(level, lessonOrder, language, accessRef)) {
                is ApiResult.Success -> if (generation == loadGeneration) {
                    val snapshot = result.value
                    // Come back to the card the learner left on, never past the
                    // end: a saved index equal to the deck length would open on
                    // nothing at all.
                    val saved = resumeStore?.lessonResumeIndex(level, lessonOrder) ?: 0
                    val cards = snapshot.lesson.cards.size
                    _state.value = LessonUiState(
                        isLoading = false,
                        lesson = snapshot.lesson,
                        cardIndex = saved.coerceIn(0, (cards - 1).coerceAtLeast(0)),
                        previewCardLimit = snapshot.previewCardLimit,
                        completionAllowed = snapshot.completionAllowed,
                        completionError = snapshot.completionError,
                    )
                }

                is ApiResult.Failure -> if (generation == loadGeneration) {
                    _state.update {
                        it.copy(isLoading = false, error = result.error)
                    }
                }
            }
        }
    }

    /** The server-owned card index at which a free preview stops. */
    private fun previewStopIndex(): Int = _state.value.previewCardLimit
        .coerceIn(1, _state.value.totalCards.coerceAtLeast(1))

    fun answerChoice(card: ChoiceCard, selectedIndex: Int) {
        if (_state.value.isAnswered) return
        val correct = card.isCorrect(selectedIndex)
        if (!correct) {
            addMistake(CourseMistakeDto(
                materialRef = card.materialRef,
                selectedIndex = selectedIndex,
            ))
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
            addMistake(CourseMistakeDto(
                materialRef = card.materialRef,
                selectedTokens = built,
            ))
        }
        record(correct, explanation)
    }

    fun answerMatchPairs(card: MatchPairsCard, wrongAttempts: List<Pair<Int, Int>>) {
        if (_state.value.isAnswered) return
        wrongAttempts.forEach { (left, right) ->
            addMistake(CourseMistakeDto(
                materialRef = card.materialRef,
                selectedLeftIndex = left,
                selectedRightIndex = right,
            ))
        }
        record(wrongAttempts.isEmpty(), card.explanation)
    }

    /** New word, grammar, pronunciation and unsupported cards just advance. */
    fun acknowledge() {
        if (_state.value.isAnswered) return
        advance()
    }

    /**
     * Opens the writing sheet for [target] and fetches its strokes.
     *
     * Only single characters have outlines; a phrase falls back to showing
     * the characters themselves rather than failing.
     */
    fun openWriter(target: WriterTarget) {
        _state.update {
            it.copy(writerChar = target, writerStrokes = null, isWriterLoading = true)
        }
        viewModelScope.launch {
            val single = target.hanzi.trim().takeIf { it.length == 1 }
            val strokes = if (single == null) {
                emptyList()
            } else {
                when (val result = repository.strokes(single)) {
                    is ApiResult.Success -> result.value
                    is ApiResult.Failure -> emptyList()
                }
            }
            _state.update { it.copy(writerStrokes = strokes, isWriterLoading = false) }
        }
    }

    fun closeWriter() {
        _state.update { it.copy(writerChar = null, writerStrokes = null, isWriterLoading = false) }
    }

    /** Keeps the resume point in step with the card on screen. */
    private fun rememberPosition(index: Int) {
        val store = resumeStore ?: return
        viewModelScope.launch { store.setLessonResumeIndex(level, lessonOrder, index) }
    }

    private fun record(correct: Boolean, explanation: String) {
        _state.update {
            it.copy(
                answer = AnswerState.Checked(correct, explanation),
                correctCount = it.correctCount + if (correct) 1 else 0,
                gradedAnswered = it.gradedAnswered + 1,
                hearts = if (correct) it.hearts else (it.hearts - 1).coerceAtLeast(0),
            )
        }
    }

    /** Moves past the feedback bar to the next card, or finishes the lesson. */
    fun advance() {
        val current = _state.value
        val next = current.cardIndex + 1

        if (!current.completionAllowed && next >= previewStopIndex()) {
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

        rememberPosition(next)
        _state.update {
            it.copy(
                cardIndex = next,
                answer = AnswerState.Unanswered,
                audioError = null,
            )
        }
    }

    private fun finish() {
        if (_state.value.isSubmitting) return
        if (!_state.value.completionAllowed) {
            _state.update { it.copy(outcome = LessonOutcome.PreviewExhausted) }
            return
        }
        val attemptKey = activeAttemptKey ?: return
        val stableEventId = eventId.takeIf { it.isNotBlank() } ?: return
        _state.update { it.copy(isSubmitting = true, error = null) }
        viewModelScope.launch {
            val result = repository.completeLesson(
                lessonOrder = lessonOrder,
                eventId = stableEventId,
                mistakes = mistakes.toList(),
                accessRef = accessRef,
            )
            if (result is ApiResult.Success) resumeStore?.clearLessonResume(level, lessonOrder)
            if (activeAttemptKey != attemptKey) return@launch
            _state.update { current ->
                when (result) {
                    is ApiResult.Success -> current.copy(
                        isSubmitting = false,
                        outcome = LessonOutcome.Completed(
                            correct = current.correctCount,
                            graded = current.gradedAnswered,
                            duplicate = result.value.duplicate,
                            gamification = result.value.gamification,
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

    fun playAudio(text: String) {
        if (_state.value.isAudioLoading || text.isBlank()) return
        val attemptKey = activeAttemptKey ?: return
        _state.update { it.copy(isAudioLoading = true, audioError = null) }
        audioJob = viewModelScope.launch {
            when (val result = repository.ttsAudio(text)) {
                is ApiResult.Failure -> if (activeAttemptKey == attemptKey) _state.update {
                    it.copy(isAudioLoading = false, audioError = result.error)
                }

                is ApiResult.Success -> {
                    if (activeAttemptKey != attemptKey) return@launch
                    runCatching {
                        audioPlayer.play(result.value)
                    }.fold(
                        onSuccess = {
                            if (activeAttemptKey == attemptKey) _state.update {
                                it.copy(isAudioLoading = false, audioError = null)
                            }
                        },
                        onFailure = {
                            if (activeAttemptKey == attemptKey) _state.update {
                                it.copy(isAudioLoading = false, audioError = ApiError.Unknown)
                            }
                        },
                    )
                }
            }
        }
    }

    private fun stopAudio() {
        audioJob?.cancel()
        audioJob = null
        audioPlayer.release()
    }

    private fun addMistake(mistake: CourseMistakeDto) {
        if (mistakes.size < MAX_MISTAKES_PER_COMPLETION) mistakes += mistake
    }

    override fun onCleared() {
        activeAttemptKey = null
        loadGeneration++
        stopAudio()
        super.onCleared()
    }

    class Factory(
        private val repository: CourseRepository,
        private val audioPlayer: LessonAudioPlayer,
        private val level: String,
        private val lessonOrder: Int,
        private val language: AppLanguage,
        private val resumeStore: LessonResumeStore,
        private val accessRef: String = "",
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = LessonViewModel(
            repository = repository,
            audioPlayer = audioPlayer,
            level = level,
            lessonOrder = lessonOrder,
            language = language,
            accessRef = accessRef,
            resumeStore = resumeStore,
        ) as T
    }

    companion object {
        /** Matches DesktopCourseCompleteRequest.mistakes.max_length. */
        const val MAX_MISTAKES_PER_COMPLETION = 50
    }
}