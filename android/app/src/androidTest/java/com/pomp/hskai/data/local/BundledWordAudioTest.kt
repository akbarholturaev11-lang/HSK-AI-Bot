package com.pomp.hskai.data.local

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.core.audio.AndroidLessonAudioPlayer
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/**
 * The bundled pronunciation plays on the phone itself.
 *
 * The files are re-encoded at build time (trimmed, 32 kbps), so this is the
 * check that the result is still an MP3 the platform player accepts — with
 * nothing fetched, which is the point of bundling them.
 */
@RunWith(AndroidJUnit4::class)
class BundledWordAudioTest {

    private val context = InstrumentationRegistry.getInstrumentation().targetContext
    private val audio = BundledWordAudio(context)

    @Test
    fun dictionaryWordsAreInTheApkAndPlay() {
        val player = AndroidLessonAudioPlayer(context)
        try {
            for (word in listOf("好", "你们", "对不起", "春(天)")) {
                val mp3 = audio.find(word)
                assertNotNull(word, mp3)
                assertTrue(word, mp3!!.size > 1_000)
                // play() returns once the player has prepared and started.
                runBlocking { withTimeout(5_000) { player.play(mp3) } }
            }
        } finally {
            player.release()
        }
    }

    @Test
    fun anythingElseIsNotBundled() {
        assertNull(audio.find("这不是词典里的句子"))
        assertNull(audio.find("hello"))
    }
}
