package com.pomp.hskai.feature.practice

import com.pomp.hskai.data.api.DrillWordDto
import com.pomp.hskai.data.repository.DictionaryWord
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The drill has to keep two promises: practise what the server says is due,
 * and never stop working when the server says nothing.
 */
class WordDrillTest {

    private fun word(hanzi: String) = DictionaryWord(
        hanzi = hanzi,
        pinyin = "$hanzi-pinyin",
        meaning = "$hanzi-meaning",
        level = "hsk1",
    )

    private val pool = listOf("你", "好", "我", "是", "人", "大", "小", "中").map(::word)

    /** Deterministic stand-in for the shuffle, so the assertions can be exact. */
    private val noShuffle: (List<DictionaryWord>) -> List<DictionaryWord> = { it }

    @Test
    fun `the words the server asked for come first, in its order`() {
        val questions = WordDrill.build(
            targets = listOf(
                DrillWordDto(hanzi = "我", kind = "review"),
                DrillWordDto(hanzi = "好", kind = "new"),
            ),
            pool = pool,
            limit = 3,
            shuffle = noShuffle,
        )

        assertEquals(listOf("我", "好"), questions.take(2).map { it.hanzi })
        assertTrue(questions[0].isReview)
        assertTrue(!questions[1].isReview)
    }

    @Test
    fun `an empty server list still produces a full drill`() {
        val questions = WordDrill.build(
            targets = emptyList(),
            pool = pool,
            limit = 5,
            shuffle = noShuffle,
        )

        assertEquals(5, questions.size)
    }

    @Test
    fun `a word the client does not know is skipped, not faked`() {
        val questions = WordDrill.build(
            targets = listOf(DrillWordDto(hanzi = "龘", kind = "review")),
            pool = pool,
            limit = 2,
            shuffle = noShuffle,
        )

        assertTrue(questions.none { it.hanzi == "龘" })
        assertEquals(2, questions.size)
    }

    @Test
    fun `every question offers four distinct options including the answer`() {
        val questions = WordDrill.build(
            targets = emptyList(),
            pool = pool,
            limit = 4,
            shuffle = noShuffle,
        )

        questions.forEach { question ->
            assertEquals(4, question.options.size)
            assertEquals(4, question.options.toSet().size)
            assertTrue(question.hanzi in question.options)
        }
    }

    @Test
    fun `a pool too small for distractors yields nothing rather than a rigged question`() {
        val questions = WordDrill.build(
            targets = emptyList(),
            pool = listOf(word("你"), word("好")),
            limit = 4,
            shuffle = noShuffle,
        )

        assertTrue(questions.isEmpty())
    }

    @Test
    fun `two-character words never enter the pool`() {
        val mixed = pool + DictionaryWord(
            hanzi = "你好",
            pinyin = "nǐ hǎo",
            meaning = "salom",
            level = "hsk1",
        )

        assertTrue(WordDrill.pool(mixed).none { it.hanzi == "你好" })
    }
}
