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

    /** Server actions are a closed set; anything unknown opens the paywall. */
    fun destination(action: String): AppDestination = when (action.trim()) {
        "course" -> AppDestination.Course
        else -> AppDestination.Subscription
    }
}
