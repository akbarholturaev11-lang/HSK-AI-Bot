package com.pomp.hskai.core.notify

import android.app.NotificationManager
import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PaymentNotificationChannelTest {

    @Test
    fun paymentDecisionChannelCanAlertOnScreen() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        PaymentNotifications.ensureChannel(context)
        val channel = context.getSystemService(NotificationManager::class.java)
            .getNotificationChannel(PaymentNotifications.CHANNEL_ID)

        assertEquals(NotificationManager.IMPORTANCE_HIGH, channel.importance)
    }
}
