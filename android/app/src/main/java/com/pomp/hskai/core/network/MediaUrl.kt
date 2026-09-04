package com.pomp.hskai.core.network

/**
 * Turns a server-relative media path into an absolute URL, or refuses.
 *
 * Ad media is fetched by the image and video players, which do not go through
 * the Retrofit stack and so are not covered by [OriginGuardInterceptor]. This
 * is the guard for those requests: anything that does not resolve to the
 * app's own API origin returns null and simply is not loaded.
 */
object MediaUrl {

    // Anything that opens with a scheme ("https:", "file:", "javascript:") is
    // a URL, not a media path. Only our own origin is accepted as a URL.
    private val SCHEME = Regex("^[A-Za-z][A-Za-z0-9+.\\-]*:")

    /**
     * @param path what the server sent, e.g. `/uploads/course_ads/clip.mp4`.
     * @param origin the compiled-in API origin, without a trailing slash.
     * @return an absolute https URL under [origin], or null when the value
     *   points anywhere else.
     */
    fun resolve(path: String?, origin: String): String? {
        val trimmed = path?.trim().orEmpty()
        if (trimmed.isEmpty()) return null
        val base = origin.trim().trimEnd('/')
        if (!base.startsWith("https://")) return null

        val absolute = when {
            trimmed.startsWith("/") -> base + trimmed
            // An absolute URL is only allowed when it is our own origin: a
            // creative must never make the app fetch from somewhere else.
            trimmed.startsWith("$base/") -> trimmed
            SCHEME.containsMatchIn(trimmed) -> return null
            else -> "$base/$trimmed"
        }
        // `..` could climb out of the media directory on a sloppy server.
        if (absolute.contains("/../") || absolute.endsWith("/..")) return null
        return absolute
    }
}
