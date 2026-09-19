package com.pomp.hskai.widget

/** Change timing here only. Bump SCHEDULE_VERSION when changing a schedule. */
object WidgetPolicy {
    const val SCHEDULE_VERSION = 3
    const val REFRESH_MINUTES = 60L
    /**
     * Panda art rotates only in the active daytime window. Outside it the
     * widget keeps the neutral reaction; there are no separate morning or
     * evening states to surprise the learner.
     *
     * Change these values (and bump [SCHEDULE_VERSION]) when product wants a
     * different cadence. The seven 90-minute slots map to the seven daytime
     * panda reactions in [WidgetReaction.DAYTIME_ROTATION].
     */
    const val REACTION_START_HOUR = 9
    const val REACTION_END_HOUR = 19
    const val REACTION_SLOT_MINUTES = 90
    /**
     * From this hour a day with no XP at all is running out, so the panda
     * stops rotating and asks. It is the same hour the rotation ends: one
     * boundary, not two that can drift apart.
     */
    const val RISK_HOUR = REACTION_END_HOUR
    /** Night art window. Nothing is scheduled here; only the drawing changes. */
    const val NIGHT_HOUR = 22
    const val DAWN_HOUR = 6
    /** Half of today's goal is enough to switch the panda from asking to cheering. */
    const val CHEER_PERCENT = 50
    const val REMINDER_HOUR = 20
    const val STALE_AFTER_MILLIS = 2 * 60 * 60 * 1_000L
    const val MAX_PENDING_EVENTS = 32
    /** How many bodies each reminder rotates through, so it never reads canned. */
    const val REMINDER_VARIANTS = 3
}
