package com.pomp.hskai.widget

import java.time.ZonedDateTime
import org.junit.Assert.*
import org.junit.Test

/** Access and freshness only. How the day is going is [WidgetVisualStateTest]. */
class WidgetStateTest {
    private val now = ZonedDateTime.parse("2026-09-11T18:00:00+05:00[Asia/Tashkent]")
    private fun snapshot() = WidgetSnapshot(now.toInstant().toEpochMilli(), "2026-09-11", now.zone.id, "hsk1", 2, 80, 3, false, false)

    @Test fun `unlinked outranks everything`() {
        assertEquals(WidgetAccess.UNLINKED, WidgetStateResolver.resolve(false, snapshot().copy(dayComplete = true), now))
    }
    @Test fun `missing stale future and previous local day do not leak progress`() {
        listOf(null, snapshot().copy(fetchedAtMillis = now.toInstant().toEpochMilli() - WidgetPolicy.STALE_AFTER_MILLIS),
            snapshot().copy(fetchedAtMillis = now.toInstant().toEpochMilli() + 1),
            snapshot().copy(localDay = "2026-09-10"), snapshot().copy(zoneId = "Europe/London")
        ).forEach { assertEquals(WidgetAccess.STALE, WidgetStateResolver.resolve(true, it, now)) }
    }
    @Test fun `foundation outranks a finished day`() {
        assertEquals(WidgetAccess.FOUNDATION, WidgetStateResolver.resolve(true, snapshot().copy(foundationRequired = true, dayComplete = true), now))
    }
    @Test fun `a linked fresh snapshot is simply active`() {
        assertEquals(WidgetAccess.ACTIVE, WidgetStateResolver.resolve(true, snapshot(), now))
        assertEquals(WidgetAccess.ACTIVE, WidgetStateResolver.resolve(true, snapshot().copy(dayComplete = true), now))
        assertEquals(WidgetAccess.ACTIVE, WidgetStateResolver.resolve(true, snapshot().copy(streak = 0), now))
    }
    @Test fun `midnight invalidates yesterday even under the freshness limit`() {
        val midnight = now.plusDays(1).withHour(0)
        assertEquals(WidgetAccess.STALE, WidgetStateResolver.resolve(true, snapshot().copy(fetchedAtMillis = midnight.minusMinutes(1).toInstant().toEpochMilli()), midnight))
    }
    @Test fun `policy supports the WorkManager minimum and the hourly visual boundaries`() {
        assertTrue(WidgetPolicy.REFRESH_MINUTES >= 15)
        assertTrue(WidgetPolicy.REFRESH_MINUTES <= 60)
        assertTrue(WidgetPolicy.SCHEDULE_VERSION > 0)
        assertTrue(WidgetPolicy.REMINDER_VARIANTS > 0)
    }
}
