package com.pomp.hskai.data.lesson

import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.domain.model.Lesson
import com.pomp.hskai.domain.model.PictureReviewCard
import com.pomp.hskai.domain.model.PictureWord
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.intOrNull

/**
 * The server's optional `lesson_plan` (UIUX-008), applied after parsing.
 *
 * The server never rewrites the lesson; it says which extra practice cards to
 * leave out for the learner's onboarding lesson length and goal, and where the
 * picture deck goes. It runs AFTER [LessonParser.parse], so every remaining
 * card keeps the `material_ref` of its original position and the envelope's
 * `total_cards` check still counts the lesson the server served.
 *
 * Only `practice` and `retention_review` cards can be left out, whatever the
 * payload says: teaching, grammar, dialogue, N1 checks and the exit ticket
 * always stay. An unknown version or a malformed plan means the lesson as
 * served.
 */
object LessonPlan {
    const val VERSION = 1
    const val MAX_WORDS = 10
    private val TRIMMABLE = setOf("practice", "retention_review")
    private val EXIT = setOf("learning_exit_check", "learning_repair_bank", "exit_ticket")

    fun apply(
        lesson: Lesson,
        payload: JsonObject,
        language: AppLanguage,
        /** Whether this device can draw the emoji; a word it cannot show is dropped. */
        isDrawable: (String) -> Boolean = { true },
    ): Lesson {
        val plan = payload["lesson_plan"] as? JsonObject ?: return lesson
        if ((plan["version"] as? JsonPrimitive)?.intOrNull != VERSION) return lesson

        val omit = (plan["omit"] as? JsonArray).orEmpty().mapNotNull { element ->
            val entry = element as? JsonObject ?: return@mapNotNull null
            val section = entry.int("section_no") ?: return@mapNotNull null
            val card = entry.int("card_no") ?: return@mapNotNull null
            LessonParser.materialRef(lesson.level, lesson.order, section, card)
        }.toSet()

        val review = plan["picture_review"] as? JsonObject
        val anchor = review?.get("anchor") as? JsonObject
        val anchorSection = anchor?.int("section_no")
        val atStart = (anchor?.get("position") as? JsonPrimitive)?.contentOrNull() == "start"
        val words = words(review?.get("words"), language, isDrawable)
        val deck = if (anchorSection != null && words.isNotEmpty()) {
            PictureReviewCard(
                materialRef = "lesson:${lesson.level}:${lesson.order}:picture_review",
                words = words,
            )
        } else {
            null
        }

        var placed = false
        val sections = lesson.sections.map { section ->
            var cards = if (section.purpose in TRIMMABLE) {
                section.cards.filterNot { it.materialRef in omit }
            } else {
                section.cards
            }
            if (deck != null && !placed && section.sectionNo == anchorSection && section.purpose !in EXIT) {
                cards = if (atStart) listOf(deck) + cards else cards + deck
                placed = true
            }
            if (cards === section.cards) section else section.copy(cards = cards)
        }
        return lesson.copy(sections = sections)
    }

    private fun words(
        element: JsonElement?,
        language: AppLanguage,
        isDrawable: (String) -> Boolean,
    ): List<PictureWord> {
        val seen = mutableSetOf<String>()
        return (element as? JsonArray).orEmpty().mapNotNull { item ->
            val word = item as? JsonObject ?: return@mapNotNull null
            val hanzi = (word["zh"] as? JsonPrimitive)?.contentOrNull()?.trim().orEmpty()
            val image = (word["image"] as? JsonPrimitive)?.contentOrNull()?.trim().orEmpty()
            if (hanzi.isEmpty() || image.isEmpty() || !seen.add(hanzi)) return@mapNotNull null
            if (!runCatching { isDrawable(image) }.getOrDefault(false)) return@mapNotNull null
            val meaning = word["meaning"] as? JsonObject
            PictureWord(
                hanzi = hanzi,
                pinyin = (word["pinyin"] as? JsonPrimitive)?.contentOrNull().orEmpty(),
                meaning = meaning?.let { pick(it, language) }.orEmpty(),
                image = image,
            )
        }.take(MAX_WORDS)
    }

    private fun pick(meaning: JsonObject, language: AppLanguage): String {
        fun text(code: String) = (meaning[code] as? JsonPrimitive)?.contentOrNull()?.takeIf { it.isNotBlank() }
        // Same fallback as LessonParser: learner language, then default, then Uzbek.
        return text(language.backendCode)
            ?: text(AppLanguage.DEFAULT.backendCode)
            ?: text(AppLanguage.UZBEK.backendCode)
            ?: ""
    }

    private fun JsonObject.int(key: String): Int? = (this[key] as? JsonPrimitive)?.intOrNull

    private fun JsonPrimitive.contentOrNull(): String? = if (isString) content else null
}
