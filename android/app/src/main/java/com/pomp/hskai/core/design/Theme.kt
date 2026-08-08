package com.pomp.hskai.core.design

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

/**
 * Light-only for now, on purpose.
 *
 * The Course v3 identity is a warm cream "paper" surface. Automatically
 * inverting it would produce muddy, low-contrast Chinese text, so dark mode
 * ships only when it has been designed deliberately rather than derived.
 */
private val PompLightColorScheme = lightColorScheme(
    primary = PompColors.Cinnabar,
    onPrimary = PompColors.Paper,
    primaryContainer = PompColors.CinnabarSoft,
    onPrimaryContainer = PompColors.CinnabarDark,

    secondary = PompColors.Jade,
    onSecondary = PompColors.Paper,
    secondaryContainer = PompColors.JadeSoft,
    onSecondaryContainer = PompColors.Ink,

    tertiary = PompColors.Gold,
    onTertiary = PompColors.Ink,
    tertiaryContainer = PompColors.GoldSoft,
    onTertiaryContainer = PompColors.Ink,

    background = PompColors.Paper,
    onBackground = PompColors.Ink,
    surface = PompColors.Paper,
    onSurface = PompColors.Ink,
    surfaceVariant = PompColors.PaperRaised,
    onSurfaceVariant = PompColors.InkSecondary,

    outline = PompColors.Divider,
    outlineVariant = PompColors.Locked,

    error = PompColors.CinnabarDark,
    onError = PompColors.Paper,
)

@Composable
fun PompHskAiTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = PompLightColorScheme,
        typography = PompTypography,
        content = content,
    )
}
