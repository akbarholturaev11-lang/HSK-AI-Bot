package com.pomp.hskai.core.notify

import com.pomp.hskai.core.navigation.AppDestination
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
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
        assertEquals(AppDestination.Course, AccountNoticePolicy.destination("course", true))
        assertEquals(AppDestination.Subscription, AccountNoticePolicy.destination("subscription", true))
        assertEquals(AppDestination.Subscription, AccountNoticePolicy.destination("", true))
        assertEquals(AppDestination.Subscription, AccountNoticePolicy.destination("lesson/99", true))
    }

    @Test
    fun `Play accepts only neutral limit renewal notices with a course action`() {
        assertTrue(AccountNoticePolicy.canShow("daily_limit_renewed", "course", false))
        (keys.filter { it != "daily_limit_renewed" } + "unknown_offer" + "").forEach { key ->
            listOf("course", "subscription", "", "https://example.test/pay").forEach { action ->
                assertFalse("Play must suppress $key / $action", AccountNoticePolicy.canShow(key, action, false))
            }
        }
        listOf("subscription", "", "https://example.test/pay").forEach { action ->
            assertFalse(AccountNoticePolicy.canShow("daily_limit_renewed", action, false))
        }
    }

    @Test
    fun `Direct preserves account notices and Play never resolves to checkout`() {
        (keys + "unknown_offer").forEach { key ->
            assertTrue(AccountNoticePolicy.canShow(key, "subscription", true))
        }
        assertEquals(AppDestination.Course, AccountNoticePolicy.destination("course", false))
        listOf("subscription", "", "lesson/99").forEach { action ->
            assertEquals(AppDestination.Profile, AccountNoticePolicy.destination(action, false))
        }
    }

    @Test
    fun `Play migration clears old offer slots and preserves neutral and payment notices`() {
        val cleared = AccountNoticePolicy.playSuppressedNotificationIds()
        assertEquals(setOf(4500, 4501, 4502, 4503, 4505), cleared)
        assertFalse(AccountNoticePolicy.notificationId("daily_limit_renewed") in cleared)
        assertFalse(4401 in cleared)
    }
}
