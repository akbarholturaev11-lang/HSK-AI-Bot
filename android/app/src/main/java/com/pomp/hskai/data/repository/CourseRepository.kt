package com.pomp.hskai.data.repository

import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.api.CourseCompleteRequest
import com.pomp.hskai.data.api.CourseCompleteResponse
import com.pomp.hskai.data.api.CourseMapDto
import com.pomp.hskai.data.api.CourseMistakeDto
import com.pomp.hskai.data.local.CourseMapCacheEntity
import com.pomp.hskai.data.local.CourseMapDao
import com.pomp.hskai.domain.model.CourseMap
import java.util.TimeZone
import java.util.UUID
import kotlinx.serialization.json.Json

/**
 * A course map plus how trustworthy it is right now.
 *
 * [isStale] means the network refresh failed and this came from the cache. The
 * UI must label it; it must never quietly present old entitlement as current.
 */
data class CourseMapSnapshot(
    val map: CourseMap,
    val isStale: Boolean,
    val fetchedAtMillis: Long,
    val refreshError: ApiError? = null,
)

class CourseRepository(
    private val api: AndroidCourseApi,
    /**
     * Supplies a valid bearer token, refreshing if needed. Injected as a
     * function rather than the whole AuthRepository so the course logic can be
     * unit tested without an auth stack.
     */
    private val accessToken: suspend () -> ApiResult<String>,
    private val dao: CourseMapDao,
    private val json: Json,
    private val now: () -> Long = System::currentTimeMillis,
    private val timezoneOffsetMinutes: () -> Int = {
        // Not `!= 0`-style logic anywhere: UTC+0 is a real offset.
        TimeZone.getDefault().getOffset(System.currentTimeMillis()) / 60_000
    },
) {

    /**
     * Server first, cache as a fallback.
     *
     * The cache can only ever repeat the last decision the server made, so it
     * cannot widen access. When the refresh fails and nothing is cached, the
     * failure is reported rather than papered over.
     */
    suspend fun courseMap(): ApiResult<CourseMapSnapshot> {
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return cached(result.error)
            is ApiResult.Success -> result.value
        }

        val response = apiCall {
            api.courseMap("Bearer $token", timezoneOffsetMinutes())
        }
        return when (response) {
            is ApiResult.Failure -> cached(response.error)
            is ApiResult.Success -> {
                val dto = response.value
                if (!dto.ok || dto.units.isEmpty()) {
                    cached(ApiError.Unknown)
                } else {
                    val fetchedAt = now()
                    dao.upsert(
                        CourseMapCacheEntity(
                            level = dto.level,
                            payloadJson = json.encodeToString(CourseMapDto.serializer(), dto),
                            fetchedAtMillis = fetchedAt,
                        )
                    )
                    ApiResult.Success(
                        CourseMapSnapshot(
                            map = CourseMapper.toDomain(dto),
                            isStale = false,
                            fetchedAtMillis = fetchedAt,
                        )
                    )
                }
            }
        }
    }

    /**
     * Reports the completion. The event id is stable for the whole attempt, so
     * a retry after a dropped connection returns the server's stored result
     * instead of awarding XP twice.
     */
    suspend fun completeLesson(
        lessonOrder: Int,
        eventId: String = newEventId(),
        mistakes: List<CourseMistakeDto> = emptyList(),
    ): ApiResult<CourseCompleteResponse> {
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return result
            is ApiResult.Success -> result.value
        }
        return apiCall {
            api.complete(
                "Bearer $token",
                CourseCompleteRequest(
                    lessonOrder = lessonOrder,
                    eventId = eventId,
                    mistakes = mistakes,
                ),
            )
        }
    }

    /** Cached progress must not outlive the session. */
    suspend fun clearCache() = dao.clear()

    private suspend fun cached(error: ApiError): ApiResult<CourseMapSnapshot> {
        val entity = dao.findMostRecent() ?: return ApiResult.Failure(error)
        val dto = runCatching {
            json.decodeFromString(CourseMapDto.serializer(), entity.payloadJson)
        }.getOrNull() ?: return ApiResult.Failure(error)
        return ApiResult.Success(
            CourseMapSnapshot(
                map = CourseMapper.toDomain(dto),
                isStale = true,
                fetchedAtMillis = entity.fetchedAtMillis,
                refreshError = error,
            )
        )
    }

    companion object {
        /**
         * `android:<uuid>` — the Android completion namespace the backend
         * dedupes on, distinct from the desktop one.
         */
        fun newEventId(): String =
            "android:" + UUID.randomUUID().toString().replace("-", "")
    }
}
