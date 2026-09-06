package com.pomp.hskai.feature.onboarding

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp
import com.pomp.hskai.core.design.PompColors

/** Exact native equivalent of `.bub:before` / `.hello:before`. */
@Composable
internal fun MiniAppBubbleTail(
    centered: Boolean,
    modifier: Modifier = Modifier,
) {
    Canvas(
        modifier
            .size(14.dp)
            .graphicsLayer {
                rotationZ = if (centered) -45f else 45f
                translationX = if (centered) 0f else -5.dp.toPx()
                translationY = if (centered) 5.dp.toPx() else 0f
            },
    ) {
        drawRect(PompColors.PaperRaised)
        val stroke = 1.dp.toPx()
        val half = stroke / 2f
        drawLine(
            color = PompColors.Divider,
            start = Offset(half, 0f),
            end = Offset(half, size.height),
            strokeWidth = stroke,
        )
        drawLine(
            color = PompColors.Divider,
            start = Offset(0f, size.height - half),
            end = Offset(size.width, size.height - half),
            strokeWidth = stroke,
        )
    }
}
