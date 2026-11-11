package com.pomp.hskai.feature.onboarding

import android.animation.ValueAnimator
import android.os.Build
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.components.HskSceneSurface
import com.pomp.hskai.core.design.components.HskContentSkeleton
import com.pomp.hskai.feature.profile.ProfileUiState

/** Authenticated native adaptation. Web signup/install/demo quiz scenes have no native role. */
@Composable
fun LiOnboardingChoices(
    state: OnboardingUiState,
    profile: ProfileUiState,
    onGoal: (String) -> Unit,
    onMinutes: (Int) -> Unit,
    onFocus: (String) -> Unit,
    onStreak: (Int) -> Unit,
    onBack: () -> Unit,
    onNext: () -> Unit,
    onFinish: () -> Unit,
    onTrial: () -> Unit,
    onRetryTrial: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val intro = state.step == 8
    BackHandler(enabled = !state.submitting && !profile.trialStarting) {
        if (intro) onFinish() else onBack()
    }
    val title = when (state.step) {
        3 -> R.string.hsk_course_onboarding_ask_goal
        4 -> R.string.li_copy_timeq
        5 -> R.string.li_copy_focusq
        6 -> R.string.li_copy_streakq
        7 -> R.string.li_copy_ready
        else -> when {
            profile.trial?.active == true -> R.string.li_copy_trialon
            profile.trial?.eligible == true -> R.string.li_copy_protitle
            else -> R.string.li_copy_ready
        }
    }
    HskSceneSurface(modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize().safeDrawingPadding().padding(24.dp)) {
            Column(Modifier.weight(1f).verticalScroll(rememberScrollState()),
                horizontalAlignment = Alignment.CenterHorizontally) {
                OnboardingPandaMascot(
                    modifier = Modifier.height(180.dp).fillMaxWidth(),
                    motionEnabled = Build.VERSION.SDK_INT < 26 || ValueAnimator.areAnimatorsEnabled(),
                )
                Text(stringResource(title), style = MaterialTheme.typography.headlineSmall,
                    textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(16.dp))
                when (state.step) {
                    3 -> {
                        Text(stringResource(R.string.li_copy_multihint))
                        listOf(
                            "hsk_exam" to R.string.li_goals_hsk_exam_hd,
                            "daily_communication" to R.string.li_goals_daily_communication_hd,
                            "travel" to R.string.li_goals_travel_hd,
                            "work_china" to R.string.li_goals_work_china_hd,
                            "study_china" to R.string.li_goals_study_china_hd,
                        ).forEach { (value, label) ->
                            LiChoice(stringResource(label), value in state.selectedGoals, state.submitting) { onGoal(value) }
                        }
                    }
                    4 -> {
                        Text(stringResource(R.string.li_copy_timesub))
                        listOf(5, 10, 15, 20, 30).forEach { value ->
                            LiChoice("$value ${stringResource(R.string.li_copy_min)}", value == state.dailyMinutes, state.submitting) { onMinutes(value) }
                        }
                    }
                    5 -> {
                        Text(stringResource(R.string.li_copy_focussub))
                        listOf(
                            "speaking" to R.string.li_focus_speaking_hd,
                            "listening" to R.string.li_focus_listening_hd,
                            "vocabulary" to R.string.li_focus_vocabulary_hd,
                            "grammar" to R.string.li_focus_grammar_hd,
                            "none" to R.string.li_focus_none_hd,
                        ).forEach { (value, label) ->
                            LiChoice(stringResource(label), value == state.preferredFocus, state.submitting) { onFocus(value) }
                        }
                    }
                    6 -> listOf(7, 14, 30, 50).forEach { value ->
                        LiChoice("$value ${stringResource(R.string.li_copy_days)}", value == state.streakTargetDays, state.submitting) { onStreak(value) }
                    }
                    7 -> {
                        Text("${state.dailyMinutes} ${stringResource(R.string.li_copy_min)}")
                        Text("${state.streakTargetDays} ${stringResource(R.string.li_copy_days)}")
                    }
                    8 -> when {
                        profile.trialLoading -> HskContentSkeleton(rows = 2)
                        profile.trial?.active == true -> Text(stringResource(R.string.li_copy_nocharge))
                        profile.trial?.eligible == true -> {
                            Text(stringResource(R.string.li_copy_probody))
                            val goalCopy = when (state.selectedGoal) {
                                "travel" -> R.string.li_progoal_travel_subtitle
                                "study_china" -> R.string.li_progoal_study_china_subtitle
                                "work_china" -> R.string.li_progoal_work_china_subtitle
                                "daily_communication" -> R.string.li_progoal_daily_communication_subtitle
                                else -> R.string.li_progoal_hsk_exam_subtitle
                            }
                            Text(stringResource(goalCopy))
                            listOf(R.string.li_copy_t1 to R.string.li_copy_t1s,
                                R.string.li_copy_t2 to R.string.li_copy_t2s,
                                R.string.li_copy_t3 to R.string.li_copy_t3s).forEach { (title, body) ->
                                ListItem(headlineContent = { Text(stringResource(title)) },
                                    supportingContent = { Text(stringResource(body)) })
                            }
                        }
                        profile.trialStatusError != null -> TextButton(onClick = onRetryTrial) { Text(stringResource(R.string.hsk_course_lesson_flow_retry)) }
                        else -> Text(stringResource(R.string.li_copy_ready))
                    }
                }
                if (state.error || profile.trialError.isNotEmpty()) {
                    Text(stringResource(R.string.hsk_course_onboarding_save_error), color = MaterialTheme.colorScheme.error)
                }
            }
            if (intro) {
                if (profile.trial?.eligible == true && !profile.trialLoading) {
                    Button(onClick = onTrial, enabled = !profile.trialStarting, modifier = Modifier.fillMaxWidth()) {
                        Text(stringResource(R.string.li_copy_procta))
                    }
                }
                TextButton(onClick = onFinish, enabled = !profile.trialStarting, modifier = Modifier.fillMaxWidth()) {
                    Text(stringResource(if (profile.trial?.active == true) R.string.li_copy_cont else if (profile.trial?.eligible == true) R.string.li_copy_later else R.string.li_copy_first))
                }
            } else {
                Button(onClick = onNext, enabled = !state.submitting, modifier = Modifier.fillMaxWidth()) {
                    Text(stringResource(if (state.submitting) R.string.hsk_course_onboarding_saving else if (state.step == 7) R.string.li_copy_first else R.string.li_copy_cont))
                }
                TextButton(onClick = onBack, enabled = !state.submitting, modifier = Modifier.fillMaxWidth()) {
                    Text(stringResource(R.string.li_copy_back))
                }
            }
        }
    }
}

@Composable
private fun LiChoice(label: String, selected: Boolean, busy: Boolean, onClick: () -> Unit) {
    FilterChip(selected = selected, onClick = onClick, enabled = !busy,
        label = { Text(label, modifier = Modifier.padding(vertical = 8.dp)) }, modifier = Modifier.fillMaxWidth())
}
