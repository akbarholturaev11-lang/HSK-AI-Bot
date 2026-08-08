package com.pomp.hskai.domain.model

/**
 * A parsed Course v3 mini-lesson.
 *
 * Card content is already resolved to the learner's language; the renderer
 * never has to know about the `{uz, ru, tj}` payload shape.
 */
data class Lesson(
    val level: String,
    val order: Int,
    val sourceLesson: Int,
    val part: Int,
    val partCount: Int,
    val isCheckpoint: Boolean,
    val title: String,
    val subtitle: String,
    val sections: List<LessonSection>,
) {
    val cards: List<LessonCard> get() = sections.flatMap { it.cards }

    /** Cards that have a right answer and therefore count toward accuracy. */
    val gradedCards: List<LessonCard> get() = cards.filter { it.isGraded }
}

data class LessonSection(
    /** Server-assigned, used to build `material_ref`. */
    val sectionNo: Int,
    val title: String,
    /** `practice`, `dialog`, `retention_review`, … There is no `type` field. */
    val purpose: String,
    val cards: List<LessonCard>,
)

sealed interface LessonCard {
    /**
     * `lesson:<level>:<order>:section:<section_no>:card:<1-based index>`.
     *
     * The only thing the client reports about a mistake. The server rebuilds
     * the prompt, the options and the right answer from this reference, so a
     * tampered client cannot forge material.
     */
    val materialRef: String

    /** Whether a wrong choice here should be recorded as a mistake. */
    val isGraded: Boolean get() = false
}

/** Which stimulus a multiple-choice card presents. */
enum class ChoiceKind {
    MEANING,
    TRANSLATION,
    HANZI,
    PINYIN,
    QUICK_QUIZ,
    GAP_FILL,
    LISTENING,
    DIALOG_CLOZE,
}

data class DialogLine(
    val speaker: String,
    val text: String,
    val isBlank: Boolean,
)

/**
 * Every multiple-choice card. They grade identically and differ only in what
 * they show above the options, so the difference is [kind] plus the optional
 * stimulus fields rather than eight near-identical classes.
 */
data class ChoiceCard(
    override val materialRef: String,
    val kind: ChoiceKind,
    val title: String,
    val prompt: String,
    val options: List<String>,
    val correctIndex: Int,
    val explanation: String,
    /** `gap_fill`: the sentence containing `____`. */
    val sentence: String? = null,
    /** `listening_choice`: the phrase to speak, and its pinyin. */
    val audioText: String? = null,
    val audioPinyin: String? = null,
    /** `dialog_cloze`: the dialogue with one line left blank. */
    val lines: List<DialogLine> = emptyList(),
    /** Retention review deck: `previous` or `current`. */
    val reviewOrigin: String? = null,
) : LessonCard {
    override val isGraded: Boolean get() = true

    val isReviewCard: Boolean get() = reviewOrigin != null

    fun isCorrect(selectedIndex: Int): Boolean = selectedIndex == correctIndex
}

/** A new word being introduced. Celebration card, not a question. */
data class NewWordCard(
    override val materialRef: String,
    val number: Int,
    val hanzi: String,
    val pinyin: String,
    val partOfSpeech: String,
    val meaning: String,
) : LessonCard

data class GrammarExample(
    val hanzi: String,
    val pinyin: String,
    val translation: String,
)

data class GrammarCard(
    override val materialRef: String,
    val number: Int,
    val title: String,
    val titleZh: String,
    val rule: String,
    val examples: List<GrammarExample>,
) : LessonCard

/**
 * Speak-after-the-teacher card.
 *
 * Never graded and always skippable: the existing course deliberately does not
 * let pronunciation soft-lock a learner who cannot speak right now.
 */
data class PronunciationCard(
    override val materialRef: String,
    val phrase: String,
    val pinyin: String,
    val translation: String,
) : LessonCard

data class MatchPairsCard(
    override val materialRef: String,
    /** Hanzi to meaning, already localized. */
    val pairs: List<Pair<String, String>>,
    val explanation: String,
) : LessonCard {
    override val isGraded: Boolean get() = true
}

/** Build the Chinese sentence from Hanzi tiles. */
data class SentenceBuilderCard(
    override val materialRef: String,
    /** The meaning to express, in the learner's language. */
    val promptSentence: String,
    val tokens: List<String>,
    val answerTokens: List<String>,
    val explanation: String,
) : LessonCard {
    override val isGraded: Boolean get() = true

    fun isCorrect(built: List<String>): Boolean = built == answerTokens
}

/** Hear the Chinese, build the translation from native-language tiles. */
data class ReverseBuilderCard(
    override val materialRef: String,
    val hanzi: String,
    val pinyin: String,
    val translation: String,
    val tokens: List<String>,
    val answerTokens: List<String>,
    val explanation: String,
) : LessonCard {
    override val isGraded: Boolean get() = true

    fun isCorrect(built: List<String>): Boolean = built == answerTokens
}

/**
 * A card type this build does not know how to render.
 *
 * It is shown as a recoverable "not supported" state and is never graded, so
 * new server-side content can never be silently skipped or auto-marked
 * correct by an older client.
 */
data class UnsupportedCard(
    override val materialRef: String,
    val rawType: String,
) : LessonCard
