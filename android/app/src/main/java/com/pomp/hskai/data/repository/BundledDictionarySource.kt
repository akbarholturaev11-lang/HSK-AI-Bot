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
        val key = language.backendCode.takeIf { it in LANGUAGES } ?: DEFAULT_LANGUAGE
        val digest = MessageDigest.getInstance("SHA-256")
        val merged = linkedMapOf<String, SeedWord>()

        SOURCES.forEach { source ->
            val raw = runCatching {
                appContext.assets.open(source.name).bufferedReader().use { it.readText() }
            }.getOrNull() ?: return@forEach
            val match = source.pattern.find(raw) ?: return@forEach
            val parsed = runCatching {
                json.decodeFromString<List<SeedWord>>(match.groupValues[1])
            }.getOrNull().orEmpty()

            digest.update(source.name.toByteArray(Charsets.UTF_8))
            digest.update(0)
            digest.update(raw.toByteArray(Charsets.UTF_8))

            parsed.forEach { word ->
                val hanzi = word.hanzi.trim()
                val pinyin = word.pinyin.trim()
                val meaning = word.meaning[key]?.trim().orEmpty()
                if (hanzi.isBlank() || pinyin.isBlank() || meaning.isBlank()) return@forEach
                val existing = merged[hanzi]
                if (existing == null) {
                    merged[hanzi] = word.copy(
                        hanzi = hanzi,
                        pinyin = pinyin,
                        meaning = word.meaning.mapValues { it.value.trim() },
                        level = word.level.trim(),
                    )
                } else {
                    val levels = existing.level.split("|").filter(String::isNotBlank).toMutableList()
                    val next = word.level.trim()
                    if (next.isNotBlank() && next !in levels) levels += next
                    merged[hanzi] = existing.copy(level = levels.joinToString("|"))
                }
            }
        }

        val words = merged.values.mapIndexedNotNull { index, word ->
            val meaning = word.meaning[key]?.trim().orEmpty()
            if (meaning.isBlank()) null else DictionaryWordEntity(
                hanzi = word.hanzi,
                pinyin = word.pinyin,
                pinyinPlain = PinyinSearch.plain(word.pinyin),
                meaning = meaning,
                level = word.level,
                position = index,
            )
        }
        if (words.isEmpty()) return null
        val version = digest.digest().joinToString("") { "%02x".format(it.toInt() and 0xff) }.take(16)
        return BundledDictionary(
            version = version,
            language = key,
            words = words,
        )
    }

    private data class Source(val name: String, val pattern: Regex)

    private companion object {
        const val DEFAULT_LANGUAGE = "ru"
        val LANGUAGES = setOf("uz", "ru", "tj")
        val SOURCES = listOf(
            Source(
                "hsk-words.js",
                Regex("""const\s+WORDS\s*=\s*(\[.*])\s*;?\s*$""", RegexOption.DOT_MATCHES_ALL),
            ),
            Source(
                "hsk30-words.js",
                Regex("""window\.HSK30_WORDS\s*=\s*(\[.*])\s*;?\s*$""", RegexOption.DOT_MATCHES_ALL),
            ),
        )
    }
}

@Serializable
private data class SeedWord(
    @SerialName("h") val hanzi: String = "",
    @SerialName("p") val pinyin: String = "",
    @SerialName("m") val meaning: Map<String, String> = emptyMap(),
    @SerialName("lv") val level: String = "",
)
