package com.pomp.hskai.feature.dictionary

import org.junit.Assert.assertEquals
import org.junit.Test

class DictionaryHistoryTest {

    @Test
    fun `the newest search comes first`() {
        assertEquals(listOf("好", "你"), DictionaryHistory.record(listOf("你"), "好"))
    }

    @Test
    fun `searching an entry again moves it to the top instead of repeating it`() {
        assertEquals(listOf("你", "好", "学习"), DictionaryHistory.record(listOf("好", "你", "学习"), "你"))
    }

    @Test
    fun `only the last five are kept`() {
        val full = listOf("一", "二", "三", "四", "五")

        assertEquals(listOf("六", "一", "二", "三", "四"), DictionaryHistory.record(full, "六"))
    }

    @Test
    fun `a blank entry changes nothing`() {
        assertEquals(listOf("好"), DictionaryHistory.record(listOf("好"), "  "))
    }
}
