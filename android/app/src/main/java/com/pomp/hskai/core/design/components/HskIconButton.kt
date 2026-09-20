package com.pomp.hskai.core.design.components

import androidx.compose.foundation.layout.size
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.pomp.hskai.core.design.PompColors

/**
 * A chrome icon — close, back, settings, the rating bell.
 *
 * It used to sit inside a glass circle with a shadow. On the near-white
 * Paper the circle reads as a pale blob around the glyph rather than as a
 * button, and at the corners of a screen it looked like a loose decoration
 * that had drifted out of place. The icon stands on its own; the tap target
 * stays [size] whatever the glyph measures.
 */
@Composable
fun HskGlassIconButton(
    icon: ImageVector,
    contentDescription: String?,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    size: Dp = 44.dp,
    iconSize: Dp = 20.dp,
    tint: Color = PompColors.InkSecondary,
) {
    IconButton(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.size(size),
    ) {
        Icon(
            imageVector = icon,
            contentDescription = contentDescription,
            tint = if (enabled) tint else PompColors.InkDisabled,
            modifier = Modifier.size(iconSize),
        )
    }
}
