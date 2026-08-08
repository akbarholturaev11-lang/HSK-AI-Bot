package com.pomp.hskai.core.navigation

/**
 * Every internal destination the app is willing to open from a URI.
 *
 * Widgets, notifications and external links may only ask for one of these.
 * Arbitrary paths are rejected rather than forwarded, and a premium
 * destination is still gated by server entitlement after routing — the URI
 * alone never unlocks content.
 */
sealed interface AppDestination {
    data object Today : AppDestination
    data object Course : AppDestination
    data object CurrentLesson : AppDestination
    data object Voice : AppDestination
    data object Profile : AppDestination
    data object WidgetSetup : AppDestination
    data class Practice(val tool: PracticeTool) : AppDestination
}

enum class PracticeTool(val slug: String) {
    MISTAKES("mistakes"),
    RECOGNITION("recognition"),
    MEMORIZE("memorize"),
    PRONUNCIATION("pronunciation"),
    TESTS("tests"),
    ;

    companion object {
        fun fromSlug(value: String?): PracticeTool? =
            entries.firstOrNull { it.slug == value?.trim()?.lowercase() }
    }
}

object DeepLinkRouter {

    const val SCHEME = "pomp-hsk-ai"

    /**
     * Resolves a deep link to a known destination, or null when the URI is not
     * on the allowlist. Callers must treat null as "ignore", never as
     * "open whatever the URI said".
     *
     * Parsing is deliberately done here rather than via `android.net.Uri`, so
     * the allowlist is plain Kotlin and fully covered by JVM unit tests.
     */
    fun resolve(raw: String?): AppDestination? {
        val value = raw?.trim().orEmpty()
        val prefix = "$SCHEME://"
        if (!value.startsWith(prefix, ignoreCase = true)) return null
        val body = value.substring(prefix.length)
            .substringBefore('?')
            .substringBefore('#')
        val segments = body.split('/')
            .map { it.trim().lowercase() }
            .filter { it.isNotEmpty() }
        return when (segments.firstOrNull()) {
            "today" -> AppDestination.Today
            "course" -> AppDestination.Course
            "voice" -> AppDestination.Voice
            "profile" -> when (segments.getOrNull(1)) {
                null -> AppDestination.Profile
                "widget" -> AppDestination.WidgetSetup
                else -> null
            }

            "lesson" -> when (segments.getOrNull(1)) {
                // Only "the lesson the server says is current" is addressable.
                // A specific lesson number from a URI is deliberately not.
                "current" -> AppDestination.CurrentLesson
                else -> null
            }

            "practice" -> PracticeTool.fromSlug(segments.getOrNull(1))
                ?.let { AppDestination.Practice(it) }

            else -> null
        }
    }

    fun uriFor(destination: AppDestination): String = when (destination) {
        AppDestination.Today -> "$SCHEME://today"
        AppDestination.Course -> "$SCHEME://course"
        AppDestination.CurrentLesson -> "$SCHEME://lesson/current"
        AppDestination.Voice -> "$SCHEME://voice"
        AppDestination.Profile -> "$SCHEME://profile"
        AppDestination.WidgetSetup -> "$SCHEME://profile/widget"
        is AppDestination.Practice -> "$SCHEME://practice/${destination.tool.slug}"
    }
}
