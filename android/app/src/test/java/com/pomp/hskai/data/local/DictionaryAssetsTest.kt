package com.pomp.hskai.data.local

import com.pomp.hskai.core.i18n.AppLanguage
import java.io.File
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The dictionary's offline material as the app reads it — the real files in
 * `src/main/assets`, not samples, so a generator change that breaks the
 * format fails here and not on a phone.
 */
class DictionaryAssetsTest {

    private val json = Json { ignoreUnknownKeys = true }
    private val assets = File("src/main/assets")

    @Test
    fun `examples are found in the learner's language and use the word`() {
        val examples = DictionaryInsightsParser.examples(File(assets, "hsk-examples.json").readText(), json)
        assertNotNull(examples)

        val uzbek = examples!!.find("好", AppLanguage.UZBEK)
        val russian = examples.find("好", AppLanguage.RUSSIAN)

        assertTrue(uzbek.isNotEmpty())
        assertTrue(uzbek.all { "好" in it.hanzi && it.pinyin.isNotBlank() && it.translation.isNotBlank() })
        assertEquals(uzbek.map { it.hanzi }, russian.map { it.hanzi })
        assertTrue(uzbek.first().translation != russian.first().translation)
        assertTrue(examples.find("不存在的词", AppLanguage.UZBEK).isEmpty())
    }

    @Test
    fun `a breakdown lists its parts and a pictograph only its picture`() {
        val parts = DictionaryInsightsParser.parts(File(assets, "hanzi-parts.json").readText(), json)
        assertNotNull(parts)

        val hao = parts!!.find("好", AppLanguage.TAJIK)
        val person = parts.find("人", AppLanguage.RUSSIAN)

        assertEquals(listOf("女", "子"), hao?.parts?.map { it.hanzi })
        assertTrue(hao!!.hint.isNotBlank())
        assertTrue(person!!.parts.isEmpty())
        assertTrue(person.hint.isNotBlank())
        assertNull(parts.find("𠀀", AppLanguage.UZBEK))
    }

    @Test
    fun `all dictionary words have examples and legacy characters have breakdowns`() {
        val examples = DictionaryInsightsParser.examples(File(assets, "hsk-examples.json").readText(), json)!!
        val parts = DictionaryInsightsParser.parts(File(assets, "hanzi-parts.json").readText(), json)!!

        val noExample = allDictionaryWords().filter { examples.find(it, AppLanguage.TAJIK).isEmpty() }
        val noBreakdown = dictionaryWords()
            .flatMap { word -> word.filter { it in '一'..'鿿' }.map(Char::toString) }
            .distinct()
            .filter { parts.find(it, AppLanguage.UZBEK) == null }

        assertEquals(emptyList<String>(), noExample)
        assertEquals(emptyList<String>(), noBreakdown)
    }

    @Test
    fun `a frame entry finds sentences that use both of its halves`() {
        val examples = DictionaryInsightsParser.examples(File(assets, "hsk-examples.json").readText(), json)!!

        val frame = examples.find("不但……而且……", AppLanguage.RUSSIAN)

        assertTrue(frame.isNotEmpty())
        assertTrue(frame.all { "不但" in it.hanzi && "而且" in it.hanzi })
    }

    @Test
    fun `a broken file reads as nothing rather than crashing`() {
        assertNull(DictionaryInsightsParser.examples("not json", json))
        assertNull(DictionaryInsightsParser.parts("{", json))
    }

    @Test
    fun `audio file names follow the word's code points`() {
        assertEquals("20320_20204.mp3", BundledWordAudio.fileName("你们"))
        assertEquals("26149_40_22825_41.mp3", BundledWordAudio.fileName(" 春(天) "))
        assertNull(BundledWordAudio.fileName("hello"))
        assertNull(BundledWordAudio.fileName(""))
    }

    private fun dictionaryWords(): List<String> {
        val raw = File(assets, "hsk-words.js").readText()
        return json.parseToJsonElement(raw.substring(raw.indexOf('['), raw.lastIndexOf(']') + 1))
            .jsonArray
            .map { it.jsonObject.getValue("h").jsonPrimitive.content.trim() }
            .filter { it.isNotEmpty() }
            .distinct()
    }

    private fun allDictionaryWords(): List<String> =
        (dictionaryWords() + hsk30DictionaryWords()).distinct()

    private fun hsk30DictionaryWords(): List<String> {
        val raw = File(assets, "hsk30-words.js").readText()
        val marker = Regex("window\\.HSK30_WORDS\\s*=\\s*").find(raw)
            ?: error("HSK 3.0 word list is missing")
        return json.parseToJsonElement(raw.substring(marker.range.last + 1, raw.lastIndexOf(';')))
            .jsonArray
            .map { it.jsonObject.getValue("h").jsonPrimitive.content.trim() }
            .filter { it.isNotEmpty() }
            .distinct()
    }

    @Test
    fun `every dictionary word has its pronunciation in the apk`() {
        // The generator is Python and the reader is Kotlin; this is where the
        // two have to agree on a name for every single word.
        val words = dictionaryWords()
        assertTrue(words.size > 1000)

        val silent = words.filter { word ->
            val name = BundledWordAudio.fileName(word)
            name == null || !File(assets, "audio/words/$name").isFile
        }

        assertEquals(emptyList<String>(), silent)
    }
}
