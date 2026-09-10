package com.pomp.hskai.core.design

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import com.pomp.hskai.core.settings.AppSettings
import com.pomp.hskai.core.settings.AppThemeMode

/**
 * Android appearance is user-controlled: light, dark, or system.
 *
 * Light mode keeps the Mini App's warm paper palette. Dark mode is deliberately
 * designed around Cosmos Blue (#002F49), instead of auto-inverting the cream UI.
 */
@Composable
fun PompHskAiTheme(content: @Composable () -> Unit) {
    val context = LocalContext.current
    val settings = remember(context) { AppSettings(context) }
    val mode by settings.themeMode.collectAsState(initial = AppThemeMode.DEFAULT)
    val darkTheme = when (mode) {
        AppThemeMode.LIGHT -> false
        AppThemeMode.DARK -> true
        AppThemeMode.SYSTEM -> isSystemInDarkTheme()
    }
    val palette = PompColors.paletteFor(darkTheme)

    SideEffect { PompColors.useDarkTheme(darkTheme) }

    MaterialTheme(
        colorScheme = pompColorScheme(darkTheme = darkTheme, palette = palette),
        typography = PompTypography,
        content = content,
    )
}

private fun pompColorScheme(
    darkTheme: Boolean,
    palette: PompPalette,
): ColorScheme = if (darkTheme) {
    darkColorScheme(
        primary = palette.cinnabar,
        onPrimary = palette.paper,
        primaryContainer = palette.cinnabarSoft,
        onPrimaryContainer = palette.cinnabarDark,

        secondary = palette.jade,
        onSecondary = palette.paper,
        secondaryContainer = palette.jadeSoft,
        onSecondaryContainer = palette.ink,

        tertiary = palette.gold,
        onTertiary = palette.paper,
        tertiaryContainer = palette.goldSoft,
        onTertiaryContainer = palette.ink,

        background = palette.paper,
        onBackground = palette.ink,
        surface = palette.paper,
        onSurface = palette.ink,
        surfaceVariant = palette.paperRaised,
        onSurfaceVariant = palette.inkSecondary,

        outline = palette.divider,
        outlineVariant = palette.divider,

        error = palette.cinnabarDark,
        onError = palette.paper,
    )
} else {
    lightColorScheme(
        primary = palette.cinnabar,
        onPrimary = palette.paper,
        primaryContainer = palette.cinnabarSoft,
        onPrimaryContainer = palette.cinnabarDark,

        secondary = palette.jade,
        onSecondary = palette.paper,
        secondaryContainer = palette.jadeSoft,
        onSecondaryContainer = palette.ink,

        tertiary = palette.gold,
        onTertiary = palette.ink,
        tertiaryContainer = palette.goldSoft,
        onTertiaryContainer = palette.ink,

        background = palette.paper,
        onBackground = palette.ink,
        surface = palette.paper,
        onSurface = palette.ink,
        surfaceVariant = palette.paperRaised,
        onSurfaceVariant = palette.inkSecondary,

        outline = palette.divider,
        outlineVariant = palette.divider,

        error = palette.cinnabarDark,
        onError = palette.paper,
    )
}
