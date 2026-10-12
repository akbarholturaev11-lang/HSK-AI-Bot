package com.pomp.hskai.core.design.components

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.MenuBook
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.progressBarRangeInfo
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch as launchCoroutine

/**
 * Branded loading state for HSK AI.
 *
 * Regular loading states breathe with a soft halo. The app launch variant
 * assembles and turns the gold knot once, then reveals the brand wordmark.
 */
@Composable
fun HskBrandLoader(
    modifier: Modifier = Modifier,
    compact: Boolean = false,
    launch: Boolean = false,
) {
    val brandRevealStarted = remember { mutableStateOf(false) }
    val brandReveal = remember { Animatable(0f) }
    val goldWave = remember { Animatable(0f) }
    LaunchedEffect(launch, brandRevealStarted.value) {
        if (!launch || !brandRevealStarted.value) return@LaunchedEffect
        coroutineScope {
            launchCoroutine {
                brandReveal.animateTo(
                    targetValue = 1f,
                    animationSpec = tween(durationMillis = 620, easing = FastOutSlowInEasing),
                )
            }
            delay(560)
            goldWave.animateTo(
                targetValue = 1f,
                animationSpec = tween(durationMillis = 900, easing = FastOutSlowInEasing),
            )
        }
    }

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

    val boxSize = if (compact) 24.dp else if (launch) 256.dp else 92.dp
    val haloSize = if (compact) 24.dp else if (launch) 132.dp else 82.dp
    val sealSize = if (compact) 20.dp else if (launch) 96.dp else 58.dp
    val sealCorner = if (compact) 6.dp else 18.dp
    val brandRed = if (launch) PompColors.LightCinnabar else PompColors.Cinnabar
    val density = LocalDensity.current
    val shimmerStart = with(density) { (-120f + 260f * goldWave.value).dp.toPx() }
    val shimmerWidth = with(density) { 42.dp.toPx() }
    val goldShimmer = Brush.linearGradient(
        colors = listOf(
            PompColors.Gold,
            PompColors.Gold,
            Color(0xFFFFF2C4),
            PompColors.Gold,
            PompColors.Gold,
        ),
        start = Offset(shimmerStart, 0f),
        end = Offset(shimmerStart + shimmerWidth, 0f),
    )

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
                    color = brandRed.copy(alpha = haloAlpha),
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
                        ambientColor = brandRed.copy(alpha = 0.20f),
                        spotColor = brandRed.copy(alpha = 0.28f),
                    ),
                ),
            shape = RoundedCornerShape(sealCorner),
            color = brandRed,
        ) {
            if (launch) {
                HskInterlacedKnot(
                    modifier = Modifier.size(sealSize),
                    onSpinStarted = { brandRevealStarted.value = true },
                )
            } else {
                Image(
                    painter = painterResource(R.drawable.ic_launcher_foreground),
                    contentDescription = null,
                    modifier = Modifier.size(sealSize),
                )
            }
        }
        if (launch) {
            Row(
                modifier = Modifier
                    .align(Alignment.Center)
                    .offset(y = 76.dp)
                    .graphicsLayer {
                        alpha = brandReveal.value
                        translationY = with(density) { 18.dp.toPx() } * (1f - brandReveal.value)
                    },
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "HSK AI",
                    style = MaterialTheme.typography.titleLarge.copy(
                        brush = goldShimmer,
                        fontWeight = FontWeight.ExtraBold,
                        letterSpacing = 1.5.sp,
                    ),
                )
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.MenuBook,
                    contentDescription = null,
                    tint = PompColors.Gold,
                    modifier = Modifier.size(24.dp),
                )
            }
        }
    }
}

/** Assembles the two gold strands, then reveals the over-under crossings. */
@Composable
private fun HskInterlacedKnot(
    modifier: Modifier = Modifier,
    onSpinStarted: () -> Unit,
) {
    val flatProgress = remember { Animatable(0f) }
    val diagonalProgress = remember { Animatable(0f) }
    val crossingProgress = remember { Animatable(0f) }
    val settleScale = remember { Animatable(1f) }
    val rotation = remember { Animatable(0f) }
    val density = LocalDensity.current
    val strandOffset = with(density) { 7.dp.toPx() }

    LaunchedEffect(Unit) {
        flatProgress.animateTo(
            targetValue = 1f,
            animationSpec = spring(dampingRatio = 0.76f, stiffness = 320f),
        )
        delay(80)
        diagonalProgress.animateTo(
            targetValue = 1f,
            animationSpec = spring(dampingRatio = 0.68f, stiffness = 350f),
        )
        delay(90)
        crossingProgress.animateTo(
            targetValue = 1f,
            animationSpec = tween(durationMillis = 240, easing = FastOutSlowInEasing),
        )
        delay(80)
        settleScale.animateTo(
            targetValue = 1.035f,
            animationSpec = spring(dampingRatio = 0.70f, stiffness = 420f),
        )
        settleScale.animateTo(
            targetValue = 1f,
            animationSpec = spring(dampingRatio = 0.82f, stiffness = 520f),
        )
        onSpinStarted()
        rotation.animateTo(
            targetValue = 360f,
            animationSpec = tween(durationMillis = 900, easing = FastOutSlowInEasing),
        )
    }

    Box(
        modifier = modifier.graphicsLayer {
            scaleX = settleScale.value
            scaleY = settleScale.value
            rotationZ = rotation.value
        },
    ) {
        Image(
            painter = painterResource(R.drawable.ic_launcher_strand_a_base),
            contentDescription = null,
            modifier = Modifier.matchParentSize().graphicsLayer {
                val progress = flatProgress.value
                alpha = 0.76f + 0.24f * progress
                scaleX = 0.86f + 0.14f * progress
                scaleY = 0.86f + 0.14f * progress
                rotationZ = -7f * (1f - progress)
                translationX = -strandOffset * (1f - progress)
            },
        )
        Image(
            painter = painterResource(R.drawable.ic_launcher_strand_b),
            contentDescription = null,
            modifier = Modifier.matchParentSize().graphicsLayer {
                val progress = diagonalProgress.value
                alpha = 0.48f + 0.52f * progress
                scaleX = 0.82f + 0.18f * progress
                scaleY = 0.82f + 0.18f * progress
                rotationZ = 8f * (1f - progress)
                translationX = strandOffset * (1f - progress)
                translationY = -strandOffset * 0.6f * (1f - progress)
            },
        )
        Image(
            painter = painterResource(R.drawable.ic_launcher_strand_a_overpass),
            contentDescription = null,
            modifier = Modifier.matchParentSize().graphicsLayer {
                val progress = crossingProgress.value
                alpha = progress
                scaleX = 0.92f + 0.08f * progress
                scaleY = 0.92f + 0.08f * progress
                translationY = -strandOffset * 0.45f * (1f - progress)
            },
        )
    }
}
