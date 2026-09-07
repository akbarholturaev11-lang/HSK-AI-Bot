package com.pomp.hskai.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class AndroidOnboardingProfileDto(
    @SerialName("goal") val goal: String = "hsk_exam",
    @SerialName("daily_minutes") val dailyMinutes: Int = 10,
    @SerialName("start_mode") val startMode: String = "lesson_1",
    @SerialName("timezone_offset_minutes") val timezoneOffsetMinutes: Int = 0,
    @SerialName("onboarding_completed") val onboardingCompleted: Boolean? = null,
)

@Serializable
data class AndroidOnboardingStatusDto(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("completed") val completed: Boolean = false,
    @SerialName("level") val level: String = "",
    @SerialName("profile") val profile: AndroidOnboardingProfileDto = AndroidOnboardingProfileDto(),
)

@Serializable
data class AndroidOnboardingRequestDto(
    @SerialName("level") val level: String,
    @SerialName("goal") val goal: String,
    @SerialName("daily_minutes") val dailyMinutes: Int = 10,
    @SerialName("start_mode") val startMode: String = "lesson_1",
    @SerialName("language") val language: String,
    @SerialName("timezone_offset_minutes") val timezoneOffsetMinutes: Int,
    @SerialName("activation_variant") val activationVariant: String = "direct_start_v1",
)

@Serializable
data class AndroidOnboardingCompleteDto(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("profile") val profile: AndroidOnboardingProfileDto? = null,
    @SerialName("level") val level: String = "",
    @SerialName("lesson") val lesson: Int? = null,
    @SerialName("tab") val tab: String = "course",
    @SerialName("placement") val placement: Boolean = false,
    @SerialName("review_only") val reviewOnly: Boolean = false,
    @SerialName("foundation_required") val foundationRequired: Boolean = false,
    @SerialName("error") val error: String? = null,
)
