package com.pomp.hskai.core.design

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.Color

internal data class PompPalette(
    val paper: Color,
    val paperRaised: Color,
    val ink: Color,
    val inkSecondary: Color,
    val inkDisabled: Color,
    val cinnabar: Color,
    val cinnabarDark: Color,
    val cinnabarSoft: Color,
    val jade: Color,
    val jadeSoft: Color,
    val gold: Color,
    val goldSoft: Color,
    val flame: Color,
    val flameSoft: Color,
    val blue: Color,
    val blueSoft: Color,
    val overlay: Color,
    val shadow: Color,
    val divider: Color,
    val courseTrail: Color,
    val tileAmberSoft: Color,
    val tileAmberInk: Color,
    val tileBlueSoft: Color,
    val tileBlueInk: Color,
    val doneDepth: Color,
    val lockedDepth: Color,
    val chestDepth: Color,
    val bossDepth: Color,
    val planOnGold: Color,
    val planDone: Color,
    val optionDepth: Color,
)

/**
 * HSK AI brand tokens. The light palette is still copied value-for-value from
 * the Mini App, while the Android client can now switch to the deliberately
 * designed Cosmos Blue dark palette (#002F49).
 *
 * `android/tools/check_palette_matches_miniapp.py` keeps the light tokens tied
 * to `app/static/course-v3.html`; dark-mode tokens are Android-only.
 */
object PompColors {
    val LightPaper = Color(0xFFFDF9F0)        // --paper
    val LightPaperRaised = Color(0xFFFFFFFF)  // --card
    val LightInk = Color(0xFF211D17)          // --ink
    val LightInkSecondary = Color(0xFF665D50) // --ink2
    val LightInkDisabled = Color(0xFFA89E8E)  // --ink3

    val LightCinnabar = Color(0xFFE04A40)     // --cin
    val LightCinnabarDark = Color(0xFFB23530) // --cin2
    val LightCinnabarSoft = Color(0xFFFDEBE7) // --cinbg

    val LightJade = Color(0xFF2FA06A)         // --jade
    val LightJadeSoft = Color(0xFFE3F4EA)     // --jadebg

    val LightGold = Color(0xFFE9A916)         // --gold
    val LightGoldSoft = Color(0xFFFAF0D3)     // --goldbg

    val LightFlame = Color(0xFFFF9600)        // --flame
    val LightFlameSoft = Color(0xFFFFEFD6)    // --flamebg

    val LightBlue = Color(0xFF2E86C1)         // --blue
    val LightBlueSoft = Color(0xFFE8F2FA)     // --bluebg

    val LightOverlay = Color(0xFF171310)      // --overlay
    val LightShadow = Color(0xFFE4D9C4)       // --shadow
    val LightDivider = Color(0xFFEAE0CC)      // --line

    private val LightPalette = PompPalette(
        paper = LightPaper,
        paperRaised = LightPaperRaised,
        ink = LightInk,
        inkSecondary = LightInkSecondary,
        inkDisabled = LightInkDisabled,
        cinnabar = LightCinnabar,
        cinnabarDark = LightCinnabarDark,
        cinnabarSoft = LightCinnabarSoft,
        jade = LightJade,
        jadeSoft = LightJadeSoft,
        gold = LightGold,
        goldSoft = LightGoldSoft,
        flame = LightFlame,
        flameSoft = LightFlameSoft,
        blue = LightBlue,
        blueSoft = LightBlueSoft,
        overlay = LightOverlay,
        shadow = LightShadow,
        divider = LightDivider,
        courseTrail = Color(0xFFEBE2CC),
        tileAmberSoft = Color(0xFFF8EFD9),
        tileAmberInk = Color(0xFFB07A1E),
        tileBlueSoft = Color(0xFFE7F0F8),
        tileBlueInk = Color(0xFF2F6F9E),
        doneDepth = Color(0xFF245F47),
        lockedDepth = Color(0xFFD8D2C4),
        chestDepth = Color(0xFFD8C79A),
        bossDepth = Color(0xFFE8CFC9),
        planOnGold = Color(0xFF3A2C08),
        planDone = Color(0xFF7FD6A8),
        optionDepth = Color(0xFFE6DDCF),
    )

    private val DarkPalette = PompPalette(
        paper = Color(0xFF002F49),
        paperRaised = Color(0xFF063A55),
        ink = Color(0xFFF7FBFF),
        inkSecondary = Color(0xFFB8CFE0),
        inkDisabled = Color(0xFF7FA3B8),
        cinnabar = Color(0xFF14B8E6),
        cinnabarDark = Color(0xFF7DDDF4),
        cinnabarSoft = Color(0xFF073E5A),
        jade = Color(0xFF67E6B4),
        jadeSoft = Color(0xFF084B43),
        gold = Color(0xFFF4C86A),
        goldSoft = Color(0xFF463A19),
        flame = Color(0xFFFFB056),
        flameSoft = Color(0xFF4A2C17),
        blue = Color(0xFF46C7FF),
        blueSoft = Color(0xFF063D58),
        overlay = Color(0xFF000E17),
        shadow = Color(0xFF001824),
        divider = Color(0xFF0C5574),
        courseTrail = Color(0xFF2B6C86),
        tileAmberSoft = Color(0xFF3A321B),
        tileAmberInk = Color(0xFFF2C56B),
        tileBlueSoft = Color(0xFF073E5A),
        tileBlueInk = Color(0xFF9DDFFF),
        doneDepth = Color(0xFF144D42),
        lockedDepth = Color(0xFF1F4A60),
        chestDepth = Color(0xFF5A491D),
        bossDepth = Color(0xFF593140),
        planOnGold = Color(0xFF2B2208),
        planDone = Color(0xFF7FE6B7),
        optionDepth = Color(0xFF082C42),
    )

    private var activePalette by mutableStateOf(LightPalette)

    internal fun paletteFor(darkTheme: Boolean): PompPalette =
        if (darkTheme) DarkPalette else LightPalette

    fun useDarkTheme(enabled: Boolean) {
        activePalette = paletteFor(enabled)
    }

    val Paper: Color get() = activePalette.paper
    val PaperRaised: Color get() = activePalette.paperRaised
    val Ink: Color get() = activePalette.ink
    val InkSecondary: Color get() = activePalette.inkSecondary
    val InkDisabled: Color get() = activePalette.inkDisabled

    val Cinnabar: Color get() = activePalette.cinnabar
    val CinnabarDark: Color get() = activePalette.cinnabarDark
    val CinnabarSoft: Color get() = activePalette.cinnabarSoft

    val Jade: Color get() = activePalette.jade
    val JadeSoft: Color get() = activePalette.jadeSoft

    val Gold: Color get() = activePalette.gold
    val GoldSoft: Color get() = activePalette.goldSoft

    val Flame: Color get() = activePalette.flame
    val FlameSoft: Color get() = activePalette.flameSoft

    val Blue: Color get() = activePalette.blue
    val BlueSoft: Color get() = activePalette.blueSoft

    val Overlay: Color get() = activePalette.overlay
    val Shadow: Color get() = activePalette.shadow
    val Divider: Color get() = activePalette.divider

    /** Literal used by the Mini App SVG learning trail (not a CSS token). */
    /**
     * Yo'lakcha foni.
     *
     * Yarim shaffof ATAYLAB: to'liq to'q rang qog'oz fonidan ajralib turib,
     * tugunlardan ko'ra ko'proq e'tibor tortardi. Yo'l darslarni bog'lashi
     * kerak, o'zini ko'rsatishi emas.
     */
    val CourseTrail: Color get() = activePalette.courseTrail.copy(alpha = 0.55f)

    val TileAmberSoft: Color get() = activePalette.tileAmberSoft
    val TileAmberInk: Color get() = activePalette.tileAmberInk
    val TileBlueSoft: Color get() = activePalette.tileBlueSoft
    val TileBlueInk: Color get() = activePalette.tileBlueInk

    val Locked: Color get() = Divider
    val DoneDepth: Color get() = activePalette.doneDepth
    val LockedDepth: Color get() = activePalette.lockedDepth
    val ChestDepth: Color get() = activePalette.chestDepth
    val BossDepth: Color get() = activePalette.bossDepth

    val NodeDoneDepth: Color get() = DoneDepth
    val NodeLockedDepth: Color get() = LockedDepth
    val NodeChestDepth: Color get() = ChestDepth
    val NodeBossDepth: Color get() = BossDepth

    /**
     * Daily-plan card literals. The Mini App writes these straight into the
     * `.tplan` rules instead of declaring tokens, so they are copied by value
     * and stay outside the palette check — there is no token to compare with.
     */
    val PlanOnGold: Color get() = activePalette.planOnGold
    val PlanDone: Color get() = activePalette.planDone

    /** `.opt` depth — the 4px ledge the answer buttons sit on. */
    val OptionDepth: Color get() = activePalette.optionDepth
}
