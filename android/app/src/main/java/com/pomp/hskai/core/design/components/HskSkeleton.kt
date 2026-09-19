package com.pomp.hskai.core.design.components

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.pomp.hskai.core.design.PompColors

/**
 * Lightweight list skeleton. One pulse animation drives the whole row, so a
 * screen can show several placeholders without starting shimmer animations for
 * every individual bar.
 */
@Composable
fun HskListSkeletonRow(
    modifier: Modifier = Modifier,
    leadingCircle: Boolean = true,
    compact: Boolean = false,
) {
    val transition = rememberInfiniteTransition(label = "hsk-skeleton")
    val alpha by transition.animateFloat(
        initialValue = if (PompColors.IsDark) 0.28f else 0.42f,
        targetValue = if (PompColors.IsDark) 0.52f else 0.72f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 900),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "skeleton-alpha",
    )
    val shape = RoundedCornerShape(if (compact) 14.dp else 16.dp)

    HskGlassSurface(
        modifier = modifier,
        shape = shape,
        shadowElevation = if (compact) 3.dp else 5.dp,
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(
                    horizontal = if (compact) 12.dp else 14.dp,
                    vertical = if (compact) 10.dp else 13.dp,
                ),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (leadingCircle) {
                SkeletonBlock(
                    modifier = Modifier.size(if (compact) 32.dp else 40.dp),
                    alpha = alpha,
                    shape = CircleShape,
                )
                Spacer(Modifier.width(12.dp))
            }
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(7.dp),
            ) {
                SkeletonBlock(
                    modifier = Modifier.fillMaxWidth(0.56f).height(if (compact) 10.dp else 12.dp),
                    alpha = alpha,
                )
                SkeletonBlock(
                    modifier = Modifier.fillMaxWidth(0.82f).height(if (compact) 8.dp else 10.dp),
                    alpha = alpha * 0.82f,
                )
            }
            Spacer(Modifier.width(12.dp))
            SkeletonBlock(
                modifier = Modifier.width(if (compact) 32.dp else 42.dp).height(10.dp),
                alpha = alpha * 0.74f,
            )
        }
    }
}

@Composable
fun HskContentSkeleton(
    rows: Int,
    modifier: Modifier = Modifier,
    compact: Boolean = false,
    leadingCircle: Boolean = true,
) {
    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        repeat(rows.coerceAtLeast(1)) {
            HskListSkeletonRow(
                modifier = Modifier.fillMaxWidth(),
                leadingCircle = leadingCircle,
                compact = compact,
            )
        }
    }
}

@Composable
private fun SkeletonBlock(
    modifier: Modifier,
    alpha: Float,
    shape: androidx.compose.ui.graphics.Shape = RoundedCornerShape(999.dp),
) {
    val color = if (PompColors.IsDark) {
        Color.White.copy(alpha = alpha * 0.26f)
    } else {
        PompColors.Divider.copy(alpha = alpha)
    }
    Box(modifier = modifier.background(color = color, shape = shape))
}
