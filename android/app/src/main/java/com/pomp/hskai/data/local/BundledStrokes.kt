package com.pomp.hskai.data.local

import android.content.Context
import androidx.compose.ui.geometry.Offset
import com.pomp.hskai.core.hanzi.CharacterStrokes
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * How every dictionary character is written, shipped inside the APK.
 *
 * The word list travels with the app too (`AssetBundledDictionarySource`), but
 * the writing order used to be fetched one request at a time with no cache at
 * all: a learner with no connection saw the words and an empty writing box.
 * Both halves of the dictionary now work offline, and neither costs a round
 * trip for something that only changes with a release.
 *
 * Files are named by code point, the same way the server names its own stroke
 * cache (`{ord(char)}.json`), so the two layouts can be compared without
 * translating between them.
 *
 * Built by `android/tools/build_stroke_assets.py` from the same data the Mini
 * App's dictionary page uses, so the two cannot drift apart.
 */
class BundledStrokes(
    context: Context,
    private val json: Json = Json { ignoreUnknownKeys = true },
) {
    private val appContext = context.applicationContext

    /** The character's writing data, or null when it is not in the bundle. */
    fun find(char: String): CharacterStrokes? {
        val single = char.trim().singleOrNull() ?: return null
        return runCatching {
            val raw = appContext.assets
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
        const val STROKES_DIR = "strokes"
    }
}

@Serializable
private data class BundledStrokesDto(
    @SerialName("strokes") val strokes: List<String> = emptyList(),
    @SerialName("medians") val medians: List<List<List<Float>>> = emptyList(),
)
