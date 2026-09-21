package com.pomp.hskai.widget

import java.time.ZonedDateTime

/**
 * Operational projection: can the widget speak for this learner at all.
 *
 * It answers access and freshness only. What the panda feels is
 * [WidgetVisualState] and nothing here decides that, so an expired cache can
 * never be mistaken for a mood.
 */
enum class WidgetAccess { UNLINKED, STALE, FOUNDATION, ACTIVE }

/**
 * The canonical visual state. There is exactly one engine that produces it.
 *
 * [urgency] rises through an unfinished day, so a caller can compare two
 * states without re-reading the clock. [variants] is how many drawings the
 * state owns; the catalog in [WidgetArt] must match it exactly.
 */
enum class WidgetVisualState(val urgency: Int, val variants: Int) {
    MORNING(urgency = 0, variants = 3),
    DAY(urgency = 1, variants = 3),
    WAITING(urgency = 2, variants = 4),
    EVENING(urgency = 3, variants = 4),
    LATE(urgency = 4, variants = 4),
    CRITICAL(urgency = 5, variants = 5),
    COMPLETED(urgency = 0, variants = 5),
}

/**
 * Rare moments that outrank both a finished day and the clock.
 *
 * Only [MILESTONE] has a signal today: a finished day whose server-owned
 * streak has landed on a round number. The other four are named so the
 * resolver, the art map and the priority order can grow without a second
 * migration — nothing emits them, because no local or server field reports
 * them and inventing one would put a lie on the home screen.
 */
enum class WidgetSpecialKind { MILESTONE, STREAK_BROKEN, COMEBACK, NEW_USER, SEASONAL }

/** [days] carries the milestone reached; it is zero for the other kinds. */
data class WidgetSpecialState(val kind: WidgetSpecialKind, val days: Int = 0)

/** What the widget draws: one state, one of its variants, and why. */
data class WidgetVisual(
    val state: WidgetVisualState,
    val variant: Int,
    val special: WidgetSpecialState? = null,
)

/**
 * Time and today's completion decide the panda. Nothing else does.
 *
 * The order is fixed: a special moment, then a finished day, then the local
 * clock. A finished day therefore stays calm at 23:30 instead of escalating,
 * and an unfinished one keeps asking at 23:30 instead of going to sleep.
 */
object WidgetVisualResolver {
    /** Local-hour boundaries, first hour inclusive. The gap 00:00–04:59 is the new day. */
    const val MORNING_HOUR = 5
    const val DAY_HOUR = 10
    const val WAITING_HOUR = 14
    const val EVENING_HOUR = 18
    const val LATE_HOUR = 20
    const val CRITICAL_HOUR = 22

    /** Round streak days worth marking. The server owns the count; this only reads it. */
    val MILESTONE_DAYS = listOf(7, 30, 50, 100, 365)

    /**
     * The state the wall clock alone asks for, in the learner's own zone.
     *
     * 00:00–04:59 is the reset window: the local day has turned over, so it
     * opens gently rather than carrying yesterday's [WidgetVisualState.CRITICAL]
     * into a day that has not been missed yet.
     */
    fun timeState(now: ZonedDateTime): WidgetVisualState = when (now.hour) {
        in MORNING_HOUR until DAY_HOUR -> WidgetVisualState.MORNING
        in DAY_HOUR until WAITING_HOUR -> WidgetVisualState.DAY
        in WAITING_HOUR until EVENING_HOUR -> WidgetVisualState.WAITING
        in EVENING_HOUR until LATE_HOUR -> WidgetVisualState.EVENING
        in LATE_HOUR until CRITICAL_HOUR -> WidgetVisualState.LATE
        in CRITICAL_HOUR..23 -> WidgetVisualState.CRITICAL
        else -> WidgetVisualState.MORNING
    }

    /**
     * The only special moment with a real signal behind it.
     *
     * A milestone needs the day to be finished, because the streak the server
     * reports is the run this finished day belongs to. Reading it on an
     * unfinished day would celebrate yesterday.
     */
    fun special(snapshot: WidgetSnapshot?): WidgetSpecialState? {
        val streak = snapshot?.takeIf { it.dayComplete }?.streak ?: return null
        if (streak !in MILESTONE_DAYS) return null
        return WidgetSpecialState(WidgetSpecialKind.MILESTONE, streak)
    }

    /**
     * SPECIAL > COMPLETED > time. [key] is a stable per-install value, never
     * an identifier: see [variantFor].
     */
    fun resolve(
        snapshot: WidgetSnapshot?,
        key: String,
        now: ZonedDateTime = ZonedDateTime.now(),
    ): WidgetVisual {
        val special = special(snapshot)
        val state = when {
            special != null -> WidgetVisualState.COMPLETED
            snapshot?.dayComplete == true -> WidgetVisualState.COMPLETED
            else -> timeState(now)
        }
        return WidgetVisual(state, variantFor(state, key, now.toLocalDate().toString()), special)
    }

    /**
     * Which drawing of the state to show today.
     *
     * The widget re-renders on every refresh, every clock tick and every
     * launcher restart, so a random pick would make the panda flicker between
     * faces. This hashes instead: one local date plus one state plus one
     * install always lands on the same variant, and the drawing only moves
     * when the state or the day does.
     *
     * [key] is [WidgetSession.epoch] — a UUID this install made for itself on
     * link. No account id ever enters the widget store, and this does not add
     * one.
     */
    fun variantFor(state: WidgetVisualState, key: String, localDate: String): Int =
        (fnv1a("$key|$localDate|${state.name}") % state.variants).toInt()

    /**
     * FNV-1a, 32 bits, written out rather than borrowed.
     *
     * `String.hashCode` is stable on today's JVM but is not promised to be,
     * and a variant that moved after a process restart would look like a bug
     * on someone's home screen.
     */
    private fun fnv1a(value: String): Long {
        var hash = 2_166_136_261L
        for (byte in value.encodeToByteArray()) {
            hash = hash xor (byte.toLong() and 0xFF)
            hash = (hash * 16_777_619L) and 0xFFFFFFFFL
        }
        return hash
    }
}
