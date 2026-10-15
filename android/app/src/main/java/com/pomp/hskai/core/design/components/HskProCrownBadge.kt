package com.pomp.hskai.core.design.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.pomp.hskai.core.design.PompColors

/** The Mini App league's gold square Pro crown, shared by Android profile and rating. */
@Composable
fun HskProCrownBadge(modifier: Modifier = Modifier, size: Dp = 16.dp) {
    Box(
        modifier = modifier
            .size(size)
            .background(PompColors.Gold, RoundedCornerShape(size * 0.26f))
            .semantics { contentDescription = "Pro" },
        contentAlignment = Alignment.Center,
    ) {
        Canvas(modifier = Modifier.fillMaxSize().padding(size * 0.15f)) {
            val w = this.size.width
            val h = this.size.height
            val crown = Path().apply {
                moveTo(w * 0.09f, h * 0.28f)
                lineTo(w * 0.29f, h * 0.48f)
                lineTo(w * 0.50f, h * 0.16f)
                lineTo(w * 0.71f, h * 0.48f)
                lineTo(w * 0.91f, h * 0.28f)
                lineTo(w * 0.80f, h * 0.75f)
                lineTo(w * 0.20f, h * 0.75f)
                close()
            }
            drawPath(
                path = crown,
                color = Color.White,
                style = Stroke(
                    width = (size.value * 0.09f).dp.toPx(),
                    cap = StrokeCap.Round,
                    join = StrokeJoin.Round,
                ),
            )
            drawLine(
                color = Color.White,
                start = Offset(w * 0.22f, h * 0.88f),
                end = Offset(w * 0.78f, h * 0.88f),
                strokeWidth = (size.value * 0.08f).dp.toPx(),
                cap = StrokeCap.Round,
            )
        }
    }
}
