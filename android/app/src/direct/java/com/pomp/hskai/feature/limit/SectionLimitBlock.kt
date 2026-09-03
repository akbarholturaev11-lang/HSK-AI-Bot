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
    LimitBlock(
        sectionTitle = sectionTitle,
        headline = stringResource(R.string.limit_unlock_headline),
        primaryLabel = stringResource(R.string.limit_unlock_button),
        onPrimary = limit.actions.onUnlock,
        modifier = modifier,
        reason = reason,
        hint = stringResource(R.string.limit_unlock_hint),
        isBusy = limit.state.isBusy,
        errorText = if (error != null) stringResource(error.messageRes) else null,
    )
}
