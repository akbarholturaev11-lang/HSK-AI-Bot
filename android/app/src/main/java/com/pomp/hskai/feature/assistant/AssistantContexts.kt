package com.pomp.hskai.feature.assistant

import com.pomp.hskai.data.api.RatingEntryDto
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.GrammarCard
import com.pomp.hskai.domain.model.Lesson
import com.pomp.hskai.domain.model.MatchPairsCard
import com.pomp.hskai.domain.model.NewWordCard
import com.pomp.hskai.domain.model.PronunciationCard
import com.pomp.hskai.domain.model.ReverseBuilderCard
import com.pomp.hskai.domain.model.SentenceBuilderCard
import com.pomp.hskai.domain.model.UnsupportedCard
import com.pomp.hskai.feature.course.CourseUiState
import com.pomp.hskai.feature.dictionary.DictionaryUiState
import com.pomp.hskai.feature.lesson.AnswerState
import com.pomp.hskai.feature.lesson.LessonOutcome
import com.pomp.hskai.feature.lesson.LessonUiState
import com.pomp.hskai.feature.practice.DrillMode
import com.pomp.hskai.feature.practice.PracticeUiState
import com.pomp.hskai.feature.practice.WordDrillUiState
import com.pomp.hskai.feature.profile.ProfileUiState
import com.pomp.hskai.feature.rating.ChallengeRunUiState
import com.pomp.hskai.feature.rating.RatingTab
import com.pomp.hskai.feature.rating.RatingUiState
import com.pomp.hskai.feature.voice.VoiceSpeaker
import com.pomp.hskai.feature.voice.VoiceUiState

fun courseAssistantContext(state: CourseUiState): ScreenContext {
    val map = state.map
    val current = map?.currentLesson
    val details = buildString {
        if (map == null) {
            appendLine(if (state.isLoading) "Course map is loading." else "Course map is unavailable.")
        } else {
            appendLine("Level: ${map.level.uppercase()}")
            appendLine("Progress: ${map.progress.completedLessons}/${map.totalLessons} lessons")
            appendLine("XP: today ${map.progress.dailyXp}, weekly ${map.progress.weeklyXp}, streak ${map.progress.streak}")
            current?.let {
                appendLine("Current lesson: ${it.order}, part ${it.part}/${it.partCount}")
                appendLine("Preview: ${it.hanziPreview} · ${it.pinyinPreview} · ${it.subtitle}")
                appendLine("Access: ${it.access::class.simpleName}")
            }
            map.today?.let { today ->
                appendLine("Today: ${today.done}/${today.total} tasks, ${today.doneXp}/${today.goalXp} XP")
            }
        }
    }
    return ScreenContext(
        screen = "course",
        title = current?.let { "${map?.level?.uppercase()} · ${it.order}-dars" } ?: "Kurs",
        details = details.trim(),
        materialRef = current?.let { "lesson:${map?.level}:${it.order}" }.orEmpty(),
        answerState = if (state.error != null) "error" else "viewing",
    )
}

fun lessonAssistantContext(state: LessonUiState, attemptId: String): ScreenContext {
    val lesson = state.lesson
    val card = state.currentCard
    val answer = state.answer
    val details = buildString {
        if (lesson == null || card == null) {
            appendLine(if (state.isLoading) "Lesson is loading." else "Lesson is unavailable.")
        } else {
            appendLine("Lesson: ${lesson.level.uppercase()} ${lesson.order}, part ${lesson.part}/${lesson.partCount}")
            appendLine("Section: ${state.currentSectionTitle}")
            appendLine("Card: ${state.cardIndex + 1}/${state.totalCards}")
            appendLine(card.visibleDescription(answer))
            when (answer) {
                AnswerState.Unanswered -> appendLine("Answer is not checked yet; do not reveal the solution.")
                is AnswerState.Checked -> {
                    appendLine("Checked: ${if (answer.isCorrect) "correct" else "wrong"}")
                    // "What was my mistake?" needs the answer the learner actually gave.
                    if (answer.chosen.isNotBlank()) appendLine("Learner answer: ${answer.chosen}")
                    if (answer.explanation.isNotBlank()) appendLine("Explanation shown: ${answer.explanation}")
                }
            }
            when (val outcome = state.outcome) {
                is LessonOutcome.Completed -> appendLine("Lesson completed: ${outcome.correct}/${outcome.graded}")
                LessonOutcome.PreviewExhausted -> appendLine("Preview is exhausted.")
                is LessonOutcome.Failed -> appendLine("Completion failed safely.")
                LessonOutcome.InProgress -> Unit
            }
        }
    }
    return ScreenContext(
        screen = "lesson",
        title = lesson?.let { "${it.level.uppercase()} · ${it.order}-dars · ${state.currentSectionTitle}" } ?: "Dars",
        details = details.trim(),
        materialRef = card?.materialRef.orEmpty(),
        attemptId = attemptId,
        revision = "${lesson?.level}:${lesson?.order}:${state.cardIndex}:${state.answer::class.simpleName}",
        answerState = if (answer is AnswerState.Checked) "checked" else "unanswered",
    )
}

private fun com.pomp.hskai.domain.model.LessonCard.visibleDescription(answer: AnswerState): String = when (this) {
    is NewWordCard -> "New word: $hanzi · $pinyin · $meaning"
    is GrammarCard -> buildString {
        appendLine("Grammar: $title ${titleZh}".trim())
        appendLine("Rule: $rule")
        examples.take(2).forEach { appendLine("Example: ${it.hanzi} · ${it.pinyin} · ${it.translation}") }
    }.trim()
    is PronunciationCard -> "Pronunciation: $phrase · $pinyin · $translation"
    is ChoiceCard -> buildString {
        appendLine("Question type: ${kind.name.lowercase()}")
        if (title.isNotBlank()) appendLine("Title: $title")
        if (prompt.isNotBlank()) appendLine("Prompt: $prompt")
        sentence?.takeIf { it.isNotBlank() }?.let { appendLine("Sentence: $it") }
        audioText?.takeIf { it.isNotBlank() }?.let { appendLine("Audio text: $it · ${audioPinyin.orEmpty()}") }
        if (lines.isNotEmpty()) appendLine("Dialogue: ${lines.joinToString(" / ") { line -> if (line.isBlank) "${line.speaker}: ____" else "${line.speaker}: ${line.text}" }}")
        appendLine("Visible options: ${options.joinToString(" | ")}")
        if (answer is AnswerState.Checked && correctIndex in options.indices) appendLine("Correct option shown: ${options[correctIndex]}")
    }.trim()
    is MatchPairsCard -> buildString {
        appendLine("Match visible pairs.")
        appendLine("Items: ${pairs.joinToString(" | ") { it.first }}")
        if (answer is AnswerState.Checked) appendLine("Pairs shown: ${pairs.joinToString(" | ") { "${it.first} = ${it.second}" }}")
    }.trim()
    is SentenceBuilderCard -> buildString {
        appendLine("Build Chinese sentence for: $promptSentence")
        appendLine("Visible tokens: ${tokens.joinToString(" ")}")
        if (answer is AnswerState.Checked) appendLine("Correct order shown: ${answerTokens.joinToString(" ")}")
    }.trim()
    is ReverseBuilderCard -> buildString {
        appendLine("Hear/see: $hanzi · $pinyin")
        appendLine("Visible translation target: $translation")
        appendLine("Visible tokens: ${tokens.joinToString(" ")}")
        if (answer is AnswerState.Checked) appendLine("Correct order shown: ${answerTokens.joinToString(" ")}")
    }.trim()
    is UnsupportedCard -> "Unsupported lesson card type: $rawType"
}

fun practiceAssistantContext(state: PracticeUiState, level: String, mistakesOpen: Boolean): ScreenContext {
    val exam = state.examSession
    val examQuestion = exam?.questions?.getOrNull(state.examIndex)
    val practice = state.session
    val practiceQuestion = practice?.questions?.getOrNull(state.questionIndex)
    val review = state.reviewSession
    val reviewQuestion = review?.questions?.getOrNull(state.reviewIndex)
    val details = buildString {
        when {
            state.examResult != null -> appendLine("Exam result: ${state.examResult.score}/${state.examResult.total}, ${state.examResult.percent}%, pass score ${state.examResult.passScore}")
            exam != null && examQuestion != null -> {
                appendLine("Active exam. Give usage help only; do not solve.")
                appendLine("Level: ${exam.level}, question ${state.examIndex + 1}/${exam.questions.size}")
                appendLine("Section: ${examQuestion.section}, format: ${examQuestion.format}")
                appendLine("Prompt: ${examQuestion.prompt}")
                if (examQuestion.sentence.isNotBlank()) appendLine("Sentence: ${examQuestion.sentence}")
                if (examQuestion.audioText.isNotBlank()) appendLine("Audio text is present.")
                appendLine("Options are visible, but solution must stay hidden during active exam.")
            }
            state.result != null -> appendLine("Practice result: ${state.result.score}/${state.result.total}, ${state.result.percent}%. Recommendation: ${state.result.recommendation}")
            practice != null && practiceQuestion != null -> {
                appendLine("Practice: ${practice.mode}/${practice.skill}, ${practice.level}, question ${state.questionIndex + 1}/${practice.questions.size}")
                appendLine("Prompt: ${practiceQuestion.prompt}")
                if (practiceQuestion.sentence.isNotBlank()) appendLine("Sentence: ${practiceQuestion.sentence}")
                if (practiceQuestion.pinyin.isNotBlank()) appendLine("Pinyin: ${practiceQuestion.pinyin}")
                appendLine("Visible options: ${practiceQuestion.options.joinToString(" | ")}")
                state.selectedIndex?.let { appendLine("Selected: ${practiceQuestion.options.getOrNull(it).orEmpty()}") }
            }
            state.reviewResult != null -> appendLine("Mistake review result: ${state.reviewResult.score}/${state.reviewResult.total}")
            review != null && reviewQuestion != null -> {
                appendLine("Mistake review question ${state.reviewIndex + 1}/${review.questions.size}")
                appendLine("Prompt: ${reviewQuestion.prompt}")
                if (reviewQuestion.sentence.isNotBlank()) appendLine("Sentence: ${reviewQuestion.sentence}")
                appendLine("Visible options: ${reviewQuestion.options.joinToString(" | ")}")
                state.reviewFeedback?.let { appendLine("Feedback is already shown.") }
            }
            mistakesOpen -> appendLine("Mistakes overview: ${state.mistakes?.summary?.total ?: 0} weak items ready for review.")
            else -> appendLine("Practice home for $level. Sections: dictionary, recognition, pronunciation, test center, mistakes.")
        }
    }
    return ScreenContext(
        screen = if (exam != null && state.examResult == null) "exam" else "practice",
        title = if (exam != null && state.examResult == null) "${exam.level.uppercase()} imtihon" else "Mashq",
        details = details.trim(),
        materialRef = examQuestion?.id ?: practiceQuestion?.id ?: reviewQuestion?.id.orEmpty(),
        attemptId = exam?.id.orEmpty(),
        revision = listOf(level, state.questionIndex, state.reviewIndex, state.examIndex, state.selectedIndex, state.reviewSelectedIndex, state.examSelectedIndex).joinToString(":"),
        answerState = if (exam != null && state.examResult == null) "restricted" else "viewing",
    )
}

fun wordDrillAssistantContext(state: WordDrillUiState): ScreenContext {
    val question = state.current
    val title = if (state.mode == DrillMode.RECOGNITION) "Ieroglif tanish" else "Talaffuz mashqi"
    val details = buildString {
        if (state.finished) appendLine("Drill result: ${state.correctCount}/${state.total}")
        else if (question == null) appendLine(if (state.isLoading) "Drill is loading." else "No drill question is visible.")
        else {
            appendLine("Question ${state.index + 1}/${state.total}")
            appendLine("Word: ${question.hanzi} · ${question.pinyin} · ${question.meaning}")
            if (state.mode == DrillMode.RECOGNITION) appendLine("Visible options: ${question.options.joinToString(" | ")}")
            state.selected?.let { appendLine("Selected: $it") }
            if (state.isAnswered) appendLine("Checked: ${if (state.wasCorrect) "correct" else "wrong"}")
            state.spokenScore?.let { appendLine("Pronunciation score: $it") }
        }
    }
    return ScreenContext("word_drill", title, details.trim(), question?.hanzi.orEmpty(), revision = "${state.mode}:${state.index}:${state.isAnswered}:${state.spokenScore}", answerState = if (state.isAnswered) "checked" else "viewing")
}

fun dictionaryAssistantContext(state: DictionaryUiState): ScreenContext {
    val word = state.selectedWord
    val details = buildString {
        if (word != null) {
            appendLine("Selected word: ${word.hanzi} · ${word.pinyin} · ${word.meaning}")
            appendLine("Level: ${word.level}")
            state.currentCharacter?.let { appendLine("Writing character ${state.characterIndex + 1}: $it") }
            state.visibleStrokeCount?.let { appendLine("Visible stroke step: $it") }
        } else {
            appendLine("Dictionary search query: ${state.query}")
            appendLine("Visible results: ${state.words.take(8).joinToString(" | ") { "${it.hanzi} ${it.pinyin} ${it.meaning}" }}")
        }
    }
    return ScreenContext("dictionary", word?.hanzi ?: "Ieroglif lug'ati", details.trim(), word?.hanzi.orEmpty(), revision = "${state.query}:${word?.hanzi}:${state.characterIndex}:${state.visibleStrokeCount}")
}

fun voiceAssistantContext(state: VoiceUiState, level: String): ScreenContext {
    val details = buildString {
        appendLine("Voice role: ${state.selectedRole}, level: $level")
        state.sessionId?.let { appendLine("Session is active; AI chat must not start recording while practice mic is active.") }
        appendLine("Turns: ${state.turnCount}/${state.maxDialogs}")
        state.lines.takeLast(4).forEach { line ->
            val who = if (line.speaker == VoiceSpeaker.USER) "User" else "Partner"
            appendLine("$who: ${line.text}")
            if (line.hanzi.isNotBlank()) appendLine("Chinese: ${line.hanzi} · ${line.pinyin} · ${line.translation}")
            line.correction?.takeIf { it.isNotBlank() }?.let { appendLine("Correction shown: $it") }
        }
        state.result?.let { appendLine("Voice result is shown: ${it.goodCount} good, ${it.mistakeCount} mistakes, ${it.messageCount} messages.") }
    }
    return ScreenContext("voice", "AI Voice", details.trim(), state.sessionId.orEmpty(), attemptId = state.sessionId.orEmpty(), revision = "${state.sessionId}:${state.turnCount}:${state.result != null}")
}

fun ratingAssistantContext(state: RatingUiState): ScreenContext {
    val rating = state.rating
    val details = buildString {
        appendLine("Rating tab: ${if (state.tab == RatingTab.LEAGUE) "league" else "friends"}")
        if (rating != null) {
            appendLine("League: ${rating.league}, rank ${rating.rank}/${rating.leagueSize}, weekly XP ${rating.weeklyXp}")
            appendLine("Visible leaders: ${rating.leaderboard.take(6).joinToString(" | ") { "#${it.rank} ${it.name} ${it.xp}XP" }}")
        }
        appendLine("Pending challenges: ${state.pendingChallenges.size}, active challenges: ${state.activeChallenges.size}")
        state.challengeDelivery?.let { appendLine("Last challenge delivery: $it") }
    }
    return ScreenContext("rating", "Reyting", details.trim(), revision = "${state.tab}:${state.pendingChallenges.size}:${state.activeChallenges.size}")
}

fun ratingUserAssistantContext(user: RatingEntryDto, league: String, currentWeeklyXp: Int): ScreenContext = ScreenContext(
    screen = "rating_user",
    title = user.name.ifBlank { "Reyting profili" },
    details = "Viewed rating user: ${user.name}, rank #${user.rank}, ${user.xp} XP, league $league. Viewer weekly XP: $currentWeeklyXp.",
    materialRef = user.rank.toString(),
    answerState = "viewing",
)

fun ratingChallengesAssistantContext(state: RatingUiState): ScreenContext = ScreenContext(
    screen = "rating_challenges",
    title = "Bellashuvlar",
    details = "Pending challenges visible: ${state.pendingChallenges.size}. Active challenges visible: ${state.activeChallenges.size}. The user can accept or open a challenge from this list.",
    answerState = "viewing",
)

fun challengeAssistantContext(state: ChallengeRunUiState, opponentName: String): ScreenContext {
    val question = state.questions.getOrNull(state.index)
    val details = buildString {
        if (state.finished) appendLine("Challenge with $opponentName is finished.")
        else {
            appendLine("Active challenge with $opponentName. Give usage help only; do not solve.")
            appendLine("Question ${state.index + 1}/${state.questions.size}")
            question?.let {
                appendLine("Prompt: ${it.prompt}")
                if (it.sentence.isNotBlank()) appendLine("Sentence: ${it.sentence}")
                if (it.audioText.isNotBlank()) appendLine("Audio text is present.")
                appendLine("Options are visible, but solution must stay hidden during active challenge.")
            }
        }
    }
    return ScreenContext("challenge", "Bellashuv", details.trim(), question?.id.orEmpty(), attemptId = state.sessionId, revision = "${state.sessionId}:${state.index}:${state.selected}:${state.finished}", answerState = if (state.finished) "completed" else "restricted")
}

fun profileAssistantContext(state: ProfileUiState): ScreenContext {
    val profile = state.profile
    val details = buildString {
        appendLine("Profile screen.")
        profile?.let {
            appendLine("User: ${it.user.name}, level ${it.user.level}, streak ${it.stats.streak}, total XP ${it.stats.xp}")
            appendLine("Rating: ${it.stats.weeklyXp} weekly XP, league ${it.stats.league}")
            appendLine("Subscription: paid=${it.subscription.isPaid}, state=${it.subscription.status}, until=${it.subscription.until.orEmpty()}")
        }
        state.trial?.let { appendLine("Trial offer eligible: ${it.eligible}, active: ${it.active}") }
    }
    return ScreenContext("profile", "Profil", details.trim(), answerState = if (state.error != null) "error" else "viewing")
}
