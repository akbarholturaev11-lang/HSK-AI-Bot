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

object PompColors {
    val LightPaper = Color(0xFFFDF9F0)
    val LightPaperRaised = Color(0xFFFFFFFF)
    val LightInk = Color(0xFF211D17)
    val LightInkSecondary = Color(0xFF665D50)
    val LightInkDisabled = Color(0xFFA89E8E)
    val LightCinnabar = Color(0xFFE04A40)
    val LightCinnabarDark = Color(0xFFB23530)
    val LightCinnabarSoft = Color(0xFFFDEBE7)
    val LightJade = Color(0xFF2FA06A)
    val LightJadeSoft = Color(0xFFE3F4EA)
    val LightGold = Color(0xFFE9A916)
    val LightGoldSoft = Color(0xFFFAF0D3)
    val LightFlame = Color(0xFFFF9600)
    val LightFlameSoft = Color(0xFFFFEFD6)
    val LightBlue = Color(0xFF2E86C1)
    val LightBlueSoft = Color(0xFFE8F2FA)
    val LightOverlay = Color(0xFF171310)
    val LightShadow = Color(0xFFE4D9C4)
    val LightDivider = Color(0xFFEAE0CC)

    private val LightPalette = PompPalette(
        paper = LightPaper, paperRaised = LightPaperRaised, ink = LightInk,
        inkSecondary = LightInkSecondary, inkDisabled = LightInkDisabled,
        cinnabar = LightCinnabar, cinnabarDark = LightCinnabarDark,
        cinnabarSoft = LightCinnabarSoft, jade = LightJade, jadeSoft = LightJadeSoft,
        gold = LightGold, goldSoft = LightGoldSoft, flame = LightFlame,
        flameSoft = LightFlameSoft, blue = LightBlue, blueSoft = LightBlueSoft,
        overlay = LightOverlay, shadow = LightShadow, divider = LightDivider,
        courseTrail = Color(0xFFEBE2CC), tileAmberSoft = Color(0xFFF8EFD9),
        tileAmberInk = Color(0xFFB07A1E), tileBlueSoft = Color(0xFFE7F0F8),
        tileBlueInk = Color(0xFF2F6F9E), doneDepth = Color(0xFF245F47),
        lockedDepth = Color(0xFFD8D2C4), chestDepth = Color(0xFFD8C79A),
        bossDepth = Color(0xFFE8CFC9), planOnGold = Color(0xFF3A2C08),
        planDone = Color(0xFF7FD6A8), optionDepth = Color(0xFFE6DDCF),
    )

    private val DarkPalette = PompPalette(
        paper = Color(0xFF002F49),
        paperRaised = Color(0xFF073B55),
        ink = Color(0xFFF5FAFD),
        inkSecondary = Color(0xFFB8CDDA),
        inkDisabled = Color(0xFF7FA3B5),
        cinnabar = Color(0xFF20BCEB),
        cinnabarDark = Color(0xFF1299C4),
        cinnabarSoft = Color(0xFF0B4C66),
        jade = Color(0xFF48D99A),
        jadeSoft = Color(0xFF0A5146),
        gold = Color(0xFFF4C95D),
        goldSoft = Color(0xFF584819),
        flame = Color(0xFFFF6B66),
        flameSoft = Color(0xFF5B3135),
        blue = Color(0xFF20BCEB),
        blueSoft = Color(0xFF0B4C66),
        overlay = Color(0xFF000E17),
        shadow = Color(0xFF001824),
        divider = Color(0xFF17617D),
        courseTrail = Color(0xFF17617D),
        tileAmberSoft = Color(0xFF584819),
        tileAmberInk = Color(0xFFF4C95D),
        tileBlueSoft = Color(0xFF0B4C66),
        tileBlueInk = Color(0xFF7EDDF6),
        doneDepth = Color(0xFF0A5146),
        lockedDepth = Color(0xFF0E4D6B),
        chestDepth = Color(0xFF584819),
        bossDepth = Color(0xFF5B3135),
        planOnGold = Color(0xFF302706),
        planDone = Color(0xFF48D99A),
        optionDepth = Color(0xFF0A435F),
    )

    private var activePalette by mutableStateOf(LightPalette)
    internal fun paletteFor(darkTheme: Boolean): PompPalette = if (darkTheme) DarkPalette else LightPalette
    fun useDarkTheme(enabled: Boolean) { activePalette = paletteFor(enabled) }
    val IsDark: Boolean get() = activePalette === DarkPalette

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
    val PlanOnGold: Color get() = activePalette.planOnGold
    val PlanDone: Color get() = activePalette.planDone
    val OptionDepth: Color get() = activePalette.optionDepth
}
