package com.pomp.hskai.feature.onboarding

import android.animation.ValueAnimator
import android.os.Build
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.MenuBook
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
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
    guestEntry: Boolean = false,
) {
    val intro = state.step == 8
    BackHandler(enabled = !state.submitting && !profile.trialStarting) {
        if (intro) onFinish() else onBack()
    }
    val configuration = LocalConfiguration.current
    val context = LocalContext.current
    val language = configuration.locales[0].language
    val copy = remember(context, language) {
        OnboardingCopy.forLanguage(language).withBundledCatalog(context, language)
    }
    val motionEnabled = Build.VERSION.SDK_INT < 26 || ValueAnimator.areAnimatorsEnabled()
    HskSceneSurface(modifier.fillMaxSize()) {
        BoxWithConstraints(Modifier.fillMaxSize().safeDrawingPadding(), contentAlignment = Alignment.TopCenter) {
            val compactHeight = maxHeight <= 700.dp
            val layout = OnboardingLayoutSpec.resolve(maxWidth.value.toInt(), maxHeight.value.toInt()).let {
                it.copy(
                    guidePandaWidth = if (it.compactWidth) 68 else 84,
                    guidePandaHeight = if (it.compactWidth) 78 else 94,
                    guideTopPadding = if (compactHeight) 8 else 14,
                    guideBottomPadding = if (compactHeight) 8 else 16,
                )
            }
            val optionHeight = if (compactHeight) 56.dp else 68.dp
            Column(Modifier.widthIn(max = 520.dp).fillMaxSize()) {
                if (!intro) {
                    OnboardingTopBar(state.step, stringResource(R.string.li_copy_back), onBack,
                        state.submitting, motionEnabled, layout,
                        totalSteps = 5, showStepCount = false, showProgress = state.step <= 5)
                }
                Box(Modifier.weight(1f).fillMaxWidth()) {
                    // PWA question layout: small Li beside the speech bubble, then choices.
                    // Each question owns its scroll position; the opaque footer never overlaps it.
                    key(state.step) {
                        if (state.step in 3..6) {
                            ChoiceStep(
                                question = stringResource(liQuestion(state)),
                                helper = when (state.step) {
                                    3 -> copy.goalHint + " " + stringResource(R.string.li_copy_multihint)
                                    4 -> stringResource(R.string.li_copy_timesub)
                                    5 -> stringResource(R.string.li_copy_focussub)
                                    else -> null
                                },
                                reactionKey = liQuestion(state), motionEnabled = motionEnabled, layoutSpec = layout,
                                liGuide = true,
                            ) {
                                Column(verticalArrangement = Arrangement.spacedBy(if (compactHeight) 8.dp else 10.dp)) {
                                    when (state.step) {
                                        3 -> listOf(
                                            LiGoal("hsk_exam", R.string.li_goals_hsk_exam_hd, R.string.li_goals_hsk_exam_s, OnboardingIconKind.HskExam),
                                            LiGoal("daily_communication", R.string.li_goals_daily_communication_hd, R.string.li_goals_daily_communication_s, OnboardingIconKind.DailyCommunication),
                                            LiGoal("travel", R.string.li_goals_travel_hd, R.string.li_goals_travel_s, OnboardingIconKind.Travel),
                                            LiGoal("work_china", R.string.li_goals_work_china_hd, R.string.li_goals_work_china_s, OnboardingIconKind.WorkChina),
                                            LiGoal("study_china", R.string.li_goals_study_china_hd, R.string.li_goals_study_china_s, OnboardingIconKind.StudyChina),
                                        ).forEach { goal ->
                                            ChoiceCard(selected = goal.key in state.selectedGoals, enabled = !state.submitting,
                                                motionEnabled = motionEnabled, layoutSpec = layout,
                                                title = stringResource(goal.title), subtitle = stringResource(goal.subtitle),
                                                leading = { MiniAppOnboardingIcon(goal.icon, PompColors.CinnabarDark) },
                                                onClick = { onGoal(goal.key) })
                                        }
                                        4 -> listOf(5, 10, 15, 20, 30).forEach { value ->
                                            LiChoice("$value ${stringResource(R.string.li_copy_min)}", value == state.dailyMinutes,
                                                state.submitting, layout, motionEnabled, optionHeight, Icons.Outlined.Schedule) { onMinutes(value) }
                                        }
                                        5 -> listOf(
                                            Triple("speaking", R.string.li_focus_speaking_hd, Icons.Outlined.Mic),
                                            Triple("listening", R.string.li_focus_listening_hd, Icons.Outlined.Hearing),
                                            Triple("vocabulary", R.string.li_focus_vocabulary_hd, Icons.AutoMirrored.Outlined.MenuBook),
                                            Triple("grammar", R.string.li_focus_grammar_hd, Icons.Outlined.EditNote),
                                            Triple("none", R.string.li_focus_none_hd, Icons.Outlined.AutoAwesome),
                                        ).forEach { (value, label, icon) ->
                                            LiChoice(stringResource(label), value == state.preferredFocus, state.submitting,
                                                layout, motionEnabled, optionHeight, icon) { onFocus(value) }
                                        }
                                        6 -> listOf(7, 14, 30, 50).forEach { value ->
                                            LiChoice("$value ${stringResource(R.string.li_copy_days)}", value == state.streakTargetDays,
                                                state.submitting, layout, motionEnabled, optionHeight, Icons.Outlined.LocalFireDepartment) { onStreak(value) }
                                        }
                                    }
                                }
                            }
                        } else {
                            Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp),
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.spacedBy(16.dp)) {
                                OnboardingPandaMascot(modifier = Modifier.size(120.dp, 132.dp), motionEnabled = motionEnabled)
                                Text(stringResource(if (!intro) {
                                    if (guestEntry) R.string.li_copy_profile else R.string.li_copy_ready
                                } else when {
                                    profile.trial?.active == true -> R.string.li_copy_trialon
                                    profile.trial?.eligible == true -> R.string.li_copy_protitle
                                    else -> R.string.li_copy_ready
                                }), style = MaterialTheme.typography.headlineSmall, textAlign = TextAlign.Center)
                                if (!intro) {
                                    Text("${state.dailyMinutes} ${stringResource(R.string.li_copy_min)}")
                                    Text("${state.streakTargetDays} ${stringResource(R.string.li_copy_days)}")
                                } else when {
                                    profile.trialLoading -> HskContentSkeleton(rows = 2)
                                    profile.trial?.active == true -> Text(stringResource(R.string.li_copy_nocharge))
                                    profile.trial?.eligible == true -> {
                                        Text(stringResource(R.string.li_copy_probody))
                                        Text(stringResource(when (state.selectedGoal) {
                                            "travel" -> R.string.li_progoal_travel_subtitle
                                            "study_china" -> R.string.li_progoal_study_china_subtitle
                                            "work_china" -> R.string.li_progoal_work_china_subtitle
                                            "daily_communication" -> R.string.li_progoal_daily_communication_subtitle
                                            else -> R.string.li_progoal_hsk_exam_subtitle
                                        }))
                                        listOf(R.string.li_copy_t1 to R.string.li_copy_t1s,
                                            R.string.li_copy_t2 to R.string.li_copy_t2s,
                                            R.string.li_copy_t3 to R.string.li_copy_t3s).forEach { (title, body) ->
                                            ListItem(headlineContent = { Text(stringResource(title)) },
                                                supportingContent = { Text(stringResource(body)) })
                                        }
                                    }
                                    profile.trialStatusError != null -> TextButton(onClick = onRetryTrial) {
                                        Text(stringResource(R.string.hsk_course_lesson_flow_retry))
                                    }
                                }
                                if (profile.trialError.isNotEmpty()) {
                                    Text(stringResource(R.string.hsk_course_onboarding_save_error), color = MaterialTheme.colorScheme.error)
                                }
                            }
                        }
                    }
                }
                if (intro) {
                    Surface(color = PompColors.Paper) {
                        Column(Modifier.fillMaxWidth().padding(horizontal = layout.footerHorizontalPadding.dp,
                            vertical = layout.footerBottomPadding.dp)) {
                            if (profile.trial?.eligible == true && !profile.trialLoading) {
                                Button(onClick = onTrial, enabled = !profile.trialStarting, modifier = Modifier.fillMaxWidth().heightIn(min = 54.dp)) {
                                    Text(stringResource(R.string.li_copy_procta))
                                }
                            }
                            TextButton(onClick = onFinish, enabled = !profile.trialStarting, modifier = Modifier.fillMaxWidth()) {
                                Text(stringResource(if (profile.trial?.active == true) R.string.li_copy_cont else if (profile.trial?.eligible == true) R.string.li_copy_later else R.string.li_copy_first))
                            }
                        }
                    }
                } else {
                    OnboardingFooter(copy, state, onNext, motionEnabled, layout,
                        labelOverride = stringResource(when {
                            state.step != 7 -> R.string.li_copy_cont
                            guestEntry -> R.string.li_copy_signuptitle
                            else -> R.string.li_copy_first
                        }))
                }
            }
        }
    }
}

private data class LiGoal(val key: String, val title: Int, val subtitle: Int, val icon: OnboardingIconKind)

private fun liQuestion(state: OnboardingUiState): Int = when (state.step) {
    3 -> when (state.selectedGoals.lastOrNull()) {
        "hsk_exam" -> R.string.li_goals_hsk_exam_say
        "daily_communication" -> R.string.li_goals_daily_communication_say
        "travel" -> R.string.li_goals_travel_say
        "work_china" -> R.string.li_goals_work_china_say
        "study_china" -> R.string.li_goals_study_china_say
        else -> R.string.hsk_course_onboarding_ask_goal
    }
    4 -> when (state.dailyMinutes) {
        5 -> R.string.li_times_5_say
        10 -> R.string.li_times_10_say
        15 -> R.string.li_times_15_say
        20 -> R.string.li_times_20_say
        30 -> R.string.li_times_30_say
        else -> R.string.li_copy_timeq
    }
    5 -> when (state.preferredFocus) {
        "speaking" -> R.string.li_focus_speaking_say
        "listening" -> R.string.li_focus_listening_say
        "vocabulary" -> R.string.li_focus_vocabulary_say
        "grammar" -> R.string.li_focus_grammar_say
        "none" -> R.string.li_focus_none_say
        else -> R.string.li_copy_focusq
    }
    else -> R.string.li_copy_streakq
}

@Composable
private fun LiChoice(label: String, selected: Boolean, busy: Boolean, layout: OnboardingLayoutSpec,
    motionEnabled: Boolean, height: Dp, icon: ImageVector, onClick: () -> Unit) {
    ChoiceCard(selected = selected, enabled = !busy, motionEnabled = motionEnabled, layoutSpec = layout,
        title = label, subtitle = "",
        leading = { Icon(icon, null, tint = if (selected) PompColors.CinnabarDark else PompColors.InkSecondary) },
        onClick = onClick, minHeight = height)
}
