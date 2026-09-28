package com.pomp.hskai.data.local

import android.content.Context
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.data.repository.CharacterBreakdown
import com.pomp.hskai.data.repository.CharacterPart
import com.pomp.hskai.data.repository.DictionaryInsightsSource
import com.pomp.hskai.data.repository.ExampleSentence
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * Examples and character breakdowns, shipped inside the APK.
 *
 * Built by `android/tools/build_dictionary_insights.py`: the examples from the
 * course's own sentences, the breakdowns from hand-written sources. Nothing
 * here asks the network — the dictionary entry is complete offline.
 *
 * Each file is read once, on first use, and kept: together they are a few
 * hundred kilobytes, and an entry is opened many times in a row.
 */
class BundledDictionaryInsights(
    context: Context,
    private val json: Json = Json { ignoreUnknownKeys = true },
) : DictionaryInsightsSource {
    private val appContext = context.applicationContext
    private val lock = Mutex()
    private var examples: DictionaryInsightsParser.Examples? = null
    private var parts: DictionaryInsightsParser.Parts? = null

    override suspend fun examples(word: String, language: AppLanguage): List<ExampleSentence> =
        loadExamples()?.find(word.trim(), language).orEmpty()

    override suspend fun breakdown(character: String, language: AppLanguage): CharacterBreakdown? =
        loadParts()?.find(character.trim(), language)

    private suspend fun loadExamples() = lock.withLock {
        examples ?: read(EXAMPLES_ASSET)?.let { DictionaryInsightsParser.examples(it, json) }
            ?.also { examples = it }
    }

    private suspend fun loadParts() = lock.withLock {
        parts ?: read(PARTS_ASSET)?.let { DictionaryInsightsParser.parts(it, json) }
            ?.also { parts = it }
    }

    private suspend fun read(name: String): String? = withContext(Dispatchers.IO) {
        runCatching { appContext.assets.open(name).bufferedReader().use { it.readText() } }.getOrNull()
    }

    private companion object {
        const val EXAMPLES_ASSET = "hsk-examples.json"
        const val PARTS_ASSET = "hanzi-parts.json"
    }
}

/** Reads the two asset files; separate from the assets so it can be tested. */
internal object DictionaryInsightsParser {

    class Examples(
        private val languages: List<String>,
        private val sentences: List<List<String>>,
        private val words: Map<String, List<Int>>,
    ) {
        fun find(word: String, language: AppLanguage): List<ExampleSentence> {
            val column = languageColumn(languages, language) ?: return emptyList()
            return words[word].orEmpty().mapNotNull { index ->
                val row = sentences.getOrNull(index) ?: return@mapNotNull null
                val translation = row.getOrNull(2 + column)?.takeIf { it.isNotBlank() }
                    ?: return@mapNotNull null
                ExampleSentence(hanzi = row[0], pinyin = row[1], translation = translation)
            }
        }
    }

    class Parts(
        private val languages: List<String>,
        private val chars: Map<String, PartsEntryDto>,
    ) {
        fun find(character: String, language: AppLanguage): CharacterBreakdown? {
            val entry = chars[character] ?: return null
            val column = languageColumn(languages, language) ?: return null
            val hint = entry.hint.getOrNull(column)?.takeIf { it.isNotBlank() } ?: return null
            return CharacterBreakdown(
                character = character,
                parts = entry.parts.mapNotNull { part ->
                    val meaning = part.getOrNull(2 + column) ?: return@mapNotNull null
                    if (part.size < 2) null else CharacterPart(part[0], part[1], meaning)
                },
                hint = hint,
            )
        }
    }

    fun examples(raw: String, json: Json): Examples? = runCatching {
        val dto = json.decodeFromString<ExamplesDto>(raw)
        Examples(dto.languages, dto.sentences, dto.words)
    }.getOrNull()

    fun parts(raw: String, json: Json): Parts? = runCatching {
        val dto = json.decodeFromString<PartsDto>(raw)
        Parts(dto.languages, dto.chars)
    }.getOrNull()

    /** The account language, or Russian — the bundled word list's fallback too. */
    private fun languageColumn(languages: List<String>, language: AppLanguage): Int? =
        languages.indexOf(language.backendCode).takeIf { it >= 0 }
            ?: languages.indexOf(FALLBACK_LANGUAGE).takeIf { it >= 0 }

    private const val FALLBACK_LANGUAGE = "ru"
}

@Serializable
internal data class ExamplesDto(
    @SerialName("languages") val languages: List<String> = emptyList(),
    @SerialName("sentences") val sentences: List<List<String>> = emptyList(),
    @SerialName("words") val words: Map<String, List<Int>> = emptyMap(),
)

@Serializable
internal data class PartsDto(
    @SerialName("languages") val languages: List<String> = emptyList(),
    @SerialName("chars") val chars: Map<String, PartsEntryDto> = emptyMap(),
)

@Serializable
internal data class PartsEntryDto(
    @SerialName("parts") val parts: List<List<String>> = emptyList(),
    @SerialName("hint") val hint: List<String> = emptyList(),
)
