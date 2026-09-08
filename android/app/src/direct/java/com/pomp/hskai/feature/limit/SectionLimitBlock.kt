package com.pomp.hskai.feature.limit

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import com.pomp.hskai.R

/**
 * The limit block as this distribution channel is allowed to present it.
 *
 * Screens call this and never build the card themselves, so the wording and
 * the buttons can differ per channel without any screen knowing which build
 * it is running in.
 *
 * The second button used to be "watch an ad to continue". An ad no longer
 * opens anything — hitting a limit shows the paywall, not a video — so that
 * slot now carries the 7-day free Pro trial, exactly as it does on the Mini
 * App's own paywall. It appears only while the server still says this account
 * may take it.
 *
 * @param resetAt server instant when the daily limit reopens, or null when
 *   nothing reopens (a subscription-only section). This channel offers a
 *   subscription instead of a wait, so it does not show the hour.
 */
@Composable
fun SectionLimitBlock(
    sectionTitle: String,
    limit: LimitGate,
    modifier: Modifier = Modifier,
    reason: String? = null,
    resetAt: String? = null,
) {
    val error = limit.state.error
    val trialOffered = limit.state.trialEligible
    LimitBlock(
        sectionTitle = sectionTitle,
        headline = stringResource(R.string.limit_unlock_headline),
        // The subscription leads: it is the answer that lasts. The trial is
        // the quieter alternative under it, not a competing shout.
        primaryLabel = stringResource(R.string.limit_unlock_button),
        onPrimary = limit.actions.onUnlock,
        modifier = modifier,
        reason = reason,
        hint = stringResource(R.string.limit_unlock_hint),
        secondaryLabel = if (trialOffered) {
            stringResource(R.string.limit_try_trial)
        } else {
            null
        },
        onSecondary = if (trialOffered) limit.actions.onStartTrial else null,
        isBusy = limit.state.isBusy || limit.state.trialStarting,
        errorText = when {
            error != null -> stringResource(error.messageRes)
            limit.state.trialError.isNotBlank() -> stringResource(R.string.limit_trial_failed)
            else -> null
        },
        noticeText = if (limit.state.recheckFoundNothing) {
            stringResource(R.string.limit_recheck_none)
        } else {
            null
        },
    )
}
