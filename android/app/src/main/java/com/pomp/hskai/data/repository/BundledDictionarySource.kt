package com.pomp.hskai.data.repository

import android.content.Context
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.text.PinyinSearch
import com.pomp.hskai.data.local.DictionaryWordEntity
import java.security.MessageDigest
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

data class BundledDictionary(
    val version: String,
    val language: String,
    val words: List<DictionaryWordEntity>,
)

interface BundledDictionarySource {
    suspend fun load(language: AppLanguage): BundledDictionary?
}

class AssetBundledDictionarySource(
    context: Context,
    private val json: Json,
) : BundledDictionarySource {
    private val appContext = context.applicationContext

    override suspend fun load(language: AppLanguage): BundledDictionary? {
        val raw = runCatching {
            appContext.assets.open(ASSET_NAME).bufferedReader().use { it.readText() }
        }.getOrNull() ?: return null
        val match = WORDS_ARRAY.find(raw) ?: return null
        val parsed = runCatching {
            json.decodeFromString<List<SeedWord>>(match.groupValues[1])
        }.getOrNull().orEmpty()
        val key = language.backendCode.takeIf { it in LANGUAGES } ?: DEFAULT_LANGUAGE
        val words = parsed.mapIndexedNotNull { index, word ->
            val hanzi = word.hanzi.trim()
            val pinyin = word.pinyin.trim()
            val meaning = word.meaning[key]?.trim().orEmpty()
            if (hanzi.isBlank() || pinyin.isBlank() || meaning.isBlank()) {
                null
            } else {
                DictionaryWordEntity(
                    hanzi = hanzi,
                    pinyin = pinyin,
                    pinyinPlain = PinyinSearch.plain(pinyin),
                    meaning = meaning,
                    level = word.level.trim(),
                    position = index,
                )
            }
        }
        if (words.isEmpty()) return null
        return BundledDictionary(
            version = sha256(raw).take(16),
            language = key,
            words = words,
        )
    }

    private companion object {
        const val ASSET_NAME = "hsk-words.js"
        const val DEFAULT_LANGUAGE = "ru"
        val LANGUAGES = setOf("uz", "ru", "tj")
        val WORDS_ARRAY = Regex("""const\s+WORDS\s*=\s*(\[.*])\s*;?\s*$""", RegexOption.DOT_MATCHES_ALL)

        fun sha256(value: String): String {
            val digest = MessageDigest.getInstance("SHA-256")
                .digest(value.toByteArray(Charsets.UTF_8))
            return digest.joinToString("") { "%02x".format(it.toInt() and 0xff) }
        }
    }
}

@Serializable
private data class SeedWord(
    @SerialName("h") val hanzi: String = "",
    @SerialName("p") val pinyin: String = "",
    @SerialName("m") val meaning: Map<String, String> = emptyMap(),
    @SerialName("lv") val level: String = "",
)
