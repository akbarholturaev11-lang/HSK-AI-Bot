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
    /**
     * Whether the server says this account may still take the 7-day Pro trial.
     *
     * The client never decides this. One Telegram account gets one trial and
     * only the server knows whether it has been taken, so this is read from
     * `trial/status` and nothing here counts anything locally.
     */
    val trialEligible: Boolean = false,
    /** A trial request in flight — the button must not be pressed twice. */
    val trialStarting: Boolean = false,
    /**
     * Why the server refused the trial, or empty.
     *
     * A silent "nothing happened" is the worst outcome of pressing a button,
     * so a refusal is shown rather than swallowed.
     */
    val trialError: String = "",
    /**
     * Whether this build may offer a subscription at all.
     *
     * The Google Play build may not send a learner out of the app to pay, so
     * it answers false and every screen simply leaves that option out. It
     * lives here because the gate is already the seam where the two channels
     * differ — a screen must never ask which build it is running in.
     */
    val canSubscribe: Boolean = false,
)

/**
 * The actions a limit block may trigger.
 *
 * Not every channel has every action: the Google Play build has no
 * subscription flow of its own, so it uses the status re-check and support
 * instead. Keeping them all here lets the screens stay identical in both
 * builds while each channel's block uses only what it is allowed to.
 */
data class LimitGateActions(
    /** Opens the subscription flow. Only the `direct` channel has one. */
    val onUnlock: () -> Unit = {},
    /** Re-reads access and limits from the server. Nothing is unlocked locally. */
    val onRecheck: () -> Unit = {},
    /** Opens the configured support contact. Never a payment page. */
    val onSupport: () -> Unit = {},
    /**
     * Starts the 7-day Pro trial.
     *
     * This is where the removed "continue with an ad" button used to sit. An
     * ad no longer opens anything, so the slot it left is the free trial —
     * the same swap the Mini App made on its own paywall. A trial is not a
     * purchase, so the Google Play build may offer it too: the store rule
     * forbids taking payment outside the app, not giving something away.
     */
    val onStartTrial: () -> Unit = {},
)

/** The pair a screen passes down to whatever limit block its channel builds. */
data class LimitGate(
    val state: LimitGateState = LimitGateState(),
    val actions: LimitGateActions = LimitGateActions(),
)
