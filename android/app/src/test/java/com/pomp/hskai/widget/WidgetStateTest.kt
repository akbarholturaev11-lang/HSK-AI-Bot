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
        assertEquals(7, WidgetReaction.entries.size)
        assertTrue(WidgetPolicy.REACTION_SLOT_MINUTES > 0)
        assertTrue(WidgetPolicy.SCHEDULE_VERSION > 0)
    }

    @Test fun `continue art rotates through seven daytime slots only`() {
        val reactions = (0 until 7).map { index ->
            WidgetStateResolver.reaction(
                WidgetMood.CONTINUE,
                now.withHour(9).plusMinutes(index * WidgetPolicy.REACTION_SLOT_MINUTES.toLong()),
            )
        }
        assertEquals(WidgetReaction.entries.toList(), reactions)
        assertEquals(WidgetReaction.CALM, WidgetStateResolver.reaction(
            WidgetMood.CONTINUE,
            now.withHour(7),
        ))
        assertEquals(WidgetReaction.CALM, WidgetStateResolver.reaction(
            WidgetMood.CONTINUE,
            now.withHour(20),
        ))
        // Art is separate from access state: a completed day remains celebratory.
        assertEquals(WidgetReaction.CELEBRATE, WidgetStateResolver.reaction(WidgetMood.COMPLETE, now))
    }
}
