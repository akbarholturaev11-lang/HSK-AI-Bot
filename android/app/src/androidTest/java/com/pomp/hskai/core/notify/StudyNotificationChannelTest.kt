package com.pomp.hskai.core.notify

import android.app.NotificationManager
import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class StudyNotificationChannelTest {

    @Test
    fun newReminderChannelCanAlertOnScreen() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val channelId = StudyNotifications.ensureChannel(context)
        val channel = context.getSystemService(NotificationManager::class.java)
            .getNotificationChannel(channelId)

        assertEquals(StudyNotifications.CHANNEL_ID, channelId)
        assertEquals(NotificationManager.IMPORTANCE_HIGH, channel.importance)
    }
}
