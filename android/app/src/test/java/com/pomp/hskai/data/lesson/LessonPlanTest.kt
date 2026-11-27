package com.pomp.hskai.data.lesson

import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.domain.model.Lesson
import com.pomp.hskai.domain.model.PictureReviewCard
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * UIUX-008 `lesson_plan`: the server says which extra practice to leave out
 * for the learner's lesson length and goal, and where the picture deck goes.
 * The same rules are enforced server-side by
 * `tests/test_course_lesson_plan_service.py` and in the Mini App by
 * `tests/e2e/test_lesson_picture_review.py`.
 */
class LessonPlanTest {

    private val json = Json { ignoreUnknownKeys = true }

    private val choice =
        """{"type":"hanzi_choice","prompt":"?","title":"?","options":["你","好"],"correct_index":0,"explanation":"?"}"""

    private fun payload(plan: String?): JsonObject = json.parseToJsonElement(
        """
        {"source_lesson":1,"part_no":1,"part_count":1,"checkpoint":false,"title":"1","subtitle":"1",
         "sections":[
          {"section_no":1,"section_purpose":"grammar","cards":[$choice,$choice]},
          {"section_no":2,"section_purpose":"practice","cards":[$choice,$choice,$choice]},
          {"section_no":3,"section_purpose":"retention_review","cards":[$choice,$choice]},
          {"section_no":4,"section_purpose":"learning_exit_check","cards":[$choice]}
         ]${if (plan == null) "" else ""","lesson_plan":$plan"""}}
        """
    ).jsonObject

    private fun word(zh: String, image: String, meaning: String = """{"uz":"$zh-uz","ru":"$zh-ru","tj":"$zh-tj"}""") =
        """{"zh":"$zh","pinyin":"$zh-py","image":"$image","meaning":$meaning}"""

    private fun plan(
        omit: String = "[]",
        anchor: String = """{"section_no":2,"position":"end"}""",
        words: String = "[${word("苹果", "🍎")},${word("猫", "🐈")}]",
        version: Int = 1,
    ) = """{"version":$version,"daily_minutes":10,"omit":$omit,"picture_review":{"anchor":$anchor,"words":$words}}"""

    private fun applied(
        plan: String?,
        language: AppLanguage = AppLanguage.UZBEK,
        isDrawable: (String) -> Boolean = { true },
    ): Pair<Lesson, Lesson> {
        val body = payload(plan)
        val parsed = LessonParser.parse(payload = body, level = "hsk1", lessonOrder = 3, language = language)
        return parsed to LessonPlan.apply(parsed, body, language, isDrawable)
    }

    private fun refs(lesson: Lesson) = lesson.cards.map { it.materialRef.substringAfter("lesson:hsk1:3:") }

    @Test
    fun `a lesson without a plan is served as it is`() {
        val (parsed, lesson) = applied(null)
        assertSame(parsed, lesson)
    }

    @Test
    fun `an unknown plan version is ignored`() {
        val (parsed, lesson) = applied(plan(omit = """[{"section_no":2,"card_no":1}]""", version = 2))
        assertSame(parsed, lesson)
    }

    @Test
    fun `only practice and review cards are left out and the rest keep their refs`() {
        val (_, lesson) = applied(
            plan(
                omit = """[{"section_no":1,"card_no":1},{"section_no":2,"card_no":2},
                           {"section_no":3,"card_no":1},{"section_no":4,"card_no":1}]""",
                words = "[]",
            )
        )

        // Grammar (section 1) and the exit check (section 4) cannot be trimmed.
        assertEquals(
            listOf(
                "section:1:card:1", "section:1:card:2",
                "section:2:card:1", "section:2:card:3",
                "section:3:card:2",
                "section:4:card:1",
            ),
            refs(lesson),
        )
        assertTrue(lesson.cards.none { it is PictureReviewCard })
    }

    @Test
    fun `the deck goes to the end or the start of its anchor section`() {
        val (_, atEnd) = applied(plan())
        val endIndex = atEnd.cards.indexOfFirst { it is PictureReviewCard }
        assertEquals(5, endIndex)
        assertEquals("picture_review", refs(atEnd)[endIndex])
        assertEquals("section:3:card:1", refs(atEnd)[endIndex + 1])

        val (_, atStart) = applied(plan(anchor = """{"section_no":3,"position":"start"}"""))
        val startIndex = atStart.cards.indexOfFirst { it is PictureReviewCard }
        assertEquals("section:2:card:3", refs(atStart)[startIndex - 1])
        assertEquals("section:3:card:1", refs(atStart)[startIndex + 1])
        assertEquals(1, atStart.cards.count { it is PictureReviewCard })
    }

    @Test
    fun `the deck never lands in the exit check`() {
        val (_, lesson) = applied(plan(anchor = """{"section_no":4,"position":"start"}"""))
        assertTrue(lesson.cards.none { it is PictureReviewCard })
    }

    @Test
    fun `words this device cannot draw, duplicates and anything past ten are dropped`() {
        val many = (1..14).joinToString(",") { word("字$it", "🟢") }
        val (_, lesson) = applied(
            plan(words = "[${word("猫", "🐈")},${word("猫", "🐱")},${word("书", "📕")},${word("空", "")},$many]"),
            isDrawable = { it != "📕" },
        )
        val deck = lesson.cards.filterIsInstance<PictureReviewCard>().single()

        assertEquals(LessonPlan.MAX_WORDS, deck.words.size)
        assertEquals("猫", deck.words.first().hanzi)
        assertEquals("🐈", deck.words.first().image)
        assertFalse(deck.words.any { it.hanzi == "书" || it.hanzi == "空" })
        assertEquals(deck.words.size, deck.words.map { it.hanzi }.toSet().size)
    }

    @Test
    fun `a deck with no drawable word is not added`() {
        val (_, lesson) = applied(plan(), isDrawable = { false })
        assertTrue(lesson.cards.none { it is PictureReviewCard })
    }

    @Test
    fun `the meaning follows the learner language`() {
        val (_, lesson) = applied(plan(), language = AppLanguage.RUSSIAN)
        val deck = lesson.cards.filterIsInstance<PictureReviewCard>().single()
        assertEquals("苹果-ru", deck.words.first().meaning)
        assertEquals("苹果-py", deck.words.first().pinyin)
    }

    @Test
    fun `a malformed plan leaves the lesson whole`() {
        val (parsed, lesson) = applied("""{"version":1,"omit":"all","picture_review":[]}""")
        assertEquals(refs(parsed), refs(lesson))
        assertNull(lesson.cards.firstOrNull { it is PictureReviewCard })
    }
}
