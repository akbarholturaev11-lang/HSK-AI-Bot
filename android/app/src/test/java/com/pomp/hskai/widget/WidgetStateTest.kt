package com.pomp.hskai.widget

import java.time.ZonedDateTime
import org.junit.Assert.*
import org.junit.Test

class WidgetStateTest {
    private val now = ZonedDateTime.parse("2026-09-11T18:00:00+05:00[Asia/Tashkent]")
    private fun snapshot() = WidgetSnapshot(now.toInstant().toEpochMilli(), "2026-09-11", now.zone.id, "hsk1", 2, 80, 3, false, false)

    @Test fun `unlinked outranks everything`() {
        assertEquals(WidgetMood.UNLINKED, WidgetStateResolver.resolve(false, snapshot().copy(dayComplete = true), now))
    }
    @Test fun `missing stale future and previous local day do not leak progress`() {
        listOf(null, snapshot().copy(fetchedAtMillis = now.toInstant().toEpochMilli() - WidgetPolicy.STALE_AFTER_MILLIS),
            snapshot().copy(fetchedAtMillis = now.toInstant().toEpochMilli() + 1),
            snapshot().copy(localDay = "2026-09-10"), snapshot().copy(zoneId = "Europe/London")
        ).forEach { assertEquals(WidgetMood.STALE, WidgetStateResolver.resolve(true, it, now)) }
    }
    @Test fun `foundation outranks complete and streak`() {
        assertEquals(WidgetMood.FOUNDATION, WidgetStateResolver.resolve(true, snapshot().copy(foundationRequired = true, dayComplete = true), now))
    }
    @Test fun `finished day outranks streak`() {
        assertEquals(WidgetMood.COMPLETE, WidgetStateResolver.resolve(true, snapshot().copy(dayComplete = true), now))
    }
    @Test fun `streak reaction is not tied to an evening boundary`() {
        assertEquals(WidgetMood.STREAK, WidgetStateResolver.resolve(true, snapshot(), now))
        assertEquals(WidgetMood.CONTINUE, WidgetStateResolver.resolve(true, snapshot().copy(streak = 0), now))
        val daytime = now.withHour(10)
        assertEquals(WidgetMood.STREAK, WidgetStateResolver.resolve(true, snapshot().copy(
            fetchedAtMillis = daytime.toInstant().toEpochMilli(),
            localDay = daytime.toLocalDate().toString(),
        ), daytime))
    }
    @Test fun `midnight invalidates yesterday even under the freshness limit`() {
        val midnight = now.plusDays(1).withHour(0)
        assertEquals(WidgetMood.STALE, WidgetStateResolver.resolve(true, snapshot().copy(fetchedAtMillis = midnight.minusMinutes(1).toInstant().toEpochMilli()), midnight))
    }
    @Test fun `policy supports WorkManager minimum and chronological hours`() {
        assertTrue(WidgetPolicy.REFRESH_MINUTES >= 15)
        assertTrue(WidgetPolicy.REACTION_START_HOUR < WidgetPolicy.REACTION_END_HOUR)
        assertEquals(7, WidgetReaction.DAYTIME_ROTATION.size)
        assertTrue(WidgetReaction.entries.containsAll(WidgetReaction.DAYTIME_ROTATION))
        assertTrue(WidgetPolicy.REACTION_SLOT_MINUTES > 0)
        assertTrue(WidgetPolicy.SCHEDULE_VERSION > 0)
    }

    @Test fun `continue art rotates through seven daytime slots only`() {
        val reactions = (0 until 7).map { index ->
            WidgetStateResolver.reaction(
                WidgetMood.CONTINUE,
                now = now.withHour(9).plusMinutes(index * WidgetPolicy.REACTION_SLOT_MINUTES.toLong()),
            )
        }
        assertEquals(WidgetReaction.DAYTIME_ROTATION, reactions)
        assertEquals(WidgetReaction.CALM, WidgetStateResolver.reaction(
            WidgetMood.CONTINUE,
            now = now.withHour(7),
        ))
        assertEquals(WidgetReaction.CALM, WidgetStateResolver.reaction(
            WidgetMood.CONTINUE,
            now = now.withHour(20),
        ))
        // Art is separate from access state: a completed day remains celebratory.
        assertEquals(WidgetReaction.CELEBRATE, WidgetStateResolver.reaction(WidgetMood.COMPLETE, now = now))
    }

    @Test fun `an evening with nothing earned asks instead of rotating`() {
        val evening = now.withHour(WidgetPolicy.RISK_HOUR)
        val idle = snapshot().copy(dailyXp = 0, goalXp = 50)
        assertEquals(WidgetReaction.WORRIED, WidgetStateResolver.reaction(WidgetMood.STREAK, idle, evening))
        assertEquals(WidgetReaction.WORRIED, WidgetStateResolver.reaction(WidgetMood.CONTINUE, idle, evening))
        // Before the risk hour the same day is still an ordinary one.
        assertEquals(WidgetReaction.STREAK, WidgetStateResolver.reaction(WidgetMood.STREAK, idle, now.withHour(12)))
    }

    @Test fun `at night the panda rests rather than nags`() {
        val night = now.withHour(WidgetPolicy.NIGHT_HOUR)
        val idle = snapshot().copy(dailyXp = 0, goalXp = 50)
        assertEquals(WidgetReaction.SLEEPY, WidgetStateResolver.reaction(WidgetMood.STREAK, idle, night))
        assertEquals(WidgetReaction.SLEEPY, WidgetStateResolver.reaction(WidgetMood.CONTINUE, idle, night.withHour(3)))
        // A finished day is celebrated whatever the hour.
        assertEquals(WidgetReaction.CELEBRATE, WidgetStateResolver.reaction(WidgetMood.COMPLETE, idle, night))
    }

    @Test fun `half of today's goal switches the panda to cheering`() {
        val midday = now.withHour(12)
        assertEquals(WidgetReaction.CHEER, WidgetStateResolver.reaction(
            WidgetMood.STREAK, snapshot().copy(dailyXp = 25, goalXp = 50), midday,
        ))
        // An unknown goal claims nothing, so the rotation is unchanged.
        assertEquals(WidgetReaction.STREAK, WidgetStateResolver.reaction(
            WidgetMood.STREAK, snapshot().copy(dailyXp = 25, goalXp = 0), midday,
        ))
    }

    @Test fun `the goal line appears only after the day has started`() {
        val midday = now.withHour(12)
        assertEquals(WidgetPrompt.GoalLeft(30), WidgetStateResolver.prompt(
            WidgetMood.STREAK, snapshot().copy(dailyXp = 20, goalXp = 50), midday,
        ))
        // Nothing earned yet, a met goal and an unknown goal all stay on the mood title.
        listOf(
            snapshot().copy(dailyXp = 0, goalXp = 50),
            snapshot().copy(dailyXp = 50, goalXp = 50),
            snapshot().copy(dailyXp = 20, goalXp = 0),
        ).forEach {
            assertEquals(WidgetPrompt.Mood, WidgetStateResolver.prompt(WidgetMood.STREAK, it, midday))
        }
    }

    @Test fun `the streak line needs a run to lose and a day that is running out`() {
        val evening = now.withHour(WidgetPolicy.RISK_HOUR)
        assertEquals(WidgetPrompt.StreakAtRisk, WidgetStateResolver.prompt(
            WidgetMood.STREAK, snapshot().copy(dailyXp = 0, streak = 4), evening,
        ))
        assertEquals(WidgetPrompt.Mood, WidgetStateResolver.prompt(
            WidgetMood.CONTINUE, snapshot().copy(dailyXp = 0, streak = 0), evening,
        ))
        assertEquals(WidgetPrompt.Mood, WidgetStateResolver.prompt(
            WidgetMood.STREAK, snapshot().copy(dailyXp = 0, streak = 4), now.withHour(12),
        ))
        // Access states keep their own title; a locked or unlinked widget asks for nothing else.
        listOf(WidgetMood.UNLINKED, WidgetMood.STALE, WidgetMood.FOUNDATION, WidgetMood.COMPLETE).forEach {
            assertEquals(WidgetPrompt.Mood, WidgetStateResolver.prompt(it, snapshot(), evening))
        }
    }
}
