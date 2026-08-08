package com.pomp.hskai.feature.today

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.domain.model.CourseLesson
import com.pomp.hskai.domain.model.CourseMap
import com.pomp.hskai.domain.model.LessonAccess
import com.pomp.hskai.feature.course.CourseUiState

/**
 * The strongest screen in the app: one dominant next action, everything else
 * subordinate. No paywall is shown for a lesson that is merely out of reach.
 */
@Composable
fun TodayScreen(
    state: CourseUiState,
    onContinue: (CourseLesson) -> Unit,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val map = state.map
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        when {
            state.isLoading && map == null -> CenteredProgress()
            map == null -> ErrorBlock(
                messageRes = state.error?.messageRes ?: R.string.error_unknown,
                onRetry = onRetry,
            )

            else -> Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 20.dp, vertical = 24.dp),
            ) {
                StatusRow(map)
                if (state.isStale) {
                    Spacer(Modifier.height(12.dp))
                    StaleBanner()
                }
                Spacer(Modifier.height(20.dp))
                NextActionCard(map = map, onContinue = onContinue)
            }
        }
    }
}

@Composable
private fun CenteredProgress() {
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        CircularProgressIndicator(color = PompColors.Cinnabar)
    }
}

@Composable
private fun ErrorBlock(messageRes: Int, onRetry: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = stringResource(messageRes),
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(16.dp))
        OutlinedButton(
            onClick = onRetry,
            modifier = Modifier.heightIn(min = 48.dp),
            shape = RoundedCornerShape(14.dp),
        ) {
            Text(
                text = stringResource(R.string.action_retry),
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.CinnabarDark,
            )
        }
    }
}

@Composable
private fun StaleBanner() {
    Surface(
        color = PompColors.GoldSoft,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(
            text = stringResource(R.string.today_stale),
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.Ink,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
        )
    }
}

@Composable
private fun StatusRow(map: CourseMap) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        StatusItem(
            label = stringResource(R.string.today_level),
            value = map.level.uppercase(),
        )
        StatusItem(
            label = stringResource(R.string.today_streak),
            value = map.progress.streak.toString(),
        )
        StatusItem(
            label = stringResource(R.string.today_xp),
            value = map.progress.xp.toString(),
        )
    }
}

@Composable
private fun StatusItem(label: String, value: String) {
    Column(horizontalAlignment = Alignment.Start) {
        Text(
            text = value,
            style = MaterialTheme.typography.titleLarge,
            color = PompColors.Ink,
        )
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.InkSecondary,
        )
    }
}

@Composable
private fun NextActionCard(map: CourseMap, onContinue: (CourseLesson) -> Unit) {
    val lesson = map.currentLesson
    if (lesson == null) {
        Text(
            text = stringResource(R.string.today_all_done),
            style = MaterialTheme.typography.titleMedium,
            color = PompColors.Jade,
        )
        return
    }
    val unitTitle = map.unitOf(lesson)?.title.orEmpty()

    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(20.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Text(
                text = stringResource(R.string.today_next_lesson),
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.CinnabarDark,
            )
            Spacer(Modifier.height(8.dp))
            if (unitTitle.isNotBlank()) {
                Text(
                    text = unitTitle,
                    style = MaterialTheme.typography.titleLarge,
                    color = PompColors.Ink,
                )
            }
            if (lesson.hanziPreview.isNotBlank()) {
                Spacer(Modifier.height(8.dp))
                Text(
                    text = lesson.hanziPreview,
                    style = PompTextStyles.hanziMedium,
                    color = PompColors.Ink,
                )
                Text(
                    text = lesson.pinyinPreview,
                    style = PompTextStyles.pinyin,
                    color = PompColors.InkSecondary,
                )
            }
            Spacer(Modifier.height(12.dp))
            Text(
                text = stringResource(
                    R.string.today_part_of,
                    lesson.part,
                    lesson.partCount,
                ) + " · " + stringResource(R.string.today_estimated_minutes),
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.InkSecondary,
            )

            val reason = lesson.access.reasonRes()
            if (reason != null) {
                Spacer(Modifier.height(12.dp))
                Text(
                    text = stringResource(reason),
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                )
            }

            // A locked lesson has no CTA yet: the subscription flow is Phase J,
            // and a button that opens nothing is worse than no button.
            if (lesson.access == LessonAccess.Open ||
                lesson.access == LessonAccess.HalfPreview
            ) {
                Spacer(Modifier.height(18.dp))
                Button(
                    onClick = { onContinue(lesson) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 52.dp),
                    shape = RoundedCornerShape(14.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = PompColors.Cinnabar,
                        contentColor = PompColors.Paper,
                    ),
                ) {
                    Text(
                        text = stringResource(R.string.today_continue),
                        style = MaterialTheme.typography.labelLarge,
                    )
                }
            }
        }
    }
}

private fun LessonAccess.reasonRes(): Int? = when (this) {
    LessonAccess.Open -> null
    LessonAccess.HalfPreview -> R.string.today_reason_preview
    LessonAccess.PremiumLocked -> R.string.today_reason_premium
    LessonAccess.NotReached -> R.string.today_reason_not_reached
}
