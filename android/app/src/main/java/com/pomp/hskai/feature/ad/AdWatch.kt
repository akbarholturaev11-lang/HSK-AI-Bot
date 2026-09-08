package com.pomp.hskai.feature.ad

/**
 * How long an ad stays before it may be closed.
 *
 * The server decides the number — it is `skip_after_seconds` on the placement
 * the admin configured — and it also refuses to count a view shorter than the
 * creative's own duration. So the client must never hold the learner for LESS
 * than the server asks, or the ad ends up shown and uncounted.
 *
 * The bounds below mirror `CourseAdService` on the server for exactly that
 * reason. If they change there, they change here.
 */
object AdWatch {

    const val MIN_SECONDS = 5
    const val MAX_SECONDS = 120
    const val DEFAULT_SECONDS = 7

    /**
     * The duration to hold the learner for.
     *
     * [fromServer] is the placement's own `skip_after_seconds`, set by the
     * admin — it wins whenever it is usable. [fromCreative] is the ad's own
     * length, used only when the placement said nothing.
     */
    fun requiredSeconds(fromServer: Int, fromCreative: Int = 0): Int {
        val chosen = when {
            fromServer > 0 -> fromServer
            fromCreative > 0 -> fromCreative
            else -> DEFAULT_SECONDS
        }
        return chosen.coerceIn(MIN_SECONDS, MAX_SECONDS)
    }

    /** Seconds still to wait; never negative, so it can be shown as-is. */
    fun remainingSeconds(elapsedSeconds: Int, requiredSeconds: Int): Int =
        (requiredSeconds - elapsedSeconds).coerceAtLeast(0)

    /** Whether the learner may move on. */
    fun canContinue(elapsedSeconds: Int, requiredSeconds: Int): Boolean =
        requiredSeconds > 0 && elapsedSeconds >= requiredSeconds

    /** Watch progress in 0f..1f, for a countdown ring. */
    fun progress(elapsedSeconds: Int, requiredSeconds: Int): Float {
        if (requiredSeconds <= 0) return 1f
        return (elapsedSeconds.toFloat() / requiredSeconds).coerceIn(0f, 1f)
    }
}
