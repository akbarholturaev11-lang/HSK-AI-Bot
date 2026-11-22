package com.pomp.hskai.widget

/** Change timing here only. Bump SCHEDULE_VERSION when changing a schedule. */
object WidgetPolicy {
    const val SCHEDULE_VERSION = 4
    /** Best-effort OS refresh; personal context can expire between ticks.
     * Every render validates the server deadline. This is not an exact-time alarm.
     */
    const val REFRESH_MINUTES = 60L
    const val REMINDER_HOUR = 20
    const val STALE_AFTER_MILLIS = 2 * 60 * 60 * 1_000L
    const val MAX_PENDING_EVENTS = 32
    /**
     * Server codes that reject the event itself (unknown name, bad shape, too
     * large). Resending the same body can never succeed, so it is dropped
     * instead of blocking the queue. Network, 5xx/503, auth and rate-limit
     * failures are not listed here and stay queued for the next retry.
     */
    private val PERMANENT_EVENT_REJECTIONS = setOf("desktop_request_invalid", "desktop_request_too_large")

    fun isPermanentEventRejection(error: com.pomp.hskai.core.network.ApiError): Boolean =
        error is com.pomp.hskai.core.network.ApiError.Server && error.code in PERMANENT_EVENT_REJECTIONS
    /** How many bodies each reminder rotates through, so it never reads canned. */
    const val REMINDER_VARIANTS = 3
}
