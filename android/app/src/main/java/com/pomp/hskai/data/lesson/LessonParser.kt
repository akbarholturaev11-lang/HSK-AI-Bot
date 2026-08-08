package com.pomp.hskai.data.lesson

import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.ChoiceKind
import com.pomp.hskai.domain.model.DialogLine
import com.pomp.hskai.domain.model.GrammarCard
import com.pomp.hskai.domain.model.GrammarExample
import com.pomp.hskai.domain.model.Lesson
import com.pomp.hskai.domain.model.LessonCard
import com.pomp.hskai.domain.model.LessonSection
import com.pomp.hskai.domain.model.MatchPairsCard
import com.pomp.hskai.domain.model.NewWordCard
import com.pomp.hskai.domain.model.PronunciationCard
import com.pomp.hskai.domain.model.ReverseBuilderCard
import com.pomp.hskai.domain.model.SentenceBuilderCard
import com.pomp.hskai.domain.model.UnsupportedCard
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.intOrNull

/**
 * Turns the checked-in Course v3 lesson JSON into domain cards.
 *
 * Hand-written rather than generated, because the payload reuses field names
 * across card types with different shapes:
 *
 *  - `options` is a list of strings, except on `meaning_guess` where it is a
 *    list of `{uz, ru, tj}` objects;
 *  - `sentence` is a plain string on `gap_fill` and a localized object on
 *    `sentence_builder`;
 *  - `tokens` / `answer_tokens` are a flat list on `sentence_builder` and a
 *    per-language object on `reverse_builder`.
 *
 * A generated model would either crash or silently drop content on those.
 *
 * Grading note: `correct_index` ships to the client, exactly as it does for
 * the Mini App and the desktop app, so answers can be checked instantly.
 * That is a UX affordance, not the source of truth — the server rebuilds the
 * material from `material_ref` and never trusts a client-supplied answer.
 */
object LessonParser {

    fun materialRef(
        level: String,
        lessonOrder: Int,
        sectionNo: Int,
        cardNo: Int,
    ): String = "lesson:$level:$lessonOrder:section:$sectionNo:card:$cardNo"

    /**
     * @param payload the `lesson` object from `/api/v3/android/course/lesson/{n}`.
     */
    fun parse(
        payload: JsonObject,
        level: String,
        lessonOrder: Int,
        language: AppLanguage,
    ): Lesson {
        val sections = (payload["sections"] as? JsonArray).orEmpty()
        return Lesson(
            level = level,
            order = lessonOrder,
            sourceLesson = payload.int("source_lesson") ?: 0,
            part = payload.int("part_no") ?: 0,
            partCount = payload.int("part_count") ?: 0,
            isCheckpoint = payload.bool("checkpoint") ?: false,
            title = payload["title"].localized(language),
            subtitle = payload["subtitle"].localized(language),
            sections = sections.mapIndexedNotNull { index, element ->
                val section = element as? JsonObject ?: return@mapIndexedNotNull null
                // The server falls back to the 1-based position when
                // section_no is absent; material_ref must match exactly.
                val sectionNo = section.int("section_no") ?: (index + 1)
                LessonSection(
                    sectionNo = sectionNo,
                    title = section["section_title"].localized(language),
                    purpose = section["section_purpose"].string().orEmpty(),
                    cards = (section["cards"] as? JsonArray).orEmpty()
                        .mapIndexedNotNull { cardIndex, cardElement ->
                            val card = cardElement as? JsonObject
                                ?: return@mapIndexedNotNull null
                            parseCard(
                                card = card,
                                language = language,
                                ref = materialRef(
                                    level = level,
                                    lessonOrder = lessonOrder,
                                    sectionNo = sectionNo,
                                    cardNo = cardIndex + 1,
                                ),
                            )
                        },
                )
            },
        )
    }

    private fun parseCard(
        card: JsonObject,
        language: AppLanguage,
        ref: String,
    ): LessonCard {
        val type = card["type"].string()?.trim()?.lowercase().orEmpty()
        val choiceKind = CHOICE_KINDS[type]
        if (choiceKind != null) return card.toChoice(choiceKind, language, ref)

        return when (type) {
            "active_word" -> card.toNewWord(language, ref)
            "_grammar" -> card.toGrammar(language, ref)
            "pronunciation" -> PronunciationCard(
                materialRef = ref,
                phrase = card["phrase"].string().orEmpty(),
                pinyin = card["pinyin"].string().orEmpty(),
                translation = card["translation"].localized(language),
            )

            "match_pairs" -> card.toMatchPairs(language, ref)
            "sentence_builder" -> SentenceBuilderCard(
                materialRef = ref,
                promptSentence = card["sentence"].localized(language),
                tokens = card["tokens"].tokens(language),
                answerTokens = card["answer_tokens"].tokens(language),
                explanation = card["explanation"].localized(language),
            )

            "reverse_builder" -> ReverseBuilderCard(
                materialRef = ref,
                hanzi = card["zh"].string().orEmpty(),
                pinyin = card["pinyin"].string().orEmpty(),
                translation = card["translation"].localized(language),
                tokens = card["tokens"].tokens(language),
                answerTokens = card["answer_tokens"].tokens(language),
                explanation = card["explanation"].localized(language),
            )

            // Anything the server adds later. Rendered as a recoverable
            // unsupported state and never auto-graded.
            else -> UnsupportedCard(materialRef = ref, rawType = type)
        }
    }

    private fun JsonObject.toChoice(
        kind: ChoiceKind,
        language: AppLanguage,
        ref: String,
    ) = ChoiceCard(
        materialRef = ref,
        kind = kind,
        title = this["title"].localized(language),
        prompt = this["prompt"].localized(language),
        options = this["options"].optionList(language),
        correctIndex = int("correct_index") ?: -1,
        explanation = this["explanation"].localized(language),
        // `sentence` is a plain string here, unlike sentence_builder.
        sentence = this["sentence"].string(),
        audioText = this["audio_text"].string(),
        audioPinyin = if (kind == ChoiceKind.LISTENING) this["pinyin"].string() else null,
        lines = (this["lines"] as? JsonArray).orEmpty().mapNotNull { element ->
            val line = element as? JsonObject ?: return@mapNotNull null
            DialogLine(
                speaker = line["speaker"].string().orEmpty(),
                text = line["zh"].string().orEmpty(),
                isBlank = line.bool("blank") ?: false,
            )
        },
        reviewOrigin = this["review_origin"].string(),
    )

    private fun JsonObject.toNewWord(language: AppLanguage, ref: String): LessonCard {
        val word = this["word"] as? JsonObject ?: return UnsupportedCard(ref, "active_word")
        return NewWordCard(
            materialRef = ref,
            number = word.int("no") ?: 0,
            hanzi = word["zh"].string().orEmpty(),
            pinyin = word["pinyin"].string().orEmpty(),
            partOfSpeech = word["pos"].string().orEmpty(),
            meaning = word["meaning"].localized(language),
        )
    }

    private fun JsonObject.toGrammar(language: AppLanguage, ref: String): LessonCard {
        val grammar = this["g"] as? JsonObject ?: return UnsupportedCard(ref, "_grammar")
        return GrammarCard(
            materialRef = ref,
            number = grammar.int("no") ?: 0,
            title = grammar["title"].localized(language),
            titleZh = grammar["title_zh"].string().orEmpty(),
            rule = grammar["rule"].localized(language),
            examples = (grammar["examples"] as? JsonArray).orEmpty().mapNotNull { element ->
                val example = element as? JsonObject ?: return@mapNotNull null
                GrammarExample(
                    hanzi = example["zh"].string().orEmpty(),
                    pinyin = example["pinyin"].string().orEmpty(),
                    translation = example["translation"].localized(language),
                )
            },
        )
    }

    private fun JsonObject.toMatchPairs(language: AppLanguage, ref: String) = MatchPairsCard(
        materialRef = ref,
        // Each pair is a two-element JSON array: [hanzi, {uz, ru, tj}].
        pairs = (this["pairs"] as? JsonArray).orEmpty().mapNotNull { element ->
            val pair = element as? JsonArray ?: return@mapNotNull null
            if (pair.size < 2) return@mapNotNull null
            val hanzi = pair[0].string().orEmpty()
            val meaning = pair[1].localized(language)
            if (hanzi.isBlank() || meaning.isBlank()) null else hanzi to meaning
        },
        explanation = this["explanation"].localized(language),
    )

    // ------------------------------------------------------------- helpers

    private val CHOICE_KINDS = mapOf(
        "meaning_guess" to ChoiceKind.MEANING,
        "translation_choice" to ChoiceKind.TRANSLATION,
        "hanzi_choice" to ChoiceKind.HANZI,
        "pinyin_choice" to ChoiceKind.PINYIN,
        "quick_quiz" to ChoiceKind.QUICK_QUIZ,
        "gap_fill" to ChoiceKind.GAP_FILL,
        "listening_choice" to ChoiceKind.LISTENING,
        "dialog_cloze" to ChoiceKind.DIALOG_CLOZE,
    )

    private fun JsonElement?.string(): String? =
        (this as? JsonPrimitive)?.takeIf { it.isString }?.content

    private fun JsonObject.int(key: String): Int? =
        (this[key] as? JsonPrimitive)?.intOrNull

    private fun JsonObject.bool(key: String): Boolean? =
        (this[key] as? JsonPrimitive)?.booleanOrNull

    /** A `{uz, ru, tj}` object, or a plain string used as-is. */
    private fun JsonElement?.localized(language: AppLanguage): String {
        string()?.let { return it }
        val obj = this as? JsonObject ?: return ""
        fun pick(code: String) = (obj[code] as? JsonPrimitive)?.contentOrNullSafe()
        return pick(language.backendCode)
            ?: pick(AppLanguage.DEFAULT.backendCode)
            ?: pick(AppLanguage.UZBEK.backendCode)
            ?: ""
    }

    private fun JsonPrimitive.contentOrNullSafe(): String? =
        content.takeIf { isString && it.isNotBlank() }

    /** Options are strings, except on `meaning_guess` where they are objects. */
    private fun JsonElement?.optionList(language: AppLanguage): List<String> =
        (this as? JsonArray).orEmpty().map { it.localized(language) }

    /**
     * Tokens are a flat list on `sentence_builder` and a per-language object
     * on `reverse_builder`, where each language has its own tile set.
     */
    private fun JsonElement?.tokens(language: AppLanguage): List<String> = when (this) {
        is JsonArray -> mapNotNull { it.string() }
        is JsonObject -> {
            val forLanguage = this[language.backendCode] as? JsonArray
                ?: this[AppLanguage.DEFAULT.backendCode] as? JsonArray
            forLanguage.orEmpty().mapNotNull { it.string() }
        }

        else -> emptyList()
    }
}
