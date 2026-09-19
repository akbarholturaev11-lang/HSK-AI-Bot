package com.pomp.hskai.feature.update

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * When an update stops being an offer and starts being a nudge.
 *
 * Both rules are arithmetic on version codes and nothing else, which is the
 * point: the banner appearing one release too early would put a red line
 * across every screen of an app that is merely a week old, and a second
 * notification for a release already announced is how people switch the
 * channel off.
 */
class UpdateNudgeTest {

    private fun release(versionCode: Int) = UpdateRelease(
        versionName = "1.2.$versionCode",
        versionCode = versionCode,
        url = "https://pub-example.r2.dev/hsk-ai-1.2.$versionCode-$versionCode-direct-release.apk",
        size = 3_766_687L,
    )

    @Test
    fun `one missed release is the profile card's business alone`() {
        assertFalse(
            AppUpdate.isFarBehind(release = release(5), installedVersionCode = 4),
        )
    }

    @Test
    fun `two missed releases raise the banner`() {
        assertTrue(
            AppUpdate.isFarBehind(release = release(6), installedVersionCode = 4),
        )
    }

    @Test
    fun `and it stays up the further behind the install falls`() {
        assertTrue(
            AppUpdate.isFarBehind(release = release(9), installedVersionCode = 4),
        )
    }

    @Test
    fun `a release is announced once`() {
        assertTrue(AppUpdate.shouldAnnounce(release = release(5), announcedVersionCode = 4))
        assertFalse(AppUpdate.shouldAnnounce(release = release(5), announcedVersionCode = 5))
    }

    @Test
    fun `nothing was announced yet on a fresh install`() {
        assertTrue(AppUpdate.shouldAnnounce(release = release(5), announcedVersionCode = 0))
    }
}
