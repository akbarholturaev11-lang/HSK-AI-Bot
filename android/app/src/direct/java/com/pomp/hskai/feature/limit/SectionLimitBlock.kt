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
    onWatchAd: (() -> Unit)? = null,
) {
    val error = limit.state.error
    // An ad opens the section now and costs nothing, so it leads when it is
    // available; the subscription becomes the second, unlimited option.
    val unlockLabel = stringResource(R.string.limit_unlock_button)
    LimitBlock(
        sectionTitle = sectionTitle,
        headline = stringResource(R.string.limit_unlock_headline),
        primaryLabel = if (onWatchAd != null) {
            stringResource(R.string.limit_watch_ad)
        } else {
            unlockLabel
        },
        onPrimary = onWatchAd ?: limit.actions.onUnlock,
        modifier = modifier,
        reason = reason,
        hint = stringResource(R.string.limit_unlock_hint),
        secondaryLabel = if (onWatchAd != null) unlockLabel else null,
        onSecondary = if (onWatchAd != null) limit.actions.onUnlock else null,
        isBusy = limit.state.isBusy,
        errorText = if (error != null) stringResource(error.messageRes) else null,
    )
}
