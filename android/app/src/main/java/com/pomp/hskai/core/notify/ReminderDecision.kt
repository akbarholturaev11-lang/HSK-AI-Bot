package com.pomp.hskai.core.notify

/**
 * What, if anything, today's reminder should say.
 *
 * The decision is deliberately free of Android and of the network so it can be
 * unit tested on its own. The worker only gathers the inputs and delivers the
 * result; it never decides here.
 */
enum class Reminder {
    /** The learner has a run going and has not studied today yet. */
    STREAK_AT_RISK,

    /** No streak to lose, but today's XP target is still short. */
    DAILY_GOAL,

    /** Say nothing. */
    NONE,
}

/**
 * The facts a reminder is allowed to be based on.
 *
 * [localDate] and [dailyXp] come from the server's course map, so "today" means
 * the same day the backend counts, not the device's idea of it. [lastNotified]
 * is the last date this device actually posted a reminder.
 */
data class ReminderFacts(
    val notificationsEnabled: Boolean,
    val dailyXp: Int,
    val dailyGoal: Int,
    val streak: Int,
    val localDate: String?,
    val lastNotified: String?,
)

object ReminderDecision {

    /**
     * At most one reminder a day, and never after the learner has already done
     * the work — a notification that arrives once the goal is met reads as
     * nagging and is the fastest way to get reminders turned off for good.
     */
    fun decide(facts: ReminderFacts): Reminder {
        if (!facts.notificationsEnabled) return Reminder.NONE

        // Without the server's date there is no honest way to tell today from
        // yesterday, so nothing is sent rather than guessing.
        val today = facts.localDate?.trim()?.takeIf { it.isNotEmpty() } ?: return Reminder.NONE
        if (facts.lastNotified?.trim() == today) return Reminder.NONE

        val goal = facts.dailyGoal.coerceAtLeast(1)
        val earned = facts.dailyXp.coerceAtLeast(0)
        if (earned >= goal) return Reminder.NONE

        // A run that is about to break is the more urgent of the two, and it
        // is only at risk while nothing at all has been done today.
        if (facts.streak > 0 && earned == 0) return Reminder.STREAK_AT_RISK

        return Reminder.DAILY_GOAL
    }
}
