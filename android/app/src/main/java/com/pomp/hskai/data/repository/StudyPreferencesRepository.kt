package com.pomp.hskai.data.repository

import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import com.pomp.hskai.data.api.AndroidStudyPreferencesApi
import com.pomp.hskai.data.api.StudyPreferencesRequestDto
import com.pomp.hskai.domain.model.CourseStudySetup

class StudyPreferencesRepository(
    private val api: AndroidStudyPreferencesApi,
    private val accessToken: suspend () -> ApiResult<String>,
    private val onSessionExpired: suspend () -> Unit = {},
    private val readLastSetupPromptAskedAtMillis: suspend () -> Long? = { null },
    private val writeLastSetupPromptAskedAtMillis: suspend (Long) -> Unit = {},
) {
    suspend fun setGoal(goal: String): ApiResult<CourseStudySetup> = update(goal = goal)

    suspend fun setDailyMinutes(minutes: Int): ApiResult<CourseStudySetup> =
        update(dailyMinutes = minutes)

    suspend fun setPreferredFocus(focus: String): ApiResult<CourseStudySetup> =
        update(preferredFocus = focus)

    suspend fun lastSetupPromptAskedAtMillis(): Long? = try {
        readLastSetupPromptAskedAtMillis()
    } catch (_: Exception) {
        null
    }

    suspend fun markSetupPromptAskedAtMillis(value: Long) {
        try {
            writeLastSetupPromptAskedAtMillis(value)
        } catch (_: Exception) {
            // Prompt persistence is best-effort UI policy; a storage failure
            // must never block learning or mutate server-owned study state.
        }
    }

    private suspend fun update(
        goal: String? = null,
        dailyMinutes: Int? = null,
        preferredFocus: String? = null,
    ): ApiResult<CourseStudySetup> {
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return result
            is ApiResult.Success -> result.value
        }
        val result = apiCall {
            api.setStudyPreferences(
                authorization = "Bearer $token",
                body = StudyPreferencesRequestDto(
                    goal = goal,
                    dailyMinutes = dailyMinutes,
                    preferredFocus = preferredFocus,
                ),
            )
        }
        if (result is ApiResult.Failure) {
            if (result.error is ApiError.SessionExpired) onSessionExpired()
            return result
        }
        val payload = (result as ApiResult.Success).value
        val setup = payload.studySetup
        if (!payload.ok || setup == null) return ApiResult.Failure(ApiError.Unknown)
        return ApiResult.Success(
            CourseStudySetup(
                goal = setup.goal,
                goalChosen = setup.goalChosen,
                dailyMinutes = setup.dailyMinutes,
                preferredFocus = setup.preferredFocus,
                dailyGoalXp = setup.dailyGoalXp,
                dailyGoalIsCustom = setup.dailyGoalIsCustom,
                planSize = setup.planSize,
                pendingGoal = setup.pendingGoal,
                pending = setup.pending,
            )
        )
    }
}
