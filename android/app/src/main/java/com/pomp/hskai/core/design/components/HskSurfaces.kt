package com.pomp.hskai.core.design.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.pomp.hskai.core.design.PompColors

/**
 * HSK AI's glass-like surface.
 *
 * This first version deliberately avoids a blur dependency. It uses translucent
 * native Compose surfaces, a bright inner wash and a restrained shadow. Real
 * background blur can be layered in later without changing call sites.
 */
@Composable
fun HskGlassSurface(
    modifier: Modifier = Modifier,
    shape: Shape = RoundedCornerShape(20.dp),
    shadowElevation: Dp = 12.dp,
    content: @Composable () -> Unit,
) {
    val surface = if (PompColors.IsDark) {
        PompColors.PaperRaised.copy(alpha = 0.88f)
    } else {
        Color.White.copy(alpha = 0.72f)
    }
    val border = if (PompColors.IsDark) {
        PompColors.Divider.copy(alpha = 0.86f)
    } else {
        Color.White.copy(alpha = 0.92f)
    }
    val topWash = if (PompColors.IsDark) {
        Color.White.copy(alpha = 0.05f)
    } else {
        Color.White.copy(alpha = 0.30f)
    }

    Surface(
        modifier = modifier.shadow(
            elevation = shadowElevation,
            shape = shape,
            clip = false,
            ambientColor = PompColors.Shadow.copy(alpha = 0.14f),
            spotColor = PompColors.Shadow.copy(alpha = 0.18f),
        ),
        shape = shape,
        color = surface,
        border = BorderStroke(1.dp, border),
        tonalElevation = 0.dp,
        shadowElevation = 0.dp,
    ) {
        Box(
            modifier = Modifier.background(
                Brush.verticalGradient(
                    0f to topWash,
                    0.34f to Color.Transparent,
                    1f to Color.Transparent,
                ),
            ),
        ) {
            content()
        }
    }
}
