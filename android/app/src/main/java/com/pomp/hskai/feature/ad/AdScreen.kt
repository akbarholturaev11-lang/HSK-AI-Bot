package com.pomp.hskai.feature.ad

import android.view.ViewGroup
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.ui.text.style.TextAlign
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
 * One ad, watched to the end, in exchange for opening a closed section.
 *
 * The countdown here is only what the learner sees. Whether the section
 * actually opens is decided by the server, which measures the real time
 * between the attempt and the report — this screen cannot grant anything.
 */
@Composable
fun AdScreen(
    state: AdUiState,
    onContinue: () -> Unit,
    onClose: () -> Unit,
    onOpenLink: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    // Held in a local so the non-null branch does not depend on a smart cast
    // through a property.
    val mediaUrl = state.mediaUrl
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        when {
            state.isLoading -> Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center,
            ) {
                CircularProgressIndicator(color = PompColors.Cinnabar)
            }

            state.unavailable || mediaUrl == null -> AdMessage(
                text = stringResource(R.string.ad_unavailable),
                actionLabel = stringResource(R.string.action_back),
                onAction = onClose,
            )

            else -> AdContent(
                state = state,
                mediaUrl = mediaUrl,
                onContinue = onContinue,
                onClose = onClose,
                onOpenLink = onOpenLink,
            )
        }
    }
}

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
            .fillMaxSize()
            .padding(20.dp),
        verticalArrangement = Arrangement.Center,
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
                color = PompColors.CinnabarDark,
            )
        }

        Spacer(Modifier.height(8.dp))
        OutlinedButton(
            onClick = onClose,
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 48.dp),
            shape = RoundedCornerShape(14.dp),
        ) {
            Text(
                text = stringResource(R.string.action_back),
                color = PompColors.InkSecondary,
            )
        }
    }
}

/**
 * The video creative.
 *
 * Media3's player types are marked unstable, which is a promise about source
 * compatibility rather than about behaviour; the opt-in is required to use
 * them at all and is spelled out in full so it cannot be confused with
 * Kotlin's own `OptIn`.
 */
@androidx.annotation.OptIn(markerClass = [androidx.media3.common.util.UnstableApi::class])
@Composable
private fun AdVideo(url: String, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val player = remember { ExoPlayer.Builder(context).build() }

    DisposableEffect(url) {
        player.setMediaItem(MediaItem.fromUri(url))
        // An ad shorter than the required watch time would otherwise stop and
        // leave the learner staring at a frozen frame until the countdown ends.
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

@Composable
private fun AdMessage(text: String, actionLabel: String, onAction: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(16.dp))
        OutlinedButton(
            onClick = onAction,
            modifier = Modifier.heightIn(min = 48.dp),
            shape = RoundedCornerShape(14.dp),
        ) {
            Text(text = actionLabel, color = PompColors.CinnabarDark)
        }
    }
}
