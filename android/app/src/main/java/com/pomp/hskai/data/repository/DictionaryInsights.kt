package com.pomp.hskai.data.repository

import com.pomp.hskai.core.i18n.AppLanguage

/** A real sentence that uses the word, as the course teaches it. */
data class ExampleSentence(
    val hanzi: String,
    val pinyin: String,
    val translation: String,
)

/** One building block of a character: 女 in 好. */
data class CharacterPart(
    val hanzi: String,
    val pinyin: String,
    val meaning: String,
)

/**
 * What a character is made of and a line that makes it stick.
 *
 * A pictograph has no parts; its [hint] describes the picture instead.
 */
data class CharacterBreakdown(
    val character: String,
    val parts: List<CharacterPart>,
    val hint: String,
)

/** The parts of a dictionary entry beyond the word itself, all on the device. */
interface DictionaryInsightsSource {
    suspend fun examples(word: String, language: AppLanguage): List<ExampleSentence>
    suspend fun breakdown(character: String, language: AppLanguage): CharacterBreakdown?
}
