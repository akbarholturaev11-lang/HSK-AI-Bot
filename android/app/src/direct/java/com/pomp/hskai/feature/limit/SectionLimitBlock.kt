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
 * When the server allows a trial, show exactly two choices: a free
 * 7-day trial and the Pro subscription. Closing stays in the overlay's X.
 * After trial eligibility ends, offer Pro only.
 *
 * @param resetAt server instant when the daily limit reopens, or null when
 *   nothing reopens (a subscription-only section). This channel offers a
 *   subscription instead of a wait, so it does not show the hour.
 */
@Composable
fun SectionLimitBlock(
    sectionTitle: String,
    sourceKey: String,
    limit: LimitGate,
    onClose: () -> Unit,
    modifier: Modifier = Modifier,
    reason: String? = null,
    resetAt: String? = null,
) {
    val error = limit.state.error
    val trialOffered = limit.state.trialEligible
    val openSubscription: () -> Unit = { limit.actions.onUnlock(sourceKey) }
    LimitBlock(
        sectionTitle = sectionTitle,
        headline = stringResource(R.string.limit_unlock_headline),
        // Server-eligible trial first; Pro second. Dismiss remains on the X.
        primaryLabel = if (trialOffered) stringResource(R.string.limit_try_trial)
            else stringResource(R.string.limit_unlock_button),
        onPrimary = if (trialOffered) limit.actions.onStartTrial else openSubscription,
        modifier = modifier,
        reason = reason,
        hint = stringResource(R.string.limit_unlock_hint),
        secondaryLabel = if (trialOffered) stringResource(R.string.limit_unlock_button) else null,
        onSecondary = if (trialOffered) openSubscription else null,
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
