package com.pomp.hskai.data.repository

import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import com.pomp.hskai.data.api.AndroidOnboardingApi
import com.pomp.hskai.data.api.AndroidOnboardingCompleteDto
import com.pomp.hskai.data.api.AndroidOnboardingRequestDto
import com.pomp.hskai.data.api.AndroidOnboardingStatusDto
import java.util.TimeZone
import kotlinx.coroutines.withTimeoutOrNull

/**
 * Thin native transport around the canonical Course Mini App onboarding.
 * All course decisions remain server-owned; Android only sends the choices.
 */
class OnboardingRepository(
    private val api: AndroidOnboardingApi,
    private val accessToken: suspend () -> ApiResult<String>,
    private val onSessionExpired: suspend () -> Unit = {},
    private val timezoneOffsetMinutes: () -> Int = {
        TimeZone.getDefault().getOffset(System.currentTimeMillis()) / 60_000
    },
) {
    suspend fun status(): ApiResult<AndroidOnboardingStatusDto> {
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return result
            is ApiResult.Success -> result.value
        }
        val result = apiCall { api.status("Bearer $token") }
        if (result is ApiResult.Failure) notifySessionExpired(result.error)
        return result
    }

    suspend fun complete(
        level: String,
        goal: String,
        language: String,
        dailyMinutes: Int = 10,
        startMode: String = "lesson_1",
    ): ApiResult<AndroidOnboardingCompleteDto> {
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return result
            is ApiResult.Success -> result.value
        }
        // Mini App aborts onboarding save after 12 seconds and exposes retry.
        // Keep the native client on the same interaction contract instead of
        // inheriting the application's broader 60-second HTTP call timeout.
        val result = withTimeoutOrNull(ONBOARDING_SAVE_TIMEOUT_MS) {
            apiCall {
                api.complete(
                    authorization = "Bearer $token",
                    body = AndroidOnboardingRequestDto(
                        level = level,
                        goal = goal,
                        dailyMinutes = dailyMinutes,
                        startMode = startMode,
                        language = normalizeBackendLanguage(language),
                        timezoneOffsetMinutes = timezoneOffsetMinutes(),
                    ),
                )
            }
        } ?: ApiResult.Failure(ApiError.Timeout)
        if (result is ApiResult.Failure) notifySessionExpired(result.error)
        return result
    }

    private suspend fun notifySessionExpired(error: ApiError) {
        if (error is ApiError.SessionExpired) onSessionExpired()
    }

    private fun normalizeBackendLanguage(language: String): String = when (language.lowercase()) {
        "uz" -> "uz"
        "tg", "tj" -> "tj"
        else -> "ru"
    }

    private companion object {
        const val ONBOARDING_SAVE_TIMEOUT_MS = 12_000L
    }
}
