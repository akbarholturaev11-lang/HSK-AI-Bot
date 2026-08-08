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
    /** Completable now. */
    data object Open : LessonAccess

    /** Visible as a half preview, but the preview cannot finish the lesson. */
    data object HalfPreview : LessonAccess

    /** Premium content the learner has not paid for. */
    data object PremiumLocked : LessonAccess

    /** Free content that is simply further down the path. */
    data object NotReached : LessonAccess

    val showsPaywall: Boolean
        get() = this is HalfPreview || this is PremiumLocked
}

data class CourseLesson(
    /** Flat mini-part number within the level. Never derived on the client. */
    val order: Int,
    /** The HSK textbook lesson this part belongs to. */
    val sourceLesson: Int,
    val part: Int,
    val partCount: Int,
    val isCheckpoint: Boolean,
    val status: LessonStatus,
    val access: LessonAccess,
    /** Preview of the new words, e.g. "你 · 好 · 您". */
    val hanziPreview: String,
    val pinyinPreview: String,
    val subtitle: String,
) {
    val isCurrent: Boolean get() = status == LessonStatus.CURRENT
}

data class CourseUnit(
    val number: Int,
    val title: String,
    val lessons: List<CourseLesson>,
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
    val hasRewardChest: Boolean,
)

data class CourseUser(
    val name: String,
    val initials: String,
    val isPaid: Boolean,
    val referralCode: String,
)

data class CourseMap(
    val level: String,
    val units: List<CourseUnit>,
    val progress: CourseProgress,
    val user: CourseUser,
    val notificationsEnabled: Boolean,
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
