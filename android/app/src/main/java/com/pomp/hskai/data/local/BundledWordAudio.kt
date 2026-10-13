package com.pomp.hskai.data.local

import android.content.Context

/**
 * The pronunciation of every dictionary word, shipped inside the APK.
 *
 * Rendered by `android/tools/build_word_audio.py` with the server's own voice
 * and rate, so a word sounds the same whether it comes from here or from
 * `/api/v3/android/tts`. With it the listen button works with no connection.
 *
 * Files are named by the word's code points: 你们 -> `20320_20204.mp3`.
 */
class BundledWordAudio(context: Context) {
    private val appContext = context.applicationContext

    /** The word's MP3, or null when it is not a bundled dictionary word. */
    fun find(text: String): ByteArray? {
        val name = fileName(text) ?: return null
        return runCatching {
            appContext.assets.open("$AUDIO_DIR/$name").use { it.readBytes() }
        }.getOrNull()?.takeIf { it.isNotEmpty() }
    }

    companion object {
        private const val AUDIO_DIR = "audio/words"

        /**
         * The asset name for [text], or null when there is no Chinese in it.
         *
         * Every character counts, brackets included: the list has entries
         * such as 春(天), and the file is named after the entry as written.
         */
        internal fun fileName(text: String): String? {
            val word = text.trim()
            if (word.none { it in '一'..'鿿' }) return null
            val name = word.map { it.code }.joinToString("_") + ".mp3"
            if (name.toByteArray(Charsets.UTF_8).size <= 240) return name
            // Long lesson sentences need a short, deterministic Android asset name.
            // Keep this SHA-1 naming identical to the Python offline generator.
            val digest = java.security.MessageDigest.getInstance("SHA-1")
                .digest(word.toByteArray(Charsets.UTF_8))
            return "sha1_" + digest.joinToString("") {
                "%02x".format(it.toInt() and 0xff)
            } + ".mp3"
        }
    }
}
