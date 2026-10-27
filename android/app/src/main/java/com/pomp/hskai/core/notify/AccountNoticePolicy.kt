package com.pomp.hskai.core.notify

import com.pomp.hskai.core.navigation.AppDestination

/**
 * Where an account notice opens and which slot it occupies in the shade.
 *
 * Free of Android so it can be unit tested. Each kind of notice has its own
 * slot: a newer notice of the same kind replaces the older one, but a trial
 * reminder never hides a discount.
 */
object AccountNoticePolicy {

    private const val BASE_ID = 4500

    private val SLOTS = mapOf(
        "subscription_expiring" to 1,
        "subscription_offer" to 2,
        "trial_expiring" to 3,
        "daily_limit_renewed" to 4,
        "discount_offer" to 5,
    )

    fun notificationId(key: String): Int = BASE_ID + (SLOTS[key.trim()] ?: 0)

    /** Consumption-only Play accepts only the known, neutral course reminder. */
    fun canShow(key: String, action: String, externalCheckoutEnabled: Boolean): Boolean =
        externalCheckoutEnabled ||
            (key.trim() == "daily_limit_renewed" && action.trim() == "course")

    /** A verified server hint overrides only the destination, never Play copy policy. */
    fun destinationForNotice(action: String, externalCheckoutEnabled: Boolean, updateRequired: Boolean): AppDestination =
        if (updateRequired && action.trim() == "course") AppDestination.Update
        else destination(action, externalCheckoutEnabled)

    /** Remove old Direct offers from the shade without cancelling neutral notices. */
    fun playSuppressedNotificationIds(): Set<Int> =
        (SLOTS.keys.filterNot { canShow(it, "course", false) } + "")
            .map(::notificationId).toSet()

    /** Unknown actions cannot turn a Play notice into a purchase entry point. */
    fun destination(action: String, externalCheckoutEnabled: Boolean): AppDestination = when (action.trim()) {
        "course" -> AppDestination.Course
        else -> if (externalCheckoutEnabled) AppDestination.Subscription else AppDestination.Profile
    }
}
