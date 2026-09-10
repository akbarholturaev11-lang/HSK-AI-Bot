package com.pomp.hskai.feature.profile

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
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
import androidx.compose.material.icons.filled.AcUnit
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material.icons.filled.LocalFireDepartment
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringArrayResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.domain.model.CourseProgress

@Composable
internal fun StreakCalendar(progress: CourseProgress?, dailyXp: Int) {
    val days = stringArrayResource(R.array.profile_week_days)
    val meta = weekCalendarMeta(progress)
    val streak = progress?.streak ?: 0
    val end = if (dailyXp > 0) meta.todayIndex else meta.todayIndex - 1

    Column {
        SectionHeader(
            title = stringResource(R.string.profile_calendar_title),
            trailing = "$streak ${stringResource(R.string.profile_streak)}",
        )
        Surface(
            color = PompColors.PaperRaised,
            shape = RoundedCornerShape(16.dp),
            border = BorderStroke(1.dp, PompColors.Divider),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(
                modifier = Modifier.padding(14.dp),
                verticalArrangement = Arrangement.spacedBy(5.dp),
            ) {
                Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                    days.forEach { label ->
                        Text(
                            text = label,
                            style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp),
                            color = PompColors.InkDisabled,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.weight(1f),
                        )
                    }
                }
                Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                    for (index in 0 until 7) {
                        val studied = if (meta.fromServer) {
                            meta.activeDates.contains(meta.dates.getOrNull(index))
                        } else {
                            index <= end && (end - index) < streak
                        }
                        val missed = !studied && index < meta.todayIndex
                        DayCell(
                            studied = studied,
                            missed = missed,
                            isToday = index == meta.todayIndex,
                            modifier = Modifier.weight(1f),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun DayCell(
    studied: Boolean,
    missed: Boolean,
    isToday: Boolean,
    modifier: Modifier = Modifier,
) {
    val iceFill = if (PompColors.IsDark) PompColors.BlueSoft else Color(0xFFE9F4FA)
    val iceBorder = if (PompColors.IsDark) PompColors.Divider else Color(0xFFD2E6F0)
    val iceInk = if (PompColors.IsDark) PompColors.TileBlueInk else Color(0xFF78AAC6)
    val fill = when {
        studied -> PompColors.Cinnabar
        missed -> iceFill
        else -> PompColors.Paper
    }
    val border = when {
        isToday -> PompColors.Gold
        studied -> PompColors.Cinnabar
        missed -> iceBorder
        else -> PompColors.Divider
    }
    Surface(
        color = fill,
        shape = RoundedCornerShape(8.dp),
        border = BorderStroke(if (isToday) 2.dp else 1.dp, border),
        modifier = modifier.height(30.dp),
    ) {
        Box(contentAlignment = Alignment.Center) {
            when {
                studied -> Icon(
                    imageVector = Icons.Filled.LocalFireDepartment,
                    contentDescription = null,
                    tint = PompColors.Paper,
                    modifier = Modifier.size(13.dp),
                )
                missed -> Icon(
                    imageVector = Icons.Filled.AcUnit,
                    contentDescription = null,
                    tint = iceInk,
                    modifier = Modifier.size(12.dp),
                )
            }
        }
    }
}

@Composable
internal fun Achievements(completedLessons: Int, streak: Int) {
    Column {
        SectionHeader(title = stringResource(R.string.profile_achievements))
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            AchievementRow(
                icon = Icons.Filled.Check,
                tint = PompColors.Jade,
                tintSoft = PompColors.JadeSoft,
                title = stringResource(R.string.profile_ach_first),
                detail = if (completedLessons >= 1) stringResource(R.string.profile_ach_first_done) else "0 / 1",
                fraction = if (completedLessons >= 1) 1f else 0f,
                barColor = PompColors.Jade,
            )
            AchievementRow(
                icon = Icons.Filled.MenuBook,
                tint = PompColors.Cinnabar,
                tintSoft = PompColors.CinnabarSoft,
                title = stringResource(R.string.profile_ach_lessons),
                detail = "$completedLessons / 100",
                fraction = (completedLessons / 100f).coerceIn(0f, 1f),
                barColor = PompColors.Cinnabar,
            )
            AchievementRow(
                icon = Icons.Filled.LocalFireDepartment,
                tint = PompColors.Gold,
                tintSoft = PompColors.GoldSoft,
                title = stringResource(R.string.profile_ach_streak),
                detail = "$streak / 30",
                fraction = (streak / 30f).coerceIn(0f, 1f),
                barColor = PompColors.Cinnabar,
            )
        }
    }
}

@Composable
private fun AchievementRow(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    tint: Color,
    tintSoft: Color,
    title: String,
    detail: String,
    fraction: Float,
    barColor: Color,
) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Surface(
                color = tintSoft,
                shape = RoundedCornerShape(11.dp),
                modifier = Modifier.size(38.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = icon,
                        contentDescription = null,
                        tint = tint,
                        modifier = Modifier.size(18.dp),
                    )
                }
            }
            Column(modifier = Modifier.weight(1f)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text(
                        text = title,
                        style = MaterialTheme.typography.bodyMedium.copy(fontSize = 14.sp),
                        fontWeight = FontWeight.Medium,
                        color = PompColors.Ink,
                    )
                    Text(
                        text = detail,
                        style = MaterialTheme.typography.bodyMedium.copy(fontSize = 14.sp),
                        color = PompColors.InkSecondary,
                    )
                }
                Spacer(Modifier.height(7.dp))
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(7.dp)
                        .clip(RoundedCornerShape(5.dp))
                        .background(PompColors.Divider),
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth(fraction)
                            .height(7.dp)
                            .clip(RoundedCornerShape(5.dp))
                            .background(barColor),
                    )
                }
            }
        }
    }
}

@Composable
private fun SectionHeader(title: String, trailing: String? = null) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 8.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp),
            fontWeight = FontWeight.SemiBold,
            color = PompColors.InkSecondary,
        )
        if (trailing != null) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Filled.LocalFireDepartment,
                    contentDescription = null,
                    tint = PompColors.Cinnabar,
                    modifier = Modifier.size(12.dp),
                )
                Spacer(Modifier.width(4.dp))
                Text(
                    text = trailing,
                    style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp),
                    color = PompColors.Cinnabar,
                )
            }
        }
    }
}

private data class WeekMeta(
    val dates: List<String>,
    val activeDates: Set<String>,
    val todayIndex: Int,
    val fromServer: Boolean,
)

private fun weekCalendarMeta(progress: CourseProgress?): WeekMeta {
    val local = progress?.localDate?.takeIf { isIsoDay(it) }
    val start = progress?.weekStart?.takeIf { isIsoDay(it) }
    val dates = if (start != null) (0 until 7).map { shiftIsoDay(start, it) } else emptyList()
    val active = progress?.weekActivityDates.orEmpty().filter { isIsoDay(it) }.toSet()
    val todayIndex = dates.indexOf(local).coerceAtLeast(0)
    return WeekMeta(
        dates = dates,
        activeDates = active,
        todayIndex = todayIndex,
        fromServer = start != null && progress?.weekActivityDates != null,
    )
}

private fun isIsoDay(value: String): Boolean =
    value.length == 10 && value[4] == '-' && value[7] == '-' &&
        value.filterIndexed { index, _ -> index != 4 && index != 7 }.all { it.isDigit() }

private fun shiftIsoDay(day: String, days: Int): String =
    runCatching { java.time.LocalDate.parse(day).plusDays(days.toLong()).toString() }
        .getOrDefault(day)
