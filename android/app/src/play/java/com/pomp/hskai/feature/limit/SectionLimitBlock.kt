package com.pomp.hskai.feature.limit

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import com.pomp.hskai.R
import com.pomp.hskai.core.text.ResetTime

/**
 * The limit block as the Google Play build is allowed to present it.
 *
 * It states what happened and when the allowance returns, and offers two
 * things: re-read the account status from the server, and ask for help.
 * There is no checkout here and no way out of the app to one.
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
    LimitBlock(
        sectionTitle = sectionTitle,
        headline = if (reopensAt != null) {
            stringResource(R.string.limit_daily_headline, reopensAt)
        } else {
            stringResource(R.string.limit_locked_headline)
        },
        primaryLabel = stringResource(R.string.limit_check_account),
        onPrimary = limit.actions.onRecheck,
        modifier = modifier,
        reason = reason,
        hint = stringResource(R.string.limit_status_hint),
        secondaryLabel = if (hasSupport) stringResource(R.string.limit_support) else null,
        onSecondary = if (hasSupport) limit.actions.onSupport else null,
        isBusy = limit.state.isBusy,
        errorText = if (error != null) stringResource(error.messageRes) else null,
    )
}
