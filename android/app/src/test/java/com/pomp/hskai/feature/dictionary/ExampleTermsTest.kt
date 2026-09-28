package com.pomp.hskai.feature.dictionary

import org.junit.Assert.assertEquals
import org.junit.Test

/** What an example sentence marks for an entry, including the unusual ones. */
class ExampleTermsTest {

    @Test
    fun `a plain word is marked as it is`() {
        assertEquals(listOf("你们"), exampleTerms("你们"))
    }

    @Test
    fun `an optional part is tried with and without it, longest first`() {
        assertEquals(listOf("春天", "春"), exampleTerms("春(天)"))
        assertEquals(listOf("极了", "极"), exampleTerms("极（了）"))
    }

    @Test
    fun `a frame is marked by each of its halves`() {
        assertEquals(listOf("不但", "而且"), exampleTerms("不但……而且……"))
    }

    @Test
    fun `the marked sentence keeps every character in order`() {
        val sentence = "这门课不但有用，而且很有意思！"

        assertEquals(sentence, highlighted(sentence, "不但……而且……").text)
        assertEquals(2, highlighted(sentence, "不但……而且……").spanStyles.size)
    }
}
