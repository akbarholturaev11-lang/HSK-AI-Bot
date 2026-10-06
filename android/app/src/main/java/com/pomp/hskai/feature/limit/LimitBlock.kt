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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
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
import com.pomp.hskai.core.design.PompShapes
import com.pomp.hskai.core.design.PompSpacing

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
            .padding(horizontal = PompSpacing.XLarge, vertical = PompSpacing.Large),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(Modifier.height(PompSpacing.Small))
        Surface(color = PompColors.GoldSoft, shape = CircleShape) {
            Box(Modifier.size(64.dp), contentAlignment = Alignment.Center) {
                Icon(Icons.Filled.Lock, contentDescription = null, tint = PompColors.GoldInk, modifier = Modifier.size(28.dp))
            }
        }
        Spacer(Modifier.height(PompSpacing.Large))
        Text(
            stringResource(R.string.limit_screen_badge),
            style = MaterialTheme.typography.labelLarge,
            color = PompColors.Cinnabar,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(PompSpacing.XSmall))
        Text(
            headline, style = MaterialTheme.typography.headlineMedium, color = PompColors.Ink,
            fontWeight = FontWeight.Bold, textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(PompSpacing.Small))
        Text(
            reason?.takeIf { it.isNotBlank() } ?: sectionTitle,
            style = MaterialTheme.typography.bodyLarge, color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(PompSpacing.Large))
        Surface(
            color = PompColors.PaperRaised, shape = PompShapes.Large,
            border = BorderStroke(1.dp, PompColors.Divider),
        ) {
            Column(Modifier.fillMaxWidth().padding(PompSpacing.Large), verticalArrangement = Arrangement.spacedBy(PompSpacing.Small)) {
                listOf(
                    stringResource(R.string.limit_benefit_lessons),
                    stringResource(R.string.limit_benefit_practice),
                    stringResource(R.string.limit_benefit_voice),
                ).forEach { benefit ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.Check, contentDescription = null, tint = PompColors.JadeInk, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(PompSpacing.Small))
                        Text(benefit, color = PompColors.Ink, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
        }
        Spacer(Modifier.height(PompSpacing.XLarge))
        Button(
            onClick = onPrimary, enabled = !isBusy,
            modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp),
            shape = PompShapes.Medium,
            colors = ButtonDefaults.buttonColors(containerColor = PompColors.Cinnabar),
        ) {
            if (isBusy) CircularProgressIndicator(
                color = PompColors.OnCinnabar, strokeWidth = 2.dp, modifier = Modifier.size(18.dp),
            ) else Text(primaryLabel, style = MaterialTheme.typography.labelLarge)
        }
        if (secondaryLabel != null && onSecondary != null) {
            Spacer(Modifier.height(PompSpacing.Small))
            OutlinedButton(
                onClick = onSecondary, enabled = !isBusy,
                modifier = Modifier.fillMaxWidth().heightIn(min = 54.dp),
                shape = PompShapes.Medium,
                border = BorderStroke(1.dp, PompColors.Cinnabar),
            ) { Text(secondaryLabel, color = PompColors.CinnabarDark) }
        }
        if (tertiaryLabel != null && onTertiary != null) {
            Spacer(Modifier.height(PompSpacing.XSmall))
            TextButton(onClick = onTertiary, enabled = !isBusy) {
                Text(tertiaryLabel, color = PompColors.InkSecondary)
            }
        }
        if (!hint.isNullOrBlank()) {
            Spacer(Modifier.height(PompSpacing.Small))
            Text(hint, color = PompColors.InkSecondary, style = MaterialTheme.typography.bodySmall, textAlign = TextAlign.Center)
        }
        val message = errorText ?: noticeText
        if (!message.isNullOrBlank()) {
            Spacer(Modifier.height(PompSpacing.Medium))
            Text(message, color = if (errorText != null) PompColors.FlameInk else PompColors.InkSecondary, textAlign = TextAlign.Center)
        }
    }
}
