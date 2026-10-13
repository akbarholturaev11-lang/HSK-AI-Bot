package com.pomp.hskai.core.design.components

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
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
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
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
import kotlinx.coroutines.delay

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
    onLaunchAnimationFinished: () -> Unit = {},
) {
    // Mini App uses one deterministic 2,920ms CSS timeline. Do the same in
    // Compose: chained springs previously delayed the knot, title and shimmer.
    val elapsedMs = remember { Animatable(0f) }
    val currentOnLaunchAnimationFinished by rememberUpdatedState(onLaunchAnimationFinished)
    LaunchedEffect(launch) {
        if (launch) {
            elapsedMs.snapTo(0f)
            elapsedMs.animateTo(2920f, animationSpec = tween(2920, easing = LinearEasing))
            currentOnLaunchAnimationFinished()
        }
    }
    val context = LocalContext.current
    /* Cold-start only: synchronize the same Golden Logo chime and two haptics
       with the shared reveal (crossings at 570ms, gold shimmer at 1910ms). */
    LaunchedEffect(launch) {
        if (!launch) return@LaunchedEffect
        val feedback = HskLaunchFeedback(context.applicationContext)
        try {
            feedback.play()
            delay(570)
            feedback.pulse(strong = false)
            delay(1340)
            feedback.pulse(strong = true)
            delay(1100)
        } finally {
            feedback.release()
        }
    }
    val titleReveal = launchPhase(elapsedMs.value, 1330f, 620f, HskEaseOut)
    val bookReveal = launchPhase(elapsedMs.value, 1410f, 560f, HskEaseOut)
    val goldWave = launchPhase(elapsedMs.value, 1910f, 900f, FastOutSlowInEasing)

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
    val brandRed = if (launch) Color(0xFFF0614C) else PompColors.Cinnabar
    val density = LocalDensity.current
    val shimmerStart = with(density) { (-120f + 260f * goldWave).dp.toPx() }
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
            // CSS centers the full 96px seal + 22px gap + 36px title group.
            // Its seal center is 29px above the viewport center.
            .then(if (launch) Modifier.offset(y = (-29).dp) else Modifier)
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
                    brush = if (launch) Brush.radialGradient(
                        colors = listOf(
                            brandRed.copy(alpha = 0.24f * haloAlpha),
                            brandRed.copy(alpha = 0f),
                        ),
                    ) else Brush.radialGradient(
                        colors = listOf(brandRed.copy(alpha = haloAlpha), brandRed.copy(alpha = haloAlpha)),
                    ),
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
            color = if (launch) Color.Transparent else brandRed,
        ) {
            Box(
                modifier = Modifier.fillMaxSize().then(
                    if (launch) Modifier.background(
                        Brush.linearGradient(listOf(Color(0xFFF0614C), Color(0xFFC02F32))),
                    ) else Modifier
                ),
            ) {
                if (launch) {
                    HskInterlacedKnot(
                        modifier = Modifier.fillMaxSize(),
                        elapsedMs = elapsedMs.value,
                    )
                } else {
                    Image(
                        painter = painterResource(R.drawable.ic_launcher_foreground),
                        contentDescription = null,
                        modifier = Modifier.fillMaxSize(),
                    )
                }
            }
        }
        if (launch) {
            Row(
                modifier = Modifier
                    .align(Alignment.Center)
                    .offset(y = 88.dp)
                    .graphicsLayer {
                        alpha = titleReveal
                        translationY = with(density) { 18.dp.toPx() } * (1f - titleReveal)
                    },
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "HSK AI",
                    style = MaterialTheme.typography.titleLarge.copy(
                        brush = goldShimmer,
                        fontWeight = FontWeight.ExtraBold,
                        fontSize = 25.sp,
                        letterSpacing = 2.7.sp,
                    ),
                )
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.MenuBook,
                    contentDescription = null,
                    tint = PompColors.Gold,
                    modifier = Modifier.size(24.dp).graphicsLayer {
                        alpha = if (titleReveal <= 0f) 0f else bookReveal / titleReveal
                        translationY = with(density) { 16.dp.toPx() } * (1f - bookReveal)
                        rotationZ = -12f * (1f - bookReveal)
                    },
                )
            }
        }
    }
}

/* CSS curves and offsets from course-v3.html: the same visual timebase drives
   the knot, title, book and gold flash, independent of device spring physics. */
private val HskAssembleEase = CubicBezierEasing(0.18f, 0.82f, 0.28f, 1.16f)
private val HskEaseOut = CubicBezierEasing(0.16f, 1f, 0.3f, 1f)
private val HskSpinEase = CubicBezierEasing(0.24f, 0.82f, 0.32f, 1f)

private fun launchPhase(
    clockMs: Float,
    startMs: Float,
    durationMs: Float,
    easing: androidx.compose.animation.core.Easing = LinearEasing,
): Float {
    if (clockMs <= startMs) return 0f
    if (clockMs >= startMs + durationMs) return 1f
    return easing.transform(((clockMs - startMs) / durationMs).coerceIn(0f, 1f))
}

@Composable
private fun HskInterlacedKnot(modifier: Modifier = Modifier, elapsedMs: Float) {
    val flat = launchPhase(elapsedMs, 0f, 520f, HskAssembleEase)
    val diagonal = launchPhase(elapsedMs, 80f, 530f, HskAssembleEase)
    val crossing = launchPhase(elapsedMs, 570f, 240f, FastOutSlowInEasing)
    val spin = launchPhase(elapsedMs, 1170f, 900f, HskSpinEase)
    val settle = when {
        elapsedMs < 890f -> 1f
        elapsedMs < 1047f -> 1f + 0.035f * launchPhase(elapsedMs, 890f, 157f, HskEaseOut)
        elapsedMs < 1170f -> 1.035f - 0.035f * launchPhase(elapsedMs, 1047f, 123f, HskEaseOut)
        else -> 1f
    }
    val density = LocalDensity.current
    val strandOffset = with(density) { 7.dp.toPx() }
    Box(
        modifier = modifier.graphicsLayer {
            scaleX = settle
            scaleY = settle
            rotationZ = 360f * spin
        },
    ) {
        Image(
            painter = painterResource(R.drawable.ic_launcher_strand_a_base),
            contentDescription = null,
            modifier = Modifier.matchParentSize().graphicsLayer {
                alpha = 0.76f + 0.24f * flat
                scaleX = 0.86f + 0.14f * flat
                scaleY = 0.86f + 0.14f * flat
                rotationZ = -7f * (1f - flat)
                translationX = -strandOffset * (1f - flat)
            },
        )
        Image(
            painter = painterResource(R.drawable.ic_launcher_strand_b),
            contentDescription = null,
            modifier = Modifier.matchParentSize().graphicsLayer {
                alpha = 0.48f + 0.52f * diagonal
                scaleX = 0.82f + 0.18f * diagonal
                scaleY = 0.82f + 0.18f * diagonal
                rotationZ = 8f * (1f - diagonal)
                translationX = strandOffset * (1f - diagonal)
                translationY = -strandOffset * 0.6f * (1f - diagonal)
            },
        )
        Image(
            painter = painterResource(R.drawable.ic_launcher_strand_a_overpass),
            contentDescription = null,
            modifier = Modifier.matchParentSize().graphicsLayer {
                alpha = crossing
                scaleX = 0.92f + 0.08f * crossing
                scaleY = 0.92f + 0.08f * crossing
                translationY = -strandOffset * 0.45f * (1f - crossing)
            },
        )
    }
}
