package com.pomp.hskai.data.api

import com.pomp.hskai.data.repository.MISTAKE_REVIEW_FORMATS
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The universal mistake review (server v3) and this build have to agree on
 * three things the compiler cannot see: which exercise kinds the build
 * declares, that an answer carries exactly one of index / tiles, and that the
 * new fields of the reply are read.
 */
class MistakeReviewContractTest {
    // The same settings as HskAiApplication.json.
    private val json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
    }

    @Test
    fun `start declares every exercise kind the review screen draws`() {
        val body = json.parseToJsonElement(
            json.encodeToString(
                MistakeReviewStartRequest(
                    accessRef = "ref-1",
                    category = "grammar",
                    formats = MISTAKE_REVIEW_FORMATS,
                ),
            ),
        ).jsonObject

        assertEquals("grammar", body["category"]?.jsonPrimitive?.content)
        val formats = body["formats"]!!.jsonArray.map { it.jsonPrimitive.content }
        assertTrue("sentence_builder" in formats)
        assertTrue("listen_builder" in formats)
        assertTrue("listening_choice" in formats)
        assertEquals(formats.size, formats.toSet().size)
    }

    @Test
    fun `an all-category start sends no category`() {
        val body = json.encodeToString(MistakeReviewStartRequest(accessRef = "ref-1"))
        assertFalse(body.contains("category"))
        // Without formats the server treats this as an old build.
        assertFalse(body.contains("formats"))
    }

    @Test
    fun `an option answer sends only its index`() {
        val body = json.parseToJsonElement(
            json.encodeToString(MistakeReviewAnswerRequest("session-1", "t:1:meaning_choice", selectedIndex = 2)),
        ).jsonObject
        assertEquals("2", body["selected_index"]?.jsonPrimitive?.content)
        assertFalse(body.containsKey("selected_tokens"))
    }

    @Test
    fun `a built sentence sends only its tiles`() {
        val body = json.parseToJsonElement(
            json.encodeToString(
                MistakeReviewAnswerRequest(
                    "session-1",
                    "t:1:sentence_builder",
                    selectedTokens = listOf("我", "是", "学生"),
                ),
            ),
        ).jsonObject
        assertFalse(body.containsKey("selected_index"))
        assertEquals(listOf("我", "是", "学生"), body["selected_tokens"]!!.jsonArray.map { it.jsonPrimitive.content })
    }

    @Test
    fun `review questions keep their format, tiles and autoplay`() {
        val session = json.decodeFromString<MistakeReviewStartResponse>(
            """
            {"ok": true, "session": {"id": "mistake-review:1:v3:abc", "version": 3, "category": "grammar", "targets": 1,
              "questions": [
                {"id": "t:1:sentence_builder", "category": "grammar", "format": "sentence_builder",
                 "prompt": "Gapni tuzing: «Men talabaman.»", "options": [], "tokens": ["学生", "我", "是"],
                 "sentence": "", "pinyin": "", "audio_text": "", "language": "uz", "autoplay": false},
                {"id": "t:1:sentence_listening", "category": "grammar", "format": "sentence_listening",
                 "prompt": "Tinglang", "options": ["我是学生。", "你好"], "audio_text": "我是学生。", "autoplay": true}
              ]}}
            """.trimIndent(),
        ).session!!

        assertEquals(3, session.version)
        val (builder, listening) = session.questions
        assertTrue(builder.isBuilder)
        assertEquals(listOf("学生", "我", "是"), builder.tokens)
        assertFalse(listening.isBuilder)
        assertTrue(listening.autoplay)
        assertEquals("sentence_listening", listening.format)
    }

    @Test
    fun `the overview reads targets and the completion reads cleared`() {
        val overview = json.decodeFromString<MistakesOverviewResponse>(
            """
            {"ok": true, "summary": {"total": 1, "categories": {"word": 1}, "unit": "targets"},
             "targets": [{"id": 5, "category": "word", "kind": "word", "zh": "你", "pinyin": "nǐ",
               "meaning": "sen", "translation": "", "wrong": "您", "passed": 1, "required": 3,
               "count": 2, "level": null, "sources": ["lesson"]}], "items": []}
            """.trimIndent(),
        )
        val target = overview.targets.single()
        assertEquals("你", target.zh)
        assertEquals(1, target.passed)
        assertEquals(3, target.required)
        assertEquals(listOf("lesson"), target.sources)

        val done = json.decodeFromString<MistakeReviewCompleteResponse>(
            """{"ok": true, "score": 3, "total": 3, "percent": 100, "remaining": 0, "cleared": 1}""",
        )
        assertEquals(1, done.cleared)
    }
}
