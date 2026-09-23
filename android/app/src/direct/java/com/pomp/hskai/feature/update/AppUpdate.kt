package com.pomp.hskai.feature.update

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * A build the server says exists, already checked against the one running.
 */
@Serializable
data class UpdateRelease(
    @SerialName("version_name") val versionName: String,
    @SerialName("version_code") val versionCode: Int,
    val url: String,
    val size: Long = 0L,
)

/**
 * Reading the server's answer, with no Android in the way.
 *
 * The server already refuses to offer an update to a caller that is current,
 * and already validates the link. This checks both again anyway: the client
 * is the side that downloads a file and asks the system to install it, and a
 * client that trusts the answer blindly will cheerfully re-offer the build it
 * is already running the day the server gets it wrong — a card that never goes
 * away is a card people learn to ignore.
 */
object AppUpdate {

    /**
     * How many releases someone has to miss before the profile card stops
     * being enough.
     *
     * Every release raises `versionCode` by exactly one, so the gap between
     * the installed code and the published one is the number of releases
     * skipped. One missed release is ordinary — the card in the profile says
     * so and that is the end of it. Two means the card has been passed over
     * at least once, and a learner running a build two releases old is the
     * one who reports bugs that were fixed weeks ago.
     */
    const val NUDGE_AFTER_MISSED_RELEASES = 2
    const val CHECK_CACHE_TTL_MILLIS = 30L * 60L * 1000L

    private val json = Json { ignoreUnknownKeys = true }

    fun isCheckCacheFresh(
        checkedAtMillis: Long,
        nowMillis: Long,
        checkedVersionCode: Int,
        installedVersionCode: Int,
    ): Boolean {
        if (checkedVersionCode != installedVersionCode || checkedAtMillis <= 0L) return false
        val age = nowMillis - checkedAtMillis
        return age in 0 until CHECK_CACHE_TTL_MILLIS
    }

    fun parse(status: Int, body: String?, installedVersionCode: Int): UpdateRelease? {
        if (status != 200 || body.isNullOrBlank()) return null
        val release = try {
            json.decodeFromString(UpdateRelease.serializer(), body)
        } catch (error: Exception) {
            return null
        }
        if (release.versionCode <= installedVersionCode) return null
        if (release.versionName.isBlank()) return null
        if (!isInstallableUrl(release.url)) return null
        return release
    }

    /**
     * Only a plain https link to an `.apk`.
     *
     * This is not the real defence — Android refuses to install an update that
     * is not signed by the same key as the installed app, so a swapped file
     * cannot replace this app with something else. It is the cheap one: it
     * stops the app downloading and opening whatever a mistyped setting points
     * at, long before the system gets a chance to say no.
     */
    fun isInstallableUrl(url: String): Boolean {
        val trimmed = url.trim()
        if (!trimmed.startsWith("https://", ignoreCase = true)) return false
        if (trimmed.length > 2048) return false
        val withoutScheme = trimmed.removePrefix("https://").removePrefix("HTTPS://")
        if (withoutScheme.contains('@')) return false
        val path = withoutScheme.substringBefore('?').substringBefore('#')
        if (!path.contains('/')) return false
        return path.endsWith(".apk", ignoreCase = true)
    }

    /**
     * Whether the bytes on disk are the bytes we were promised.
     *
     * Catches the release that was uploaded to the bot and to storage as two
     * different files — the one failure the signature check cannot catch,
     * because both would be signed by us.
     */
    fun isExpectedSize(downloadedBytes: Long, announcedBytes: Long): Boolean {
        if (announcedBytes <= 0L) return downloadedBytes > 0L
        return downloadedBytes == announcedBytes
    }

    /**
     * Whether this install is far enough behind to be told so on every screen.
     *
     * [parse] has already refused anything that is not newer, so the only
     * question left is the size of the gap.
     */
    fun isFarBehind(release: UpdateRelease, installedVersionCode: Int): Boolean =
        release.versionCode - installedVersionCode >= NUDGE_AFTER_MISSED_RELEASES

    /**
     * Whether this release still owes the learner a notification.
     *
     * One per release, ever: the code of the last release announced is kept
     * on the device, so reopening the app, a second background check the same
     * day and a reinstall of the same build all stay silent. Announcing a
     * release twice is how a notification becomes the thing people switch off.
     */
    fun shouldAnnounce(release: UpdateRelease, announcedVersionCode: Int): Boolean =
        release.versionCode > announcedVersionCode
}
