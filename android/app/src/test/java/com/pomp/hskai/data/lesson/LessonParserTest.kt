package com.pomp.hskai.data.lesson

import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.ChoiceKind
import com.pomp.hskai.domain.model.GrammarCard
import com.pomp.hskai.domain.model.MatchPairsCard
import com.pomp.hskai.domain.model.NewWordCard
import com.pomp.hskai.domain.model.PronunciationCard
import com.pomp.hskai.domain.model.ReverseBuilderCard
import com.pomp.hskai.domain.model.SentenceBuilderCard
import com.pomp.hskai.domain.model.UnsupportedCard
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The fixtures below mirror the real payloads in
 * `app/static/course_v3_data/**/lesson_*.json`. Their shapes are additionally
 * guarded server-side by `tests/test_course_card_contract.py`, so a
 * regeneration of the course data cannot silently break this parser.
 */
class LessonParserTest {

    private val json = Json { ignoreUnknownKeys = true }

    private fun parse(body: String, language: AppLanguage = AppLanguage.UZBEK) =
        LessonParser.parse(
            payload = json.parseToJsonElement(body) as JsonObject,
            level = "hsk1",
            lessonOrder = 3,
            language = language,
        )

    @Test
    fun `material ref matches the server format exactly`() {
        // app/services/course_lesson_mistake_material_service.py builds
        // lesson:<level>:<order>:section:<section_no>:card:<1-based index>.
        assertEquals(
            "lesson:hsk1:3:section:2:card:5",
            LessonParser.materialRef("hsk1", 3, 2, 5),
        )
        assertTrue(
            Regex("^lesson:(hsk[1-4]):(\\d+):section:(\\d+):card:(\\d+)$")
                .matches(LessonParser.materialRef("hsk4", 181, 1, 1))
        )
    }

    @Test
    fun `section_no drives the ref, not the array position`() {
        val lesson = parse(
            """
            {"sections":[
              {"section_no":7,"section_purpose":"practice","cards":[
                {"type":"pronunciation","phrase":"你","pinyin":"nǐ",
                 "translation":{"uz":"sen","ru":"ты","tj":"ту"}},
                {"type":"pronunciation","phrase":"好","pinyin":"hǎo",
                 "translation":{"uz":"yaxshi","ru":"хорошо","tj":"хуб"}}
              ]}
            ]}
            """.trimIndent()
        )
        assertEquals(
            listOf(
                "lesson:hsk1:3:section:7:card:1",
                "lesson:hsk1:3:section:7:card:2",
            ),
            lesson.cards.map { it.materialRef },
        )
    }

    @Test
    fun `a missing section_no falls back to the one-based position`() {
        val lesson = parse(
            """
            {"sections":[
              {"section_purpose":"practice","cards":[
                {"type":"pronunciation","phrase":"你","pinyin":"nǐ",
                 "translation":{"uz":"sen","ru":"ты","tj":"ту"}}
              ]}
            ]}
            """.trimIndent()
        )
        assertEquals("lesson:hsk1:3:section:1:card:1", lesson.cards[0].materialRef)
    }

    @Test
    fun `plain string options are read as written`() {
        val card = parse(
            """
            {"sections":[{"section_no":1,"cards":[
              {"type":"hanzi_choice",
               "prompt":{"uz":"hǎo qaysi ieroglif?","ru":"?","tj":"?"},
               "title":{"uz":"Ieroglifni tanlang","ru":"?","tj":"?"},
               "options":["你","好","您"],"correct_index":1,
               "explanation":{"uz":"好 = yaxshi","ru":"?","tj":"?"}}
            ]}]}
            """.trimIndent()
        ).cards[0] as ChoiceCard

        assertEquals(ChoiceKind.HANZI, card.kind)
        assertEquals(listOf("你", "好", "您"), card.options)
        assertEquals(1, card.correctIndex)
        assertTrue(card.isCorrect(1))
        assertFalse(card.isCorrect(0))
        assertEquals("Ieroglifni tanlang", card.title)
    }

    @Test
    fun `localized object options are resolved per language`() {
        // meaning_guess is the one choice type whose options are objects.
        val body = """
            {"sections":[{"section_no":1,"cards":[
              {"type":"meaning_guess",
               "prompt":{"uz":"你 ma'nosi?","ru":"Значение 你?","tj":"Маънои 你?"},
               "title":{"uz":"Ma'nosi nima?","ru":"Что означает?","tj":"Маъно чист?"},
               "options":[
                 {"uz":"siz","ru":"вы","tj":"шумо"},
                 {"uz":"yaxshi","ru":"хорошо","tj":"хуб"},
                 {"uz":"sen","ru":"ты","tj":"ту"}],
               "correct_index":2,
               "review_origin":"previous",
               "explanation":{"uz":"你 = sen","ru":"你 = ты","tj":"你 = ту"}}
            ]}]}
        """.trimIndent()

        val uz = parse(body, AppLanguage.UZBEK).cards[0] as ChoiceCard
        assertEquals(listOf("siz", "yaxshi", "sen"), uz.options)

        val ru = parse(body, AppLanguage.RUSSIAN).cards[0] as ChoiceCard
        assertEquals(listOf("вы", "хорошо", "ты"), ru.options)

        val tj = parse(body, AppLanguage.TAJIK).cards[0] as ChoiceCard
        assertEquals(listOf("шумо", "хуб", "ту"), tj.options)
        assertEquals("Маънои 你?", tj.prompt)

        // Retention review deck marker survives.
        assertTrue(uz.isReviewCard)
        assertEquals("previous", uz.reviewOrigin)
    }

    @Test
    fun `gap fill keeps its sentence as a plain string`() {
        val card = parse(
            """
            {"sections":[{"section_no":1,"cards":[
              {"type":"gap_fill","sentence":"____好！",
               "prompt":{"uz":"Bo'sh joyga","ru":"?","tj":"?"},
               "options":["关","好","你"],"correct_index":2,
               "explanation":{"uz":"To'g'ri: 你","ru":"?","tj":"?"}}
            ]}]}
            """.trimIndent()
        ).cards[0] as ChoiceCard

        assertEquals(ChoiceKind.GAP_FILL, card.kind)
        assertEquals("____好！", card.sentence)
    }

    @Test
    fun `listening and dialog cards keep their stimulus`() {
        val cards = parse(
            """
            {"sections":[{"section_no":1,"cards":[
              {"type":"listening_choice","audio_text":"你好！","pinyin":"Nǐ hǎo!",
               "title":{"uz":"Eshiting","ru":"?","tj":"?"},
               "options":["您好！","你好！"],"correct_index":1,
               "explanation":{"uz":"你好！","ru":"?","tj":"?"}},
              {"type":"dialog_cloze",
               "title":{"uz":"Dialogni to'ldiring","ru":"?","tj":"?"},
               "lines":[{"speaker":"A","zh":"你好！","blank":false},
                        {"speaker":"B","zh":"","blank":true}],
               "options":["你们好！","你好！"],"correct_index":1,
               "explanation":{"uz":"To'g'ri","ru":"?","tj":"?"}}
            ]}]}
            """.trimIndent()
        ).cards

        val listening = cards[0] as ChoiceCard
        assertEquals("你好！", listening.audioText)
        assertEquals("Nǐ hǎo!", listening.audioPinyin)

        val dialog = cards[1] as ChoiceCard
        assertEquals(2, dialog.lines.size)
        assertEquals("A", dialog.lines[0].speaker)
        assertFalse(dialog.lines[0].isBlank)
        assertTrue(dialog.lines[1].isBlank)
        // The blank line has no text of its own; the option fills it.
        assertEquals("", dialog.lines[1].text)
    }

    @Test
    fun `sentence builder uses a flat token list and a localized prompt`() {
        val card = parse(
            """
            {"sections":[{"section_no":1,"cards":[
              {"type":"sentence_builder",
               "sentence":{"uz":"Salom!","ru":"Привет!","tj":"Салом!"},
               "tokens":["好","您","你"],"answer_tokens":["你","好"],
               "explanation":{"uz":"你好！","ru":"你好！","tj":"你好！"}}
            ]}]}
            """.trimIndent()
        ).cards[0] as SentenceBuilderCard

        assertEquals("Salom!", card.promptSentence)
        assertEquals(listOf("好", "您", "你"), card.tokens)
        assertEquals(listOf("你", "好"), card.answerTokens)
        assertTrue(card.isCorrect(listOf("你", "好")))
        assertFalse(card.isCorrect(listOf("好", "你")))
    }

    @Test
    fun `reverse builder picks the token set for the learner's language`() {
        val body = """
            {"sections":[{"section_no":1,"cards":[
              {"type":"reverse_builder","zh":"你好","pinyin":"nǐ hǎo",
               "translation":{"uz":"salom","ru":"привет","tj":"салом"},
               "tokens":{"uz":["nǐ","salom","hǎo"],
                         "ru":["привет","nǐ","hǎo"],
                         "tj":["салом","nǐ","hǎo"]},
               "answer_tokens":{"uz":["salom"],"ru":["привет"],"tj":["салом"]},
               "explanation":{"uz":"你好","ru":"你好","tj":"你好"}}
            ]}]}
        """.trimIndent()

        val uz = parse(body, AppLanguage.UZBEK).cards[0] as ReverseBuilderCard
        assertEquals(listOf("nǐ", "salom", "hǎo"), uz.tokens)
        assertEquals(listOf("salom"), uz.answerTokens)

        val ru = parse(body, AppLanguage.RUSSIAN).cards[0] as ReverseBuilderCard
        assertEquals(listOf("привет", "nǐ", "hǎo"), ru.tokens)
        assertEquals(listOf("привет"), ru.answerTokens)
        assertEquals("你好", ru.hanzi)
    }

    @Test
    fun `match pairs reads the hanzi and meaning tuple`() {
        val card = parse(
            """
            {"sections":[{"section_no":1,"cards":[
              {"type":"match_pairs","pairs":[
                 ["你",{"uz":"sen","ru":"ты","tj":"ту"}],
                 ["好",{"uz":"yaxshi","ru":"хорошо","tj":"хуб"}]],
               "explanation":{"uz":"Juftliklar","ru":"?","tj":"?"}}
            ]}]}
            """.trimIndent()
        ).cards[0] as MatchPairsCard

        assertEquals(listOf("你" to "sen", "好" to "yaxshi"), card.pairs)
        assertTrue(card.isGraded)
    }

    @Test
    fun `new word and grammar cards are read from their nested objects`() {
        val cards = parse(
            """
            {"sections":[{"section_no":1,"cards":[
              {"type":"active_word","word":{"no":1,"zh":"你","pinyin":"nǐ",
               "pos":"pron.","meaning":{"uz":"sen","ru":"ты","tj":"ту"}}},
              {"type":"_grammar","g":{"no":1,
               "title":{"uz":"To'rt ton","ru":"Четыре тона","tj":"Чор садо"},
               "title_zh":"四声",
               "rule":{"uz":"Har bir bo'g'in","ru":"Каждый слог","tj":"Ҳар ҳиҷо"},
               "examples":[{"zh":"妈","pinyin":"mā",
                 "translation":{"uz":"ona","ru":"мама","tj":"модар"}}]}}
            ]}]}
            """.trimIndent()
        ).cards

        val word = cards[0] as NewWordCard
        assertEquals("你", word.hanzi)
        assertEquals("nǐ", word.pinyin)
        assertEquals("pron.", word.partOfSpeech)
        assertEquals("sen", word.meaning)
        assertFalse(word.isGraded)

        val grammar = cards[1] as GrammarCard
        assertEquals("To'rt ton", grammar.title)
        assertEquals("四声", grammar.titleZh)
        assertEquals(1, grammar.examples.size)
        assertEquals("妈", grammar.examples[0].hanzi)
        assertEquals("ona", grammar.examples[0].translation)
    }

    @Test
    fun `pronunciation is never graded`() {
        val card = parse(
            """
            {"sections":[{"section_no":1,"cards":[
              {"type":"pronunciation","phrase":"你","pinyin":"nǐ",
               "translation":{"uz":"sen","ru":"ты","tj":"ту"}}
            ]}]}
            """.trimIndent()
        ).cards[0] as PronunciationCard

        assertEquals("你", card.phrase)
        // The course deliberately never lets pronunciation soft-lock a learner.
        assertFalse(card.isGraded)
    }

    @Test
    fun `an unknown card type is kept, not skipped, and never graded`() {
        val lesson = parse(
            """
            {"sections":[{"section_no":1,"cards":[
              {"type":"pronunciation","phrase":"你","pinyin":"nǐ",
               "translation":{"uz":"sen","ru":"ты","tj":"ту"}},
              {"type":"tone_drill_v2","whatever":true},
              {"type":"hanzi_choice","prompt":{"uz":"?","ru":"?","tj":"?"},
               "title":{"uz":"?","ru":"?","tj":"?"},
               "options":["你","好"],"correct_index":0,
               "explanation":{"uz":"?","ru":"?","tj":"?"}}
            ]}]}
            """.trimIndent()
        )

        // Three cards in, three cards out: nothing is silently dropped.
        assertEquals(3, lesson.cards.size)
        val unsupported = lesson.cards[1] as UnsupportedCard
        assertEquals("tone_drill_v2", unsupported.rawType)
        assertEquals("lesson:hsk1:3:section:1:card:2", unsupported.materialRef)
        assertFalse(unsupported.isGraded)
        // Only the real question counts toward accuracy.
        assertEquals(1, lesson.gradedCards.size)
    }

    @Test
    fun `a malformed card degrades instead of throwing`() {
        val lesson = parse(
            """
            {"sections":[{"section_no":1,"cards":[
              {"type":"active_word"},
              {"type":"_grammar"},
              {"type":"match_pairs","pairs":[["你"],[]]}
            ]}]}
            """.trimIndent()
        )

        assertEquals(3, lesson.cards.size)
        assertTrue(lesson.cards[0] is UnsupportedCard)
        assertTrue(lesson.cards[1] is UnsupportedCard)
        // Incomplete tuples are dropped, the card itself survives.
        assertTrue((lesson.cards[2] as MatchPairsCard).pairs.isEmpty())
    }

    @Test
    fun `lesson metadata is read from the payload`() {
        val lesson = parse(
            """
            {"source_lesson":7,"part_no":2,"part_count":3,"checkpoint":true,
             "title":{"uz":"7-dars","ru":"Урок 7","tj":"Дарси 7"},
             "subtitle":{"uz":"2-qism","ru":"Часть 2","tj":"Қисми 2"},
             "sections":[]}
            """.trimIndent()
        )

        assertEquals(7, lesson.sourceLesson)
        assertEquals(2, lesson.part)
        assertEquals(3, lesson.partCount)
        assertTrue(lesson.isCheckpoint)
        assertEquals("7-dars", lesson.title)
        assertEquals("2-qism", lesson.subtitle)
    }
}
