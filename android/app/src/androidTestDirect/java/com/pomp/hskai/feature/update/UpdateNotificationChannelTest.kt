package com.pomp.hskai.feature.update

import android.app.NotificationManager
import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class UpdateNotificationChannelTest {

    @Test
    fun newUpdateChannelCanAlertOnScreen() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val channelId = UpdateNotices.ensureChannel(context)
        val channel = context.getSystemService(NotificationManager::class.java)
            .getNotificationChannel(channelId)

        assertEquals(UpdateNotices.CHANNEL_ID, channelId)
        assertEquals(NotificationManager.IMPORTANCE_HIGH, channel.importance)
    }
}
