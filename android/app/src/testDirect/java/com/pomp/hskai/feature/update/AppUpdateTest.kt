package com.pomp.hskai.feature.update

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * What this app is willing to download and hand to the system installer.
 *
 * The server already filters and validates, so every case here is the same
 * question asked twice on purpose: this is the side that writes a file to disk
 * and opens an install dialog over it, and it must not do that because an
 * answer arrived saying it should.
 */
class AppUpdateTest {

    private val body = """
        {"version_name":"1.2.0","version_code":3,
         "url":"https://pub-example.r2.dev/hsk-ai-1.2.0-3-direct-release.apk",
         "size":3766687}
    """.trimIndent()

    @Test
    fun `update check cache is fresh only inside ttl for the same installed build`() {
        val ttl = AppUpdate.CHECK_CACHE_TTL_MILLIS
        val checkedAt = 10_000L

        assertTrue(
            AppUpdate.isCheckCacheFresh(
                checkedAtMillis = checkedAt,
                nowMillis = checkedAt + ttl - 1,
                checkedVersionCode = 7,
                installedVersionCode = 7,
            )
        )
        assertFalse(
            AppUpdate.isCheckCacheFresh(
                checkedAtMillis = checkedAt,
                nowMillis = checkedAt + ttl,
                checkedVersionCode = 7,
                installedVersionCode = 7,
            )
        )
        assertFalse(
            AppUpdate.isCheckCacheFresh(
                checkedAtMillis = checkedAt,
                nowMillis = checkedAt + 1,
                checkedVersionCode = 6,
                installedVersionCode = 7,
            )
        )
        assertFalse(
            AppUpdate.isCheckCacheFresh(
                checkedAtMillis = checkedAt,
                nowMillis = checkedAt - 1,
                checkedVersionCode = 7,
                installedVersionCode = 7,
            )
        )
    }

    @Test
    fun `a newer build is read back whole`() {
        val release = AppUpdate.parse(status = 200, body = body, installedVersionCode = 2)

        assertEquals("1.2.0", release?.versionName)
        assertEquals(3, release?.versionCode)
        assertEquals(3766687L, release?.size)
        assertTrue(release?.url?.endsWith(".apk") == true)
    }

    @Test
    fun `no content means no card`() {
        assertNull(AppUpdate.parse(status = 204, body = null, installedVersionCode = 2))
        assertNull(AppUpdate.parse(status = 204, body = "", installedVersionCode = 2))
    }

    @Test
    fun `a server error is not an update`() {
        for (status in listOf(400, 404, 500, 503)) {
            assertNull(AppUpdate.parse(status = status, body = body, installedVersionCode = 2))
        }
    }

    @Test
    fun `the build already running is never offered again`() {
        // The card that never goes away is the card people learn to ignore,
        // so this is checked here even though the server filters it too.
        assertNull(AppUpdate.parse(status = 200, body = body, installedVersionCode = 3))
        assertNull(AppUpdate.parse(status = 200, body = body, installedVersionCode = 4))
    }

    @Test
    fun `nonsense in place of a response is ignored`() {
        for (broken in listOf("not json", "{}", "[]", """{"version_code":3}""")) {
            assertNull(AppUpdate.parse(status = 200, body = broken, installedVersionCode = 2))
        }
    }

    @Test
    fun `a release with no version name is refused`() {
        val nameless = body.replace(""""version_name":"1.2.0"""", """"version_name":""""")
        assertNull(AppUpdate.parse(status = 200, body = nameless, installedVersionCode = 2))
    }

    @Test
    fun `only a plain https apk link is downloadable`() {
        assertTrue(AppUpdate.isInstallableUrl("https://pub.example.dev/app.apk"))
        assertTrue(AppUpdate.isInstallableUrl("https://pub.example.dev/a/b/app.APK"))
        assertTrue(AppUpdate.isInstallableUrl("https://pub.example.dev/app.apk?v=3"))
    }

    @Test
    fun `anything else is refused before a byte is fetched`() {
        for (url in listOf(
            "http://pub.example.dev/app.apk",
            "https://pub.example.dev/app.zip",
            "https://pub.example.dev/",
            "https://user:secret@pub.example.dev/app.apk",
            "ftp://pub.example.dev/app.apk",
            "app.apk",
            "",
        )) {
            assertFalse(url, AppUpdate.isInstallableUrl(url))
        }
    }

    @Test
    fun `a release behind a refused link never becomes a card`() {
        val insecure = body.replace("https://", "http://")
        assertNull(AppUpdate.parse(status = 200, body = insecure, installedVersionCode = 2))
    }

    @Test
    fun `a download that is not the promised file is rejected`() {
        // The one failure the signature check cannot catch: the release was
        // uploaded to the bot and to storage as two different builds, both
        // signed by us.
        assertTrue(AppUpdate.isExpectedSize(downloadedBytes = 100, announcedBytes = 100))
        assertFalse(AppUpdate.isExpectedSize(downloadedBytes = 99, announcedBytes = 100))
        assertFalse(AppUpdate.isExpectedSize(downloadedBytes = 0, announcedBytes = 100))
    }

    @Test
    fun `an unannounced size only requires that something arrived`() {
        assertTrue(AppUpdate.isExpectedSize(downloadedBytes = 100, announcedBytes = 0))
        assertFalse(AppUpdate.isExpectedSize(downloadedBytes = 0, announcedBytes = 0))
    }
}
