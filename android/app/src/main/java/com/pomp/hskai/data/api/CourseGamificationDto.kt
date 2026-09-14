package com.pomp.hskai.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Exact CourseGamificationService snapshot returned after a Course v3 completion.
 * Keeping this typed prevents native clients from silently dropping Mini App
 * celebration signals such as XP and streak updates.
 */
@Serializable
data class CourseGamificationDto(
    @SerialName("xp") val xp: Int = 0,
    @SerialName("awarded_xp") val awardedXp: Int = 0,
    @SerialName("duplicate") val duplicate: Boolean = false,
    @SerialName("streak") val streak: Int = 0,
    @SerialName("longest_streak") val longestStreak: Int = 0,
    @SerialName("previous_streak") val previousStreak: Int = 0,
    @SerialName("streak_updated") val streakUpdated: Boolean = false,
    @SerialName("streak_reset") val streakReset: Boolean = false,
    @SerialName("activity_date") val activityDate: String? = null,
    @SerialName("last_activity_date") val lastActivityDate: String? = null,
    @SerialName("local_date") val localDate: String? = null,
    @SerialName("week_start") val weekStart: String? = null,
    @SerialName("week_activity_dates") val weekActivityDates: List<String> = emptyList(),
    @SerialName("league") val league: String = "",
    @SerialName("weekly_xp") val weeklyXp: Int = 0,
    @SerialName("daily_xp") val dailyXp: Int = 0,
    @SerialName("league_points") val leaguePoints: Int = 0,
    @SerialName("weekly_reset_day") val weeklyResetDay: String = "monday",
    @SerialName("weekly_reset_at") val weeklyResetAt: String? = null,
    @SerialName("weekly_reset_seconds") val weeklyResetSeconds: Int = 0,
    @SerialName("energy") val energy: CourseEnergyDto = CourseEnergyDto(),
    @SerialName("reward_chest") val rewardChest: RewardChestDto? = null,
)

@Serializable
data class CourseEnergyDto(
    @SerialName("current") val current: Int = 0,
    @SerialName("max") val max: Int = 5,
    @SerialName("blocks_study") val blocksStudy: Boolean = false,
)
