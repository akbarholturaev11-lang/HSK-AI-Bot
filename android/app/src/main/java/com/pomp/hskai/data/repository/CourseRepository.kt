package com.pomp.hskai.data.repository

import com.pomp.hskai.core.audio.TtsCache
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.hanzi.CharacterStrokes
import com.pomp.hskai.data.local.BundledDictionary
import androidx.compose.ui.geometry.Offset
import com.pomp.hskai.core.network.apiCall
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.api.AndroidFoundationApi
import com.pomp.hskai.data.api.CourseCompleteRequest
import com.pomp.hskai.data.api.CourseCompleteResponse
import com.pomp.hskai.data.api.CourseLessonResponse
import com.pomp.hskai.data.api.LessonUnlockRequest
import com.pomp.hskai.data.api.LessonUnlockResponse
import com.pomp.hskai.data.api.CourseMapDto
import com.pomp.hskai.data.api.CourseMistakeDto
import com.pomp.hskai.data.api.FoundationCompleteRequest
import com.pomp.hskai.data.api.FoundationCompleteResponse
import com.pomp.hskai.data.api.FoundationResponseDto
import com.pomp.hskai.data.api.LanguageRequest
import com.pomp.hskai.data.api.NotificationsRequest
import com.pomp.hskai.data.api.OkResponse
import com.pomp.hskai.data.api.RewardChestOpenResponse
import com.pomp.hskai.data.lesson.LessonParser
import com.pomp.hskai.data.local.CourseMapCacheEntity
import com.pomp.hskai.data.local.CourseMapDao
import com.pomp.hskai.data.local.LessonCacheDao
import com.pomp.hskai.data.local.LessonCacheEntity
import com.pomp.hskai.domain.model.CourseMap
import com.pomp.hskai.domain.model.Lesson
import java.io.ByteArrayOutputStream
import java.util.TimeZone
import java.util.UUID
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.serialization.json.Json

data class CourseMapSnapshot(
    val map: CourseMap,
    val isStale: Boolean,
    val fetchedAtMillis: Long,
    val refreshError: ApiError? = null,
)

data class LessonSnapshot(
    val lesson: Lesson,
    val isHalfPreview: Boolean,
    val previewCardLimit: Int,
    val completionAllowed: Boolean,
    val completionError: String?,
    /** Read from disk because the request never reached the server. */
    val isStale: Boolean = false,
)

class CourseRepository(
    private val api: AndroidCourseApi,
    private val accessToken: suspend () -> ApiResult<String>,
    private val dao: CourseMapDao,
    private val lessonDao: LessonCacheDao? = null,
    private val json: Json,
    private val foundationApi: AndroidFoundationApi? = null,
    private val onSessionExpired: suspend () -> Unit = {},
    private val ttsCache: TtsCache? = null,
    /** The stroke data shipped in the APK. Absent in tests. */
    private val bundled: BundledDictionary? = null,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
    private val now: () -> Long = System::currentTimeMillis,
    private val timezoneOffsetMinutes: () -> Int = {
        TimeZone.getDefault().getOffset(System.currentTimeMillis()) / 60_000
    },
) {

    /**
     * The map already on disk, with nothing asked of the network.
     *
     * The cache used to be reachable only after a request had failed, so every
     * single open waited out a full round trip before anything was drawn —
     * with a perfectly good copy of the same screen sitting on disk. On a 4G
     * connection that is seconds of empty screen, every time, for data that
     * had not changed.
     *
     * It is not marked stale here. "Stale" means the refresh failed, and while
     * one is still in flight nobody knows that yet; the failure path below
     * still marks it, which is when the banner belongs on screen.
     */
    suspend fun cachedCourseMap(): CourseMapSnapshot? {
        val entity = dao.findMostRecent() ?: return null
        val dto = runCatching {
            json.decodeFromString(CourseMapDto.serializer(), entity.payloadJson)
        }.getOrNull() ?: return null
        return CourseMapSnapshot(
            map = CourseMapper.toDomain(dto),
            isStale = false,
            fetchedAtMillis = entity.fetchedAtMillis,
        )
    }

    suspend fun courseMap(): ApiResult<CourseMapSnapshot> {
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> {
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

    suspend fun foundation(): ApiResult<FoundationResponseDto> {
        val transport = foundationApi ?: return ApiResult.Failure(ApiError.Unknown)
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return result
            is ApiResult.Success -> result.value
        }
        val result = apiCall { transport.foundation("Bearer $token") }
        if (result is ApiResult.Failure) notifySessionExpired(result.error)
        if (result is ApiResult.Success) {
            val payload = result.value
            if (
                !payload.ok ||
                payload.foundation.id != FOUNDATION_ID ||
                payload.foundation.version != FOUNDATION_VERSION ||
                payload.foundation.cards.isEmpty() ||
                payload.foundation.requiredObjectives != FOUNDATION_REQUIRED_OBJECTIVES
            ) {
                return ApiResult.Failure(ApiError.Unknown)
            }
        }
        return result
    }

    suspend fun completeFoundation(
        speakingBonus: Boolean,
        eventId: String = newFoundationEventId(),
    ): ApiResult<FoundationCompleteResponse> {
        val transport = foundationApi ?: return ApiResult.Failure(ApiError.Unknown)
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return result
            is ApiResult.Success -> result.value
        }
        val result = withTimeoutOrNull(FOUNDATION_SAVE_TIMEOUT_MILLIS) {
            apiCall {
                transport.completeFoundation(
                    "Bearer $token",
                    FoundationCompleteRequest(
                        foundationId = FOUNDATION_ID,
                        foundationVersion = FOUNDATION_VERSION,
                        speakingBonus = speakingBonus,
                        eventId = eventId,
                    ),
                )
            }
        } ?: ApiResult.Failure(ApiError.Timeout)
        if (result is ApiResult.Failure) notifySessionExpired(result.error)
        return result
    }

    suspend fun lesson(
        level: String,
        lessonOrder: Int,
        language: AppLanguage,
        /** The ad view that opened this lesson, when one did. */
        accessRef: String = "",
    ): ApiResult<LessonSnapshot> {
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return cachedLesson(level, lessonOrder, language, result.error)
            is ApiResult.Success -> result.value
        }
        return when (
            val result = apiCall { api.lesson("Bearer $token", lessonOrder, accessRef) }
        ) {
            is ApiResult.Failure -> {
                notifySessionExpired(result.error)
                cachedLesson(level, lessonOrder, language, result.error)
            }
            is ApiResult.Success -> {
                val envelope = result.value
                val snapshot = snapshotOf(envelope, level, lessonOrder, language)
                    ?: return ApiResult.Failure(ApiError.Unknown)
                // Written only now, after the server said yes and the payload
                // parsed. A malformed or refused lesson is never stored.
                lessonDao?.upsert(
                    LessonCacheEntity(
                        level = level.trim().lowercase(),
                        lessonOrder = lessonOrder,
                        envelopeJson = json.encodeToString(
                            CourseLessonResponse.serializer(),
                            envelope,
                        ),
                        fetchedAtMillis = now(),
                    )
                )
                ApiResult.Success(snapshot)
            }
        }
    }

    /**
     * Builds the snapshot, or null when the envelope does not agree with what
     * was asked for.
     *
     * One path for fresh and cached envelopes alike, so a lesson off the disk
     * can never come out more permissive than the server last made it.
     */
    private fun snapshotOf(
        envelope: CourseLessonResponse,
        level: String,
        lessonOrder: Int,
        language: AppLanguage,
        isStale: Boolean = false,
    ): LessonSnapshot? {
        val requestedLevel = level.trim().lowercase()
        val responseLevel = envelope.level.trim().lowercase()
        if (
            !envelope.ok ||
            envelope.lessonOrder != lessonOrder ||
            responseLevel != requestedLevel ||
            envelope.previewHalf == envelope.completionAllowed
        ) {
            return null
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
            return null
        }
        val limit = if (envelope.completionAllowed) {
            cardCount
        } else {
            envelope.previewCardLimit.coerceIn(1, cardCount)
        }
        return LessonSnapshot(
            lesson = parsed,
            isHalfPreview = envelope.previewHalf,
            previewCardLimit = limit,
            completionAllowed = envelope.completionAllowed,
            completionError = envelope.completionError,
            isStale = isStale,
        )
    }

    /**
     * The lesson as it was last served, for a request that never got an answer.
     *
     * Deliberately narrower than the course map's fallback: only [ApiError.Offline]
     * and [ApiError.Timeout] qualify. If the server answered at all — a spent
     * allowance, a lesson that is no longer unlocked, an expired session — that
     * answer stands, and the disk copy must not talk over it.
     *
     * Serving it grants nothing new. The backend spends the daily slot on the
     * GET itself, so every row in this table is a lesson already paid for, and
     * reopening one has never cost a second slot.
     */
    private suspend fun cachedLesson(
        level: String,
        lessonOrder: Int,
        language: AppLanguage,
        error: ApiError,
    ): ApiResult<LessonSnapshot> {
        if (error !is ApiError.Offline && error !is ApiError.Timeout) {
            return ApiResult.Failure(error)
        }
        val row = lessonDao?.find(level.trim().lowercase(), lessonOrder)
            ?: return ApiResult.Failure(error)
        val envelope = runCatching {
            json.decodeFromString(CourseLessonResponse.serializer(), row.envelopeJson)
        }.getOrNull() ?: return ApiResult.Failure(error)
        val snapshot = snapshotOf(envelope, level, lessonOrder, language, isStale = true)
            ?: return ApiResult.Failure(error)
        return ApiResult.Success(snapshot)
    }

    /** Stroke outlines for one character; the server proxies and caches them. */
    suspend fun strokes(char: String): ApiResult<CharacterStrokes> {
        val single = char.trim()
        if (single.length != 1) return ApiResult.Failure(ApiError.Unknown)

        // The APK carries every character the dictionary can open, so the
        // writing order draws with no connection and without a round trip for
        // something that only changes with a release. Anything outside that
        // set — a character met in a lesson, say — still asks the server.
        bundled?.strokes(single)?.let { return ApiResult.Success(it) }

        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return result
            is ApiResult.Success -> result.value
        }
        return when (val result = apiCall { api.stroke("Bearer $token", single) }) {
            is ApiResult.Failure -> result
            is ApiResult.Success -> ApiResult.Success(
                CharacterStrokes(
                    outlines = result.value.strokes,
                    // A payload without medians still draws; the stroke simply
                    // appears whole instead of being written.
                    medians = result.value.medians.map { points ->
                        points.mapNotNull { point ->
                            if (point.size >= 2) Offset(point[0], point[1]) else null
                        }
                    },
                )
            )
        }
    }

    suspend fun ttsAudio(text: String): ApiResult<ByteArray> {
        val phrase = text.trim()
        if (phrase.isEmpty() || phrase.length > MAX_TTS_TEXT_LENGTH || !CJK.containsMatchIn(phrase)) {
            return ApiResult.Failure(ApiError.Unknown)
        }
        // Served before the token is asked for, and deliberately so: the phrase
        // is already drawn on the screen that is asking to hear it, so replaying
        // our own copy of its audio opens nothing a session would have gated.
        // It also makes the second tap instant and survives a dropped network.
        val cacheKey = ttsCacheKey(phrase)
        ttsCache?.read(cacheKey)?.let { return ApiResult.Success(it) }
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
                    onSuccess = {
                        ttsCache?.write(cacheKey, it)
                        ApiResult.Success(it)
                    },
                    onFailure = { ApiResult.Failure(ApiError.Unknown) },
                )
            }
        }
    }

    /** Rate is part of the key: the same phrase sounds different slowed down. */
    private fun ttsCacheKey(phrase: String): String = "$DEFAULT_TTS_RATE|$phrase"

    /**
     * Opens a not-yet-reached lesson after the skip-ahead test, the way the
     * Mini App has always allowed.
     *
     * The score is reported, not enforced: the server records it and opens the
     * lesson either way, and a spent daily allowance is refused there rather
     * than guessed at here.
     */
    suspend fun unlockLesson(
        lessonOrder: Int,
        score: Int,
    ): ApiResult<LessonUnlockResponse> {
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return result
            is ApiResult.Success -> result.value
        }
        val result = apiCall {
            api.unlockLesson(
                "Bearer $token",
                LessonUnlockRequest(lessonOrder = lessonOrder, score = score),
            )
        }
        if (result is ApiResult.Failure) notifySessionExpired(result.error)
        // The map's progress moved on the server, so the cached copy is stale.
        if (result is ApiResult.Success) clearCache()
        return result
    }

    suspend fun completeLesson(
        lessonOrder: Int,
        eventId: String = newEventId(),
        mistakes: List<CourseMistakeDto> = emptyList(),
        accessRef: String = "",
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
                    accessRef = accessRef,
                    mistakes = mistakes,
                ),
            )
        }
        if (result is ApiResult.Failure) notifySessionExpired(result.error)
        return result
    }

    suspend fun openRewardChest(): ApiResult<RewardChestOpenResponse> {
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return result
            is ApiResult.Success -> result.value
        }
        val result = apiCall { api.openRewardChest("Bearer $token") }
        if (result is ApiResult.Failure) notifySessionExpired(result.error)
        return result
    }

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

    suspend fun clearCache() {
        dao.clear()
        lessonDao?.clear()
        ttsCache?.clear()
    }

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
        private const val FOUNDATION_ID = "starter0_hsk1"
        private const val FOUNDATION_VERSION = 1
        private const val FOUNDATION_SAVE_TIMEOUT_MILLIS = 12_000L
        private val FOUNDATION_REQUIRED_OBJECTIVES = listOf("meaning", "build", "listen")
        private val CJK = Regex("[\\u4E00-\\u9FFF]")

        fun newEventId(): String =
            "android:" + UUID.randomUUID().toString().replace("-", "")

        fun newFoundationEventId(): String =
            "android:foundation:" + UUID.randomUUID().toString().replace("-", "")
    }
}
