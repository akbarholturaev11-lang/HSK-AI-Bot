package com.pomp.hskai.core.notify

import java.util.Calendar
import java.util.TimeZone
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ReminderScheduleTest {

    private fun at(hour: Int, minute: Int): Calendar =
        Calendar.getInstance(TimeZone.getTimeZone("UTC")).apply {
            set(2026, Calendar.SEPTEMBER, 3, hour, minute, 0)
            set(Calendar.MILLISECOND, 0)
        }

    @Test
    fun `morning waits until the evening of the same day`() {
        assertEquals(11 * 60L, ReminderSchedule.minutesUntilReminderHour(at(9, 0)))
        assertEquals(30L, ReminderSchedule.minutesUntilReminderHour(at(19, 30)))
    }

    @Test
    fun `after the hour it rolls to tomorrow`() {
        assertEquals(23 * 60L + 59, ReminderSchedule.minutesUntilReminderHour(at(20, 1)))
        assertEquals(19 * 60L, ReminderSchedule.minutesUntilReminderHour(at(1, 0)))
    }

    /**
     * Exactly on the hour must not schedule a zero delay: the check has just
     * run and would otherwise fire straight back.
     */
    @Test
    fun `exactly on the hour waits a full day`() {
        assertEquals(24 * 60L, ReminderSchedule.minutesUntilReminderHour(at(20, 0)))
    }

    @Test
    fun `the delay is always inside one day and never negative`() {
        for (hour in 0..23) {
            for (minute in listOf(0, 17, 43, 59)) {
                val minutes = ReminderSchedule.minutesUntilReminderHour(at(hour, minute))
                assertTrue("hour=$hour minute=$minute -> $minutes", minutes > 0)
                assertTrue("hour=$hour minute=$minute -> $minutes", minutes <= 24 * 60)
            }
        }
    }
}
