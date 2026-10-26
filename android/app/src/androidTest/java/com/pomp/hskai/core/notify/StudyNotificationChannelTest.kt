package com.pomp.hskai.core.notify

import android.app.NotificationManager
import android.app.NotificationChannel
import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assume.assumeTrue
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

    @Test
    fun deniedStudyPermissionCannotPost() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        // The isolated QA runner revokes this permission BEFORE starting
        // instrumentation. Revoking inside the test can kill its own process.
        assumeTrue(context.packageName.endsWith(".qa"))
        assumeTrue(Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU)
        assertEquals(PackageManager.PERMISSION_DENIED, ContextCompat.checkSelfPermission(
            context, Manifest.permission.POST_NOTIFICATIONS,
        ))
        assertFalse(StudyNotifications.canPost(context))
        assertFalse(StudyNotifications.postReminder(context, Reminder.DAILY_GOAL))
    }

    @Test
    fun mutedLegacyStudyChannelIsNotSilentlyReenabled() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        assumeTrue(context.packageName.endsWith(".qa"))
        val manager = context.getSystemService(NotificationManager::class.java)
        val legacy = "study_reminders"
        // This fixture owns only a channel it creates in the isolated QA app.
        assumeTrue(manager.getNotificationChannel(legacy) == null)
        manager.createNotificationChannel(NotificationChannel(
            legacy, "QA muted study channel", NotificationManager.IMPORTANCE_NONE,
        ))
        try {
            assertEquals(legacy, StudyNotifications.ensureChannel(context))
            assertEquals(NotificationManager.IMPORTANCE_NONE,
                manager.getNotificationChannel(legacy).importance)
            assertFalse(StudyNotifications.canPost(context))
        } finally {
            manager.deleteNotificationChannel(legacy)
        }
    }
}
