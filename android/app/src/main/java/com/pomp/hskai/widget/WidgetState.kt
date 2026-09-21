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

/**
 * Whether the widget may speak for this learner, and nothing else.
 *
 * It never decides how the day is going: that is [WidgetVisualResolver], the
 * one engine that produces a [WidgetVisualState]. Keeping the two apart is
 * what stops an expired cache from being read as a mood.
 */
object WidgetStateResolver {
    fun resolve(
        linked: Boolean,
        snapshot: WidgetSnapshot?,
        now: ZonedDateTime = ZonedDateTime.now(),
    ): WidgetAccess {
        if (!linked) return WidgetAccess.UNLINKED
        if (snapshot == null) return WidgetAccess.STALE
        val age = now.toInstant().toEpochMilli() - snapshot.fetchedAtMillis
        if (age < 0 || age >= WidgetPolicy.STALE_AFTER_MILLIS ||
            snapshot.localDay != now.toLocalDate().toString() ||
            snapshot.zoneId != now.zone.id
        ) return WidgetAccess.STALE
        if (snapshot.foundationRequired) return WidgetAccess.FOUNDATION
        return WidgetAccess.ACTIVE
    }
}

@Serializable
data class AndroidWidgetEvent(
    val event_name: String,
    val event_id: String = java.util.UUID.randomUUID().toString(),
)

@Serializable
data class WidgetSession(
    /**
     * A UUID this install made for itself on link. It guards late responses
     * from a previous account, and it is also the stable key the panda's
     * variant is hashed from — no account id is stored to get one.
     */
    val epoch: String = java.util.UUID.randomUUID().toString(),
    val linked: Boolean = false,
    val snapshot: WidgetSnapshot? = null,
    val reminderEnabled: Boolean = false,
    val lastReminderDay: String? = null,
    val onboardingOffered: Boolean = false,
    val events: List<AndroidWidgetEvent> = emptyList(),
)
