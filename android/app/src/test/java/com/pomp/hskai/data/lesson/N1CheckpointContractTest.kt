package com.pomp.hskai.data.lesson

import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.SentenceBuilderCard
import com.pomp.hskai.domain.model.UnsupportedCard
import java.io.File
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** The exact checked-in N1 checkpoint must be playable by the native parser. */
class N1CheckpointContractTest {
    private fun runtimeJson(order: Int = 4): String {
        val relative = "app/static/course_v3_data/nhsk1/lesson_${order.toString().padStart(2, '0')}.json"
        return sequenceOf(
            File("../$relative"),
            File("../../$relative"),
            File(relative),
        ).firstOrNull { it.isFile }?.readText(Charsets.UTF_8)
            ?: error("Missing checked-in N1 runtime checkpoint: $relative")
    }

    @Test fun nativeParsesEverySourceCheckpointWithTwoModes() {
        val checkpoints = listOf(4, 9, 15, 25, 32, 39, 47, 54, 61, 68, 76, 83, 89, 97, 103)
        for (order in checkpoints) {
            val parsed = LessonParser.parse(
                payload = Json.parseToJsonElement(runtimeJson(order)).jsonObject,
                level = "nhsk1",
                lessonOrder = order,
                language = AppLanguage.UZBEK,
            )
            val original = parsed.sections.take(2)
            assertEquals("Original checkpoint section refs must stay fixed: $order",
                listOf(1, 2), original.map { it.sectionNo })
            assertEquals(3, parsed.sections[2].sectionNo)
            assertEquals(4, parsed.sections[3].sectionNo)
            val count = if (order == 4) 3 else 2
            assertEquals(count, parsed.sections[2].cards.size)
            assertEquals(count, parsed.sections[3].cards.size)
            assertTrue(parsed.sections.drop(2).flatMap { it.cards }.none { it is UnsupportedCard })
            assertTrue(parsed.sections[2].cards[0] is ChoiceCard)
            assertTrue(parsed.sections[3].cards[0] is ChoiceCard)
        }
    }

    @Test fun parseAllSixNewQuestionsWithoutDroppingOldMaterialReferences() {
        val lesson = LessonParser.parse(
            payload = Json.parseToJsonElement(runtimeJson()).jsonObject,
            level = "nhsk1",
            lessonOrder = 4,
            language = AppLanguage.UZBEK,
        )
        assertEquals(listOf(1, 2, 3, 4), lesson.sections.map { it.sectionNo })
        assertEquals(
            listOf("practice", "dialog", "learning_exit_check", "learning_repair_bank"),
            lesson.sections.map { it.purpose },
        )
        assertEquals(18, lesson.cards.size)
        assertEquals(12, lesson.sections.take(2).sumOf { it.cards.size })
        assertEquals("lesson:nhsk1:4:section:2:card:6", lesson.sections[1].cards.last().materialRef)
        assertTrue(lesson.sections.drop(2).flatMap { it.cards }.none { it is UnsupportedCard })
        assertEquals(3, lesson.sections[2].cards.size)
        assertEquals(3, lesson.sections[3].cards.size)
        assertEquals("不客气！", (lesson.sections[3].cards[1] as ChoiceCard).audioText)
        assertEquals(listOf("老师", "再见"),
            (lesson.sections[3].cards[2] as SentenceBuilderCard).answerTokens)
        assertFalse((lesson.sections[2].cards[0] as ChoiceCard).isCorrect(0))
        assertTrue((lesson.sections[2].cards[0] as ChoiceCard).isCorrect(1))
    }
}
