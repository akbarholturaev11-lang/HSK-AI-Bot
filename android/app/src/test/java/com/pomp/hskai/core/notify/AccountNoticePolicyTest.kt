package com.pomp.hskai.core.notify

import com.pomp.hskai.core.navigation.AppDestination
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

class AccountNoticePolicyTest {

    private val keys = listOf(
        "subscription_expiring",
        "subscription_offer",
        "trial_expiring",
        "daily_limit_renewed",
        "discount_offer",
    )

    @Test
    fun `each kind of notice keeps its own place in the shade`() {
        val ids = keys.map(AccountNoticePolicy::notificationId)
        assertEquals(keys.size, ids.toSet().size)
    }

    @Test
    fun `account notices never replace study, update or payment notifications`() {
        val taken = setOf(4201, 4301, 4401)
        (keys + "unknown_key").forEach { key ->
            assertEquals(false, AccountNoticePolicy.notificationId(key) in taken)
        }
    }

    @Test
    fun `an unknown key still gets a slot of its own`() {
        assertNotEquals(
            AccountNoticePolicy.notificationId("trial_expiring"),
            AccountNoticePolicy.notificationId("something_new"),
        )
    }

    @Test
    fun `a renewed limit opens the course and everything else the subscription`() {
        assertEquals(AppDestination.Course, AccountNoticePolicy.destination("course"))
        assertEquals(AppDestination.Subscription, AccountNoticePolicy.destination("subscription"))
        assertEquals(AppDestination.Subscription, AccountNoticePolicy.destination(""))
        assertEquals(AppDestination.Subscription, AccountNoticePolicy.destination("lesson/99"))
    }
}
