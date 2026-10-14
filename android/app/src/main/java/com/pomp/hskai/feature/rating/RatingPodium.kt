package com.pomp.hskai.feature.rating

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Group
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors

/**
 * Illustration, not a second scoring system.
 * The backend owns leagues (lifetime XP), leaderboard (weekly XP), and participants.
 * Only the centre pedestal shows the real global member count.
 */
@Composable
internal fun RatingPodium(league: String, memberCount: Int, resetSeconds: Long) {
    val currentIndex = LEAGUE_LADDER.indexOfFirst { it.first.equals(league, ignoreCase = true) }
        .takeIf { it >= 0 } ?: 1
    val leftIndex = if (currentIndex <= 1) currentIndex + 1 else currentIndex - 1
    val rightIndex = when (currentIndex) {
        0, 1 -> currentIndex + 2
        2 -> 3
        else -> 1
    }
    Column(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 1.dp),
            verticalAlignment = Alignment.Bottom,
            horizontalArrangement = Arrangement.spacedBy(0.dp),
        ) {
            CupWithPedestal(
                league = LEAGUE_LADDER[leftIndex].first,
                metal = CupMetal.SILVER,
                isCenter = false,
                count = null,
                modifier = Modifier.weight(1f),
            )
            CupWithPedestal(
                league = league,
                metal = CupMetal.GOLD,
                isCenter = true,
                count = memberCount,
                modifier = Modifier.weight(1.22f),
            )
            CupWithPedestal(
                league = LEAGUE_LADDER[rightIndex].first,
                metal = CupMetal.BRONZE,
                isCenter = false,
                count = null,
                modifier = Modifier.weight(1f),
            )
        }
        Row(
            modifier = Modifier.fillMaxWidth().padding(top = 10.dp, bottom = 2.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Filled.Group, contentDescription = null, tint = PompColors.InkSecondary, modifier = Modifier.size(14.dp))
            Spacer(Modifier.width(5.dp))
            Text(stringResource(R.string.rating_tab_league), color = PompColors.InkSecondary, fontSize = 12.sp)
            Spacer(Modifier.width(12.dp))
            Text("·", color = PompColors.InkDisabled, fontSize = 14.sp)
            Spacer(Modifier.width(12.dp))
            Icon(Icons.Filled.Schedule, contentDescription = null, tint = PompColors.InkSecondary, modifier = Modifier.size(15.dp))
            Spacer(Modifier.width(5.dp))
            Text(countdownText(resetSeconds), color = PompColors.InkSecondary, fontSize = 12.sp)
            Spacer(Modifier.width(4.dp))
            Text(stringResource(R.string.rating_time_left), color = PompColors.InkSecondary, fontSize = 12.sp)
        }
    }
}

/** Full Chinese tier names for the illustrated podium only; other badge labels stay unchanged. */
private fun podiumLeagueName(league: String): String = when (league.lowercase()) {
    "bronze" -> "玄武"
    "silver" -> "朱雀"
    "gold" -> "青龙"
    "sapphire" -> "凤凰"
    else -> leagueGlyph(league)
}

private enum class CupMetal(val light: Color, val medium: Color, val dark: Color, val gloss: Color) {
    GOLD(Color(0xFFFFF3AF), Color(0xFFFFC538), Color(0xFFAD6510), Color(0xFFFFE79D)),
    SILVER(Color(0xFFF8FBFF), Color(0xFFAFBECC), Color(0xFF5B7087), Color(0xFFE4EFF8)),
    BRONZE(Color(0xFFFFE3B5), Color(0xFFC37B38), Color(0xFF85441C), Color(0xFFF6BD7B)),
}

@Composable
private fun CupWithPedestal(
    league: String,
    metal: CupMetal,
    isCenter: Boolean,
    count: Int?,
    modifier: Modifier,
) {
    Column(modifier = modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            modifier = Modifier.fillMaxWidth().height(if (isCenter) 162.dp else 139.dp),
            contentAlignment = Alignment.Center,
        ) {
            TrophyIllustration(metal = metal, modifier = Modifier.fillMaxWidth().height(if (isCenter) 160.dp else 136.dp))
            if (isCenter) {
                Text(
                    "1",
                    fontSize = 26.sp,
                    color = metal.dark,
                    fontWeight = FontWeight.Black,
                    modifier = Modifier.padding(top = 2.dp),
                )
            }
        }
        val shape = RoundedCornerShape(topStart = 22.dp, topEnd = 22.dp, bottomStart = 12.dp, bottomEnd = 12.dp)
        val bg = if (isCenter) Brush.linearGradient(
            listOf(Color(0xFFFFFEF7), Color(0xFFF3DFAF))
        ) else Brush.linearGradient(listOf(Color(0xFFFFFDF8), Color(0xFFE9DECA)))
        Column(
            modifier = Modifier.fillMaxWidth()
                .height(if (isCenter) 98.dp else 78.dp)
                .background(bg, shape)
                .border(BorderStroke(1.dp, Color(0xFFE4D3B5)), shape)
                .padding(horizontal = 2.dp, vertical = 10.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Text(
                stringResource(R.string.rating_league_name, podiumLeagueName(league)),
                fontSize = if (isCenter) 14.sp else 11.sp,
                lineHeight = if (isCenter) 17.sp else 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = PompColors.Ink,
                textAlign = TextAlign.Center,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            if (count != null) {
                Spacer(Modifier.height(4.dp))
                Text(count.toString(), color = Color(0xFFA97618), fontWeight = FontWeight.Bold, fontSize = 25.sp)
            }
        }
    }
}

@Composable
private fun TrophyIllustration(metal: CupMetal, modifier: Modifier = Modifier) {
    Canvas(modifier) {
        val sx = size.width / 150f
        val sy = size.height / 160f
        withTransform({ scale(sx, sy, pivot = androidx.compose.ui.geometry.Offset.Zero) }) {
            val fill = Brush.horizontalGradient(
                colors = listOf(metal.dark, metal.light, metal.medium, metal.gloss, metal.dark),
                startX = 24f,
                endX = 122f,
            )
            val handleLeft = Path().apply {
                moveTo(36f, 44f); cubicTo(-4f, 24f, 6f, 94f, 37f, 84f)
            }
            val handleRight = Path().apply {
                moveTo(114f, 44f); cubicTo(154f, 24f, 144f, 94f, 113f, 84f)
            }
            drawPath(handleLeft, brush = fill, style = Stroke(width = 10f, cap = StrokeCap.Round))
            drawPath(handleRight, brush = fill, style = Stroke(width = 10f, cap = StrokeCap.Round))
            val bowl = Path().apply {
                moveTo(30f, 27f); lineTo(120f, 27f); lineTo(112f, 83f)
                cubicTo(106f, 105f, 90f, 114f, 75f, 114f)
                cubicTo(60f, 114f, 44f, 105f, 38f, 83f)
                close()
            }
            drawPath(bowl, brush = fill)
            drawOval(brush = fill, topLeft = androidx.compose.ui.geometry.Offset(30f, 20f),
                size = androidx.compose.ui.geometry.Size(90f, 15f))
            drawCircle(color = metal.gloss, radius = 25f, center = androidx.compose.ui.geometry.Offset(75f, 73f), style = Stroke(width = 3f))
            drawCircle(color = metal.dark.copy(alpha = 0.6f), radius = 20f, center = androidx.compose.ui.geometry.Offset(75f, 73f), style = Stroke(width = 1.5f))
            drawRect(brush = fill, topLeft = androidx.compose.ui.geometry.Offset(66f, 110f),
                size = androidx.compose.ui.geometry.Size(18f, 28f))
            drawOval(brush = fill, topLeft = androidx.compose.ui.geometry.Offset(48f, 131f),
                size = androidx.compose.ui.geometry.Size(54f, 12f))
            drawRoundRect(brush = fill, topLeft = androidx.compose.ui.geometry.Offset(37f, 140f),
                size = androidx.compose.ui.geometry.Size(76f, 12f), cornerRadius = androidx.compose.ui.geometry.CornerRadius(4f))
        }
    }
}
