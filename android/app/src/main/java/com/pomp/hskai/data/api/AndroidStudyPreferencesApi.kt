package com.pomp.hskai.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.POST

/** Bearer transport for the Mini App's progressive personalization contract. */
interface AndroidStudyPreferencesApi {
    @POST("api/v3/android/preferences/study")
    suspend fun setStudyPreferences(
        @Header("Authorization") authorization: String,
        @Body body: StudyPreferencesRequestDto,
    ): Response<StudyPreferencesResponseDto>
}

@Serializable
data class StudyPreferencesRequestDto(
    @SerialName("goal") val goal: String? = null,
    @SerialName("daily_minutes") val dailyMinutes: Int? = null,
    @SerialName("preferred_focus") val preferredFocus: String? = null,
)

@Serializable
data class StudyPreferencesResponseDto(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("study_setup") val studySetup: CourseStudySetupDto? = null,
)
