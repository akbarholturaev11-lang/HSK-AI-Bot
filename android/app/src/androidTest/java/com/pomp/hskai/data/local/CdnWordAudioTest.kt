package com.pomp.hskai.data.local

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.runBlocking
import okhttp3.OkHttpClient
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/** The Play and direct APKs ship no dictionary MP3s; audio is fetched once. */
@RunWith(AndroidJUnit4::class)
class CdnWordAudioTest {

    @Test
    fun noMandarinMp3IsBundledInsideTheApk() {
        val assets = InstrumentationRegistry.getInstrumentation().targetContext.assets
        assertTrue(assets.list("audio/words").isNullOrEmpty())
    }

    @Test
    fun filenamesAreStillSharedWithPythonAndMiniApp() {
        assertEquals("20320_20204.mp3", CdnWordAudio.fileName("你们"))
        assertEquals("26149_40_22825_41.mp3", CdnWordAudio.fileName("春(天)"))
        assertNull(CdnWordAudio.fileName("hello"))
    }

    @Test
    fun absentCdnOriginDoesNotMakeUnexpectedRequests() = runBlocking {
        assertNull(CdnWordAudio("", OkHttpClient()).find("你好"))
    }
}
