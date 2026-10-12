package com.pomp.hskai.feature.practice

import java.io.File
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ReadyPhrasesAssetsTest {

    @Test
    fun `bundled phrase catalog is complete translated and consistently ordered`() {
        val root = Json.parseToJsonElement(File("src/main/assets/ready-phrases-v1.json").readText()).jsonObject
        val categories = root.getValue("categories").jsonArray
        val phrases = root.getValue("phrases").jsonArray

        assertEquals(12, categories.size)
        assertEquals(300, phrases.size)
        assertEquals(1, root.getValue("version").jsonPrimitive.content.toInt())

        val categoryIds = categories.map { it.jsonObject.getValue("id").jsonPrimitive.content }.toSet()
        val phraseIds = mutableSetOf<String>()
        val hanzi = mutableSetOf<String>()
        val orderByCategory = mutableMapOf<String, MutableList<Int>>()
        phrases.forEach { element ->
            val phrase = element.jsonObject
            val id = phrase.getValue("id").jsonPrimitive.content
            val categoryId = phrase.getValue("category_id").jsonPrimitive.content
            val chinese = phrase.getValue("zh").jsonPrimitive.content
            val pinyin = phrase.getValue("pinyin").jsonPrimitive.content
            val translations = phrase.getValue("translations").jsonObject

            assertTrue(phraseIds.add(id))
            assertTrue(hanzi.add(chinese))
            assertTrue(categoryId in categoryIds)
            assertTrue(chinese.any { it in '\u4e00'..'\u9fff' })
            assertFalse(pinyin.isBlank())
            listOf("uz", "ru", "tj").forEach { language ->
                assertFalse(translations.getValue(language).jsonPrimitive.content.isBlank())
            }
            orderByCategory.getOrPut(categoryId) { mutableListOf() }
                .add(phrase.getValue("sort_order").jsonPrimitive.content.toInt())
        }

        assertEquals(categoryIds, orderByCategory.keys)
        orderByCategory.values.forEach { orders -> assertEquals((1..orders.size).toList(), orders) }
    }
}
