package com.pomp.hskai.feature.foundation

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles

/** Mini App `.foundation-step`: compact pill above every Starter 0 card. */
@Composable
internal fun FoundationStepPill(
    index: Int,
    total: Int,
    label: String,
    modifier: Modifier = Modifier,
) {
    Surface(
        color = PompColors.CinnabarSoft,
        shape = RoundedCornerShape(999.dp),
        modifier = modifier,
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = "${index + 1} / ${total.coerceAtLeast(1)}",
                style = MaterialTheme.typography.labelSmall.copy(
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                ),
                color = PompColors.CinnabarDark,
            )
            if (label.isNotBlank()) {
                Text(
                    text = label,
                    style = MaterialTheme.typography.labelSmall.copy(
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                    ),
                    color = PompColors.CinnabarDark,
                    maxLines = 1,
                )
            }
        }
    }
}

/** Mini App `.foundation-hero`: 72px Hanzi, 21px pinyin, centered copy. */
@Composable
internal fun FoundationHero(
    example: FoundationExample,
    title: String,
    text: String,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        if (example.zh.isNotBlank()) {
            Text(
                text = example.zh,
                style = PompTextStyles.hanziLarge.copy(
                    fontSize = 72.sp,
                    lineHeight = 76.sp,
                ),
                color = PompColors.Ink,
                textAlign = TextAlign.Center,
            )
        }
        if (example.pinyin.isNotBlank()) {
            Spacer(Modifier.height(6.dp))
            Text(
                text = example.pinyin,
                style = MaterialTheme.typography.titleMedium.copy(
                    fontSize = 21.sp,
                    fontWeight = FontWeight.SemiBold,
                ),
                color = PompColors.CinnabarDark,
                textAlign = TextAlign.Center,
            )
        }
        if (title.isNotBlank()) {
            Spacer(Modifier.height(16.dp))
            Text(
                text = title,
                style = MaterialTheme.typography.headlineSmall.copy(
                    fontSize = 22.sp,
                    lineHeight = 28.sp,
                    fontWeight = FontWeight.Medium,
                ),
                color = PompColors.Ink,
                textAlign = TextAlign.Center,
            )
        }
        if (text.isNotBlank()) {
            Spacer(Modifier.height(7.dp))
            Text(
                text = text,
                style = MaterialTheme.typography.bodyMedium.copy(
                    fontSize = 14.sp,
                    lineHeight = 22.sp,
                ),
                color = PompColors.InkSecondary,
                textAlign = TextAlign.Center,
            )
        }
    }
}

/** Mini App `.foundation-audio`: 64px cinnabar circle with a strong floating shadow. */
@Composable
internal fun FoundationCircularAudio(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(modifier = modifier, contentAlignment = Alignment.Center) {
        Surface(
            color = PompColors.CinnabarDark.copy(alpha = 0.22f),
            shape = CircleShape,
            modifier = Modifier
                .size(64.dp)
                .padding(top = 7.dp),
        ) {}
        Surface(
            color = PompColors.Cinnabar,
            shape = CircleShape,
            border = BorderStroke(1.dp, PompColors.CinnabarDark.copy(alpha = 0.15f)),
            modifier = Modifier
                .size(64.dp)
                .clickable(onClick = onClick),
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = Icons.Filled.VolumeUp,
                    contentDescription = null,
                    tint = PompColors.Paper,
                    modifier = Modifier.size(27.dp),
                )
            }
        }
    }
}
