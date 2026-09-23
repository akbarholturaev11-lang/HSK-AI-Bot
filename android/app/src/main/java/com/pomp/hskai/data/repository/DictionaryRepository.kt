package com.pomp.hskai.data.repository

import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.toApiError
import com.pomp.hskai.core.text.PinyinSearch
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.local.DictionaryDao
import com.pomp.hskai.data.local.DictionaryMetaEntity
import com.pomp.hskai.data.local.DictionaryWordEntity
import java.io.IOException
import java.net.SocketTimeoutException

/** One dictionary entry as the screen shows it. */
data class DictionaryWord(
    val hanzi: String,
    val pinyin: String,
    val meaning: String,
    val level: String,
)

/**
 * The character dictionary, served from the device and refreshed from the one
 * server list.
 *
 * The list only changes with a deploy, so it is downloaded once and then read
 * from the cache: opening the dictionary must not cost 90 KB every time. A
 * language change invalidates the copy, because the stored meanings are in the
 * previous language.
 */
internal const val DICTIONARY_CHECK_TTL_MILLIS = 24L * 60L * 60L * 1000L

class DictionaryRepository(
    private val api: AndroidCourseApi,
    private val accessToken: suspend () -> ApiResult<String>,
    private val dao: DictionaryDao,
    private val onSessionExpired: suspend () -> Unit = {},
    private val bundledSource: BundledDictionarySource? = null,
    private val clientVersionCode: Int = 0,
    private val readLastCheckedAtMillis: suspend (String) -> Long? = { null },
    private val readLastCheckedClientVersion: suspend (String) -> Int? = { null },
    private val writeLastChecked: suspend (String, Long, Int) -> Unit = { _, _, _ -> },
    private val now: () -> Long = System::currentTimeMillis,
) {

    /**
     * Brings the cache up to date.
     *
     * Returns the number of entries the dictionary now holds. A failure is
     * only reported when there is nothing usable to show: with a populated
     * cache the learner keeps their dictionary rather than an error.
     */
    suspend fun sync(language: AppLanguage): ApiResult<Int> {
        var cached = dao.meta()
        var cachedCount = dao.count()
        var sameLanguage = cached?.language == language.backendCode
        if ((cachedCount == 0 || !sameLanguage) && bundledSource != null) {
            bundledSource.load(language)?.let { bundled ->
                dao.replace(
                    words = bundled.words,
                    meta = DictionaryMetaEntity(
                        version = bundled.version,
                        language = bundled.language,
                    ),
                )
                cached = dao.meta()
                cachedCount = dao.count()
                sameLanguage = cached?.language == language.backendCode
            }
        }
        val languageKey = language.backendCode
        if (cachedCount > 0 && sameLanguage && clientVersionCode > 0) {
            val checkedAt = runCatching { readLastCheckedAtMillis(languageKey) }.getOrNull()
            val checkedClient = runCatching { readLastCheckedClientVersion(languageKey) }.getOrNull()
            val age = checkedAt?.let { now() - it }
            if (
                checkedClient == clientVersionCode &&
                age != null &&
                age in 0L until DICTIONARY_CHECK_TTL_MILLIS
            ) {
                return ApiResult.Success(cachedCount)
            }
        }

        val etag = cached?.version
            ?.takeIf { it.isNotBlank() && sameLanguage && cachedCount > 0 }
            ?.let { "W/\"dictionary-$it\"" }

        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return keepOrFail(result.error, cachedCount)
            is ApiResult.Success -> result.value
        }

        val response = try {
            api.dictionary("Bearer $token", etag)
        } catch (_: SocketTimeoutException) {
            return keepOrFail(ApiError.Timeout, cachedCount)
        } catch (_: IOException) {
            return keepOrFail(ApiError.Offline, cachedCount)
        } catch (_: Exception) {
            return keepOrFail(ApiError.Unknown, cachedCount)
        }

        // The server confirmed the stored copy is still the current one.
        if (response.code() == NOT_MODIFIED) {
            markChecked(languageKey)
            return ApiResult.Success(cachedCount)
        }

        val body = response.body()
        if (!response.isSuccessful || body == null || !body.ok) {
            val error = response.toApiError()
            if (error is ApiError.SessionExpired) onSessionExpired()
            return keepOrFail(error, cachedCount)
        }

        val words = body.words
            .asSequence()
            .filter { it.hanzi.isNotBlank() && it.meaning.isNotBlank() }
            .mapIndexed { index, dto ->
                DictionaryWordEntity(
                    hanzi = dto.hanzi,
                    pinyin = dto.pinyin,
                    pinyinPlain = PinyinSearch.plain(dto.pinyin),
                    meaning = dto.meaning,
                    level = dto.level,
                    position = index,
                )
            }
            .toList()

        // An empty answer is not a reason to throw away a working dictionary.
        if (words.isEmpty()) return keepOrFail(ApiError.Unknown, cachedCount)

        dao.replace(
            words = words,
            meta = DictionaryMetaEntity(
                version = body.version,
                language = body.language.ifBlank { language.backendCode },
            ),
        )
        markChecked(languageKey)
        return ApiResult.Success(words.size)
    }

    /** Cache-only read; [sync] is what talks to the server. */
    suspend fun search(query: String, limit: Int = SEARCH_LIMIT): List<DictionaryWord> {
        val trimmed = query.trim()
        val rows = if (trimmed.isEmpty()) {
            dao.all(limit)
        } else {
            dao.search(
                query = trimmed,
                // A blank plain form would turn into '%%' and match everything,
                // so fall back to the raw query for a non-pinyin search.
                plain = PinyinSearch.plain(trimmed).ifEmpty { trimmed },
                limit = limit,
            )
        }
        return rows.map {
            DictionaryWord(
                hanzi = it.hanzi,
                pinyin = it.pinyin,
                meaning = it.meaning,
                level = it.level,
            )
        }
    }

    suspend fun clearCache() = dao.clear()

    private suspend fun markChecked(language: String) {
        if (clientVersionCode <= 0) return
        runCatching { writeLastChecked(language, now(), clientVersionCode) }
    }

    private suspend fun keepOrFail(error: ApiError, cachedCount: Int): ApiResult<Int> {
        if (error is ApiError.SessionExpired) onSessionExpired()
        return if (cachedCount > 0) ApiResult.Success(cachedCount) else ApiResult.Failure(error)
    }

    private companion object {
        const val NOT_MODIFIED = 304
        // The server currently ships HSK 1-4 as one 1247-word dictionary. A
        // 200-row cap made the default list look like it stopped at HSK2
        // because the source is ordered by level.
        const val SEARCH_LIMIT = 2_000
    }
}
