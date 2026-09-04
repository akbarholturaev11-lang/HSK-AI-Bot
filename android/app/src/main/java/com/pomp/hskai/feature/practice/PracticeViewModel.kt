package com.pomp.hskai.feature.practice

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.R
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.ExamCompleteResponse
import com.pomp.hskai.data.api.ExamSessionDto
import com.pomp.hskai.data.api.MistakeReviewAnswerResponse
import com.pomp.hskai.data.api.MistakeReviewCompleteResponse
import com.pomp.hskai.data.api.MistakeReviewSessionDto
import com.pomp.hskai.data.api.MistakesOverviewResponse
import com.pomp.hskai.data.api.PracticeCompleteResponse
import com.pomp.hskai.data.api.PracticeSessionDto
import com.pomp.hskai.data.repository.FeatureRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class PracticeToolSpec(
    val mode: String,
    val skill: String,
    val titleRes: Int,
    val bodyRes: Int,
    val glyph: String,
)

/**
 * The allowance this tool draws from, named as the server names it.
 *
 * Mirrors `CourseMiniAppPracticeService._feature`: an ad opened against the
 * wrong name would unlock nothing, so the two must not drift.
 */
val PracticeToolSpec.adFeature: String
    get() = if (mode == "placement") "placement" else "training_test"

/**
 * Names the test centre in the limit block when an exam is refused. It is not
 * started through [PracticeToolSpec]; only the section's name and the ad
 * feature it opens are needed there.
 */
internal val EXAM_TOOL = PracticeToolSpec(
    mode = "mock",
    skill = "",
    titleRes = R.string.practice_group_tests,
    bodyRes = R.string.practice_test_center_body,
    glyph = "HSK",
)

data class PracticeUiState(
    val mistakes: MistakesOverviewResponse? = null,
    val isLoadingMistakes: Boolean = false,
    val isStarting: Boolean = false,
    val isCompleting: Boolean = false,
    val session: PracticeSessionDto? = null,
    val questionIndex: Int = 0,
    val selectedIndex: Int? = null,
    val answers: Map<String, Int> = emptyMap(),
    val result: PracticeCompleteResponse? = null,
    val reviewSession: MistakeReviewSessionDto? = null,
    val reviewIndex: Int = 0,
    val reviewSelectedIndex: Int? = null,
    val reviewFeedback: MistakeReviewAnswerResponse? = null,
    val reviewAnswers: Map<String, Int> = emptyMap(),
    val reviewResult: MistakeReviewCompleteResponse? = null,
    /**
     * The HSK exam the test centre opens — the Mini App's exam, kept apart
     * from [session] because it is a different service with its own material,
     * its own grading and its own once-per-lifetime allowance.
     */
    val examSession: ExamSessionDto? = null,
    val examIndex: Int = 0,
    val examSelectedIndex: Int? = null,
    val examAnswers: Map<String, Int> = emptyMap(),
    val examResult: ExamCompleteResponse? = null,
    val examLevel: String = "",
    val error: ApiError? = null,
    /**
     * The section the learner last tried to open. A spent allowance has to
     * name it, and an ad has to know which section it is opening.
     */
    val pendingTool: PracticeToolSpec? = null,
    /**
     * Ties the running session to the ad that opened it. Empty when the
     * session came out of the daily allowance instead.
     */
    val adAccessRef: String = "",
) {
    val isPracticeRunning: Boolean get() = session != null && result == null
    val isReviewRunning: Boolean get() = reviewSession != null && reviewResult == null
    val isExamRunning: Boolean get() = examSession != null && examResult == null
}

class PracticeViewModel(
    private val repository: FeatureRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(PracticeUiState())
    val state: StateFlow<PracticeUiState> = _state.asStateFlow()

    init {
        loadMistakes()
    }

    fun loadMistakes() {
        _state.update { it.copy(isLoadingMistakes = true, error = null) }
        viewModelScope.launch {
            when (val result = repository.mistakes()) {
                is ApiResult.Success -> _state.update {
                    it.copy(isLoadingMistakes = false, mistakes = result.value)
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isLoadingMistakes = false, error = result.error)
                }
            }
        }
    }

    /**
     * The attempt to repeat if an ad opens the section. Held outside the UI
     * state because it is bookkeeping, not something the screen draws.
     */
    private data class Attempt(
        val tool: PracticeToolSpec,
        val level: String,
        val language: String,
    )

    private var lastAttempt: Attempt? = null

    private data class ExamAttempt(val level: String, val language: String)

    /**
     * Set when an exam is opened, cleared when anything else is. An ad that
     * follows a refusal must re-open what was refused, so only one of the two
     * attempts may be live at a time.
     */
    private var lastExamAttempt: ExamAttempt? = null

    fun startPractice(
        tool: PracticeToolSpec,
        level: String,
        language: String,
        accessRef: String = "",
        adSupported: Boolean = false,
    ) {
        if (_state.value.isStarting) return
        lastAttempt = Attempt(tool, level, language)
        lastExamAttempt = null
        _state.update {
            it.copy(
                isStarting = true,
                error = null,
                session = null,
                result = null,
                selectedIndex = null,
                answers = emptyMap(),
                pendingTool = tool,
                adAccessRef = if (adSupported) accessRef else "",
            )
        }
        viewModelScope.launch {
            when (
                val result = repository.practiceStart(
                    mode = tool.mode,
                    level = level,
                    language = language,
                    skill = tool.skill,
                    accessRef = accessRef,
                    adSupported = adSupported,
                )
            ) {
                is ApiResult.Success -> _state.update {
                    it.copy(
                        isStarting = false,
                        session = result.value.session,
                        questionIndex = 0,
                    )
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isStarting = false, error = result.error)
                }
            }
        }
    }

    /**
     * Re-opens the section the learner was refused, now that an ad has been
     * watched. The server still decides: it checks its own record of the
     * watch against [accessRef].
     */
    fun startWithAd(accessRef: String) {
        lastExamAttempt?.let { exam ->
            startExam(
                level = exam.level,
                language = exam.language,
                accessRef = accessRef,
                adSupported = true,
            )
            return
        }
        val attempt = lastAttempt ?: return
        startPractice(
            tool = attempt.tool,
            level = attempt.level,
            language = attempt.language,
            accessRef = accessRef,
            adSupported = true,
        )
    }

    /**
     * Opens one HSK exam. This is not [startPractice] with another mode: the
     * exam has its own endpoint, its own questions and its own allowance, and
     * mixing the two is exactly what made Android and the Mini App hand out
     * different tests under the same name.
     */
    fun startExam(
        level: String,
        language: String,
        accessRef: String = "",
        adSupported: Boolean = false,
    ) {
        if (_state.value.isStarting) return
        lastExamAttempt = ExamAttempt(level, language)
        _state.update {
            it.copy(
                isStarting = true,
                error = null,
                examSession = null,
                examResult = null,
                examSelectedIndex = null,
                examAnswers = emptyMap(),
                examIndex = 0,
                examLevel = level,
                // The limit block names the section that was refused, and for
                // an exam that section is the test centre.
                pendingTool = EXAM_TOOL,
                adAccessRef = if (adSupported) accessRef else "",
            )
        }
        viewModelScope.launch {
            when (
                val result = repository.examStart(
                    level = level,
                    language = language,
                    accessRef = accessRef,
                    adSupported = adSupported,
                )
            ) {
                is ApiResult.Success -> _state.update {
                    it.copy(
                        isStarting = false,
                        examSession = result.value.session,
                        examIndex = 0,
                    )
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isStarting = false, error = result.error)
                }
            }
        }
    }

    fun selectExamOption(index: Int) {
        if (_state.value.examSelectedIndex != null) return
        _state.update { it.copy(examSelectedIndex = index) }
    }

    fun advanceExam(language: String) {
        val current = _state.value
        val session = current.examSession ?: return
        val question = session.questions.getOrNull(current.examIndex) ?: return
        val selected = current.examSelectedIndex ?: return
        val nextAnswers = current.examAnswers + (question.id to selected)
        if (current.examIndex < session.questions.lastIndex) {
            _state.update {
                it.copy(
                    examIndex = current.examIndex + 1,
                    examSelectedIndex = null,
                    examAnswers = nextAnswers,
                )
            }
            return
        }
        _state.update { it.copy(isCompleting = true, examAnswers = nextAnswers, error = null) }
        viewModelScope.launch {
            when (
                val result = repository.examComplete(
                    sessionId = session.id,
                    level = session.level,
                    language = language,
                    answers = nextAnswers,
                )
            ) {
                is ApiResult.Success -> _state.update {
                    it.copy(isCompleting = false, examResult = result.value)
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isCompleting = false, error = result.error)
                }
            }
        }
    }

    fun resetExam() {
        _state.update {
            it.copy(
                examSession = null,
                examIndex = 0,
                examSelectedIndex = null,
                examAnswers = emptyMap(),
                examResult = null,
                examLevel = "",
                error = null,
            )
        }
        loadMistakes()
    }

    fun selectPracticeOption(index: Int) {
        if (_state.value.selectedIndex != null) return
        _state.update { it.copy(selectedIndex = index) }
    }

    fun advancePractice(language: String) {
        val current = _state.value
        val session = current.session ?: return
        val question = session.questions.getOrNull(current.questionIndex) ?: return
        val selected = current.selectedIndex ?: return
        val nextAnswers = current.answers + (question.id to selected)
        val last = current.questionIndex >= session.questions.lastIndex
        if (!last) {
            _state.update {
                it.copy(
                    questionIndex = current.questionIndex + 1,
                    selectedIndex = null,
                    answers = nextAnswers,
                )
            }
            return
        }
        _state.update { it.copy(isCompleting = true, answers = nextAnswers, error = null) }
        viewModelScope.launch {
            when (
                val result = repository.practiceComplete(
                    sessionId = session.id,
                    mode = session.mode,
                    level = session.level,
                    language = language,
                    skill = session.skill,
                    answers = nextAnswers,
                    // A session an ad opened must be finished the same way,
                    // or the server judges it against the daily limit and the
                    // learner loses a practice they already completed.
                    accessRef = current.adAccessRef,
                    adSupported = current.adAccessRef.isNotBlank(),
                )
            ) {
                is ApiResult.Success -> _state.update {
                    it.copy(isCompleting = false, result = result.value)
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isCompleting = false, error = result.error)
                }
            }
        }
    }

    fun resetPractice() {
        _state.update {
            it.copy(
                session = null,
                questionIndex = 0,
                selectedIndex = null,
                answers = emptyMap(),
                result = null,
                error = null,
            )
        }
        loadMistakes()
    }

    fun startMistakeReview() {
        if (_state.value.isStarting) return
        _state.update {
            it.copy(
                isStarting = true,
                error = null,
                reviewSession = null,
                reviewResult = null,
                reviewFeedback = null,
                reviewAnswers = emptyMap(),
            )
        }
        viewModelScope.launch {
            when (val result = repository.startMistakeReview()) {
                is ApiResult.Success -> _state.update {
                    it.copy(
                        isStarting = false,
                        reviewSession = result.value.session,
                        reviewIndex = 0,
                    )
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isStarting = false, error = result.error)
                }
            }
        }
    }

    fun answerReview(index: Int) {
        val current = _state.value
        if (current.reviewFeedback != null || current.reviewSelectedIndex != null) return
        val session = current.reviewSession ?: return
        val question = session.questions.getOrNull(current.reviewIndex) ?: return
        _state.update { it.copy(reviewSelectedIndex = index, error = null) }
        viewModelScope.launch {
            when (
                val result = repository.answerMistakeReview(
                    sessionId = session.id,
                    questionId = question.id,
                    selectedIndex = index,
                )
            ) {
                is ApiResult.Success -> _state.update {
                    it.copy(
                        reviewFeedback = result.value,
                        reviewAnswers = it.reviewAnswers + (question.id to index),
                    )
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(
                        reviewSelectedIndex = null,
                        error = result.error,
                    )
                }
            }
        }
    }

    fun advanceReview() {
        val current = _state.value
        val session = current.reviewSession ?: return
        if (current.reviewFeedback == null) return
        val last = current.reviewIndex >= session.questions.lastIndex
        if (!last) {
            _state.update {
                it.copy(
                    reviewIndex = current.reviewIndex + 1,
                    reviewSelectedIndex = null,
                    reviewFeedback = null,
                )
            }
            return
        }
        _state.update { it.copy(isCompleting = true, error = null) }
        viewModelScope.launch {
            when (
                val result = repository.completeMistakeReview(
                    sessionId = session.id,
                    answers = current.reviewAnswers,
                )
            ) {
                is ApiResult.Success -> _state.update {
                    it.copy(isCompleting = false, reviewResult = result.value)
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isCompleting = false, error = result.error)
                }
            }
        }
    }

    fun resetReview() {
        _state.update {
            it.copy(
                reviewSession = null,
                reviewIndex = 0,
                reviewSelectedIndex = null,
                reviewFeedback = null,
                reviewAnswers = emptyMap(),
                reviewResult = null,
                error = null,
            )
        }
        loadMistakes()
    }

    class Factory(
        private val repository: FeatureRepository,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            PracticeViewModel(repository) as T
    }
}
