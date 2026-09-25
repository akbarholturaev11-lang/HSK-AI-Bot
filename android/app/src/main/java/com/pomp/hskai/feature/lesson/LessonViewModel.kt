package com.pomp.hskai.feature.lesson

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.audio.LessonAudioPlayer
import com.pomp.hskai.core.audio.VoiceRecorder
import com.pomp.hskai.core.hanzi.CharacterStrokes
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.settings.LessonResumeStore
import com.pomp.hskai.data.api.CourseCompleteResponse
import com.pomp.hskai.data.api.CourseGamificationDto
import com.pomp.hskai.data.api.CourseMistakeDto
import com.pomp.hskai.data.api.RatingResponse
import com.pomp.hskai.data.api.VoicePronounceResponse
import com.pomp.hskai.data.repository.CourseRepository
import com.pomp.hskai.data.repository.FeatureRepository
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
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/** What the learner has done with the card currently on screen. */
sealed interface AnswerState {
    data object Unanswered : AnswerState
    data class Checked(
        val isCorrect: Boolean,
        val explanation: String,
        /**
         * What the learner actually picked or built, as they saw it. Only the
         * AI chat reads it, so a question like "what was my mistake?" is asked
         * about the real answer. Grading and the mistake record never use it.
         */
        val chosen: String = "",
    ) : AnswerState
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
        /** Exact weekly leaderboard positions around this completion. */
        val rankBefore: Int = 0,
        val rankAfter: Int = 0,
        /** Wall-clock seconds spent in the deck, measured on device only. */
        val elapsedSeconds: Int = 0,
    ) : LessonOutcome

    /** The free half-preview ran out. Completion is not possible. */
    data object PreviewExhausted : LessonOutcome

    data class Failed(val error: ApiError) : LessonOutcome
}

/** One row of the rank-up board: the Mini App shows three, centred on you. */
data class LessonRankRow(
    val rank: Int,
    val avatar: String,
    val name: String,
    val xp: Int,
    val isMe: Boolean,
)

/**
 * The rank-up board. [passedName] is the learner the lesson overtook, which is
 * what the headline names — without it the Mini App shows nothing at all.
 */
data class LessonRankBoard(
    val rows: List<LessonRankRow>,
    val passedName: String,
)

data class LessonUiState(
    val isLoading: Boolean = true,
    val lesson: Lesson? = null,
    val cardIndex: Int = 0,
    val answer: AnswerState = AnswerState.Unanswered,
    val correctCount: Int = 0,
    val gradedAnswered: Int = 0,
    /** Consecutive correct answers, matching Mini App Flow.streak. */
    val answerStreak: Int = 0,
    val isSubmitting: Boolean = false,
    val previewCardLimit: Int = 0,
    val completionAllowed: Boolean = false,
    val completionError: String? = null,
    /**
     * Opened from the phone's own copy because the request never reached the
     * server. The cards are the ones already paid for; completing still needs a
     * connection, and fails into the existing retry CTA until it comes back.
     */
    val isStale: Boolean = false,
    val isAudioLoading: Boolean = false,
    val audioError: ApiError? = null,
    val isPronunciationRecording: Boolean = false,
    val isPronunciationScoring: Boolean = false,
    val pronunciationScore: Int? = null,
    val pronunciationError: ApiError? = null,
    val outcome: LessonOutcome = LessonOutcome.InProgress,
    /**
     * The three leaderboard rows the rank-up celebration shows, fetched once
     * after a completion that actually moved the learner up. Null until it
     * arrives, and null forever when it did not: the Mini App shows no board
     * it cannot name either.
     */
    val rankBoard: LessonRankBoard? = null,
    val error: ApiError? = null,
    /**
     * The Mini App's five hearts. A wrong answer costs one and the count is
     * shown in the lesson header. It never ends the lesson — the learner is
     * here to learn, not to lose — but it makes a careless streak visible.
     */
    val hearts: Int = MAX_HEARTS,
    /** Stroke outlines for the character the pencil is showing, if any. */
    val writerChar: WriterTarget? = null,
    /** Which character of [writerChar] the sheet is on; a phrase has several. */
    val writerIndex: Int = 0,
    val writerStrokes: CharacterStrokes? = null,
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
) {
    /**
     * The characters the sheet can write, in order.
     *
     * Punctuation and spaces are dropped: they have no stroke data, and a
     * page that says «3 / 8» where two of the eight cannot be drawn is
     * counting things it will not show.
     */
    val characters: List<String>
        get() = hanzi.filter { it.isHanzi() }.map { it.toString() }
}

/** CJK ideographs, the range hanzi-writer has data for. */
private fun Char.isHanzi(): Boolean = code in 0x3400..0x9FFF || code in 0xF900..0xFAFF

/** Small seam that keeps the microphone flow independently testable. */
interface PronunciationScorer {
    suspend fun score(
        target: String,
        targetPinyin: String,
        language: String,
        level: String,
        audioDataUrl: String,
    ): ApiResult<VoicePronounceResponse>
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
    private val audioPlayer: LessonAudioPlayer,
    /**
     * Only the rank-up board needs it, and only after a completion that moved
     * the learner up. Absent in tests, where no board is asserted.
     */
    private val featureRepository: FeatureRepository? = null,
    private val pronunciationScorer: PronunciationScorer? = null,
    /** Records pronunciation cards; absent only in unit tests that do not speak. */
    private val voiceRecorder: VoiceRecorder? = null,
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
    /** Set when the deck loads; the completion screen reports how long it took. */
    private var startedAtMs: Long = 0

    private fun elapsedSeconds(): Int {
        if (startedAtMs <= 0L) return 0
        val seconds = (android.os.SystemClock.elapsedRealtime() - startedAtMs) / 1000L
        // A resumed lesson can span hours of idle time; keep the tile believable.
        return seconds.coerceIn(0L, 3600L).toInt()
    }
    private var audioJob: Job? = null
    private var pronunciationJob: Job? = null

    /** The stroke fetch for the character the writing sheet is on. */
    private var writerJob: Job? = null

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
        stopPronunciation()
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
        stopPronunciation()
        _state.update { it.copy(isAudioLoading = false, audioError = null) }
    }

    fun load() {
        if (activeAttemptKey == null) return
        val generation = ++loadGeneration
        startedAtMs = android.os.SystemClock.elapsedRealtime()
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
                        isStale = snapshot.isStale,
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
        record(correct, card.explanation, chosen = card.options.getOrNull(selectedIndex).orEmpty())
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
        record(correct, explanation, chosen = built.joinToString(" "))
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
        record(
            wrongAttempts.isEmpty(),
            card.explanation,
            chosen = wrongAttempts.mapNotNull { (left, right) ->
                val first = card.pairs.getOrNull(left)?.first ?: return@mapNotNull null
                val second = card.pairs.getOrNull(right)?.second ?: return@mapNotNull null
                "$first = $second"
            }.joinToString(", "),
        )
    }

    /** New word, grammar and unsupported cards just advance. */
    fun acknowledge() {
        if (_state.value.isAnswered) return
        advance()
    }

    /** Records and scores the phrase shown by the current pronunciation card. */
    fun speakPronunciation() {
        val current = _state.value
        val card = current.currentCard as? PronunciationCard ?: return
        if (current.isAnswered || current.isPronunciationRecording || current.isPronunciationScoring) return
        val recorder = voiceRecorder ?: run {
            _state.update { it.copy(pronunciationError = ApiError.Unknown) }
            return
        }
        val scorer = pronunciationScorer
        if (scorer == null && featureRepository == null) {
            _state.update { it.copy(pronunciationError = ApiError.Unknown) }
            return
        }

        stopAudio()
        runCatching { recorder.start() }.onFailure {
            _state.update { it.copy(pronunciationError = ApiError.Unknown) }
            return
        }
        _state.update {
            it.copy(
                isAudioLoading = false,
                audioError = null,
                isPronunciationRecording = true,
                pronunciationScore = null,
                pronunciationError = null,
            )
        }
        val attemptKey = activeAttemptKey ?: run {
            recorder.cancel()
            return
        }
        val cardIndex = current.cardIndex
        pronunciationJob = viewModelScope.launch {
            delay(PRONUNCIATION_WINDOW_MILLIS)
            val recording = runCatching { recorder.stop() }.getOrElse {
                if (activeAttemptKey == attemptKey) _state.update {
                    it.copy(isPronunciationRecording = false, pronunciationError = ApiError.Unknown)
                }
                return@launch
            }
            if (activeAttemptKey != attemptKey || _state.value.cardIndex != cardIndex) return@launch
            _state.update { it.copy(isPronunciationRecording = false, isPronunciationScoring = true) }
            when (
                val result = scorer?.score(
                    card.phrase,
                    card.pinyin,
                    language.backendCode,
                    level,
                    recording.dataUrl,
                ) ?: featureRepository!!.scorePronunciation(
                    target = card.phrase,
                    targetPinyin = card.pinyin,
                    language = language.backendCode,
                    level = level,
                    audioDataUrl = recording.dataUrl,
                )
            ) {
                is ApiResult.Success -> if (activeAttemptKey == attemptKey && _state.value.cardIndex == cardIndex) {
                    val score = result.value.score
                    val passed = result.value.ok && score >= PRONUNCIATION_PASS_SCORE
                    val detail = result.value.heard.ifBlank { result.value.message }
                    _state.update {
                        it.copy(
                            isPronunciationScoring = false,
                            pronunciationScore = score,
                            pronunciationError = null,
                            // Pronunciation cards remain ungraded/skippable, but
                            // feedback now owns the Next button after a real try.
                            answer = AnswerState.Checked(
                                isCorrect = passed,
                                explanation = listOf("$score%", detail)
                                    .filter { text -> text.isNotBlank() }
                                    .joinToString(" · "),
                            ),
                        )
                    }
                }

                is ApiResult.Failure -> if (activeAttemptKey == attemptKey && _state.value.cardIndex == cardIndex) {
                    _state.update {
                        it.copy(isPronunciationScoring = false, pronunciationError = result.error)
                    }
                }
            }
        }
    }

    /** "I cannot speak now" skips safely without leaving the recorder open. */
    fun skipPronunciation() {
        if (_state.value.currentCard !is PronunciationCard) return
        advance()
    }

    /**
     * Opens the writing sheet for [target], on its first character.
     *
     * A listening card's target is the whole sentence that was said, so the
     * sheet is usually asked for several characters at once. It writes them
     * one at a time — the Mini App's `hsk-lugat` page does the same, because
     * a stroke set belongs to one character and a sentence drawn into one
     * box is a sentence drawn on top of itself.
     */
    fun openWriter(target: WriterTarget) {
        writerJob?.cancel()
        _state.update {
            it.copy(
                writerChar = target,
                writerIndex = 0,
                writerStrokes = null,
                isWriterLoading = false,
            )
        }
        showWriterCharacter(0)
    }

    /** Moves the sheet to [index] of the open target and fetches its strokes. */
    fun showWriterCharacter(index: Int) {
        val target = _state.value.writerChar ?: return
        val characters = target.characters
        if (index !in characters.indices) return
        _state.update {
            it.copy(writerIndex = index, writerStrokes = null, isWriterLoading = true)
        }
        writerJob?.cancel()
        writerJob = viewModelScope.launch {
            // Null rather than an empty set: the sheet then shows the plain
            // character instead of an empty writing box.
            val strokes = when (val result = repository.strokes(characters[index])) {
                is ApiResult.Success -> result.value
                is ApiResult.Failure -> null
            }
            _state.update {
                // A tap on the next character while this one was still loading
                // must not have its answer land on the character now showing.
                if (it.writerIndex == index) {
                    it.copy(writerStrokes = strokes, isWriterLoading = false)
                } else {
                    it
                }
            }
        }
    }

    fun closeWriter() {
        writerJob?.cancel()
        writerJob = null
        _state.update {
            it.copy(writerChar = null, writerIndex = 0, writerStrokes = null, isWriterLoading = false)
        }
    }

    /** Keeps the resume point in step with the card on screen. */
    private fun rememberPosition(index: Int) {
        val store = resumeStore ?: return
        viewModelScope.launch { store.setLessonResumeIndex(level, lessonOrder, index) }
    }

    private fun record(correct: Boolean, explanation: String, chosen: String = "") {
        _state.update {
            it.copy(
                answer = AnswerState.Checked(correct, explanation, chosen),
                correctCount = it.correctCount + if (correct) 1 else 0,
                gradedAnswered = it.gradedAnswered + 1,
                answerStreak = if (correct) it.answerStreak + 1 else 0,
                hearts = if (correct) it.hearts else (it.hearts - 1).coerceAtLeast(0),
            )
        }
    }

    /** Moves past the feedback bar to the next card, or finishes the lesson. */
    fun advance() {
        stopPronunciation()
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
                pronunciationScore = null,
                pronunciationError = null,
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
            if (result is ApiResult.Success) loadRankBoard(result.value, attemptKey)
            _state.update { current ->
                when (result) {
                    is ApiResult.Success -> current.copy(
                        isSubmitting = false,
                        outcome = LessonOutcome.Completed(
                            correct = current.correctCount,
                            graded = current.gradedAnswered,
                            duplicate = result.value.duplicate,
                            gamification = result.value.gamification,
                            rankBefore = result.value.rankBefore,
                            rankAfter = result.value.rankAfter,
                            elapsedSeconds = elapsedSeconds(),
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

    /**
     * The rank-up board, fetched once after a completion that actually moved
     * the learner up the weekly league.
     *
     * The move itself is the server's answer — `rank_before` and `rank_after`
     * from the completion — never something inferred from XP. The board is
     * only fetched to put names and numbers on it; if the request fails the
     * celebration simply skips that scene, exactly as the Mini App does when
     * it cannot confirm who was passed.
     */
    private fun loadRankBoard(completion: CourseCompleteResponse, attemptKey: String) {
        val repo = featureRepository ?: return
        val before = completion.rankBefore
        val after = completion.rankAfter
        if (completion.duplicate || before <= 0 || after <= 0 || after >= before) return
        viewModelScope.launch {
            val result = repo.rating()
            if (activeAttemptKey != attemptKey) return@launch
            val board = (result as? ApiResult.Success)?.value?.let(::buildRankBoard) ?: return@launch
            _state.update { it.copy(rankBoard = board) }
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

    private fun stopPronunciation() {
        pronunciationJob?.cancel()
        pronunciationJob = null
        voiceRecorder?.cancel()
        _state.update {
            it.copy(isPronunciationRecording = false, isPronunciationScoring = false)
        }
    }

    private fun addMistake(mistake: CourseMistakeDto) {
        if (mistakes.size < MAX_MISTAKES_PER_COMPLETION) mistakes += mistake
    }

    override fun onCleared() {
        activeAttemptKey = null
        loadGeneration++
        stopAudio()
        stopPronunciation()
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
        private val featureRepository: FeatureRepository? = null,
        private val voiceRecorder: VoiceRecorder,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = LessonViewModel(
            repository = repository,
            audioPlayer = audioPlayer,
            featureRepository = featureRepository,
            voiceRecorder = voiceRecorder,
            level = level,
            lessonOrder = lessonOrder,
            language = language,
            accessRef = accessRef,
            resumeStore = resumeStore,
        ) as T
    }

    private fun buildRankBoard(rating: RatingResponse): LessonRankBoard? {
        val rows = rating.leaderboard
        val meIndex = rows.indexOfFirst { it.isCurrentUser }
        if (meIndex < 0) return null
        // The one directly below is the one this lesson overtook. Without a
        // name for them there is nothing to celebrate, so no board is built.
        val passed = rows.getOrNull(meIndex + 1) ?: return null
        val above = rows.getOrNull(meIndex - 1)
        val board = listOfNotNull(above, rows[meIndex], passed).map { entry ->
            LessonRankRow(
                rank = entry.rank,
                avatar = entry.name.take(1).uppercase().ifBlank { "阿" },
                name = entry.name,
                xp = entry.xp,
                isMe = entry.isCurrentUser,
            )
        }
        return LessonRankBoard(rows = board, passedName = passed.name)
    }

    companion object {
        /** Matches DesktopCourseCompleteRequest.mistakes.max_length. */
        const val MAX_MISTAKES_PER_COMPLETION = 50
        const val PRONUNCIATION_WINDOW_MILLIS = 2_600L
        const val PRONUNCIATION_PASS_SCORE = 60
    }
}
