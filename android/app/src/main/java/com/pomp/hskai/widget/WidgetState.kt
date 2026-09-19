package com.pomp.hskai.widget

import java.time.ZonedDateTime
import kotlinx.serialization.Serializable

/** No credentials, identifiers, lesson content or access grants in this cache. */
@Serializable
data class WidgetSnapshot(
    val fetchedAtMillis: Long,
    val localDay: String,
    val zoneId: String,
    val level: String,
    val lessonOrder: Int?,
    val xp: Int,
    val streak: Int,
    val dayComplete: Boolean,
    val foundationRequired: Boolean,
    /**
     * Today's progress against the server's own daily goal.
     *
     * Both default, so a cache written by an older build still decodes — a
     * failed decode would drop the stored session and show "link your
     * account" to someone who is linked. A zero goal means "not known", and
     * nothing claims progress from it.
     */
    val dailyXp: Int = 0,
    val goalXp: Int = 0,
)

enum class WidgetMood { UNLINKED, STALE, FOUNDATION, COMPLETE, STREAK, CONTINUE }

/** Silent panda reactions. Art only; access and progress live in [WidgetMood]. */
enum class WidgetReaction {
    CALM,
    WAVE,
    THINKING,
    FOCUS,
    CHEER,
    STREAK,
    CELEBRATE,
    WORRIED,
    SLEEPY;

    companion object {
        /** The seven daytime slots, in order. Night and risk art are not in it. */
        val DAYTIME_ROTATION = listOf(CALM, WAVE, THINKING, FOCUS, CHEER, STREAK, CELEBRATE)
    }
}

/**
 * Which line the widget asks with.
 *
 * The wording stays in resources and the choice stays out of the layout, so a
 * copy change is a string edit and a rule change is this file.
 */
sealed interface WidgetPrompt {
    /** Fall back to the title of the access/progress mood. */
    data object Mood : WidgetPrompt

    /** The day is running out, nothing earned yet, and there is a run to lose. */
    data object StreakAtRisk : WidgetPrompt

    /** Today is under way and the goal is still within reach. */
    data class GoalLeft(val xp: Int) : WidgetPrompt
}

object WidgetStateResolver {
    fun resolve(
        linked: Boolean,
        snapshot: WidgetSnapshot?,
        now: ZonedDateTime = ZonedDateTime.now(),
    ): WidgetMood {
        if (!linked) return WidgetMood.UNLINKED
        if (snapshot == null) return WidgetMood.STALE
        val age = now.toInstant().toEpochMilli() - snapshot.fetchedAtMillis
        if (age < 0 || age >= WidgetPolicy.STALE_AFTER_MILLIS ||
            snapshot.localDay != now.toLocalDate().toString() ||
            snapshot.zoneId != now.zone.id
        ) return WidgetMood.STALE
        if (snapshot.foundationRequired) return WidgetMood.FOUNDATION
        if (snapshot.dayComplete) return WidgetMood.COMPLETE
        // A streak is useful encouragement throughout the day. It is not an
        // evening-only reminder, so there is no morning/evening mood branch.
        if (snapshot.streak > 0) return WidgetMood.STREAK
        return WidgetMood.CONTINUE
    }

    /**
     * Resolves art separately from access/progress state.
     *
     * Without a snapshot the art is the same as before: time of day only. With
     * one it follows the learner — asking when the day is running out, resting
     * at night, cheering once the goal is half done.
     */
    fun reaction(
        mood: WidgetMood,
        snapshot: WidgetSnapshot? = null,
        now: ZonedDateTime = ZonedDateTime.now(),
    ): WidgetReaction = when (mood) {
        WidgetMood.UNLINKED -> WidgetReaction.CALM
        WidgetMood.STALE -> WidgetReaction.THINKING
        WidgetMood.FOUNDATION -> WidgetReaction.WAVE
        WidgetMood.COMPLETE -> WidgetReaction.CELEBRATE
        WidgetMood.STREAK -> progressReaction(snapshot, now, WidgetReaction.STREAK)
        WidgetMood.CONTINUE -> progressReaction(snapshot, now, daytimeReaction(now))
    }

    /** Picks the line; the strings themselves are resources. */
    fun prompt(
        mood: WidgetMood,
        snapshot: WidgetSnapshot?,
        now: ZonedDateTime = ZonedDateTime.now(),
    ): WidgetPrompt {
        if (mood != WidgetMood.STREAK && mood != WidgetMood.CONTINUE || snapshot == null) {
            return WidgetPrompt.Mood
        }
        if (snapshot.streak > 0 && atRisk(snapshot, now)) return WidgetPrompt.StreakAtRisk
        val left = snapshot.goalXp - snapshot.dailyXp
        // Only once something has been earned today. "20 XP left" before the
        // first lesson is the goal restated, not progress.
        if (snapshot.goalXp > 0 && snapshot.dailyXp > 0 && left > 0) return WidgetPrompt.GoalLeft(left)
        return WidgetPrompt.Mood
    }

    private fun progressReaction(
        snapshot: WidgetSnapshot?,
        now: ZonedDateTime,
        fallback: WidgetReaction,
    ): WidgetReaction = when {
        atRisk(snapshot, now) -> WidgetReaction.WORRIED
        asleep(now) -> WidgetReaction.SLEEPY
        halfway(snapshot) -> WidgetReaction.CHEER
        else -> fallback
    }

    /** The day is nearly over and nothing at all has been earned yet. */
    private fun atRisk(snapshot: WidgetSnapshot?, now: ZonedDateTime): Boolean =
        snapshot != null && !snapshot.dayComplete && snapshot.dailyXp <= 0 &&
            now.hour >= WidgetPolicy.RISK_HOUR && now.hour < WidgetPolicy.NIGHT_HOUR

    /** Late enough that asking is nagging; the panda rests instead. */
    private fun asleep(now: ZonedDateTime): Boolean =
        now.hour >= WidgetPolicy.NIGHT_HOUR || now.hour < WidgetPolicy.DAWN_HOUR

    /** Past half of today's goal. An unknown goal never claims progress. */
    private fun halfway(snapshot: WidgetSnapshot?): Boolean {
        val goal = snapshot?.goalXp ?: return false
        val done = snapshot.dailyXp
        if (goal <= 0 || done <= 0) return false
        return done * 100 >= goal * WidgetPolicy.CHEER_PERCENT
    }

    private fun daytimeReaction(now: ZonedDateTime): WidgetReaction {
        val minuteOfDay = now.hour * 60 + now.minute
        val start = WidgetPolicy.REACTION_START_HOUR * 60
        val end = WidgetPolicy.REACTION_END_HOUR * 60
        if (minuteOfDay !in start until end) return WidgetReaction.CALM
        val slot = ((minuteOfDay - start) / WidgetPolicy.REACTION_SLOT_MINUTES)
            .coerceIn(0, WidgetReaction.DAYTIME_ROTATION.lastIndex)
        return WidgetReaction.DAYTIME_ROTATION[slot]
    }
}

@Serializable
data class AndroidWidgetEvent(
    val event_name: String,
    val event_id: String = java.util.UUID.randomUUID().toString(),
)

@Serializable
data class WidgetSession(
    val epoch: String = java.util.UUID.randomUUID().toString(),
    val linked: Boolean = false,
    val snapshot: WidgetSnapshot? = null,
    val reminderEnabled: Boolean = false,
    val lastReminderDay: String? = null,
    val onboardingOffered: Boolean = false,
    val events: List<AndroidWidgetEvent> = emptyList(),
)
