package com.pomp.hskai.core.text

import org.junit.Assert.assertEquals
import org.junit.Test

class PinyinSearchTest {

    @Test
    fun `tone marks are dropped so an untoned query still matches`() {
        assertEquals("nihao", PinyinSearch.plain("nǐ hǎo"))
        assertEquals("mama", PinyinSearch.plain("mā ma"))
        assertEquals("zaijian", PinyinSearch.plain("zài jiàn"))
    }

    @Test
    fun `every tone of the same syllable folds together`() {
        val plain = listOf("mā", "má", "mǎ", "mà", "ma").map(PinyinSearch::plain)
        assertEquals(listOf("ma", "ma", "ma", "ma", "ma"), plain)
    }

    /** "lv" is what a learner types for lǜ; folding to a bare "u" would lose it. */
    @Test
    fun `u umlaut folds to v the way keyboards teach it`() {
        assertEquals("lv", PinyinSearch.plain("lǜ"))
        assertEquals("nv", PinyinSearch.plain("nǚ"))
        assertEquals("lvse", PinyinSearch.plain("lǜ sè"))
        assertEquals("nvhai", PinyinSearch.plain("nǚ hái"))
    }

    @Test
    fun `case and separators do not matter`() {
        assertEquals("beijing", PinyinSearch.plain("Běi Jīng"))
        assertEquals("xian", PinyinSearch.plain("xi'an"))
        assertEquals("nihao", PinyinSearch.plain("  NǏ   HǍO  "))
    }

    @Test
    fun `digits in a numeric reading survive`() {
        assertEquals("ni3hao3", PinyinSearch.plain("ni3 hao3"))
    }

    @Test
    fun `nothing in means nothing out`() {
        assertEquals("", PinyinSearch.plain(null))
        assertEquals("", PinyinSearch.plain(""))
        assertEquals("", PinyinSearch.plain("   "))
    }
}
