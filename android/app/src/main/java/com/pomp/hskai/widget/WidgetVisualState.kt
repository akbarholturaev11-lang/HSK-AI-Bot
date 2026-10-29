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
    val personalPhase: String? = null,
    val completionReason: String? = null,
)

/** Personal semantics come only from the current authenticated shared projection. */
object WidgetVisualResolver {
    val MILESTONE_DAYS = listOf(7, 30, 50, 100, 365)

    fun resolve(session: WidgetSession, now: ZonedDateTime = ZonedDateTime.now()): WidgetVisual {
        val personal = WidgetPersonalContext.current(session, now)
        val phase = personal?.phase ?: "neutral"
        val state = when (phase) {
            "completed" -> WidgetVisualState.COMPLETED
            "before_study" -> WidgetVisualState.DAY
            "study_time_reached" -> WidgetVisualState.WAITING
            else -> WidgetVisualState.DAY
        }
        val streak = session.snapshot?.streak ?: 0
        val special = if (phase == "completed" &&
            (personal?.goalState == "met" || personal?.planCompleted == true) && streak in MILESTONE_DAYS)
            WidgetSpecialState(WidgetSpecialKind.MILESTONE, streak) else null
        return WidgetVisual(state, variantFor(state, session.epoch, now.toLocalDate().toString()), special,
                            phase, personal?.reason)
    }

    /** Legacy caches lack a confirmed binding and can only render neutral art. */
    fun resolve(snapshot: WidgetSnapshot?, key: String, now: ZonedDateTime = ZonedDateTime.now()): WidgetVisual =
        resolve(WidgetSession(epoch = key, linked = true, snapshot = snapshot), now)

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
