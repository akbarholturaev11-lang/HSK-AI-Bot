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
)

enum class WidgetMood { UNLINKED, STALE, FOUNDATION, COMPLETE, STREAK, CONTINUE }

/** Seven silent panda reactions used by the daytime widget rotation. */
enum class WidgetReaction {
    CALM,
    WAVE,
    THINKING,
    FOCUS,
    CHEER,
    STREAK,
    CELEBRATE,
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

    /** Resolves art separately from access/progress state. */
    fun reaction(
        mood: WidgetMood,
        now: ZonedDateTime = ZonedDateTime.now(),
    ): WidgetReaction = when (mood) {
        WidgetMood.UNLINKED -> WidgetReaction.CALM
        WidgetMood.STALE -> WidgetReaction.THINKING
        WidgetMood.FOUNDATION -> WidgetReaction.WAVE
        WidgetMood.COMPLETE -> WidgetReaction.CELEBRATE
        WidgetMood.STREAK -> WidgetReaction.STREAK
        WidgetMood.CONTINUE -> daytimeReaction(now)
    }

    private fun daytimeReaction(now: ZonedDateTime): WidgetReaction {
        val minuteOfDay = now.hour * 60 + now.minute
        val start = WidgetPolicy.REACTION_START_HOUR * 60
        val end = WidgetPolicy.REACTION_END_HOUR * 60
        if (minuteOfDay !in start until end) return WidgetReaction.CALM
        val slot = ((minuteOfDay - start) / WidgetPolicy.REACTION_SLOT_MINUTES)
            .coerceIn(0, WidgetReaction.entries.lastIndex)
        return WidgetReaction.entries[slot]
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
