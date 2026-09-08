package com.pomp.hskai.feature.limit

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import com.pomp.hskai.R
import com.pomp.hskai.core.text.ResetTime

/**
 * The limit block as the Google Play build is allowed to present it.
 *
 * It states what happened and when the allowance returns, and offers what
 * this channel may offer: the 7-day free Pro trial while the account still
 * has one, re-reading the account status from the server, and support. There
 * is no checkout here and no way out of the app to one.
 *
 * The trial is not a purchase — nothing is paid, inside the app or outside —
 * so the store rule that removes the subscription button does not remove
 * this one. That is also why the two builds can finally say the same thing
 * in this slot, where before one offered an ad and the other a re-check.
 *
 * @param resetAt server instant when the daily limit reopens, or null when
 *   nothing reopens. When it is null no hour is shown at all: promising a
 *   time that never comes is worse than saying only that the section is shut.
 */
@Composable
fun SectionLimitBlock(
    sectionTitle: String,
    limit: LimitGate,
    modifier: Modifier = Modifier,
    reason: String? = null,
    resetAt: String? = null,
) {
    val reopensAt = ResetTime.localClock(resetAt)
    val hasSupport = limit.state.supportUrl.isNotBlank()
    val error = limit.state.error
    val trialOffered = limit.state.trialEligible
    val checkLabel = stringResource(R.string.limit_check_account)
    LimitBlock(
        sectionTitle = sectionTitle,
        headline = if (reopensAt != null) {
            stringResource(R.string.limit_daily_headline, reopensAt)
        } else {
            stringResource(R.string.limit_locked_headline)
        },
        // A free week opens the section now and costs the learner nothing, so
        // it leads while it is available; re-checking the account then becomes
        // the quieter second option.
        primaryLabel = if (trialOffered) {
            stringResource(R.string.limit_try_trial)
        } else {
            checkLabel
        },
        onPrimary = if (trialOffered) {
            limit.actions.onStartTrial
        } else {
            limit.actions.onRecheck
        },
        modifier = modifier,
        reason = reason,
        hint = stringResource(R.string.limit_status_hint),
        secondaryLabel = if (trialOffered) checkLabel else null,
        onSecondary = if (trialOffered) limit.actions.onRecheck else null,
        tertiaryLabel = if (hasSupport) stringResource(R.string.limit_support) else null,
        onTertiary = if (hasSupport) limit.actions.onSupport else null,
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
