package com.pomp.hskai.feature.ad

/**
 * How long an ad must play before it counts.
 *
 * The server measures the real elapsed time between opening the attempt and
 * reporting the view, and refuses anything shorter. So the client must never
 * require LESS than the server does — the learner would press "continue" on a
 * view the server then throws away, and the section would stay shut with no
 * explanation.
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
     * [fromAttempt] is what the server bound to this attempt and is therefore
     * the number it will check against — it wins whenever it is usable.
     * [fromCreative] is the listing's own duration, used only when the attempt
     * response carried nothing.
     */
    fun requiredSeconds(fromAttempt: Int, fromCreative: Int = 0): Int {
        val chosen = when {
            fromAttempt > 0 -> fromAttempt
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
