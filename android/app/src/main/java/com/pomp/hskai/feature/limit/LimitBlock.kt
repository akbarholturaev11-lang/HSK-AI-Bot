package com.pomp.hskai.feature.limit

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors

/** Channel-neutral full-screen offer; every payment decision stays on the server. */
@Composable
fun LimitBlock(
    sectionTitle: String,
    headline: String,
    primaryLabel: String,
    onPrimary: () -> Unit,
    modifier: Modifier = Modifier,
    reason: String? = null,
    hint: String? = null,
    secondaryLabel: String? = null,
    onSecondary: (() -> Unit)? = null,
    tertiaryLabel: String? = null,
    onTertiary: (() -> Unit)? = null,
    isBusy: Boolean = false,
    errorText: String? = null,
    noticeText: String? = null,
) {
    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState())
            .padding(horizontal = 26.dp, vertical = 64.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(Modifier.height(20.dp))
        Surface(color = PompColors.GoldSoft, shape = CircleShape) {
            Box(Modifier.size(94.dp), contentAlignment = Alignment.Center) {
                Icon(Icons.Filled.Lock, contentDescription = null, tint = PompColors.Gold, modifier = Modifier.size(42.dp))
            }
        }
        Spacer(Modifier.height(26.dp))
        Text(
            stringResource(R.string.limit_screen_badge),
            style = MaterialTheme.typography.labelLarge,
            color = PompColors.Cinnabar,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            headline, style = MaterialTheme.typography.headlineMedium, color = PompColors.Ink,
            fontWeight = FontWeight.Bold, textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(12.dp))
        Text(
            reason?.takeIf { it.isNotBlank() } ?: sectionTitle,
            style = MaterialTheme.typography.bodyLarge, color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(24.dp))
        Surface(
            color = PompColors.PaperRaised, shape = RoundedCornerShape(20.dp),
            border = BorderStroke(1.dp, PompColors.Divider),
        ) {
            Column(Modifier.fillMaxWidth().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                listOf(
                    stringResource(R.string.limit_benefit_lessons),
                    stringResource(R.string.limit_benefit_practice),
                    stringResource(R.string.limit_benefit_voice),
                ).forEach { benefit ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("✦", color = PompColors.Gold, style = MaterialTheme.typography.titleMedium)
                        Spacer(Modifier.width(12.dp))
                        Text(benefit, color = PompColors.Ink, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
        }
        Spacer(Modifier.height(34.dp))
        Button(
            onClick = onPrimary, enabled = !isBusy,
            modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp),
            shape = RoundedCornerShape(16.dp),
            colors = ButtonDefaults.buttonColors(containerColor = PompColors.Cinnabar),
        ) {
            if (isBusy) CircularProgressIndicator(
                color = PompColors.Paper, strokeWidth = 2.dp, modifier = Modifier.size(18.dp),
            ) else Text(primaryLabel, style = MaterialTheme.typography.labelLarge)
        }
        if (secondaryLabel != null && onSecondary != null) {
            Spacer(Modifier.height(10.dp))
            OutlinedButton(
                onClick = onSecondary, enabled = !isBusy,
                modifier = Modifier.fillMaxWidth().heightIn(min = 54.dp),
                shape = RoundedCornerShape(16.dp),
                border = BorderStroke(1.dp, PompColors.Cinnabar),
            ) { Text(secondaryLabel, color = PompColors.CinnabarDark) }
        }
        if (tertiaryLabel != null && onTertiary != null) {
            Spacer(Modifier.height(4.dp))
            TextButton(onClick = onTertiary, enabled = !isBusy) {
                Text(tertiaryLabel, color = PompColors.InkSecondary)
            }
        }
        if (!hint.isNullOrBlank()) {
            Spacer(Modifier.height(10.dp))
            Text(hint, color = PompColors.InkSecondary, style = MaterialTheme.typography.bodySmall, textAlign = TextAlign.Center)
        }
        val message = errorText ?: noticeText
        if (!message.isNullOrBlank()) {
            Spacer(Modifier.height(14.dp))
            Text(message, color = if (errorText != null) PompColors.Flame else PompColors.InkSecondary, textAlign = TextAlign.Center)
        }
    }
}
