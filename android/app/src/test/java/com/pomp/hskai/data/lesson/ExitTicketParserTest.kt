package com.pomp.hskai.data.lesson

import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.ChoiceKind
import com.pomp.hskai.domain.model.SentenceBuilderCard
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The closing check of a checkpoint lesson.
 *
 * Its cards speak the Starter 0 vocabulary, and the parser used to drop every
 * one of them: the learner finished the checkpoint without ever being asked
 * whether the objectives had landed.
 */
class ExitTicketParserTest {

    private val payload = """
    {
      "sections": [{"section_no": 1, "section_purpose": "practice", "cards": [
        {"type": "active_word", "word": {"no": 1, "zh": "你", "pinyin": "nǐ",
         "meaning": {"uz": "sen", "ru": "ты", "tj": "ту"}}}
      ]}],
      "exit_ticket": {"id": "starter0", "version": 1, "cards": [
        {"type": "choice", "card_id": "c1",
         "title": {"uz": "Natija tekshiruvi", "ru": "?", "tj": "?"},
         "prompt": {"uz": "你好 nimani anglatadi?", "ru": "?", "tj": "?"},
         "options": [{"uz": "Salom", "ru": "Привет", "tj": "Салом"},
                     {"uz": "Xayr", "ru": "Пока", "tj": "Хайр"}],
         "correct_index": 0,
         "explanation": {"uz": "你好 = salom", "ru": "?", "tj": "?"}},
        {"type": "listen_choice", "card_id": "c2",
         "title": {"uz": "Tinglang", "ru": "?", "tj": "?"},
         "prompt": {"uz": "Nima eshitdingiz?", "ru": "?", "tj": "?"},
         "audio_text": "对不起",
         "options": ["你好", "对不起"], "correct_index": 1,
         "explanation": {"uz": "对不起", "ru": "?", "tj": "?"}},
        {"type": "builder", "card_id": "c3",
         "title": {"uz": "Tuzing", "ru": "?", "tj": "?"},
         "prompt": {"uz": "Tartibda tuzing", "ru": "?", "tj": "?"},
         "tokens": ["没关系", "对不起"], "answer_tokens": ["对不起", "没关系"],
         "explanation": {"uz": "对不起 → 没关系", "ru": "?", "tj": "?"}}
      ]}
    }
    """.trimIndent()

    private fun parse() = LessonParser.parse(
        payload = Json.parseToJsonElement(payload).jsonObject,
        level = "hsk1",
        lessonOrder = 3,
        language = AppLanguage.UZBEK,
    )

    @Test
    fun `the closing check is added after the lesson's own sections`() {
        val lesson = parse()

        assertEquals(2, lesson.sections.size)
        assertEquals("exit_ticket", lesson.sections.last().purpose)
        assertEquals(3, lesson.sections.last().cards.size)
    }

    @Test
    fun `its three card types map onto the lesson's own`() {
        val cards = parse().sections.last().cards

        val meaning = cards[0] as ChoiceCard
        assertEquals(ChoiceKind.MEANING, meaning.kind)
        assertEquals(listOf("Salom", "Xayr"), meaning.options)
        assertTrue(meaning.isCorrect(0))

        val listening = cards[1] as ChoiceCard
        assertEquals(ChoiceKind.LISTENING, listening.kind)
        assertEquals("对不起", listening.audioText)

        val builder = cards[2] as SentenceBuilderCard
        assertEquals(listOf("对不起", "没关系"), builder.answerTokens)
    }

    @Test
    fun `its material refs stay clear of the lesson's own positions`() {
        val refs = parse().sections.last().cards.map { it.materialRef }

        assertTrue(refs.all { "section:99" in it })
        assertEquals("lesson:hsk1:3:section:99:card:1", refs.first())
    }
}
