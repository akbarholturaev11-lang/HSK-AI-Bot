package com.pomp.hskai.data.repository

import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.api.CourseCompleteRequest
import com.pomp.hskai.data.api.CourseCompleteResponse
import com.pomp.hskai.data.api.CourseMapDto
import com.pomp.hskai.data.api.CourseMistakeDto
import com.pomp.hskai.data.api.LanguageRequest
import com.pomp.hskai.data.api.NotificationsRequest
import com.pomp.hskai.data.api.OkResponse
import com.pomp.hskai.data.lesson.LessonParser
import com.pomp.hskai.data.local.CourseMapCacheEntity
import com.pomp.hskai.data.local.CourseMapDao
import com.pomp.hskai.domain.model.CourseMap
import com.pomp.hskai.domain.model.Lesson
import java.io.ByteArrayOutputStream
import java.util.TimeZone
import java.util.UUID
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
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

/** A lesson plus the newer access decision returned by the lesson request. */
data class LessonSnapshot(
    val lesson: Lesson,
    val isHalfPreview: Boolean,
    val previewCardLimit: Int,
    val completionAllowed: Boolean,
    val completionError: String?,
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
    private val onSessionExpired: suspend () -> Unit = {},
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
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
            is ApiResult.Failure -> {
                // A revoked/reused session must leave the authenticated UI.
                // Cached course data is only an offline transport fallback,
                // never a substitute for valid credentials.
                if (result.error is ApiError.SessionExpired) return result
                return cached(result.error)
            }
            is ApiResult.Success -> result.value
        }

        val response = apiCall {
            api.courseMap("Bearer $token", timezoneOffsetMinutes())
        }
        return when (response) {
            is ApiResult.Failure -> {
                notifySessionExpired(response.error)
                cached(response.error)
            }
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
     * Loads and parses one mini-lesson.
     *
     * Not cached yet: Phase K decides what may be studied offline. Until then
     * a lesson always comes from the server, so its access decision is current.
     */
    suspend fun lesson(
        level: String,
        lessonOrder: Int,
        language: AppLanguage,
    ): ApiResult<LessonSnapshot> {
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return result
            is ApiResult.Success -> result.value
        }
        return when (val result = apiCall { api.lesson("Bearer $token", lessonOrder) }) {
            is ApiResult.Failure -> {
                notifySessionExpired(result.error)
                result
            }
            is ApiResult.Success -> {
                val envelope = result.value
                val requestedLevel = level.trim().lowercase()
                val responseLevel = envelope.level.trim().lowercase()
                if (
                    !envelope.ok ||
                    envelope.lessonOrder != lessonOrder ||
                    responseLevel != requestedLevel ||
                    envelope.previewHalf == envelope.completionAllowed
                ) {
                    return ApiResult.Failure(ApiError.Unknown)
                }
                val parsed = runCatching {
                    LessonParser.parse(
                        payload = envelope.lesson,
                        level = responseLevel,
                        lessonOrder = lessonOrder,
                        language = language,
                    )
                }.getOrNull()
                val cardCount = parsed?.cards?.size ?: 0
                if (
                    parsed == null ||
                    cardCount <= 0 ||
                    envelope.totalCards != cardCount ||
                    envelope.previewCardLimit !in 1..cardCount
                ) {
                    ApiResult.Failure(ApiError.Unknown)
                } else {
                    val limit = if (envelope.completionAllowed) {
                        cardCount
                    } else {
                        envelope.previewCardLimit.coerceIn(1, cardCount)
                    }
                    ApiResult.Success(
                        LessonSnapshot(
                            lesson = parsed,
                            isHalfPreview = envelope.previewHalf,
                            previewCardLimit = limit,
                            completionAllowed = envelope.completionAllowed,
                            completionError = envelope.completionError,
                        )
                    )
                }
            }
        }
    }

    /**
     * Downloads one bounded Chinese TTS clip through the bearer-authenticated
     * Android adapter. The response is capped while streaming so a malformed
     * server cannot make the client allocate an unbounded body.
     */
    suspend fun ttsAudio(text: String): ApiResult<ByteArray> {
        val phrase = text.trim()
        if (phrase.isEmpty() || phrase.length > MAX_TTS_TEXT_LENGTH || !CJK.containsMatchIn(phrase)) {
            return ApiResult.Failure(ApiError.Unknown)
        }
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return result
            is ApiResult.Success -> result.value
        }
        return when (
            val result = apiCall {
                api.tts(
                    authorization = "Bearer $token",
                    text = phrase,
                    rate = DEFAULT_TTS_RATE,
                )
            }
        ) {
            is ApiResult.Failure -> {
                notifySessionExpired(result.error)
                result
            }
            is ApiResult.Success -> withContext(ioDispatcher) {
                val body = result.value
                val declared = body.contentLength()
                if (declared > MAX_TTS_AUDIO_BYTES) {
                    body.close()
                    return@withContext ApiResult.Failure(ApiError.Unknown)
                }
                runCatching {
                    body.byteStream().use { input ->
                        val output = ByteArrayOutputStream()
                        val buffer = ByteArray(TTS_BUFFER_BYTES)
                        while (true) {
                            val read = input.read(buffer)
                            if (read < 0) break
                            if (output.size() + read > MAX_TTS_AUDIO_BYTES) {
                                throw IllegalStateException("TTS response exceeds limit")
                            }
                            output.write(buffer, 0, read)
                        }
                        output.toByteArray().takeIf { it.isNotEmpty() }
                            ?: throw IllegalStateException("Empty TTS response")
                    }
                }.fold(
                    onSuccess = { ApiResult.Success(it) },
                    onFailure = { ApiResult.Failure(ApiError.Unknown) },
                )
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
        val result = apiCall {
            api.complete(
                "Bearer $token",
                CourseCompleteRequest(
                    lessonOrder = lessonOrder,
                    eventId = eventId,
                    mistakes = mistakes,
                ),
            )
        }
        if (result is ApiResult.Failure) notifySessionExpired(result.error)
        return result
    }

    /**
     * Changes the learning language on the server.
     *
     * The cached map still holds the previous language's text, so it is
     * dropped here rather than shown until the next refresh happens to land.
     */
    suspend fun setLanguage(language: AppLanguage): ApiResult<OkResponse> {
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return result
            is ApiResult.Success -> result.value
        }
        val result = apiCall {
            api.setLanguage("Bearer $token", LanguageRequest(language.backendCode))
        }
        if (result is ApiResult.Success) dao.clear()
        if (result is ApiResult.Failure) notifySessionExpired(result.error)
        return result
    }

    /** Reminder opt-in. The same flag the bot and the Mini App read. */
    suspend fun setNotifications(enabled: Boolean): ApiResult<OkResponse> {
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return result
            is ApiResult.Success -> result.value
        }
        val result = apiCall {
            api.setNotifications("Bearer $token", NotificationsRequest(enabled))
        }
        if (result is ApiResult.Failure) notifySessionExpired(result.error)
        return result
    }

    /** Cached progress must not outlive the session. */
    suspend fun clearCache() = dao.clear()

    private suspend fun cached(error: ApiError): ApiResult<CourseMapSnapshot> {
        if (error is ApiError.SessionExpired) return ApiResult.Failure(error)
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

    private suspend fun notifySessionExpired(error: ApiError) {
        if (error is ApiError.SessionExpired) onSessionExpired()
    }

    companion object {
        private const val MAX_TTS_TEXT_LENGTH = 240
        private const val MAX_TTS_AUDIO_BYTES = 2 * 1024 * 1024
        private const val TTS_BUFFER_BYTES = 8 * 1024
        private const val DEFAULT_TTS_RATE = "-10%"
        private val CJK = Regex("[\\u4E00-\\u9FFF]")

        /**
         * `android:<uuid>` — the Android completion namespace the backend
         * dedupes on, distinct from the desktop one.
         */
        fun newEventId(): String =
            "android:" + UUID.randomUUID().toString().replace("-", "")
    }
}
