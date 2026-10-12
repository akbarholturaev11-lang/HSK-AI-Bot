package com.pomp.hskai.core.audio

import java.io.File
import java.security.MessageDigest
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class DiskTtsCacheTest {

    private val root = File(System.getProperty("java.io.tmpdir"), "tts-persistent-${System.nanoTime()}")
    private val dir = File(root, "files/mandarin_audio")
    private val oldDir = File(root, "cache/tts")

    @After
    fun tearDown() {
        root.deleteRecursively()
    }

    private fun cache() = DiskTtsCache(
        dir = dir,
        legacyDir = oldDir,
        ioDispatcher = UnconfinedTestDispatcher(),
    )

    @Test
    fun `phrase is stored byte for byte in durable filesDir`() = runTest {
        val library = cache()
        val audio = ByteArray(128) { it.toByte() }

        library.write("-10%|你好", audio)
        assertArrayEquals(audio, library.read("-10%|你好"))
        assertEquals(1, dir.listFiles().orEmpty().size)
        assertTrue(dir.listFiles()!!.single().name.endsWith(".audio"))
    }

    @Test
    fun `cache can reopen in a new instance with network unavailable`() = runTest {
        cache().write("-10%|你好", "saved-on-phone".toByteArray())

        val reopened = cache()

        assertEquals("saved-on-phone", String(reopened.read("-10%|你好")!!))
        assertNull(reopened.read("-10%|谢谢"))
    }

    @Test
    fun `same phrase at another generation rate has another file`() = runTest {
        val library = cache()
        library.write("-10%|你好", "slow".toByteArray())

        assertNull(library.read("0%|你好"))
    }

    @Test
    fun `first download is kept even if server might later return different audio`() = runTest {
        val library = cache()
        library.write("-10%|你好", "first-voice".toByteArray())

        library.write("-10%|你好", "second-voice".toByteArray())

        assertEquals("first-voice", String(library.read("-10%|你好")!!))
    }

    @Test
    fun `files never expire when total bytes exceed the former 24 MB limit`() = runTest {
        val library = cache()
        val audio = ByteArray(9 * 1024 * 1024) { 42 }
        for (word in listOf("你好", "再见", "谢谢")) {
            library.write("-10%|" + word, audio)
        }

        assertTrue(dir.listFiles().orEmpty().sumOf { it.length() } > 24L * 1024 * 1024)
        assertArrayEquals(audio, library.read("-10%|你好"))
        assertArrayEquals(audio, library.read("-10%|再见"))
        assertArrayEquals(audio, library.read("-10%|谢谢"))
    }

    @Test
    fun `older cacheDir mp3 files migrate into filesDir instead of being lost`() = runTest {
        val key = "-10%|你好"
        val digest = MessageDigest.getInstance("SHA-256")
            .digest(key.toByteArray(Charsets.UTF_8))
            .joinToString(separator = "") { "%02x".format(it) }
        oldDir.mkdirs()
        val oldAudio = File(oldDir, "$digest.mp3")
        oldAudio.writeBytes("old-mp3".toByteArray())

        val library = cache()
        assertEquals("old-mp3", String(library.read(key)!!))
        assertFalse(oldAudio.exists())
        assertEquals(1, dir.listFiles().orEmpty().size)

        // The migration no longer needs cacheDir to exist after first use.
        oldDir.deleteRecursively()
        assertEquals("old-mp3", String(cache().read(key)!!))
    }

    @Test
    fun `explicit deletion is the only operation that removes stored recordings`() = runTest {
        val library = cache()
        library.write("a", ByteArray(32))

        library.clear()

        assertNull(library.read("a"))
        assertTrue(dir.listFiles().orEmpty().isEmpty())
    }

    @Test
    fun `an unwritable directory degrades gracefully instead of throwing`() = runTest {
        root.mkdirs()
        val notADir = File(root, "not-a-directory").also { it.writeText("x") }
        val library = DiskTtsCache(dir = notADir, ioDispatcher = UnconfinedTestDispatcher())

        library.write("a", ByteArray(8))

        assertNull(library.read("a"))
    }
}
