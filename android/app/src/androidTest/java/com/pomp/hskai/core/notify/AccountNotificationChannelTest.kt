package com.pomp.hskai.core.notify

import android.app.NotificationManager
import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.BuildConfig
import com.pomp.hskai.data.api.AccountNoticeDto
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeFalse
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AccountNotificationChannelTest {

    @Test
    fun accountNoticeChannelCanAlertOnScreen() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        AccountNotifications.ensureChannel(context)
        val channel = context.getSystemService(NotificationManager::class.java)
            .getNotificationChannel(AccountNotifications.CHANNEL_ID)

        assertEquals(NotificationManager.IMPORTANCE_HIGH, channel.importance)
    }

    @Test
    fun playConsumesOffersSilentlyWithoutTriggeringTelegramFallback() {
        assumeFalse(BuildConfig.EXTERNAL_CHECKOUT_ENABLED)
        val context = ApplicationProvider.getApplicationContext<Context>()
        val manager = context.getSystemService(NotificationManager::class.java)
        val keys = listOf("subscription_expiring", "subscription_offer", "trial_expiring", "discount_offer", "unknown_offer")
        keys.forEach { key -> manager.cancel(AccountNoticePolicy.notificationId(key)) }

        keys.forEach { key ->
            assertTrue(
                "A Play policy skip must acknowledge handling without a fallback or permission requirement",
                AccountNotifications.post(context, AccountNoticeDto(
                    id = 71,
                    show = true,
                    key = key,
                    title = "Special offer",
                    body = "Subscribe at https://example.test/pay",
                    action = "subscription",
                )),
            )
        }
        val suppressedIds = keys.map(AccountNoticePolicy::notificationId).toSet()
        assertTrue(manager.activeNotifications.none { it.id in suppressedIds })
    }
}
