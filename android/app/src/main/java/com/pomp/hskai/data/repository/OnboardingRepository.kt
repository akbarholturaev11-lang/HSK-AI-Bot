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
        val result = status(token)
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

        // The server may commit just before the HTTP response is lost. In
        // that case showing Retry leaves an already-onboarded learner stuck
        // behind a form that can no longer change the canonical profile.
        // Re-read server state only for transport/unknown failures; a real
        // semantic server rejection must remain visible to the learner.
        if (result is ApiResult.Failure && result.error.isReconcilable()) {
            when (val canonical = status(token)) {
                is ApiResult.Success -> if (canonical.value.ok && canonical.value.completed) {
                    return ApiResult.Success(
                        AndroidOnboardingCompleteDto(
                            ok = true,
                            profile = canonical.value.profile.copy(onboardingCompleted = true),
                            level = canonical.value.level,
                        )
                    )
                }

                is ApiResult.Failure -> notifySessionExpired(canonical.error)
            }
        }
        if (result is ApiResult.Failure) notifySessionExpired(result.error)
        return result
    }

    private suspend fun status(token: String): ApiResult<AndroidOnboardingStatusDto> =
        apiCall { api.status("Bearer $token") }

    private fun ApiError.isReconcilable(): Boolean =
        this is ApiError.Timeout || this is ApiError.Offline || this is ApiError.Unknown

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
