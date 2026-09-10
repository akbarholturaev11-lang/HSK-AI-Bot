package com.pomp.hskai.widget

/** Change timing here only. Bump SCHEDULE_VERSION when changing a schedule. */
object WidgetPolicy {
    const val SCHEDULE_VERSION = 1
    const val REFRESH_MINUTES = 60L
    const val EVENING_HOUR = 18
    const val REMINDER_HOUR = 20
    const val STALE_AFTER_MILLIS = 2 * 60 * 60 * 1_000L
    const val MAX_PENDING_EVENTS = 32
}
