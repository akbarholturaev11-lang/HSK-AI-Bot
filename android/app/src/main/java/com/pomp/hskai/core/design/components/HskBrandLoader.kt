package com.pomp.hskai.core.design.components

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.progressBarRangeInfo
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors

/**
 * Branded loading state for HSK AI.
 *
 * The seal never spins. Instead it breathes while a soft cinnabar halo expands
 * behind it. That keeps loading recognisable as part of the product rather than
 * a generic Material progress indicator.
 */
@Composable
fun HskBrandLoader(
    modifier: Modifier = Modifier,
    compact: Boolean = false,
) {
    val transition = rememberInfiniteTransition(label = "hsk-brand-loader")
    val breathe by transition.animateFloat(
        initialValue = 0.96f,
        targetValue = 1.04f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1100),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "seal-breathe",
    )
    val haloScale by transition.animateFloat(
        initialValue = 0.84f,
        targetValue = 1.16f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1450),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "halo-scale",
    )
    val haloAlpha by transition.animateFloat(
        initialValue = 0.10f,
        targetValue = 0.24f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1450),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "halo-alpha",
    )

    val boxSize = if (compact) 24.dp else 92.dp
    val haloSize = if (compact) 24.dp else 82.dp
    val sealSize = if (compact) 20.dp else 58.dp
    val sealCorner = if (compact) 6.dp else 18.dp

    Box(
        modifier = modifier
            .size(boxSize)
            .semantics {
                progressBarRangeInfo = ProgressBarRangeInfo.Indeterminate
            },
        contentAlignment = Alignment.Center,
    ) {
        Box(
            modifier = Modifier
                .size(haloSize)
                .graphicsLayer {
                    scaleX = haloScale
                    scaleY = haloScale
                }
                .background(
                    color = PompColors.Cinnabar.copy(alpha = haloAlpha),
                    shape = CircleShape,
                ),
        )
        Surface(
            modifier = Modifier
                .size(sealSize)
                .graphicsLayer {
                    scaleX = breathe
                    scaleY = breathe
                }
                .then(
                    if (compact) Modifier
                    else Modifier.shadow(
                        elevation = 12.dp,
                        shape = RoundedCornerShape(sealCorner),
                        ambientColor = PompColors.Cinnabar.copy(alpha = 0.20f),
                        spotColor = PompColors.Cinnabar.copy(alpha = 0.28f),
                    ),
                ),
            shape = RoundedCornerShape(sealCorner),
            color = PompColors.Cinnabar,
        ) {
            Image(
                painter = painterResource(R.drawable.ic_launcher_foreground),
                contentDescription = null,
                modifier = Modifier.size(sealSize),
            )
        }
    }
}
