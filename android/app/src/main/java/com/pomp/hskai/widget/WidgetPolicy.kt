package com.pomp.hskai.widget

/** Change timing here only. Bump SCHEDULE_VERSION when changing a schedule. */
object WidgetPolicy {
    const val SCHEDULE_VERSION = 2
    const val REFRESH_MINUTES = 60L
    /**
     * Panda art rotates only in the active daytime window. Outside it the
     * widget keeps the neutral reaction; there are no separate morning or
     * evening states to surprise the learner.
     *
     * Change these values (and bump [SCHEDULE_VERSION]) when product wants a
     * different cadence. The seven 90-minute slots map to the seven panda
     * reactions in [WidgetReaction].
     */
    const val REACTION_START_HOUR = 9
    const val REACTION_END_HOUR = 19
    const val REACTION_SLOT_MINUTES = 90
    const val REMINDER_HOUR = 20
    const val STALE_AFTER_MILLIS = 2 * 60 * 60 * 1_000L
    const val MAX_PENDING_EVENTS = 32
}
