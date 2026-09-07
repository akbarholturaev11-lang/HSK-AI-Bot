package com.pomp.hskai.core.design

import androidx.compose.ui.graphics.Color

/**
 * HSK AI brand tokens, taken from the Course v3 palette so the Android client
 * looks like the same product as the Mini App and the desktop app.
 *
 * Every mapped value below is the Mini App's own, copied verbatim from the
 * custom properties at the top of `app/static/course-v3.html`.
 * `android/tools/check_palette_matches_miniapp.py` re-reads both files and
 * fails the build if one drifts.
 *
 * Material 3 is only the technical base here — the default Material blue is
 * never used.
 */
object PompColors {
    val Paper = Color(0xFFFDF9F0)        // --paper
    val PaperRaised = Color(0xFFFFFFFF)  // --card
    val Ink = Color(0xFF211D17)          // --ink
    val InkSecondary = Color(0xFF665D50) // --ink2
    val InkDisabled = Color(0xFFA89E8E)  // --ink3

    val Cinnabar = Color(0xFFE04A40)     // --cin
    val CinnabarDark = Color(0xFFB23530) // --cin2
    val CinnabarSoft = Color(0xFFFDEBE7) // --cinbg

    val Jade = Color(0xFF2FA06A)         // --jade
    val JadeSoft = Color(0xFFE3F4EA)     // --jadebg

    val Gold = Color(0xFFE9A916)         // --gold
    val GoldSoft = Color(0xFFFAF0D3)     // --goldbg

    val Flame = Color(0xFFFF9600)        // --flame
    val FlameSoft = Color(0xFFFFEFD6)    // --flamebg

    val Blue = Color(0xFF2E86C1)         // --blue
    val BlueSoft = Color(0xFFE8F2FA)     // --bluebg

    val Overlay = Color(0xFF171310)      // --overlay
    val Shadow = Color(0xFFE4D9C4)       // --shadow
    val Divider = Color(0xFFEAE0CC)      // --line

    /** Literal used by the Mini App SVG learning trail (not a CSS token). */
    val CourseTrail = Color(0xFFEBE2CC)

    val TileAmberSoft = Color(0xFFF8EFD9)
    val TileAmberInk = Color(0xFFB07A1E)
    val TileBlueSoft = Color(0xFFE7F0F8)
    val TileBlueInk = Color(0xFF2F6F9E)

    val Locked = Divider
    val DoneDepth = Color(0xFF245F47)
    val LockedDepth = Color(0xFFD8D2C4)
    val ChestDepth = Color(0xFFD8C79A)
    val BossDepth = Color(0xFFE8CFC9)

    val NodeDoneDepth = DoneDepth
    val NodeLockedDepth = LockedDepth
    val NodeChestDepth = ChestDepth
    val NodeBossDepth = BossDepth
}
