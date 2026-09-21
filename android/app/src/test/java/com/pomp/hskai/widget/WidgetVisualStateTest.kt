package com.pomp.hskai.widget

import java.time.ZonedDateTime
import org.junit.Assert.*
import org.junit.Test

/** The one visual-state engine: local clock, today's completion, nothing else. */
class WidgetVisualStateTest {
    private val day = ZonedDateTime.parse("2026-09-11T12:00:00+05:00[Asia/Tashkent]")
    private val key = "3f6c2f0e-0a54-4c1b-9c6e-9a1c2d3e4f50"

    private fun snapshot(complete: Boolean, streak: Int = 3) = WidgetSnapshot(
        fetchedAtMillis = day.toInstant().toEpochMilli(),
        localDay = day.toLocalDate().toString(),
        zoneId = day.zone.id,
        level = "hsk1",
        lessonOrder = 2,
        xp = 80,
        streak = streak,
        dayComplete = complete,
        foundationRequired = false,
    )

    private fun at(hour: Int, minute: Int) = day.withHour(hour).withMinute(minute)

    /** Every boundary of the local day, from both sides. */
    private val boundaries = listOf(
        4 to 59 to WidgetVisualState.MORNING,
        5 to 0 to WidgetVisualState.MORNING,
        9 to 59 to WidgetVisualState.MORNING,
        10 to 0 to WidgetVisualState.DAY,
        13 to 59 to WidgetVisualState.DAY,
        14 to 0 to WidgetVisualState.WAITING,
        17 to 59 to WidgetVisualState.WAITING,
        18 to 0 to WidgetVisualState.EVENING,
        19 to 59 to WidgetVisualState.EVENING,
        20 to 0 to WidgetVisualState.LATE,
        21 to 59 to WidgetVisualState.LATE,
        22 to 0 to WidgetVisualState.CRITICAL,
        23 to 59 to WidgetVisualState.CRITICAL,
        0 to 0 to WidgetVisualState.MORNING,
    )

    @Test fun `an unfinished day escalates with the local clock`() {
        boundaries.forEach { (clock, expected) ->
            val (hour, minute) = clock
            val now = at(hour, minute)
            assertEquals("$hour:$minute", expected, WidgetVisualResolver.timeState(now))
            assertEquals(
                "$hour:$minute",
                expected,
                WidgetVisualResolver.resolve(snapshot(complete = false), key, now).state,
            )
        }
    }

    @Test fun `a finished day overrides every time state`() {
        boundaries.forEach { (clock, _) ->
            val (hour, minute) = clock
            assertEquals(
                "$hour:$minute",
                WidgetVisualState.COMPLETED,
                WidgetVisualResolver.resolve(snapshot(complete = true), key, at(hour, minute)).state,
            )
        }
    }

    @Test fun `2330 unfinished is critical and 2330 finished is not`() {
        val night = at(23, 30)
        assertEquals(WidgetVisualState.CRITICAL, WidgetVisualResolver.resolve(snapshot(false), key, night).state)
        assertEquals(WidgetVisualState.COMPLETED, WidgetVisualResolver.resolve(snapshot(true), key, night).state)
    }

    @Test fun `the new local day opens gently instead of carrying critical over`() {
        val midnight = day.plusDays(1).withHour(0).withMinute(0)
        assertEquals(WidgetVisualState.MORNING, WidgetVisualResolver.resolve(snapshot(false), key, midnight).state)
        assertEquals(WidgetVisualState.MORNING, WidgetVisualResolver.resolve(snapshot(false), key, midnight.withHour(4).withMinute(59)).state)
    }

    @Test fun `the same wall clock in another zone reads that zone`() {
        val tashkent = ZonedDateTime.parse("2026-09-11T22:30:00+05:00[Asia/Tashkent]")
        val london = tashkent.withZoneSameInstant(java.time.ZoneId.of("Europe/London"))
        assertEquals(WidgetVisualState.CRITICAL, WidgetVisualResolver.timeState(tashkent))
        assertEquals(WidgetVisualState.EVENING, WidgetVisualResolver.timeState(london))
    }

    @Test fun `urgency rises through an unfinished day and rests when it is done`() {
        val order = listOf(
            WidgetVisualState.MORNING, WidgetVisualState.DAY, WidgetVisualState.WAITING,
            WidgetVisualState.EVENING, WidgetVisualState.LATE, WidgetVisualState.CRITICAL,
        )
        order.zipWithNext().forEach { (earlier, later) ->
            assertTrue("$earlier -> $later", earlier.urgency < later.urgency)
        }
        assertEquals(0, WidgetVisualState.COMPLETED.urgency)
        assertEquals(5, WidgetVisualState.CRITICAL.urgency)
    }

    @Test fun `a milestone outranks a finished day and carries the streak`() {
        val special = WidgetVisualResolver.resolve(snapshot(complete = true, streak = 7), key, at(23, 30))
        assertEquals(WidgetSpecialState(WidgetSpecialKind.MILESTONE, 7), special.special)
        assertEquals(WidgetVisualState.COMPLETED, special.state)
        // Only the round numbers, and only once the day is actually finished.
        assertNull(WidgetVisualResolver.resolve(snapshot(complete = true, streak = 8), key, day).special)
        assertNull(WidgetVisualResolver.resolve(snapshot(complete = false, streak = 7), key, day).special)
        assertNull(WidgetVisualResolver.resolve(null, key, day).special)
        assertEquals(listOf(7, 30, 50, 100, 365), WidgetVisualResolver.MILESTONE_DAYS)
    }

    @Test fun `a variant is stable for one key one day and one state`() {
        WidgetVisualState.entries.forEach { state ->
            val first = WidgetVisualResolver.variantFor(state, key, "2026-09-11")
            repeat(50) { assertEquals(first, WidgetVisualResolver.variantFor(state, key, "2026-09-11")) }
            assertTrue("$state -> $first", first in 0 until state.variants)
        }
    }

    @Test fun `every day and every key lands inside the state's own range`() {
        val keys = listOf(key, "uninitialized", "0", "e9b1c0aa-1111-2222-3333-444455556666")
        WidgetVisualState.entries.forEach { state ->
            (1..120).forEach { offset ->
                val date = day.plusDays(offset.toLong()).toLocalDate().toString()
                keys.forEach { candidate ->
                    val variant = WidgetVisualResolver.variantFor(state, candidate, date)
                    assertTrue("$state $candidate $date -> $variant", variant in 0 until state.variants)
                }
            }
        }
    }

    @Test fun `the hash spreads over days rather than sticking on one drawing`() {
        // Not a distribution guarantee — only that the panda is not frozen on
        // the same face for four months, which a broken hash would do.
        val seen = (1..120).map {
            WidgetVisualResolver.variantFor(
                WidgetVisualState.CRITICAL, key, day.plusDays(it.toLong()).toLocalDate().toString(),
            )
        }.toSet()
        assertEquals(WidgetVisualState.CRITICAL.variants, seen.size)
    }

    @Test fun `resolve picks the variant of the state it resolved`() {
        val now = at(20, 30)
        val visual = WidgetVisualResolver.resolve(snapshot(false), key, now)
        assertEquals(WidgetVisualState.LATE, visual.state)
        assertEquals(
            WidgetVisualResolver.variantFor(WidgetVisualState.LATE, key, now.toLocalDate().toString()),
            visual.variant,
        )
    }
}
