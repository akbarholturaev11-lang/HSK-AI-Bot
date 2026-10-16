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
    sourceKey: String,
    limit: LimitGate,
    onClose: () -> Unit,
    modifier: Modifier = Modifier,
    reason: String? = null,
    resetAt: String? = null,
) {
    val reopensAt = ResetTime.localClock(resetAt)
    val error = limit.state.error
    val checkLabel = stringResource(R.string.limit_check_account)
    LimitBlock(
        sectionTitle = sectionTitle,
        headline = if (reopensAt != null) {
            stringResource(R.string.limit_daily_headline, reopensAt)
        } else {
            stringResource(R.string.limit_locked_headline)
        },
        primaryLabel = checkLabel,
        onPrimary = limit.actions.onRecheck,
        modifier = modifier,
        reason = reason,
        isBusy = limit.state.isBusy,
        errorText = when {
            error != null -> stringResource(error.messageRes)
            else -> null
        },
    )
}
