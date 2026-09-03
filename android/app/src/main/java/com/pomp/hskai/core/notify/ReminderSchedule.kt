package com.pomp.hskai.core.notify

import java.util.Calendar

/**
 * When the daily reminder check should run.
 *
 * Kept free of Android and of WorkManager so the timing can be unit tested
 * against a fixed clock rather than only observed on a device.
 */
object ReminderSchedule {

    /** Local hour the reminder aims for; late enough to mean "today is ending". */
    const val REMINDER_HOUR = 20

    /**
     * Minutes from [now] until the next [REMINDER_HOUR] in the device's zone.
     *
     * At exactly the reminder hour the answer is a whole day, not zero: the
     * check has just run, and a zero delay would fire it a second time.
     */
    fun minutesUntilReminderHour(now: Calendar = Calendar.getInstance()): Long {
        val target = (now.clone() as Calendar).apply {
            set(Calendar.HOUR_OF_DAY, REMINDER_HOUR)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
        }
        if (!target.after(now)) target.add(Calendar.DAY_OF_YEAR, 1)
        return (target.timeInMillis - now.timeInMillis) / 60_000
    }
}
