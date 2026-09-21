package com.pomp.hskai.core.design.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.compositeOver
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp
import com.pomp.hskai.core.design.PompColors

@Composable
fun HskPrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    loading: Boolean = false,
) {
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed && enabled) 0.985f else 1f,
        animationSpec = spring(stiffness = 700f, dampingRatio = 0.82f),
        label = "primary-button-scale",
    )

    Surface(
        onClick = onClick,
        modifier = modifier
            .defaultMinSize(minHeight = 52.dp)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            },
        enabled = enabled && !loading,
        interactionSource = interaction,
        shape = RoundedCornerShape(16.dp),
        color = if (enabled) PompColors.Cinnabar else PompColors.Divider,
        contentColor = if (enabled) PompColors.Paper else PompColors.InkDisabled,
        shadowElevation = if (pressed) 2.dp else 8.dp,
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 14.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (loading) {
                HskBrandLoader(compact = true)
            } else {
                Text(text = text, style = MaterialTheme.typography.labelLarge)
            }
        }
    }
}

@Composable
fun HskGlassButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed && enabled) 0.985f else 1f,
        animationSpec = spring(stiffness = 700f, dampingRatio = 0.82f),
        label = "glass-button-scale",
    )

    Surface(
        onClick = onClick,
        modifier = modifier
            .defaultMinSize(minHeight = 48.dp)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            },
        enabled = enabled,
        interactionSource = interaction,
        shape = RoundedCornerShape(16.dp),
        // Composited onto the page instead of left translucent. A Surface
        // that lets light through also lets its own elevation shadow through,
        // and the shadow's inner edge showed as a hard white band across the
        // button, right under the label. The colour on screen is identical —
        // this is the same blend, done once here rather than by the compositor
        // over whatever happens to be behind.
        color = if (PompColors.IsDark) {
            PompColors.PaperRaised.copy(alpha = 0.86f).compositeOver(PompColors.Paper)
        } else {
            Color.White.copy(alpha = 0.66f).compositeOver(PompColors.Paper)
        },
        contentColor = if (enabled) PompColors.Ink else PompColors.InkDisabled,
        border = BorderStroke(
            1.dp,
            if (PompColors.IsDark) PompColors.Divider else Color.White.copy(alpha = 0.88f),
        ),
        shadowElevation = if (pressed) 1.dp else 6.dp,
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 18.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(text = text, style = MaterialTheme.typography.labelLarge)
        }
    }
}
