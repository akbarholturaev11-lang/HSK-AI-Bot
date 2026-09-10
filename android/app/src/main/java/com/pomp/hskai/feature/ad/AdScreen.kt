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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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

/**
 * One ad, in the centre of the screen, over whatever the learner was doing.
 *
 * It is a card on a scrim rather than a page of its own, because that is what
 * it is: the Mini App shows the same block in the middle of the screen and
 * the app carries on behind it. A full-screen takeover read as a different
 * app having launched.
 *
 * Nothing is bought with the watch. The ad used to open a closed section, so
 * the countdown was a price; now it is only how long the block stays before
 * it may be dismissed, and the number comes from the placement the admin
 * configured.
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
    Box(
        modifier = modifier
            .fillMaxSize()
            .background(PompColors.Ink.copy(alpha = SCRIM_ALPHA))
            .statusBarsPadding()
            .padding(20.dp),
        contentAlignment = Alignment.Center,
    ) {
        when {
            state.isLoading || state.unavailable || mediaUrl == null -> Unit

            else -> Surface(
                color = if (PompColors.IsDark) PompColors.PaperRaised else PompColors.Paper,
                shape = RoundedCornerShape(20.dp),
                modifier = Modifier.fillMaxWidth(),
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
) {
    val ad = state.ad
    val isPhoto = ad?.mediaType == "photo"
    val title = ad?.title?.takeIf { it.isNotBlank() }
    val link = ad?.linkUrl?.takeIf { it.isNotBlank() }
    val linkLabel = ad?.buttonText?.takeIf { it.isNotBlank() }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(18.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = stringResource(R.string.ad_title),
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.InkSecondary,
                modifier = Modifier.weight(1f),
            )
            Text(
                text = if (state.canContinue) {
                    stringResource(R.string.ad_ready)
                } else {
                    stringResource(R.string.ad_wait_seconds, state.remainingSeconds)
                },
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.CinnabarDark,
            )
        }

        Spacer(Modifier.height(10.dp))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(16f / 9f),
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
                color = PompColors.Ink,
            )
        }

        if (link != null) {
            Spacer(Modifier.height(10.dp))
            OutlinedButton(
                onClick = { onOpenLink(link) },
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 48.dp),
                shape = RoundedCornerShape(14.dp),
            ) {
                Text(
                    text = linkLabel ?: stringResource(R.string.ad_learn_more),
                    color = PompColors.CinnabarDark,
                )
            }
        }

        Spacer(Modifier.height(14.dp))
        Button(
            onClick = onContinue,
            enabled = state.canContinue && !state.isFinishing,
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 52.dp),
            shape = RoundedCornerShape(14.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = PompColors.Cinnabar,
                contentColor = PompColors.Paper,
                disabledContainerColor = PompColors.Locked,
                disabledContentColor = PompColors.Paper,
            ),
        ) {
            if (state.isFinishing) {
                CircularProgressIndicator(
                    color = PompColors.Paper,
                    strokeWidth = 2.dp,
                    modifier = Modifier.size(18.dp),
                )
            } else {
                Text(
                    text = stringResource(R.string.ad_continue),
                    style = MaterialTheme.typography.labelLarge,
                )
            }
        }

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
