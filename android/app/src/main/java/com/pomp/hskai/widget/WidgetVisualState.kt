package com.pomp.hskai.widget

import java.time.ZonedDateTime
import java.time.Duration
import java.time.Instant
import java.time.LocalTime
import java.time.temporal.ChronoUnit

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
    val streakTier: Int = 0,
    val streakSecured: Boolean = false,
    val streakAtRisk: Boolean = false,
    val returnBand: Int = 0,
)

/** Personal semantics come only from the current authenticated shared projection. */
object WidgetVisualResolver {
    val MILESTONE_DAYS = listOf(7, 30, 50, 100, 365)

    fun resolve(session: WidgetSession, now: ZonedDateTime = ZonedDateTime.now()): WidgetVisual {
        val access = WidgetStateResolver.resolve(session, now)
        val personal = WidgetPersonalContext.current(session, now)
            ?.takeIf { access == WidgetAccess.ACTIVE || it.phase in setOf("neutral","quiet","paused","unavailable") }
        val phase = personal?.phase ?: "neutral"
        val active = access == WidgetAccess.ACTIVE && personal != null
        val streak = session.snapshot?.streak?.coerceAtLeast(0) ?: 0
        val secured = active && (session.snapshot?.streakRecordedToday == true ||
            personal!!.verifiedTodayXp?.let { it > 0 } == true ||
            phase == "completed" && personal.reason != "course_completed")
        val state = when (phase) {
            "completed" -> WidgetVisualState.COMPLETED
            "before_study" -> WidgetVisualState.DAY
            "study_time_reached" -> {
                // Server validated this personal minute and local day. Quiet,
                // unknown, stale and ambiguous-clock contexts never enter here.
                val due = now.toLocalDate().atTime(LocalTime.parse(personal!!.timeLocal)).atZone(now.zone)
                val end = now.toLocalDate().plusDays(1).atStartOfDay(now.zone)
                val span = Duration.between(due, end).toMillis().coerceAtLeast(1)
                val elapsed = Duration.between(due, now).toMillis().coerceAtLeast(0).toDouble() / span
                when {
                    secured || streak == 0 -> WidgetVisualState.WAITING
                    elapsed >= .85 -> WidgetVisualState.CRITICAL
                    elapsed >= .66 -> WidgetVisualState.LATE
                    elapsed >= .33 -> WidgetVisualState.EVENING
                    else -> WidgetVisualState.WAITING
                }
            }
            else -> WidgetVisualState.DAY
        }
        val age = personal?.lastObservedStudyAt?.let {
            ChronoUnit.DAYS.between(Instant.parse(it).atZone(now.zone).toLocalDate(), now.toLocalDate())
        }
        val returning = active && !secured && streak == 0 && phase in setOf("before_study", "study_time_reached")
        val returnBand = when {
            !returning || age == null -> 0
            age >= 90 -> 3
            age >= 30 -> 2
            age >= 7 -> 1
            else -> 0
        }
        val special = if (phase == "completed" &&
            (personal?.goalState == "met" || personal?.planCompleted == true) && streak in MILESTONE_DAYS)
            WidgetSpecialState(WidgetSpecialKind.MILESTONE, streak) else null
        val tier = when { !active || streak == 0 -> 0; streak <= 2 -> 1; streak < 30 -> 2; else -> 3 }
        return WidgetVisual(state, variantFor(state, session.epoch, now.toLocalDate().toString()), special,
            phase, personal?.reason, tier, secured,
            active && streak > 0 && !secured && phase == "study_time_reached", returnBand)
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
