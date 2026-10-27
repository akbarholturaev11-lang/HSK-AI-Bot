package com.pomp.hskai.feature.update

import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import com.pomp.hskai.BuildConfig
import java.io.File

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

    @Test
    fun `QA client cannot check download or install a production update`() {
        if (!BuildConfig.QA_BUILD) {
            assertFalse(BuildConfig.APPLICATION_ID.endsWith(".qa"))
            return
        }
        val forbiddenContext = object : ContextWrapper(null) {
            override fun getApplicationContext(): Context = error("QA must not read the release cache or initialize update work")
            override fun getFilesDir(): File = error("QA must not inspect downloaded production APKs")
            override fun startActivity(intent: Intent) = error("QA must not open an APK installer")
        }
        assertNull(fetchRelease(forbiddenContext))
        UpdateWatch.schedule(forbiddenContext)
        UpdateDownload.enqueue(forbiddenContext, UpdateRelease("next", 9999, "https://example.invalid/release.apk", 1))
        forbiddenContext.launchInstaller(File("unused.apk"))
    }

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

    @Test
    fun `download percent stays bounded until the verified file is complete`() {
        assertEquals(0, AppUpdate.downloadPercent(downloadedBytes = 0, totalBytes = 100))
        assertEquals(42, AppUpdate.downloadPercent(downloadedBytes = 42, totalBytes = 100))
        assertEquals(99, AppUpdate.downloadPercent(downloadedBytes = 110, totalBytes = 100))
        assertNull(AppUpdate.downloadPercent(downloadedBytes = 10, totalBytes = 0))
    }

    @Test
    fun `mandatory gate uses exact Direct published release boundary`() {
        val release = UpdateRelease(
            versionName = "1.7.6",
            versionCode = 40,
            url = "https://pub-example.r2.dev/hsk-ai-1.7.6-40-direct-release.apk",
        )
        // Actual releases 10, 18, 32, 40. Code gaps are irrelevant.
        assertFalse(AppUpdate.isMandatoryUpdate(release, 10, minimumSupportedVersionCode = 10))
        assertTrue(AppUpdate.isMandatoryUpdate(release, 9, minimumSupportedVersionCode = 10))
        assertTrue(AppUpdate.isMandatoryUpdate(release, 18, minimumSupportedVersionCode = 32))
        assertFalse(AppUpdate.isMandatoryUpdate(release, 9, minimumSupportedVersionCode = null))
    }

    @Test
    fun `one update tap opens installer after successful download while app is active`() {
        val ready = UpdateInstallCoordinator.shouldAutoInstall(
            pendingVersionCode = 42,
            releaseVersionCode = 42,
            phase = UpdatePhase.Downloaded,
            fileIsValid = true,
            canInstall = true,
            resumed = true,
        )
        assertTrue(ready)
    }

    @Test
    fun `installer does not auto-open prematurely or for another version`() {
        fun check(pending: Int, version: Int, phase: UpdatePhase, valid: Boolean,
                  permission: Boolean, resumed: Boolean): Boolean =
            UpdateInstallCoordinator.shouldAutoInstall(
                pending, version, phase, valid, permission, resumed,
            )
        assertFalse(check(42, 42, UpdatePhase.Ready, false, true, true))
        assertFalse(check(42, 42, UpdatePhase.Downloading, false, true, true))
        assertFalse(check(42, 42, UpdatePhase.Failed, false, true, true))
        assertFalse(check(41, 42, UpdatePhase.Downloaded, true, true, true))
        assertFalse(check(42, 42, UpdatePhase.Downloaded, false, true, true))
        assertFalse(check(42, 42, UpdatePhase.Downloaded, true, false, true))
        assertFalse(check(42, 42, UpdatePhase.Downloaded, true, true, false))
    }
}
