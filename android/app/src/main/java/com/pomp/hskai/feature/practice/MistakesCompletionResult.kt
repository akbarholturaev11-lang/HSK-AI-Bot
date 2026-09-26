package com.pomp.hskai.feature.practice

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.data.api.MistakeReviewCompleteResponse

/**
 * Exact two-argument result surface used by PracticeScreen.
 *
 * MistakesScreen keeps its three-argument variant for callers that need a
 * custom Modifier. This overload makes the normal completion path use the
 * shared panda/gamification hero without disturbing the review flow itself.
 */
@Composable
internal fun MistakesReviewResult(
    result: MistakeReviewCompleteResponse,
    onDone: () -> Unit,
) {
    val outcome = result.toCompletionOutcome()

    // Same order as the lesson and the practice shell: the result, then the
    // flame when this round actually moved the streak.
    var streakStep by rememberSaveable(result.score, result.total, result.remaining) {
        mutableStateOf(false)
    }
    if (streakStep) {
        PracticeStreakStep(outcome = outcome, onDone = onDone)
        return
    }
    val advance: () -> Unit = {
        if (outcome.hasStreakEvent) streakStep = true else onDone()
    }

    PracticeCompletionClip(outcome = outcome) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(PompColors.Paper),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .padding(horizontal = 24.dp, vertical = 32.dp),
            ) {
                PracticeCompletionHero(outcome = outcome)
                Text(
                    text = stringResource(R.string.mistakes_result_score_label),
                    fontSize = 13.sp,
                    color = PompColors.InkSecondary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 4.dp),
                )
                Text(
                    text = if (result.remaining > 0) {
                        "${stringResource(R.string.mistakes_result_remaining)}: ${result.remaining}"
                    } else {
                        stringResource(R.string.mistakes_result_all)
                    },
                    fontSize = 14.sp,
                    color = PompColors.InkSecondary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 10.dp),
                )
            }

            Button(
                onClick = advance,
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = PompColors.Cinnabar,
                    contentColor = PompColors.Paper,
                ),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(start = 16.dp, end = 16.dp, top = 10.dp, bottom = 16.dp)
                    .heightIn(min = 54.dp),
            ) {
                Icon(Icons.Filled.Check, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text(
                    // One more screen follows when the streak moved, so the button
                    // says so rather than promising to close.
                    text = if (outcome.hasStreakEvent) {
                        stringResource(R.string.lesson_next)
                    } else {
                        stringResource(R.string.mistakes_done)
                    },
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Medium,
                )
            }
        }
    }
}
