package com.pomp.hskai.feature.ad

import android.view.ViewGroup
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import coil.compose.AsyncImage
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskGlassButton
import com.pomp.hskai.core.design.components.HskGlassSurface
import com.pomp.hskai.core.design.components.HskPrimaryButton

/**
 * The lesson-end placement owns a full-screen ad surface; screen_center stays
 * a compact modal card above the current content. The backend still owns
 * audience, daily cap and the dismissal countdown for both placements.
 */
@Composable
fun AdScreen(
    state: AdUiState,
    onContinue: () -> Unit,
    onClose: () -> Unit,
    onOpenLink: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val mediaUrl = state.mediaUrl
    if (state.isLoading || state.unavailable || mediaUrl == null) return

    if (state.placement == AdViewModel.PLACEMENT_LESSON_END) {
        // Edge-to-edge lesson-end creative: no centered card or dimmed backdrop.
        // System bars remain unobstructed and CTA stays below the media.
        Box(
            modifier = modifier.fillMaxSize().background(Color(0xFF080B10)),
        ) {
            AdContent(
                state = state,
                mediaUrl = mediaUrl,
                onContinue = onContinue,
                onClose = onClose,
                onOpenLink = onOpenLink,
                fullScreen = true,
            )
        }
    } else {
        Box(
            modifier = modifier
                .fillMaxSize()
                .background(PompColors.Ink.copy(alpha = SCRIM_ALPHA))
                .statusBarsPadding()
                .padding(20.dp),
            contentAlignment = Alignment.Center,
        ) {
            HskGlassSurface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(20.dp),
                shadowElevation = 8.dp,
            ) {
                AdContent(
                    state = state,
                    mediaUrl = mediaUrl,
                    onContinue = onContinue,
                    onClose = onClose,
                    onOpenLink = onOpenLink,
                )
            }
        }
    }
}

/** Dark enough to say the app is paused, light enough to still see it. */
private const val SCRIM_ALPHA = 0.62f

@Composable
private fun AdContent(
    state: AdUiState,
    mediaUrl: String,
    onContinue: () -> Unit,
    onClose: () -> Unit,
    onOpenLink: (String) -> Unit,
    fullScreen: Boolean = false,
) {
    val ad = state.ad
    val isPhoto = ad?.mediaType == "photo"
    val title = ad?.title?.takeIf { it.isNotBlank() }
    val link = ad?.linkUrl?.takeIf { it.isNotBlank() }
    val linkLabel = ad?.buttonText?.takeIf { it.isNotBlank() }
    Column(
        modifier = if (fullScreen) {
            Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
                .padding(horizontal = 18.dp, vertical = 12.dp)
        } else {
            Modifier.fillMaxWidth().padding(18.dp)
        },
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = stringResource(R.string.ad_title),
                style = MaterialTheme.typography.labelLarge,
                color = if (fullScreen) Color.White.copy(alpha = 0.82f) else PompColors.InkSecondary,
                modifier = Modifier.weight(1f),
            )
            Text(
                text = if (state.canContinue) {
                    stringResource(R.string.ad_ready)
                } else {
                    stringResource(R.string.ad_wait_seconds, state.remainingSeconds)
                },
                style = MaterialTheme.typography.labelLarge,
                color = if (fullScreen) Color.White else PompColors.CinnabarDark,
            )
        }

        Spacer(Modifier.height(10.dp))
        Box(
            modifier = if (fullScreen) {
                Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .heightIn(min = 120.dp)
                    .background(Color.Black)
            } else {
                Modifier.fillMaxWidth().aspectRatio(16f / 9f)
            },
            contentAlignment = Alignment.Center,
        ) {
            if (isPhoto) {
                AsyncImage(
                    model = mediaUrl,
                    contentDescription = title,
                    contentScale = ContentScale.Fit,
                    modifier = Modifier.fillMaxSize(),
                )
            } else {
                AdVideo(url = mediaUrl, modifier = Modifier.fillMaxSize())
            }
        }

        Spacer(Modifier.height(10.dp))
        LinearProgressIndicator(
            progress = { state.progress },
            color = PompColors.Cinnabar,
            trackColor = PompColors.Divider,
            modifier = Modifier.fillMaxWidth(),
        )

        if (title != null) {
            Spacer(Modifier.height(12.dp))
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                color = if (fullScreen) Color.White else PompColors.Ink,
            )
        }

        if (link != null) {
            Spacer(Modifier.height(10.dp))
            HskGlassButton(
                text = linkLabel ?: stringResource(R.string.ad_learn_more),
                onClick = { onOpenLink(link) },
                modifier = Modifier.fillMaxWidth(),
            )
        }

        Spacer(Modifier.height(14.dp))
        HskPrimaryButton(
            text = stringResource(R.string.ad_continue),
            onClick = onContinue,
            enabled = state.canContinue && !state.isFinishing,
            loading = state.isFinishing,
            modifier = Modifier.fillMaxWidth(),
        )

        val error = state.error
        if (error != null) {
            Spacer(Modifier.height(10.dp))
            Text(
                text = stringResource(error.messageRes),
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.Flame,
            )
        }
    }
}

@androidx.annotation.OptIn(markerClass = [androidx.media3.common.util.UnstableApi::class])
@Composable
private fun AdVideo(url: String, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val player = remember { ExoPlayer.Builder(context).build() }

    DisposableEffect(url) {
        player.setMediaItem(MediaItem.fromUri(url))
        player.repeatMode = Player.REPEAT_MODE_ONE
        player.playWhenReady = true
        player.prepare()
        onDispose { player.release() }
    }

    AndroidView(
        modifier = modifier,
        factory = { viewContext ->
            PlayerView(viewContext).apply {
                useController = false
                layoutParams = ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT,
                )
                setPlayer(player)
            }
        },
    )
}
