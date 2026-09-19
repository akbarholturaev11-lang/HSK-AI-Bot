package com.pomp.hskai.core.design

import androidx.compose.ui.graphics.Color
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * The light palette is not "inspired by" the Mini App — it is the same list of
 * hex values, copied from the `:root` block at the top of `course-v3.html`.
 * A lesson card that reaches for `PompColors.Cinnabar` is therefore painting
 * the Mini App's own `--cin`, and the two products cannot drift apart by
 * someone nudging one of them.
 *
 * If a token here has to change, change it in `course-v3.html` first.
 */
class MiniAppPaletteTest {

    private fun assertToken(css: String, hex: Long, actual: Color) {
        assertEquals("$css must stay ${hex.toString(16)}", Color(hex), actual)
    }

    @Test
    fun `every shared token matches course-v3 root`() {
        assertToken("--ink", 0xFF211D17, PompColors.LightInk)
        assertToken("--ink2", 0xFF665D50, PompColors.LightInkSecondary)
        assertToken("--ink3", 0xFFA89E8E, PompColors.LightInkDisabled)
        assertToken("--paper", 0xFFFDF9F0, PompColors.LightPaper)
        assertToken("--card", 0xFFFFFFFF, PompColors.LightPaperRaised)
        assertToken("--line", 0xFFEAE0CC, PompColors.LightDivider)
        assertToken("--cin", 0xFFE04A40, PompColors.LightCinnabar)
        assertToken("--cin2", 0xFFB23530, PompColors.LightCinnabarDark)
        assertToken("--cinbg", 0xFFFDEBE7, PompColors.LightCinnabarSoft)
        assertToken("--gold", 0xFFE9A916, PompColors.LightGold)
        assertToken("--goldbg", 0xFFFAF0D3, PompColors.LightGoldSoft)
        assertToken("--jade", 0xFF2FA06A, PompColors.LightJade)
        assertToken("--jadebg", 0xFFE3F4EA, PompColors.LightJadeSoft)
    }
}
