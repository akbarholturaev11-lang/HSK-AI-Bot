package com.pomp.hskai.feature.lesson

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.keyframes
import androidx.compose.animation.core.snap
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.SkipNext
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.zIndex
import androidx.core.content.ContextCompat
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.core.design.components.hskMotionOff
import com.pomp.hskai.core.settings.PinyinVisibility
import com.pomp.hskai.domain.model.PictureReviewCard
import com.pomp.hskai.domain.model.PictureWord

/*
 * UIUX-008 picture pronunciation deck, the Android twin of the Mini App's
 * `cardPictureReview`: a stacked queue (the cards behind peek out a little
 * higher), a picture on the front, the lesson's microphone below and the
 * Mini App's quiet Skip under it. The answer is composed only after a scored
 * try; the card turns over (through 160°, settling flat to stay readable).
 */

private val CardShape = RoundedCornerShape(24.dp)
private const val PEEK_DP = 15f
private const val DEPTH_SCALE = 0.07f
private const val VISIBLE_DEPTH = 3

@Composable
fun PictureReviewDeckView(
    card: PictureReviewCard,
    deck: PictureDeckState,
    pinyin: PinyinVisibility,
    onSpeak: () -> Unit,
    onSkip: () -> Unit,
    onContinue: () -> Unit,
) {
    val context = LocalContext.current
    val motion = remember { !hskMotionOff(context) }
    var permissionDenied by remember { mutableStateOf(false) }
    val phase = deck.phase
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
        PictureStack(card = card, deck = deck, pinyin = pinyin, motion = motion, onContinue = onContinue)
        Spacer(Modifier.height(26.dp))
        val revealed = phase is PicturePhase.Reveal || phase is PicturePhase.Leaving
        Box(modifier = Modifier.alpha(if (revealed) 0.45f else 1f)) {
            LessonMicButton(
                enabled = phase == PicturePhase.Ask,
                isRecording = phase == PicturePhase.Recording,
                onSpeak = onSpeak,
                onPermissionResult = { denied -> permissionDenied = denied },
            )
        }
        Spacer(Modifier.height(9.dp))
        val error = deck.error
        val status = when {
            phase == PicturePhase.Recording -> stringResource(R.string.foundation_speak_listening)
            phase == PicturePhase.Scoring -> stringResource(R.string.foundation_speak_checking)
            phase is PicturePhase.Reveal ->
                stringResource(if (phase.passed) R.string.hsk_course_correct else R.string.hsk_course_wrong)
            error != null -> stringResource(error.messageRes)
            deck.unclear -> stringResource(R.string.hsk_course_pronunciation_bad)
            else -> stringResource(R.string.hsk_course_pronunciation_hint)
        }
        val statusColor = when {
            phase is PicturePhase.Reveal -> if (phase.passed) PompColors.JadeInk else PompColors.GoldInk
            error != null -> PompColors.Flame
            deck.unclear -> PompColors.InkSecondary
            else -> PompColors.InkDisabled
        }
        Text(
            text = status,
            style = MaterialTheme.typography.bodySmall.copy(fontSize = 13.sp),
            color = statusColor,
            textAlign = TextAlign.Center,
            modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
        )
        if (permissionDenied) {
            Spacer(Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.lesson_microphone_permission_required),
                style = MaterialTheme.typography.bodySmall,
                color = PompColors.Flame,
                textAlign = TextAlign.Center,
            )
        }
        Spacer(Modifier.height(10.dp))
        PictureSkipButton(enabled = phase !is PicturePhase.Leaving, onClick = onSkip)
    }
}

/** The Mini App's `.pr-skip`: quiet text and a skip icon, no button chrome. */
@Composable
private fun PictureSkipButton(enabled: Boolean, onClick: () -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(5.dp),
        modifier = Modifier
            .heightIn(min = 40.dp)
            .clip(RoundedCornerShape(10.dp))
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 6.dp),
    ) {
        Text(
            text = stringResource(R.string.hsk_course_pronunciation_skip),
            fontSize = 13.sp,
            fontWeight = FontWeight.Medium,
            color = PompColors.InkDisabled,
        )
        Icon(
            imageVector = Icons.Filled.SkipNext,
            contentDescription = null,
            tint = PompColors.InkDisabled,
            modifier = Modifier.size(16.dp),
        )
    }
}

@Composable
private fun PictureStack(
    card: PictureReviewCard,
    deck: PictureDeckState,
    pinyin: PinyinVisibility,
    motion: Boolean,
    onContinue: () -> Unit,
) {
    // A short 3D deal when the deck first appears.
    val intro = remember(card.materialRef) { Animatable(if (motion) 0f else 1f) }
    LaunchedEffect(card.materialRef) {
        if (motion) intro.animateTo(1f, tween(durationMillis = 560, easing = LinearEasing))
    }
    BoxWithConstraints(
        modifier = Modifier.fillMaxWidth().padding(top = 34.dp),
        contentAlignment = Alignment.TopCenter,
    ) {
        val width = if (maxWidth < 280.dp) maxWidth else 280.dp
        Box(modifier = Modifier.size(width = width, height = 250.dp)) {
            deck.order.take(VISIBLE_DEPTH).forEachIndexed { depth, wordIndex ->
                val word = card.words.getOrNull(wordIndex) ?: return@forEachIndexed
                key(wordIndex) {
                    PictureStackCard(
                        word = word,
                        depth = depth,
                        phase = if (depth == 0) deck.phase else PicturePhase.Ask,
                        pinyin = pinyin,
                        motion = motion,
                        introProgress = intro.value,
                        onContinue = onContinue,
                        modifier = Modifier.zIndex((VISIBLE_DEPTH - depth).toFloat()),
                    )
                }
            }
        }
    }
}

@Composable
private fun PictureStackCard(
    word: PictureWord,
    depth: Int,
    phase: PicturePhase,
    pinyin: PinyinVisibility,
    motion: Boolean,
    introProgress: Float,
    onContinue: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val density = LocalDensity.current
    val leaving = (phase as? PicturePhase.Leaving)?.outcome
    val passed: Boolean? = (phase as? PicturePhase.Reveal)?.passed ?: when (leaving) {
        PictureOutcome.PASS -> true
        PictureOutcome.WRONG -> false
        else -> null
    }
    val revealed = phase is PicturePhase.Reveal ||
        leaving == PictureOutcome.PASS || leaving == PictureOutcome.WRONG

    fun move(duration: Int) = if (motion) tween<Float>(duration, easing = FastOutSlowInEasing) else snap()
    val y by animateFloatAsState(
        targetValue = if (leaving == PictureOutcome.WRONG) 46f else -PEEK_DP * depth,
        animationSpec = move(320), label = "picture-y",
    )
    val x by animateFloatAsState(
        targetValue = when (leaving) {
            PictureOutcome.PASS -> 1.18f
            PictureOutcome.SKIP -> -1.18f
            else -> 0f
        },
        animationSpec = move(320), label = "picture-x",
    )
    val tilt by animateFloatAsState(
        targetValue = when (leaving) {
            PictureOutcome.PASS -> 9f
            PictureOutcome.SKIP -> -7f
            else -> 0f
        },
        animationSpec = move(320), label = "picture-tilt",
    )
    val scale by animateFloatAsState(
        targetValue = if (leaving == PictureOutcome.WRONG) 0.9f else 1f - DEPTH_SCALE * depth,
        animationSpec = move(320), label = "picture-scale",
    )
    val fade by animateFloatAsState(
        targetValue = if (leaving != null) 0f else 1f,
        animationSpec = move(320), label = "picture-fade",
    )
    // Turns through 160° and settles flat so the hanzi stays readable.
    val flip by animateFloatAsState(
        targetValue = if (revealed) 180f else 0f,
        animationSpec = if (revealed && motion) {
            keyframes {
                durationMillis = 520
                0f at 0
                160f at 370 using FastOutSlowInEasing
                180f at 520
            }
        } else {
            snap()
        },
        label = "picture-flip",
    )
    val fill by animateColorAsState(
        targetValue = when (passed) {
            true -> PompColors.JadeSoft
            false -> PompColors.GoldSoft
            null -> PompColors.CardSurface
        },
        label = "picture-fill",
    )
    val edge by animateColorAsState(
        targetValue = when (passed) {
            true -> PompColors.Jade
            false -> PompColors.Gold
            null -> PompColors.Divider
        },
        label = "picture-edge",
    )
    // The jump that announces a verdict.
    val hop = remember { Animatable(0f) }
    LaunchedEffect(phase is PicturePhase.Reveal) {
        if (phase is PicturePhase.Reveal && motion) {
            hop.animateTo(-14f, tween(durationMillis = 110, easing = FastOutSlowInEasing))
            hop.animateTo(0f, spring(dampingRatio = 0.45f, stiffness = 900f))
        }
    }
    val local = ((introProgress * 560f - depth * 70f) / 420f).coerceIn(0f, 1f)
    val dealt = FastOutSlowInEasing.transform(local)

    Box(
        modifier = modifier
            .fillMaxSize()
            .graphicsLayer {
                transformOrigin = TransformOrigin(0.5f, 0f)
                translationX = x * size.width
                translationY = (y + hop.value + (1f - dealt) * -70f) * density.density
                rotationZ = tilt
                rotationX = (1f - dealt) * 58f
                scaleX = scale
                scaleY = scale
                alpha = fade * dealt
                cameraDistance = 14f * density.density
            }
            .clickable(
                enabled = depth == 0 && phase is PicturePhase.Reveal,
                role = Role.Button,
                onClick = onContinue,
            ),
    ) {
        // The Mini App's `0 6px 0 var(--shadow)` depth.
        Box(
            modifier = Modifier
                .matchParentSize()
                .offset(y = 6.dp)
                .clip(CardShape)
                .background(PompColors.Shadow),
        )
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .matchParentSize()
                .graphicsLayer {
                    rotationY = flip
                    cameraDistance = 14f * density.density
                }
                .clip(CardShape)
                .background(fill)
                .border(1.5.dp, edge, CardShape)
                .padding(18.dp),
        ) {
            if (flip <= 90f) {
                // Only the front card shows its picture; the ones behind wait blank.
                if (depth == 0) {
                    Text(
                        text = word.image,
                        fontSize = 96.sp,
                        modifier = Modifier.semantics { contentDescription = word.meaning },
                    )
                }
            } else {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                    modifier = Modifier.graphicsLayer { rotationY = 180f },
                ) {
                    Text(
                        text = word.hanzi,
                        style = PompTextStyles.hanziLarge,
                        color = PompColors.Ink,
                        textAlign = TextAlign.Center,
                    )
                    if (pinyin == PinyinVisibility.ALL && word.pinyin.isNotBlank()) {
                        Text(
                            text = word.pinyin,
                            fontSize = 17.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = PompColors.CinnabarDark,
                        )
                    }
                    if (word.meaning.isNotBlank()) {
                        Text(
                            text = word.meaning,
                            style = MaterialTheme.typography.bodyMedium,
                            color = PompColors.InkSecondary,
                            textAlign = TextAlign.Center,
                        )
                    }
                }
            }
        }
    }
}

/**
 * The lesson's microphone: the pronunciation card's wide cinnabar button, with
 * its permission request. Shared so the deck and the card cannot drift apart.
 */
@Composable
internal fun LessonMicButton(
    enabled: Boolean,
    isRecording: Boolean,
    onSpeak: () -> Unit,
    onPermissionResult: (denied: Boolean) -> Unit,
) {
    val context = LocalContext.current
    val permission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        onPermissionResult(!granted)
        if (granted) onSpeak()
    }
    val micShape = RoundedCornerShape(20.dp)
    val micColor = if (isRecording) PompColors.CinnabarDark else PompColors.Cinnabar
    Box(modifier = Modifier.padding(bottom = 6.dp)) {
        Box(
            modifier = Modifier
                .matchParentSize()
                .offset(y = 6.dp)
                .clip(micShape)
                .background(if (enabled) PompColors.CinnabarDark else PompColors.Divider),
        )
        Surface(
            onClick = {
                val granted = ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.RECORD_AUDIO,
                ) == PackageManager.PERMISSION_GRANTED
                if (granted) {
                    onPermissionResult(false)
                    onSpeak()
                } else {
                    permission.launch(Manifest.permission.RECORD_AUDIO)
                }
            },
            enabled = enabled,
            shape = micShape,
            color = micColor,
            modifier = Modifier.size(width = 208.dp, height = 80.dp),
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = Icons.Filled.Mic,
                    contentDescription = stringResource(R.string.hsk_course_course_voice_inline_a11y_mic),
                    tint = PompColors.Paper,
                    modifier = Modifier.size(36.dp),
                )
            }
        }
    }
}
