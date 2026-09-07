package com.pomp.hskai.feature.limit

import com.pomp.hskai.core.network.ApiError

/**
 * What a limit block knows, whichever channel the app was installed from.
 *
 * The client never decides who is paid or how much is left: it renders what
 * the server said and offers the actions its channel is allowed to offer.
 */
data class LimitGateState(
    val isBusy: Boolean = false,
    val error: ApiError? = null,
    /**
     * Where the learner asks for help. Empty when no contact is configured —
     * the button is then hidden rather than dead.
     */
    val supportUrl: String = "",
    /**
     * A finished re-check that found nothing new.
     *
     * A subscription that arrived closes this block on its own, so a gate that
     * is still here after the read has an answer worth saying out loud: the
     * button did run, and the account has not changed.
     */
    val recheckFoundNothing: Boolean = false,
)

/**
 * The actions a limit block may trigger.
 *
 * Not every channel has every action: the Google Play build has no
 * subscription flow of its own, so it uses the status re-check and support
 * instead. Keeping all three here lets the screens stay identical in both
 * builds while each channel's block uses only what it is allowed to.
 */
data class LimitGateActions(
    /** Opens the subscription flow. Only the `direct` channel has one. */
    val onUnlock: () -> Unit = {},
    /** Re-reads access and limits from the server. Nothing is unlocked locally. */
    val onRecheck: () -> Unit = {},
    /** Opens the configured support contact. Never a payment page. */
    val onSupport: () -> Unit = {},
)

/** The pair a screen passes down to whatever limit block its channel builds. */
data class LimitGate(
    val state: LimitGateState = LimitGateState(),
    val actions: LimitGateActions = LimitGateActions(),
)
