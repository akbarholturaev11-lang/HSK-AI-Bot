package com.pomp.hskai.core.navigation

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class DeepLinkRouterTest {

    @Test
    fun `allowlisted destinations resolve`() {
        assertEquals(AppDestination.Today, DeepLinkRouter.resolve("pomp-hsk-ai://today"))
        assertEquals(AppDestination.Course, DeepLinkRouter.resolve("pomp-hsk-ai://course"))
        assertEquals(AppDestination.Voice, DeepLinkRouter.resolve("pomp-hsk-ai://voice"))
        assertEquals(AppDestination.Profile, DeepLinkRouter.resolve("pomp-hsk-ai://profile"))
        assertEquals(
            AppDestination.WidgetSetup,
            DeepLinkRouter.resolve("pomp-hsk-ai://profile/widget"),
        )
        assertEquals(
            AppDestination.CurrentLesson,
            DeepLinkRouter.resolve("pomp-hsk-ai://lesson/current"),
        )
        assertEquals(
            AppDestination.Practice(PracticeTool.MISTAKES),
            DeepLinkRouter.resolve("pomp-hsk-ai://practice/mistakes"),
        )
        assertEquals(
            AppDestination.Practice(PracticeTool.RECOGNITION),
            DeepLinkRouter.resolve("pomp-hsk-ai://practice/recognition"),
        )
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
            DeepLinkRouter.resolve("pomp-hsk-ai://lesson/181"),
        )
        assertEquals(
            AppDestination.Lesson(1),
            DeepLinkRouter.resolve("pomp-hsk-ai://lesson/1"),
        )
        // The destination carries a number and nothing else — no entitlement,
        // no unlock flag, nothing the URI could assert about access.
        val destination = DeepLinkRouter.resolve("pomp-hsk-ai://lesson/42")
        assertEquals(AppDestination.Lesson(42), destination)
    }

    @Test
    fun `lesson numbers outside the backend contract are rejected`() {
        // app/api/desktop_course.py bounds lesson_order to 1..500.
        assertEquals(500, DeepLinkRouter.LESSON_ORDER_RANGE.last)
        assertEquals(
            AppDestination.Lesson(500),
            DeepLinkRouter.resolve("pomp-hsk-ai://lesson/500"),
        )
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://lesson/501"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://lesson/0"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://lesson/-1"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://lesson/+5"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://lesson/007"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://lesson/abc"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://lesson/1e3"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://lesson"))
    }

    /**
     * Matching is exact-arity, like the desktop client's path allowlist. A
     * trailing segment must invalidate the whole URI rather than let it
     * resolve to its prefix.
     */
    @Test
    fun `an unexpected trailing segment invalidates the uri`() {
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://lesson/current/extra"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://lesson/12/extra"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://today/extra"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://course/extra"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://voice/extra"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://profile/widget/extra"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://practice/mistakes/extra"))
    }

    @Test
    fun `foreign schemes and unknown paths are rejected`() {
        assertNull(DeepLinkRouter.resolve(null))
        assertNull(DeepLinkRouter.resolve(""))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://"))
        assertNull(DeepLinkRouter.resolve("https://evil.example.com/today"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://admin"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://practice/unknown-tool"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://profile/billing"))
        assertNull(DeepLinkRouter.resolve("javascript:alert(1)"))
    }

    @Test
    fun `case and query noise do not bypass the allowlist`() {
        assertEquals(
            AppDestination.Today,
            DeepLinkRouter.resolve("POMP-HSK-AI://Today"),
        )
        assertEquals(
            AppDestination.Practice(PracticeTool.PRONUNCIATION),
            DeepLinkRouter.resolve("pomp-hsk-ai://practice/PRONUNCIATION?src=widget"),
        )
        assertEquals(
            AppDestination.Course,
            DeepLinkRouter.resolve("pomp-hsk-ai://course/#top"),
        )
        assertEquals(
            AppDestination.Lesson(7),
            DeepLinkRouter.resolve("pomp-hsk-ai://lesson/7?source=d1_recovery"),
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
