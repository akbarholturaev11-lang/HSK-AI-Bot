package com.pomp.hskai.widget

/** Change timing here only. Bump SCHEDULE_VERSION when changing a schedule. */
object WidgetPolicy {
    const val SCHEDULE_VERSION = 4
    /**
     * Hourly is enough for the panda.
     *
     * Every boundary in [WidgetVisualResolver] falls on a whole hour, so one
     * refresh per hour is the cadence the visual states need. The clock
     * boundaries themselves live in the resolver, not here: they are what the
     * widget draws, not what WorkManager runs.
     */
    const val REFRESH_MINUTES = 60L
    const val REMINDER_HOUR = 20
    const val STALE_AFTER_MILLIS = 2 * 60 * 60 * 1_000L
    const val MAX_PENDING_EVENTS = 32
    /** How many bodies each reminder rotates through, so it never reads canned. */
    const val REMINDER_VARIANTS = 3
}
