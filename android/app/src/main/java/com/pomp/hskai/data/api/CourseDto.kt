package com.pomp.hskai.data.api

import com.pomp.hskai.core.i18n.AppLanguage
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Course v3 ships its user-facing strings as a `{uz, ru, tj}` object.
 *
 * `tj` is the backend code for Tajik; the Android resource qualifier `tg` never
 * appears in payloads.
 */
@Serializable
data class LocalizedText(
    @SerialName("uz") val uz: String = "",
    @SerialName("ru") val ru: String = "",
    @SerialName("tj") val tj: String = "",
) {
    fun forLanguage(language: AppLanguage): String = when (language) {
        AppLanguage.UZBEK -> uz.ifBlank { ru }
        AppLanguage.RUSSIAN -> ru.ifBlank { uz }
        AppLanguage.TAJIK -> tj.ifBlank { ru }
    }.ifBlank { uz }
}

@Serializable
data class CourseMapDto(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("level") val level: String = "hsk1",
    @SerialName("units") val units: List<CourseUnitDto> = emptyList(),
    @SerialName("progress") val progress: CourseProgressDto = CourseProgressDto(),
    @SerialName("user") val user: CourseUserDto = CourseUserDto(),
    @SerialName("notify") val notify: CourseNotifyDto = CourseNotifyDto(),
)

@Serializable
data class CourseUnitDto(
    @SerialName("no") val number: Int = 0,
    @SerialName("title") val title: LocalizedText = LocalizedText(),
    @SerialName("lessons") val lessons: List<CourseLessonDto> = emptyList(),
)

@Serializable
data class CourseLessonDto(
    @SerialName("n") val order: Int = 0,
    @SerialName("src") val sourceLesson: Int = 0,
    @SerialName("part") val part: Int = 0,
    @SerialName("part_count") val partCount: Int = 0,
    @SerialName("checkpoint") val checkpoint: Boolean = false,
    @SerialName("status") val status: String = "locked",
    @SerialName("zh") val hanzi: String = "",
    @SerialName("py") val pinyin: String = "",
    @SerialName("tr") val subtitle: LocalizedText = LocalizedText(),
    // Server-owned access decision. The client renders it and never invents it.
    @SerialName("completion_allowed") val completionAllowed: Boolean = false,
    @SerialName("completion_error") val completionError: String? = null,
    @SerialName("preview_half") val previewHalf: Boolean = false,
    @SerialName("locked_premium") val lockedPremium: Boolean = false,
)

@Serializable
data class CourseProgressDto(
    @SerialName("completed") val completed: Int = 0,
    @SerialName("xp") val xp: Int = 0,
    @SerialName("daily_xp") val dailyXp: Int = 0,
    @SerialName("weekly_xp") val weeklyXp: Int = 0,
    @SerialName("streak") val streak: Int = 0,
    @SerialName("longest_streak") val longestStreak: Int = 0,
    @SerialName("league") val league: String = "",
    @SerialName("week_activity_dates") val weekActivityDates: List<String> = emptyList(),
    @SerialName("local_date") val localDate: String? = null,
    @SerialName("week_start") val weekStart: String? = null,
    @SerialName("reward_chest") val rewardChest: RewardChestDto? = null,
)

@Serializable
data class RewardChestDto(
    @SerialName("available") val available: Boolean = false,
)

@Serializable
data class CourseUserDto(
    @SerialName("name") val name: String = "",
    @SerialName("avatar") val avatar: String = "",
    @SerialName("language") val language: String = "ru",
    @SerialName("is_paid") val isPaid: Boolean = false,
    @SerialName("referral_code") val referralCode: String = "",
)

@Serializable
data class CourseNotifyDto(
    @SerialName("enabled") val enabled: Boolean = true,
)

@Serializable
data class CourseCompleteRequest(
    @SerialName("lesson_order") val lessonOrder: Int,
    /** Stable per-attempt id, `android:<uuid>`, so retries stay idempotent. */
    @SerialName("event_id") val eventId: String,
    @SerialName("mistakes") val mistakes: List<CourseMistakeDto> = emptyList(),
)

@Serializable
data class CourseMistakeDto(
    @SerialName("material_ref") val materialRef: String,
    @SerialName("selected_index") val selectedIndex: Int? = null,
    @SerialName("selected_answer") val selectedAnswer: String? = null,
    @SerialName("selected_tokens") val selectedTokens: List<String>? = null,
    @SerialName("selected_left_index") val selectedLeftIndex: Int? = null,
    @SerialName("selected_right_index") val selectedRightIndex: Int? = null,
)

@Serializable
data class CourseCompleteResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("completed_lesson") val completedLesson: Int = 0,
    @SerialName("next_lesson") val nextLesson: Int? = null,
    @SerialName("completed_lessons_count") val completedLessonsCount: Int = 0,
    @SerialName("duplicate") val duplicate: Boolean = false,
)

@Serializable
data class LanguageRequest(
    @SerialName("language") val language: String,
)

@Serializable
data class OkResponse(
    @SerialName("ok") val ok: Boolean = false,
)
