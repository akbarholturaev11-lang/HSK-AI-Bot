package com.pomp.hskai.core.audio

import java.io.File
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class DiskTtsCacheTest {

    private val dir = File(System.getProperty("java.io.tmpdir"), "tts-cache-${System.nanoTime()}")
    private var clock = 1_000L

    @After
    fun tearDown() {
        dir.deleteRecursively()
    }

    private fun cache(maxBytes: Long = 1024) = DiskTtsCache(
        dir = dir,
        maxBytes = maxBytes,
        ioDispatcher = UnconfinedTestDispatcher(),
        now = { clock },
    )

    @Test
    fun `audio written under a key comes back byte for byte`() = runTest {
        val cache = cache()
        val audio = ByteArray(64) { it.toByte() }

        cache.write("-10%|你好", audio)

        assertArrayEquals(audio, cache.read("-10%|你好"))
    }

    @Test
    fun `a phrase that was never fetched reads as a miss`() = runTest {
        assertNull(cache().read("-10%|谢谢"))
    }

    @Test
    fun `the same phrase at a different rate is a different entry`() = runTest {
        val cache = cache()
        cache.write("-10%|你好", "slow".toByteArray())

        assertNull(cache.read("0%|你好"))
    }

    @Test
    fun `the least recently used phrase is dropped once the cap is passed`() = runTest {
        val cache = cache(maxBytes = 300)
        cache.write("a", ByteArray(120))
        clock += 1_000
        cache.write("b", ByteArray(120))
        clock += 1_000

        // Replaying "a" makes "b" the oldest, so the third write must evict "b".
        cache.read("a")
        clock += 1_000
        cache.write("c", ByteArray(120))

        assertNull(cache.read("b"))
        assertEquals(120, cache.read("a")?.size)
        assertEquals(120, cache.read("c")?.size)
    }

    @Test
    fun `audio larger than the whole cache is not written`() = runTest {
        val cache = cache(maxBytes = 100)

        cache.write("a", ByteArray(200))

        assertNull(cache.read("a"))
    }

    @Test
    fun `clearing leaves nothing behind`() = runTest {
        val cache = cache()
        cache.write("a", ByteArray(32))

        cache.clear()

        assertNull(cache.read("a"))
        assertTrue(dir.listFiles().orEmpty().isEmpty())
    }

    @Test
    fun `an unwritable directory degrades to a miss instead of throwing`() = runTest {
        val file = File(dir.parentFile, "tts-not-a-dir-${System.nanoTime()}").also { it.writeText("x") }
        try {
            val cache = DiskTtsCache(dir = file, ioDispatcher = UnconfinedTestDispatcher())
            cache.write("a", ByteArray(8))
            assertNull(cache.read("a"))
        } finally {
            file.delete()
        }
    }
}
