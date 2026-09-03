package com.pomp.hskai.core.notify

import org.junit.Assert.assertEquals
import org.junit.Test

class ReminderDecisionTest {

    private fun facts(
        notificationsEnabled: Boolean = true,
        dailyXp: Int = 0,
        dailyGoal: Int = 50,
        streak: Int = 0,
        localDate: String? = "2026-09-03",
        lastNotified: String? = null,
    ) = ReminderFacts(
        notificationsEnabled = notificationsEnabled,
        dailyXp = dailyXp,
        dailyGoal = dailyGoal,
        streak = streak,
        localDate = localDate,
        lastNotified = lastNotified,
    )

    @Test
    fun `a running streak with nothing done today is the urgent case`() {
        assertEquals(
            Reminder.STREAK_AT_RISK,
            ReminderDecision.decide(facts(streak = 7, dailyXp = 0)),
        )
    }

    @Test
    fun `a started day is no longer a streak risk`() {
        // The run is already safe; only the target is still short.
        assertEquals(
            Reminder.DAILY_GOAL,
            ReminderDecision.decide(facts(streak = 7, dailyXp = 10)),
        )
    }

    @Test
    fun `without a streak an unfinished target is the goal reminder`() {
        assertEquals(
            Reminder.DAILY_GOAL,
            ReminderDecision.decide(facts(streak = 0, dailyXp = 0)),
        )
    }

    @Test
    fun `a met goal is never interrupted`() {
        assertEquals(Reminder.NONE, ReminderDecision.decide(facts(dailyXp = 50, streak = 7)))
        assertEquals(Reminder.NONE, ReminderDecision.decide(facts(dailyXp = 90, streak = 7)))
    }

    @Test
    fun `the toggle being off silences everything`() {
        assertEquals(
            Reminder.NONE,
            ReminderDecision.decide(facts(notificationsEnabled = false, streak = 7)),
        )
    }

    @Test
    fun `only one reminder a day`() {
        assertEquals(
            Reminder.NONE,
            ReminderDecision.decide(
                facts(streak = 7, localDate = "2026-09-03", lastNotified = "2026-09-03"),
            ),
        )
        // A new day opens it again.
        assertEquals(
            Reminder.STREAK_AT_RISK,
            ReminderDecision.decide(
                facts(streak = 7, localDate = "2026-09-04", lastNotified = "2026-09-03"),
            ),
        )
    }

    /**
     * Without the server's date the client cannot tell today from yesterday,
     * so it must stay quiet rather than risk a daily reminder every run.
     */
    @Test
    fun `a missing server date sends nothing`() {
        assertEquals(Reminder.NONE, ReminderDecision.decide(facts(localDate = null, streak = 7)))
        assertEquals(Reminder.NONE, ReminderDecision.decide(facts(localDate = "", streak = 7)))
        assertEquals(Reminder.NONE, ReminderDecision.decide(facts(localDate = "   ", streak = 7)))
    }

    @Test
    fun `a nonsense goal cannot make the target unreachable`() {
        // A zero or negative goal would otherwise divide the ring by zero and
        // leave the learner permanently short of it.
        assertEquals(Reminder.NONE, ReminderDecision.decide(facts(dailyGoal = 0, dailyXp = 5)))
        assertEquals(Reminder.NONE, ReminderDecision.decide(facts(dailyGoal = -20, dailyXp = 5)))
    }

    @Test
    fun `a negative xp reading is treated as no work done`() {
        assertEquals(
            Reminder.STREAK_AT_RISK,
            ReminderDecision.decide(facts(dailyXp = -5, streak = 3)),
        )
    }
}
