package com.pomp.hskai.core.design

import androidx.compose.ui.graphics.Color

/**
 * HSK AI brand tokens, taken from the Course v3 palette so the Android client
 * looks like the same product as the Mini App and the desktop app.
 *
 * Every value below is the Mini App's own, copied verbatim from the custom
 * properties at the top of `app/static/course-v3.html`. The comment on each
 * line names the property it mirrors, and
 * `android/tools/check_palette_matches_miniapp.py` re-reads both files and
 * fails the build if one drifts — a shade of difference is invisible in a
 * screenshot but makes the two clients stop looking like one product.
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

    /** Backdrop behind a sheet or a full-screen flow. */
    val Overlay = Color(0xFF171310)      // --overlay
    /** The warm cast the Mini App uses under raised cards. */
    val Shadow = Color(0xFFE4D9C4)       // --shadow

    val Divider = Color(0xFFEAE0CC)      // --line

    /**
     * Practice-row tiles. The Mini App writes these two pairs straight into
     * the `.t-amber` / `.t-blue` rules instead of declaring them as custom
     * properties, so they are copied by value here and are deliberately not
     * part of the palette check — there is no token for it to compare against.
     * The jade and cinnabar tiles do use tokens (`--jadebg`/`--jade`,
     * `--cinbg`/`--cin`) and are read from the palette above.
     */
    val TileAmberSoft = Color(0xFFF8EFD9) // .t-amber background
    val TileAmberInk = Color(0xFFB07A1E)  // .t-amber foreground
    val TileBlueSoft = Color(0xFFE7F0F8)  // .t-blue background
    val TileBlueInk = Color(0xFF2F6F9E)   // .t-blue foreground

    /**
     * Disabled controls. Android-only: the Mini App has no single token for
     * this, so it is deliberately not part of the palette check. Locked
     * course nodes are a separate case — the Mini App paints those with
     * `--line`, and aligning them belongs with the course-screen work.
     */
    val Locked = Color(0xFFD8CFBE)
}
