package com.pomp.hskai.data.local

import java.io.ByteArrayOutputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.OkHttpClient
import okhttp3.Request

/** Pre-rendered Mandarin MP3. Implementations must never synthesize speech. */
fun interface WordAudioSource {
    suspend fun find(text: String): ByteArray?
}

/**
 * Reads the immutable, public Cloudflare R2 corpus directly (no API bearer,
 * Railway traffic or TTS generation). CourseRepository writes a successful
 * response to its permanent TtsCache so the same phrase is never re-fetched.
 *
 * An absent or invalid CDN configuration safely returns null; the existing
 * authenticated TTS endpoint remains a fallback for new/dynamic phrases.
 */
class CdnWordAudio(
    baseOrigin: String,
    private val client: OkHttpClient,
) : WordAudioSource {
    private val root: HttpUrl? = baseOrigin.trim().trimEnd('/').toHttpUrlOrNull()
        ?.takeIf { url ->
            url.scheme == "https" && url.username.isEmpty() && url.password.isEmpty() &&
                url.query == null && url.fragment == null
        }
        ?.newBuilder()
        ?.addPathSegments("android/audio/words/v1/")
        ?.build()

    override suspend fun find(text: String): ByteArray? = withContext(Dispatchers.IO) {
        val name = fileName(text) ?: return@withContext null
        val url = root?.newBuilder()?.addPathSegment(name)?.build() ?: return@withContext null
        runCatching {
            client.newCall(Request.Builder().url(url).get().build()).execute().use { response ->
                if (!response.isSuccessful) return@use null
                val body = response.body ?: return@use null
                if (body.contentLength() > MAX_AUDIO_BYTES) return@use null
                val output = ByteArrayOutputStream()
                body.byteStream().use { stream ->
                    val buffer = ByteArray(8192)
                    while (true) {
                        val count = stream.read(buffer)
                        if (count < 0) break
                        if (output.size() + count > MAX_AUDIO_BYTES) {
                            throw java.io.IOException("CDN audio exceeds maximum")
                        }
                        output.write(buffer, 0, count)
                    }
                }
                output.toByteArray().takeIf { bytes ->
                    bytes.size >= 128 &&
                        (bytes.take(3).toByteArray().contentEquals("ID3".toByteArray()) ||
                            (bytes[0].toInt() and 0xff == 0xff &&
                                bytes[1].toInt() and 0xe0 == 0xe0))
                }
            }
        }.getOrNull()
    }

    companion object {
        private const val MAX_AUDIO_BYTES = 1024 * 1024

        /** Must match scripts/build_hsk_offline_audio.py and server filenames. */
        internal fun fileName(text: String): String? {
            val word = text.trim()
            if (word.isEmpty() || word.none { it in '一'..'鿿' } || word.length > 240) return null
            val name = word.map { it.code }.joinToString("_") + ".mp3"
            if (name.toByteArray(Charsets.UTF_8).size <= 240) return name
            val digest = java.security.MessageDigest.getInstance("SHA-1")
                .digest(word.toByteArray(Charsets.UTF_8))
            return "sha1_" + digest.joinToString("") {
                "%02x".format(it.toInt() and 0xff)
            } + ".mp3"
        }
    }
}
