package com.pomp.hskai.core.text

import java.time.Instant
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * When a daily limit reopens, on the learner's own clock.
 *
 * The server sends an instant, never a formatted hour: a learner in UTC+5 and
 * one in UTC+3 must each read their own time, and the reset hour is an admin
 * setting that can change. Nothing here is hard-coded.
 */
object ResetTime {

    // Locale.ROOT keeps the digits Latin whatever the device language is, so
    // uz/ru/tg all read the same clock.
    private val CLOCK: DateTimeFormatter = DateTimeFormatter.ofPattern("HH:mm", Locale.ROOT)

    /**
     * Formats [iso] as local clock time, or returns null when there is nothing
     * trustworthy to show.
     *
     * Null is meaningful: it means the caller must NOT promise a reset. A
     * limit with no reset (nothing reopens tomorrow) and an unparsable value
     * are the same to the learner — better to say nothing than the wrong hour.
     */
    fun localClock(iso: String?, zone: ZoneId = ZoneId.systemDefault()): String? {
        val text = iso?.trim().orEmpty()
        if (text.isEmpty()) return null
        val instant = runCatching { OffsetDateTime.parse(text).toInstant() }
            .recoverCatching { Instant.parse(text) }
            .getOrNull() ?: return null
        return instant.atZone(zone).format(CLOCK)
    }
}
