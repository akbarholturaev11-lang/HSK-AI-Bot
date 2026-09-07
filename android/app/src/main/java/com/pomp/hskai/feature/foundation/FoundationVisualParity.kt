package com.pomp.hskai.feature.foundation

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
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

@Composable
internal fun FoundationStepPill(index: Int, total: Int, label: String, modifier: Modifier = Modifier) {
    Surface(color = PompColors.CinnabarSoft, shape = RoundedCornerShape(999.dp), modifier = modifier) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = "${index + 1} / ${total.coerceAtLeast(1)}",
                style = MaterialTheme.typography.labelSmall.copy(fontSize = 11.sp, fontWeight = FontWeight.Bold),
                color = PompColors.CinnabarDark,
            )
            if (label.isNotBlank()) Text(
                text = label,
                style = MaterialTheme.typography.labelSmall.copy(fontSize = 11.sp, fontWeight = FontWeight.Bold),
                color = PompColors.CinnabarDark,
                maxLines = 1,
            )
        }
    }
}

@Composable
internal fun FoundationHero(example: FoundationExample, title: String, text: String, modifier: Modifier = Modifier) {
    Column(modifier = modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        if (example.zh.isNotBlank()) Text(
            text = example.zh,
            style = PompTextStyles.hanziLarge.copy(fontSize = 72.sp, lineHeight = 76.sp),
            color = PompColors.Ink,
            textAlign = TextAlign.Center,
        )
        if (example.pinyin.isNotBlank()) {
            Spacer(Modifier.height(6.dp))
            Text(
                text = example.pinyin,
                style = MaterialTheme.typography.titleMedium.copy(fontSize = 21.sp, fontWeight = FontWeight.SemiBold),
                color = PompColors.CinnabarDark,
                textAlign = TextAlign.Center,
            )
        }
        if (title.isNotBlank()) {
            Spacer(Modifier.height(16.dp))
            Text(
                text = title,
                style = MaterialTheme.typography.headlineSmall.copy(fontSize = 22.sp, lineHeight = 28.sp, fontWeight = FontWeight.Medium),
                color = PompColors.Ink,
                textAlign = TextAlign.Center,
            )
        }
        if (text.isNotBlank()) {
            Spacer(Modifier.height(7.dp))
            Text(
                text = text,
                style = MaterialTheme.typography.bodyMedium.copy(fontSize = 14.sp, lineHeight = 22.sp),
                color = PompColors.InkSecondary,
                textAlign = TextAlign.Center,
            )
        }
    }
}

@Composable
internal fun FoundationCircularAudio(onClick: () -> Unit, modifier: Modifier = Modifier) {
    Box(modifier = modifier, contentAlignment = Alignment.Center) {
        Surface(
            color = PompColors.CinnabarDark.copy(alpha = 0.22f),
            shape = CircleShape,
            modifier = Modifier.size(64.dp).padding(top = 7.dp),
        ) {}
        Surface(
            color = PompColors.Cinnabar,
            shape = CircleShape,
            border = BorderStroke(1.dp, PompColors.CinnabarDark.copy(alpha = 0.15f)),
            modifier = Modifier.size(64.dp).clickable(onClick = onClick),
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(Icons.Filled.VolumeUp, contentDescription = null, tint = PompColors.Paper, modifier = Modifier.size(27.dp))
            }
        }
    }
}

@Composable
internal fun FoundationListenAudio(onClick: () -> Unit, modifier: Modifier = Modifier) {
    Surface(
        color = PompColors.CinnabarSoft,
        shape = CircleShape,
        modifier = modifier.size(48.dp).clickable(onClick = onClick),
    ) {
        Box(contentAlignment = Alignment.Center) {
            Icon(Icons.Filled.VolumeUp, contentDescription = null, tint = PompColors.Cinnabar, modifier = Modifier.size(22.dp))
        }
    }
}

@Composable
internal fun FoundationPartsGrid(
    examples: List<FoundationExample>,
    onPlayExample: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(10.dp)) {
        examples.chunked(2).forEach { rowExamples ->
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                rowExamples.forEach { example ->
                    FoundationMiniCard(
                        example = example,
                        modifier = Modifier.weight(1f),
                        hanziSize = 42,
                        verticalPadding = 17,
                        onClick = { if (example.zh.isNotBlank()) onPlayExample(example.zh) },
                    )
                }
                if (rowExamples.size == 1) Spacer(Modifier.weight(1f))
            }
        }
    }
}

@Composable
internal fun FoundationToneGrid(
    examples: List<FoundationExample>,
    onPlayExample: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(modifier = modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
        examples.take(4).forEach { example ->
            FoundationMiniCard(
                example = example,
                modifier = Modifier.weight(1f),
                hanziSize = 20,
                verticalPadding = 13,
                onClick = {
                    val text = example.zh.ifBlank { example.pinyin }
                    if (text.isNotBlank()) onPlayExample(text)
                },
            )
        }
        repeat((4 - examples.take(4).size).coerceAtLeast(0)) { Spacer(Modifier.weight(1f)) }
    }
}

@Composable
internal fun FoundationWinRow(text: String, mastered: Boolean, modifier: Modifier = Modifier) {
    Surface(
        color = if (mastered) PompColors.JadeSoft else PompColors.PaperRaised,
        shape = RoundedCornerShape(13.dp),
        border = BorderStroke(1.dp, if (mastered) PompColors.Jade.copy(alpha = 0.20f) else PompColors.Divider),
        modifier = modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 13.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                imageVector = Icons.Filled.Check,
                contentDescription = null,
                tint = if (mastered) PompColors.Jade else PompColors.InkSecondary,
                modifier = Modifier.size(18.dp),
            )
            Text(
                text = text,
                style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp, fontWeight = FontWeight.SemiBold),
                color = if (mastered) PompColors.Jade else PompColors.InkSecondary,
            )
        }
    }
}

@Composable
private fun FoundationMiniCard(
    example: FoundationExample,
    modifier: Modifier,
    hanziSize: Int,
    verticalPadding: Int,
    onClick: () -> Unit,
) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(if (hanziSize >= 40) 16.dp else 13.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = modifier.clickable(onClick = onClick),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 6.dp, vertical = verticalPadding.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            if (example.zh.isNotBlank()) Text(
                text = example.zh,
                style = PompTextStyles.hanziSmall.copy(fontSize = hanziSize.sp),
                color = PompColors.Ink,
                textAlign = TextAlign.Center,
                maxLines = 1,
            )
            if (example.pinyin.isNotBlank()) Text(
                text = example.pinyin,
                style = MaterialTheme.typography.labelMedium.copy(
                    fontSize = if (hanziSize >= 40) 14.sp else 10.sp,
                    fontWeight = FontWeight.SemiBold,
                ),
                color = PompColors.CinnabarDark,
                textAlign = TextAlign.Center,
                maxLines = 1,
            )
            if (example.translation.isNotBlank()) {
                Spacer(Modifier.height(4.dp))
                Text(
                    text = example.translation,
                    style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp),
                    color = PompColors.InkSecondary,
                    textAlign = TextAlign.Center,
                    maxLines = 2,
                )
            }
        }
    }
}
