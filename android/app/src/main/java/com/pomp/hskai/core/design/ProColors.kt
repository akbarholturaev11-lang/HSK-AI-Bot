package com.pomp.hskai.core.design

import androidx.compose.ui.graphics.Color

/**
 * One colour set for every Pro and Trial window (owner decision 2026-11-22):
 * the light paper surface with a gold accent that the Pro sheet already uses.
 *
 * Same role names as the PWA `/assets/brand/hsk-pro-theme.css`
 * (`--hsk-pro-paper`, `--hsk-pro-gold-ink`, ...). Every role reads the active
 * [PompColors] token, so the theme switch keeps working; only [Halo] and
 * [Glint] are fixed effect tints. Visual only: nothing here decides price,
 * Pro, Trial or access.
 */
object ProColors {
    val Paper: Color get() = PompColors.Paper
    val Surface: Color get() = PompColors.PaperRaised
    val Ink: Color get() = PompColors.Ink
    val Muted: Color get() = PompColors.InkSecondary
    val Line: Color get() = PompColors.Divider
    val Gold: Color get() = PompColors.Gold
    val GoldInk: Color get() = PompColors.GoldInk
    val GoldSoft: Color get() = PompColors.GoldSoft
    val Cta: Color get() = PompColors.Cinnabar
    val CtaDeep: Color get() = PompColors.CinnabarInk
    val OnCta: Color get() = PompColors.OnCinnabar

    /** Soft gold glow behind the Pro panda (`--hsk-pro-halo`). */
    val Halo: Color = Color(0x4DE9A916)

    /** Light band of the one-time Pro glint (`--hsk-pro-glint`). */
    val Glint: Color = Color(0xD9FFF2C4)
}
