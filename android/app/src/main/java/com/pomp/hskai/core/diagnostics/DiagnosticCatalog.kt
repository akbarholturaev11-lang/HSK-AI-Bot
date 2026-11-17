package com.pomp.hskai.core.diagnostics

/**
 * Codes the Android reporter may send (`diag.v1`, unified-error-monitoring D1/D5).
 *
 * Every `code = "…"` literal in this file is checked by
 * `scripts/check_analytics_coverage.py` against the server catalog
 * (`app/services/monitoring/catalog.py`): a code the server does not know fails
 * CI. Expected outcomes — offline, timeout, 4xx, limit, paywall, a learner's own
 * close — have no code here, so they cannot be reported.
 */
enum class DiagFeature(val code: String) {
    APP_SHELL(code = "app_shell"),
    AUTH_SESSION(code = "auth_session"),
    ONBOARDING_ACTIVATION(code = "onboarding_activation"),
    LESSONS(code = "lessons"),
    PRACTICE(code = "practice"),
    VOICE_PRACTICE(code = "voice_practice"),
    LEARNING_REWARDS(code = "learning_rewards"),
    SUBSCRIPTION_ENTRIES(code = "subscription_entries"),
    CHECKOUT_PAYMENTS(code = "checkout_payments"),
    MONITORING(code = "monitoring"),
}

enum class DiagFailure(val code: String) {
    CRASH_UNCAUGHT(code = "crash_uncaught"),
    CRASH_NATIVE(code = "crash_native"),
    ANR(code = "anr"),
    API_5XX(code = "api_5xx"),
    API_DECODE(code = "api_decode"),
    LIVE_SESSION_FAILED(code = "live_session_failed"),
    QUEUE_DROPPED(code = "queue_dropped"),
}

enum class DiagSite(val code: String) {
    // Tagged API calls (priority flows)
    LOGIN(code = "login"),
    SESSION_RESTORE(code = "session_restore"),
    ONBOARDING(code = "onboarding"),
    LESSON_OPEN(code = "lesson_open"),
    LESSON_COMPLETE(code = "lesson_complete"),
    PRACTICE(code = "practice"),
    PROGRESS(code = "progress"),
    SUBSCRIPTION(code = "subscription"),
    PAYMENT(code = "payment"),
    HANDOFF(code = "handoff"),

    // Process, crash buckets and self-checks
    APP(code = "app"),
    PROCESS(code = "process"),
    QUEUE(code = "queue"),
    EXC_STATE(code = "exc_state"),
    EXC_ARGUMENT(code = "exc_argument"),
    EXC_NULL(code = "exc_null"),
    EXC_INDEX(code = "exc_index"),
    EXC_MEMORY(code = "exc_memory"),
    EXC_SECURITY(code = "exc_security"),
    EXC_NETWORK(code = "exc_network"),
    EXC_SERIALIZATION(code = "exc_serialization"),
    EXC_OTHER(code = "exc_other"),

    // Live voice: client-side reasons only
    LIVE_CONNECTION_LOST(code = "live_connection_lost"),
    LIVE_MESSAGE_INVALID(code = "live_message_invalid"),
    LIVE_MESSAGE_TOO_LARGE(code = "live_message_too_large"),
    LIVE_SEND_FAILED(code = "live_send_failed"),
}

/** Which feature and site a tagged API call's 5xx or decode failure belongs to. */
data class DiagTag(val feature: DiagFeature, val site: DiagSite)

/** The tags used by the priority flows. */
object DiagTags {
    val LOGIN = DiagTag(DiagFeature.AUTH_SESSION, DiagSite.LOGIN)
    val SESSION_RESTORE = DiagTag(DiagFeature.AUTH_SESSION, DiagSite.SESSION_RESTORE)
    val ONBOARDING = DiagTag(DiagFeature.ONBOARDING_ACTIVATION, DiagSite.ONBOARDING)
    val LESSON_OPEN = DiagTag(DiagFeature.LESSONS, DiagSite.LESSON_OPEN)
    val LESSON_COMPLETE = DiagTag(DiagFeature.LESSONS, DiagSite.LESSON_COMPLETE)
    val PROGRESS = DiagTag(DiagFeature.LESSONS, DiagSite.PROGRESS)
    val PRACTICE = DiagTag(DiagFeature.PRACTICE, DiagSite.PRACTICE)
    val SUBSCRIPTION = DiagTag(DiagFeature.SUBSCRIPTION_ENTRIES, DiagSite.SUBSCRIPTION)
    val HANDOFF = DiagTag(DiagFeature.SUBSCRIPTION_ENTRIES, DiagSite.HANDOFF)
    val PAYMENT = DiagTag(DiagFeature.CHECKOUT_PAYMENTS, DiagSite.PAYMENT)
}

/**
 * `LiveVoiceSocket.fail(reason)` reports only these client-side reasons.
 * Server-sent codes (limits, quota), a learner's close, connect failures and
 * backpressure are expected outcomes and are never reported.
 */
val REPORTED_LIVE_REASONS: Map<String, DiagSite> = mapOf(
    "live_connection_lost" to DiagSite.LIVE_CONNECTION_LOST,
    "live_message_invalid" to DiagSite.LIVE_MESSAGE_INVALID,
    "live_message_too_large" to DiagSite.LIVE_MESSAGE_TOO_LARGE,
    "live_send_failed" to DiagSite.LIVE_SEND_FAILED,
)

/** A crash bucket: a fixed site plus a safe category, never the message or stack. */
internal fun crashBucket(error: Throwable): Pair<DiagSite, String> = when (error) {
    is OutOfMemoryError -> DiagSite.EXC_MEMORY to "memory"
    is SecurityException -> DiagSite.EXC_SECURITY to "security"
    is NullPointerException -> DiagSite.EXC_NULL to "null"
    is IndexOutOfBoundsException, is NoSuchElementException -> DiagSite.EXC_INDEX to "index"
    // Before IllegalArgumentException: SerializationException extends it.
    is kotlinx.serialization.SerializationException -> DiagSite.EXC_SERIALIZATION to "serialization"
    is IllegalStateException -> DiagSite.EXC_STATE to "state"
    is IllegalArgumentException -> DiagSite.EXC_ARGUMENT to "argument"
    is java.io.IOException -> DiagSite.EXC_NETWORK to "network"
    else -> DiagSite.EXC_OTHER to "other"
}
