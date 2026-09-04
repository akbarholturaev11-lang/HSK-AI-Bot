package com.pomp.hskai.core.network

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class MediaUrlTest {

    private val origin = "https://pomp.example"

    @Test
    fun `a server path becomes an absolute url under our own origin`() {
        assertEquals(
            "https://pomp.example/uploads/course_ads/clip.mp4",
            MediaUrl.resolve("/uploads/course_ads/clip.mp4", origin),
        )
    }

    @Test
    fun `a trailing slash on the origin does not double up`() {
        assertEquals(
            "https://pomp.example/uploads/a.jpg",
            MediaUrl.resolve("/uploads/a.jpg", "https://pomp.example/"),
        )
    }

    @Test
    fun `a relative path without a leading slash still resolves`() {
        assertEquals(
            "https://pomp.example/uploads/a.jpg",
            MediaUrl.resolve("uploads/a.jpg", origin),
        )
    }

    @Test
    fun `our own absolute url is accepted unchanged`() {
        val url = "$origin/uploads/a.jpg"
        assertEquals(url, MediaUrl.resolve(url, origin))
    }

    @Test
    fun `another host is refused rather than fetched`() {
        // The players do not go through the Retrofit origin guard, so this is
        // the only thing standing between a creative and an arbitrary host.
        assertNull(MediaUrl.resolve("https://evil.example/a.mp4", origin))
        assertNull(MediaUrl.resolve("http://pomp.example/a.mp4", origin))
        assertNull(MediaUrl.resolve("file:///etc/passwd", origin))
        assertNull(MediaUrl.resolve("javascript:alert(1)", origin))
    }

    @Test
    fun `climbing out of the media directory is refused`() {
        assertNull(MediaUrl.resolve("/uploads/../../secret", origin))
        assertNull(MediaUrl.resolve("/uploads/..", origin))
    }

    @Test
    fun `nothing to load returns null instead of a broken url`() {
        assertNull(MediaUrl.resolve(null, origin))
        assertNull(MediaUrl.resolve("", origin))
        assertNull(MediaUrl.resolve("   ", origin))
    }

    @Test
    fun `an insecure origin is refused outright`() {
        assertNull(MediaUrl.resolve("/uploads/a.jpg", "http://pomp.example"))
        assertNull(MediaUrl.resolve("/uploads/a.jpg", ""))
    }
}
