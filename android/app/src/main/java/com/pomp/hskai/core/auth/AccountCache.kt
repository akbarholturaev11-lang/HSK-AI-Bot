package com.pomp.hskai.core.auth

import com.pomp.hskai.core.i18n.AppLanguage
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * The last confirmed [LinkedAccount], in the form it is kept for an offline
 * start.
 *
 * A blob that no longer decodes is treated as absent. That costs one start
 * behind the retry screen, never a crash or a wrong account.
 */
internal object AccountCache {

    private val json = Json { ignoreUnknownKeys = true }

    fun encode(account: LinkedAccount): String = json.encodeToString(
        CachedAccountDto.serializer(),
        CachedAccountDto(
            displayName = account.displayName,
            language = account.language.backendCode,
            level = account.level,
            accessState = account.accessState,
            isPaid = account.isPaid,
        ),
    )

    fun decode(raw: String?): LinkedAccount? {
        if (raw.isNullOrBlank()) return null
        val dto = try {
            json.decodeFromString(CachedAccountDto.serializer(), raw)
        } catch (_: IllegalArgumentException) {
            // SerializationException is one; so is a malformed payload.
            return null
        }
        return LinkedAccount(
            displayName = dto.displayName,
            language = AppLanguage.fromBackendCode(dto.language),
            level = dto.level,
            accessState = dto.accessState,
            isPaid = dto.isPaid,
        )
    }

    @Serializable
    private data class CachedAccountDto(
        val displayName: String,
        val language: String,
        val level: String,
        val accessState: String,
        val isPaid: Boolean,
    )
}
