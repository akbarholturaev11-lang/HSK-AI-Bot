package com.pomp.hskai.feature.onboarding

import android.animation.ValueAnimator
import android.os.Build
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModelStoreOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskSceneSurface
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.feature.auth.LanguageSwitch
import com.pomp.hskai.data.api.AndroidOnboardingStatusDto
import com.pomp.hskai.data.repository.OnboardingRepository
import com.pomp.hskai.feature.profile.ProfileUiState

private enum class GuestEntry { CHOOSE, QUESTIONS, SIGNUP, LOGIN }

/** The provider content is the same native LinkScreen used outside Li. */
@Composable
internal fun LiGuestEntry(
    repository: OnboardingRepository,
    preview: AndroidOnboardingStatusDto,
    initialDraft: GuestLiDraft?,
    owner: ViewModelStoreOwner,
    language: AppLanguage,
    onLanguageSelected: (AppLanguage) -> Unit,
    saveDraft: suspend (GuestLiDraft) -> Unit,
    provider: @Composable (signup: Boolean, onBack: () -> Unit) -> Unit,
) {
    var entry by rememberSaveable { mutableStateOf(if (initialDraft == null) GuestEntry.CHOOSE else GuestEntry.SIGNUP) }
    when (entry) {
        GuestEntry.CHOOSE -> LiGuestStartScreen(language, onLanguageSelected,
            onFirstTime = { entry = GuestEntry.QUESTIONS },
            onExistingAccount = { entry = GuestEntry.LOGIN })
        GuestEntry.LOGIN -> provider(false) { entry = GuestEntry.CHOOSE }
        GuestEntry.SIGNUP -> provider(true) { entry = GuestEntry.QUESTIONS }
        GuestEntry.QUESTIONS -> {
            val model: OnboardingViewModel = viewModel(
                viewModelStoreOwner = owner,
                key = "guest-li",
                factory = OnboardingViewModel.Factory(
                    repository, language.backendCode, preview, initialDraft,
                    onGuestReady = { draft -> saveDraft(draft); entry = GuestEntry.SIGNUP },
                ),
            )
            val flow by model.state.collectAsStateWithLifecycle()
            if (flow.ui.step >= 3) {
                LiOnboardingChoices(
                    state = flow.ui, profile = ProfileUiState(), onGoal = model::selectGoal,
                    onMinutes = model::selectDailyMinutes, onFocus = model::selectFocus, onStreak = model::selectStreak,
                    onBack = model::back, onNext = model::next, onFinish = {}, onTrial = {},
                    onRetryTrial = {}, guestEntry = true,
                )
            } else {
                OnboardingScreen(
                    language = language.backendCode, state = flow.ui,
                    onTrackSelected = model::selectTrack, onLevelSelected = model::selectLevel,
                    onGoalSelected = model::selectGoal, onNext = model::next, guestEntry = true,
                    onBack = { if (flow.ui.step == 0) entry = GuestEntry.CHOOSE else model.back() },
                )
            }
        }
    }
}

@Composable
internal fun LiGuestStartScreen(
    language: AppLanguage,
    onLanguageSelected: (AppLanguage) -> Unit,
    onFirstTime: () -> Unit,
    onExistingAccount: () -> Unit,
) {
    val motion = Build.VERSION.SDK_INT < 26 || ValueAnimator.areAnimatorsEnabled()
    HskSceneSurface(Modifier.fillMaxSize()) {
        BoxWithConstraints(Modifier.fillMaxSize().safeDrawingPadding(), contentAlignment = Alignment.TopCenter) {
            val horizontal = if (maxWidth <= 360.dp) 16.dp else 24.dp
            val pandaHeight = if (maxHeight <= 700.dp) 132.dp else 164.dp
            val buttonShape = RoundedCornerShape(13.dp)
            Column(Modifier.widthIn(max = 520.dp).fillMaxSize().padding(horizontal = horizontal)) {
                Row(Modifier.fillMaxWidth().padding(top = 14.dp), horizontalArrangement = Arrangement.End) {
                    LanguageSwitch(language, onLanguageSelected)
                }
                Column(
                    Modifier.weight(1f).fillMaxWidth().verticalScroll(rememberScrollState()).padding(vertical = 16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                ) {
                    SpeechBubble(stringResource(R.string.li_copy_accounttitle), centeredTail = true, large = true)
                    Spacer(Modifier.height(22.dp))
                    OnboardingPandaMascot(happy = false, motionEnabled = motion, modifier = Modifier.size(150.dp, pandaHeight))
                }
                Column(Modifier.fillMaxWidth().padding(bottom = 18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Button(
                        onClick = onFirstTime, modifier = Modifier.fillMaxWidth().heightIn(min = 54.dp), shape = buttonShape,
                        colors = ButtonDefaults.buttonColors(containerColor = PompColors.Cinnabar, contentColor = PompColors.OnCinnabar),
                    ) { Text(stringResource(R.string.li_copy_firsttime)) }
                    OutlinedButton(
                        onClick = onExistingAccount, modifier = Modifier.fillMaxWidth().heightIn(min = 54.dp), shape = buttonShape,
                        colors = ButtonDefaults.outlinedButtonColors(containerColor = PompColors.PaperRaised, contentColor = PompColors.Ink),
                        border = BorderStroke(1.dp, PompColors.Divider),
                    ) { Text(stringResource(R.string.li_copy_haveaccount)) }
                }
            }
        }
    }
}
