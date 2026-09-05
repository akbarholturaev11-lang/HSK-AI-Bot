package com.pomp.hskai.domain.model

/** Where the learner stands on a node of the path. */
enum class LessonStatus { DONE, CURRENT, LOCKED }

/**
 * Why a lesson can or cannot be started, as decided by the server.
 *
 * The distinction between [NotReached] and [PremiumLocked] matters: a lesson
 * inside the free allowance that simply has not been reached yet must never
 * show a paywall. Only [showsPaywall] destinations may offer a subscription.
 */
sealed interface LessonAccess {
    data object Open : LessonAccess
    data object HalfPreview : LessonAccess
    data object PremiumLocked : LessonAccess
    data object NotReached : LessonAccess

    val showsPaywall: Boolean
        get() = this is HalfPreview || this is PremiumLocked
}

data class CourseLesson(
    val order: Int,
    val sourceLesson: Int,
    val part: Int,
    val partCount: Int,
    val isCheckpoint: Boolean,
    val status: LessonStatus,
    val access: LessonAccess,
    val hanziPreview: String,
    val pinyinPreview: String,
    val subtitle: String,
) {
    val isCurrent: Boolean get() = status == LessonStatus.CURRENT
}

data class CourseMilestone(
    val title: String,
    val status: String,
)

data class CourseUnit(
    val number: Int,
    val title: String,
    val lessons: List<CourseLesson>,
    val isLocked: Boolean = false,
    val milestone: CourseMilestone? = null,
)

/** Exact server snapshot for the course reward chest. */
data class RewardChest(
    val ready: Boolean,
    val progress: Int,
    val nextXp: Int,
)

data class CourseProgress(
    val completedLessons: Int,
    val xp: Int,
    val dailyXp: Int,
    val weeklyXp: Int,
    val streak: Int,
    val longestStreak: Int,
    val league: String,
    val weekActivityDates: List<String>,
    val localDate: String?,
    val weekStart: String?,
    val rewardChest: RewardChest?,
) {
    val hasRewardChest: Boolean get() = rewardChest?.ready == true
}

data class CourseUser(
    val name: String,
    val initials: String,
    val isPaid: Boolean,
    val referralCode: String,
)

/** Server-owned daily-plan access state. Android only renders it. */
enum class TodayTaskAccess { OPEN, AD, LOCKED }

data class TodayTask(
    val type: String,
    val ref: String?,
    val skill: String?,
    val role: String?,
    val done: Boolean,
    val access: TodayTaskAccess,
    val available: Boolean,
)

data class CourseToday(
    val goalXp: Int,
    val doneXp: Int,
    val streak: Int,
    val total: Int,
    val done: Int,
    val complete: Boolean,
    val tasks: List<TodayTask>,
    val level: String,
    val localDay: String,
)

data class CourseMap(
    val level: String,
    val units: List<CourseUnit>,
    val progress: CourseProgress,
    val user: CourseUser,
    val notificationsEnabled: Boolean,
    val today: CourseToday? = null,
) {
    val lessons: List<CourseLesson> get() = units.flatMap { it.lessons }

    /** Total mini-parts for this level, from the server. Never hardcoded. */
    val totalLessons: Int get() = lessons.size

    /**
     * The node the learner should open next. This is the server's `current`
     * node, which may legitimately be a half preview or a premium lock.
     */
    val currentLesson: CourseLesson?
        get() = lessons.firstOrNull { it.isCurrent }
            ?: lessons.firstOrNull { it.status != LessonStatus.DONE }

    val unitOf: (CourseLesson) -> CourseUnit?
        get() = { lesson -> units.firstOrNull { unit -> lesson in unit.lessons } }
}
