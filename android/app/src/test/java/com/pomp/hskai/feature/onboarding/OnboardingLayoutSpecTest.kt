package com.pomp.hskai.feature.onboarding

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class OnboardingLayoutSpecTest {
    @Test
    fun compactWidth_matchesMiniApp360Breakpoint() {
        val atBreakpoint = OnboardingLayoutSpec.resolve(widthDp = 360, heightDp = 800)
        val aboveBreakpoint = OnboardingLayoutSpec.resolve(widthDp = 361, heightDp = 800)

        assertTrue(atBreakpoint.compactWidth)
        assertEquals(16, atBreakpoint.horizontalPadding)
        assertEquals(70, atBreakpoint.guidePandaWidth)
        assertEquals(19, atBreakpoint.questionFontSize)
        assertEquals(16, atBreakpoint.footerHorizontalPadding)
        assertFalse(aboveBreakpoint.compactWidth)
        assertEquals(24, aboveBreakpoint.horizontalPadding)
        assertEquals(90, aboveBreakpoint.guidePandaWidth)
        assertEquals(21, aboveBreakpoint.questionFontSize)
    }

    @Test
    fun shortHeight_matchesMiniApp700Breakpoint() {
        val atBreakpoint = OnboardingLayoutSpec.resolve(widthDp = 390, heightDp = 700)
        val aboveBreakpoint = OnboardingLayoutSpec.resolve(widthDp = 390, heightDp = 701)

        assertTrue(atBreakpoint.shortHeight)
        assertEquals(144, atBreakpoint.welcomePandaWidth)
        assertEquals(153, atBreakpoint.welcomePandaHeight)
        assertEquals(34, atBreakpoint.welcomeTitleSize)
        assertEquals(14, atBreakpoint.welcomeBodySize)
        assertEquals(12, atBreakpoint.footerTopPadding)
        assertEquals(14, atBreakpoint.footerBottomPadding)
        assertFalse(aboveBreakpoint.shortHeight)
        assertEquals(190, aboveBreakpoint.welcomePandaWidth)
        assertEquals(38, aboveBreakpoint.welcomeTitleSize)
    }

    @Test
    fun wideWidth_matchesMiniApp700Breakpoint() {
        val atBreakpoint = OnboardingLayoutSpec.resolve(widthDp = 700, heightDp = 900)

        assertTrue(atBreakpoint.wideWidth)
        assertEquals(220, atBreakpoint.welcomePandaWidth)
        assertEquals(233, atBreakpoint.welcomePandaHeight)
        assertEquals(30, atBreakpoint.guideVerticalPadding)
    }

    @Test
    fun shortHeightWinsWelcomeMascotSizeWhenAlsoWide() {
        val spec = OnboardingLayoutSpec.resolve(widthDp = 800, heightDp = 650)

        assertTrue(spec.wideWidth)
        assertTrue(spec.shortHeight)
        assertEquals(220, spec.welcomePandaWidth)
        assertEquals(233, spec.welcomePandaHeight)
    }
}
