package com.pomp.hskai.core.navigation

/**
 * Every internal destination the app is willing to open from a URI.
 *
 * Resolving a URI is **not** authorisation. Any destination that can show
 * premium material — [Lesson] above all — is only a *request*; the navigation
 * layer must still confirm it against the server's progress and entitlement
 * before showing anything. A URI alone never unlocks content.
 */
sealed interface AppDestination {
    data object Today : AppDestination
    data object Course : AppDestination

    /** The lesson the server currently reports as next. Always safe to ask for. */
    data object CurrentLesson : AppDestination

    /**
     * A specific mini-lesson, as used by the existing reminder flows
     * (`motivation_reminder_service` sends `target_level` + `target_lesson`
     * with `autostart`). Carrying the number here does not mean the lesson is
     * unlocked; the caller resolves entitlement from the server.
     */
    data class Lesson(val order: Int) : AppDestination

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
     * Canonical mini-lesson bounds, matching the backend contract in
     * `app/api/desktop_course.py` (`lesson_order: int = Field(ge=1, le=500)`).
     */
    val LESSON_ORDER_RANGE = 1..500

    /** Digits only, no leading zero and no sign, so `01`/`+5` are rejected. */
    private val LESSON_ORDER_FORMAT = Regex("^[1-9][0-9]{0,2}$")

    /**
     * Resolves a deep link to a known destination, or null when the URI is not
     * on the allowlist. Callers must treat null as "ignore", never as
     * "open whatever the URI said".
     *
     * Matching is exact-arity, mirroring the desktop client's exact path
     * allowlist: an unexpected trailing segment makes the whole URI
     * unrecognised instead of silently resolving to its prefix.
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

        val head = segments.firstOrNull() ?: return null
        val tail = segments.drop(1)

        return when (head) {
            "today" -> AppDestination.Today.takeIf { tail.isEmpty() }
            "course" -> AppDestination.Course.takeIf { tail.isEmpty() }
            "voice" -> AppDestination.Voice.takeIf { tail.isEmpty() }

            "profile" -> when {
                tail.isEmpty() -> AppDestination.Profile
                tail.size == 1 && tail[0] == "widget" -> AppDestination.WidgetSetup
                else -> null
            }

            "lesson" -> when {
                tail.size != 1 -> null
                tail[0] == "current" -> AppDestination.CurrentLesson
                else -> lessonOrder(tail[0])?.let { AppDestination.Lesson(it) }
            }

            "practice" -> when {
                tail.size != 1 -> null
                else -> PracticeTool.fromSlug(tail[0])
                    ?.let { AppDestination.Practice(it) }
            }

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
        is AppDestination.Lesson -> "$SCHEME://lesson/${destination.order}"
        is AppDestination.Practice -> "$SCHEME://practice/${destination.tool.slug}"
    }

    private fun lessonOrder(segment: String): Int? =
        segment.takeIf(LESSON_ORDER_FORMAT::matches)
            ?.toIntOrNull()
            ?.takeIf { it in LESSON_ORDER_RANGE }
}
