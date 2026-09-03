package com.pomp.hskai.core.text

import java.text.Normalizer
import java.util.Locale

/**
 * Tone-insensitive pinyin, used only for searching.
 *
 * Learners type "ni hao" long before they type "nǐ hǎo", and a dictionary that
 * only answers the second one is a dictionary they stop opening. The stored
 * reading keeps its tone marks; this is the extra column the query runs
 * against.
 */
object PinyinSearch {

    /**
     * Lowercased, tone marks removed, spaces and apostrophes dropped.
     *
     * `ü` is deliberately folded to `v`, the substitution every Chinese
     * keyboard teaches, so "lv" finds 绿 (lǜ).
     */
    fun plain(pinyin: String?): String {
        val raw = pinyin?.trim().orEmpty()
        if (raw.isEmpty()) return ""
        val lower = raw.lowercase(Locale.ROOT)
        // "ǚ" decomposes to "u" + umlaut + tone; folding it before the
        // diacritics are stripped keeps it as "v" instead of a bare "u".
        val vowelFolded = lower.replace('ü', 'v').replace('ǖ', 'v')
            .replace('ǘ', 'v').replace('ǚ', 'v').replace('ǜ', 'v')
        val decomposed = Normalizer.normalize(vowelFolded, Normalizer.Form.NFD)
        val builder = StringBuilder(decomposed.length)
        for (character in decomposed) {
            when {
                // Combining marks: the tone accents themselves.
                character.code in 0x0300..0x036F -> Unit
                character.isLetterOrDigit() -> builder.append(character)
                else -> Unit
            }
        }
        return builder.toString()
    }
}
