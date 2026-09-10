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
        if (snapshot.streak > 0 && now.hour >= WidgetPolicy.EVENING_HOUR) return WidgetMood.STREAK
        return WidgetMood.CONTINUE
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
