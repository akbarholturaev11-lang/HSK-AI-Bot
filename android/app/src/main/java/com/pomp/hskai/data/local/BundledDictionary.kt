package com.pomp.hskai.data.local

import android.content.Context
import androidx.compose.ui.geometry.Offset
import com.pomp.hskai.core.hanzi.CharacterStrokes
import com.pomp.hskai.core.i18n.AppLanguage
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * The dictionary that ships inside the APK.
 *
 * The word list used to be downloaded on first open and every character's
 * stroke data fetched one request at a time with no cache at all. A learner
 * who installed the app on mobile data and opened it on a train found an
 * empty dictionary; one who had used it before still saw no writing order.
 * Both sets are small and change only with a release, so they travel with it.
 *
 * The server copy still wins when there is one — a deploy can change the list
 * and the bundle would otherwise pin the app to whatever shipped. This is the
 * floor, not the source of truth.
 *
 * Built by `android/tools/build_dictionary_assets.py` from the same files the
 * Mini App's dictionary page uses, so the two cannot drift apart.
 */
class BundledDictionary(
    private val context: Context,
    private val json: Json = Json { ignoreUnknownKeys = true },
) {

    /** The shipped word list, or empty when the asset is somehow unreadable. */
    fun words(language: AppLanguage): List<BundledWord> = runCatching {
        val raw = context.assets.open(WORDS_ASSET).bufferedReader().use { it.readText() }
        json.decodeFromString<List<BundledWordDto>>(raw).mapNotNull { dto ->
            val meaning = dto.meanings[language.backendCode]
                ?: dto.meanings[AppLanguage.DEFAULT.backendCode]
                ?: return@mapNotNull null
            if (dto.hanzi.isBlank() || meaning.isBlank()) return@mapNotNull null
            BundledWord(
                hanzi = dto.hanzi,
                pinyin = dto.pinyin,
                meaning = meaning,
                level = dto.level,
            )
        }
    }.getOrDefault(emptyList())

    /**
     * How one character is written, or null when it is not in the bundle.
     *
     * Named by code point, the same way the server names its own stroke cache,
     * so the two layouts can be compared without translating between them.
     */
    fun strokes(char: String): CharacterStrokes? {
        val single = char.trim().singleOrNull() ?: return null
        return runCatching {
            val raw = context.assets
                .open("$STROKES_DIR/${single.code}.json")
                .bufferedReader()
                .use { it.readText() }
            val dto = json.decodeFromString<BundledStrokesDto>(raw)
            if (dto.strokes.isEmpty()) return null
            CharacterStrokes(
                outlines = dto.strokes,
                medians = dto.medians.map { points ->
                    points.mapNotNull { point ->
                        if (point.size >= 2) Offset(point[0], point[1]) else null
                    }
                },
            )
        }.getOrNull()
    }

    private companion object {
        const val WORDS_ASSET = "dictionary.json"
        const val STROKES_DIR = "strokes"
    }
}

/** One shipped entry, already reduced to the language being shown. */
data class BundledWord(
    val hanzi: String,
    val pinyin: String,
    val meaning: String,
    val level: String,
)

@Serializable
private data class BundledWordDto(
    @SerialName("h") val hanzi: String = "",
    @SerialName("p") val pinyin: String = "",
    @SerialName("m") val meanings: Map<String, String> = emptyMap(),
    @SerialName("lv") val level: String = "",
)

@Serializable
private data class BundledStrokesDto(
    @SerialName("strokes") val strokes: List<String> = emptyList(),
    @SerialName("medians") val medians: List<List<List<Float>>> = emptyList(),
)
