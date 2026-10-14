package com.pomp.hskai.feature.profile

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.data.api.AndroidAnswerAccuracyBreakdownDto
import com.pomp.hskai.data.api.AndroidProfileAccuracyDto

/** Both rings read the same verified profile metrics as Telegram Mini App. */
@Composable
internal fun ProfileAccuracyRings(accuracy: AndroidProfileAccuracyDto?) {
    val overall = accuracy?.overall ?: AndroidAnswerAccuracyBreakdownDto()
    val today = accuracy?.today ?: AndroidAnswerAccuracyBreakdownDto()
    Surface(
        shape = RoundedCornerShape(17.dp),
        color = PompColors.PaperRaised,
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column {
            Row(modifier = Modifier.fillMaxWidth().padding(vertical = 11.dp)) {
                AccuracyRing(overall, stringResource(R.string.profile_accuracy_overall), Modifier.weight(1f))
                Box(Modifier.width(1.dp).height(118.dp).background(PompColors.Divider))
                AccuracyRing(today, stringResource(R.string.profile_accuracy_today), Modifier.weight(1f))
            }
            Text(
                text = stringResource(R.string.profile_accuracy_note),
                fontSize = 10.sp,
                lineHeight = 13.sp,
                color = PompColors.InkSecondary,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth().padding(start = 10.dp, end = 10.dp, bottom = 9.dp),
            )
        }
    }
}

@Composable
private fun AccuracyRing(data: AndroidAnswerAccuracyBreakdownDto, title: String, modifier: Modifier) {
    val pct = data.percent?.coerceIn(0, 100)
    val color = when {
        pct == null -> PompColors.InkDisabled
        pct >= 80 -> PompColors.Jade
        pct >= 60 -> PompColors.Gold
        else -> PompColors.Cinnabar
    }
    Column(modifier = modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Box(Modifier.size(78.dp), contentAlignment = Alignment.Center) {
            CircularProgressIndicator(
                progress = { (pct ?: 0) / 100f },
                color = color,
                trackColor = PompColors.Divider,
                strokeWidth = 7.dp,
                modifier = Modifier.fillMaxSize(),
            )
            Text(pct?.let { "$it%" } ?: "—", fontSize = 20.sp,
                fontWeight = FontWeight.Bold, color = PompColors.Ink)
        }
        Spacer(Modifier.height(7.dp))
        Text(title, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = PompColors.Ink)
        Text(stringResource(R.string.profile_accuracy_count, data.total),
            fontSize = 11.sp, color = PompColors.InkSecondary)
    }
}

@Composable
internal fun ProfileProCta(onClick: () -> Unit) {
    Surface(
        color = PompColors.GoldSoft,
        shape = RoundedCornerShape(12.dp),
        border = BorderStroke(1.dp, PompColors.Gold.copy(alpha = 0.25f)),
        modifier = Modifier.fillMaxWidth().heightIn(min = 44.dp).clickable(onClick = onClick),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 9.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("♛", fontSize = 23.sp, color = PompColors.Gold)
            Spacer(Modifier.width(11.dp))
            Text(stringResource(R.string.profile_buy_pro), fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold, color = PompColors.Ink, modifier = Modifier.weight(1f))
            Icon(Icons.Filled.ChevronRight, contentDescription = null,
                tint = PompColors.Gold, modifier = Modifier.size(19.dp))
        }
    }
}
