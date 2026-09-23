package com.pomp.hskai.data.repository

import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidOnboardingApi
import com.pomp.hskai.data.api.AndroidOnboardingCompleteDto
import com.pomp.hskai.data.api.AndroidOnboardingProfileDto
import com.pomp.hskai.data.api.AndroidOnboardingRequestDto
import com.pomp.hskai.data.api.AndroidOnboardingStatusDto
import kotlinx.coroutines.delay
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.Response

class OnboardingRepositoryTest {
    @Test
    fun completeTimesOutAfterMiniAppTwelveSecondWindow() = runTest {
        val api = object : AndroidOnboardingApi {
            override suspend fun status(authorization: String): Response<AndroidOnboardingStatusDto> =
                Response.success(AndroidOnboardingStatusDto(ok = true))

            override suspend fun complete(
                authorization: String,
                body: AndroidOnboardingRequestDto,
            ): Response<AndroidOnboardingCompleteDto> {
                delay(13_000)
                return Response.success(AndroidOnboardingCompleteDto(ok = true))
            }
        }
        val repository = OnboardingRepository(
            api = api,
            accessToken = { ApiResult.Success("token") },
            timezoneOffsetMinutes = { 0 },
        )

        val result = repository.complete(
            level = "hsk1",
            goal = "hsk_exam",
            language = "uz",
        )

        assertTrue(result is ApiResult.Failure && result.error is ApiError.Timeout)
    }

    @Test
    fun completeRecoversWhenServerCommittedBeforeTimeoutResponseWasLost() = runTest {
        val profile = AndroidOnboardingProfileDto(
            goal = "hsk_exam",
            onboardingCompleted = true,
        )
        val api = object : AndroidOnboardingApi {
            override suspend fun status(authorization: String): Response<AndroidOnboardingStatusDto> =
                Response.success(
                    AndroidOnboardingStatusDto(
                        ok = true,
                        completed = true,
                        level = "hsk1",
                        profile = profile,
                    )
                )

            override suspend fun complete(
                authorization: String,
                body: AndroidOnboardingRequestDto,
            ): Response<AndroidOnboardingCompleteDto> {
                delay(13_000)
                return Response.success(AndroidOnboardingCompleteDto(ok = true))
            }
        }
        val repository = OnboardingRepository(
            api = api,
            accessToken = { ApiResult.Success("token") },
            timezoneOffsetMinutes = { 0 },
        )

        val result = repository.complete(
            level = "hsk1",
            goal = "hsk_exam",
            language = "uz",
        )

        assertTrue(result is ApiResult.Success)
        result as ApiResult.Success
        assertTrue(result.value.ok)
        assertEquals("hsk1", result.value.level)
        assertEquals(true, result.value.profile?.onboardingCompleted)
    }
}
