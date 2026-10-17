package com.pomp.hskai.core.navigation

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class DeepLinkRouterTest {

    @Test
    fun `OAuth browser return is wake up only with no callback payload`() {
        assertEquals(true, DeepLinkRouter.isAuthReturn("${DeepLinkRouter.SCHEME}://oauth-return"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://oauth-return"))
        listOf(
            null, "", "https://oauth-return", "${DeepLinkRouter.SCHEME}://oauth-return/extra",
            "${DeepLinkRouter.SCHEME}://oauth-return?access_token=untrusted", "${DeepLinkRouter.SCHEME}://oauth-return#linked",
            "${DeepLinkRouter.SCHEME}://user@oauth-return", "${DeepLinkRouter.SCHEME}://oauth-return:443",
            "${DeepLinkRouter.SCHEME}://oauth-return.evil", "${DeepLinkRouter.SCHEME}://auth/complete",
        ).forEach { assertEquals(it, false, DeepLinkRouter.isAuthReturn(it)) }
        val otherScheme = if (com.pomp.hskai.BuildConfig.QA_BUILD) "pomp-hsk-ai" else "pomp-hsk-ai-qa"
        assertEquals(false, DeepLinkRouter.isAuthReturn("$otherScheme://oauth-return"))
        assertNull(DeepLinkRouter.resolve("$otherScheme://course"))
    }

    @Test
    fun `allowlisted destinations resolve`() {
        assertEquals(AppDestination.Today, DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://today"))
        assertEquals(AppDestination.Course, DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://course"))
        assertEquals(AppDestination.Voice, DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://voice"))
        assertEquals(AppDestination.Rating, DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://rating"))
        assertEquals(AppDestination.Profile, DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://profile"))
        assertEquals(AppDestination.Subscription, DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://subscription"))
        assertEquals(
            AppDestination.Subscription,
            DeepLinkRouter.resolve(DeepLinkRouter.uriFor(AppDestination.Subscription)),
        )
        assertEquals(
            AppDestination.WidgetSetup,
            DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://profile/widget"),
        )
        assertEquals(
            AppDestination.CurrentLesson,
            DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://lesson/current"),
        )
        assertEquals(
            AppDestination.Practice(PracticeTool.MISTAKES),
            DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://practice/mistakes"),
        )
        assertEquals(
            AppDestination.Practice(PracticeTool.RECOGNITION),
            DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://practice/recognition"),
        )
    }

    /**
     * `practice` with no tool is the section home. It is the link the release
     * feedback's "try it" button sends, and it used to resolve to nothing at
     * all, so tapping that button left the app exactly where it was.
     */
    @Test
    fun `practice with no tool opens the section home`() {
        assertEquals(
            AppDestination.Practice(),
            DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://practice"),
        )
        assertEquals(
            AppDestination.Practice(),
            DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://practice/"),
        )
        assertNull(AppDestination.Practice().tool)
    }

    @Test
    fun `every tool survives a round trip through its own uri`() {
        PracticeTool.entries.forEach { tool ->
            val destination = AppDestination.Practice(tool)
            assertEquals(destination, DeepLinkRouter.resolve(DeepLinkRouter.uriFor(destination)))
        }
        val home = AppDestination.Practice()
        assertEquals(home, DeepLinkRouter.resolve(DeepLinkRouter.uriFor(home)))
    }

    /**
     * The existing reminder flows already target an exact lesson
     * (`motivation_reminder_service` sends `target_level` + `target_lesson`
     * with `autostart`), so Android has to be able to address one when those
     * reminders become Android notifications.
     *
     * Resolving the URI is not authorisation: it only produces a request that
     * the navigation layer must check against server progress and entitlement.
     */
    @Test
    fun `a specific lesson is addressable but only as a request`() {
        assertEquals(
            AppDestination.Lesson(181),
            DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://lesson/181"),
        )
        assertEquals(
            AppDestination.Lesson(1),
            DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://lesson/1"),
        )
        // The destination carries a number and nothing else — no entitlement,
        // no unlock flag, nothing the URI could assert about access.
        val destination = DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://lesson/42")
        assertEquals(AppDestination.Lesson(42), destination)
    }

    @Test
    fun `lesson numbers outside the backend contract are rejected`() {
        // app/api/desktop_course.py bounds lesson_order to 1..500.
        assertEquals(500, DeepLinkRouter.LESSON_ORDER_RANGE.last)
        assertEquals(
            AppDestination.Lesson(500),
            DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://lesson/500"),
        )
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://lesson/501"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://lesson/0"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://lesson/-1"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://lesson/+5"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://lesson/007"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://lesson/abc"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://lesson/1e3"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://lesson"))
    }

    /**
     * Matching is exact-arity, like the desktop client's path allowlist. A
     * trailing segment must invalidate the whole URI rather than let it
     * resolve to its prefix.
     */
    @Test
    fun `an unexpected trailing segment invalidates the uri`() {
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://lesson/current/extra"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://lesson/12/extra"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://today/extra"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://course/extra"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://voice/extra"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://profile/widget/extra"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://practice/mistakes/extra"))
    }

    @Test
    fun `foreign schemes and unknown paths are rejected`() {
        assertNull(DeepLinkRouter.resolve(null))
        assertNull(DeepLinkRouter.resolve(""))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://"))
        assertNull(DeepLinkRouter.resolve("https://evil.example.com/today"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://admin"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://practice/unknown-tool"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://rating/weekly"))
        assertNull(DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://profile/billing"))
        assertNull(DeepLinkRouter.resolve("javascript:alert(1)"))
    }

    @Test
    fun `case and query noise do not bypass the allowlist`() {
        assertEquals(
            AppDestination.Today,
            DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME.uppercase()}://Today"),
        )
        assertEquals(
            AppDestination.Practice(PracticeTool.PRONUNCIATION),
            DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://practice/PRONUNCIATION?src=widget"),
        )
        assertEquals(
            AppDestination.Course,
            DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://course/#top"),
        )
        assertEquals(
            AppDestination.Lesson(7),
            DeepLinkRouter.resolve("${DeepLinkRouter.SCHEME}://lesson/7?source=d1_recovery"),
        )
    }

    @Test
    fun `every destination round trips through its uri`() {
        val destinations = listOf(
            AppDestination.Today,
            AppDestination.Course,
            AppDestination.CurrentLesson,
            AppDestination.Lesson(1),
            AppDestination.Lesson(425),
            AppDestination.Voice,
            AppDestination.Rating,
            AppDestination.Profile,
            AppDestination.WidgetSetup,
        ) + PracticeTool.entries.map { AppDestination.Practice(it) }

        destinations.forEach { destination ->
            assertEquals(
                destination,
                DeepLinkRouter.resolve(DeepLinkRouter.uriFor(destination)),
            )
        }
    }
}
