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

    @Test
    fun `a specific lesson number is not addressable from a uri`() {
        // Only "current" is allowed, so a widget or notification payload can
        // never point the app at an arbitrary, possibly premium, lesson.
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://lesson/181"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://lesson"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://lesson/current/extra"))
    }

    @Test
    fun `foreign schemes and unknown paths are rejected`() {
        assertNull(DeepLinkRouter.resolve(null))
        assertNull(DeepLinkRouter.resolve(""))
        assertNull(DeepLinkRouter.resolve("https://evil.example.com/today"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://admin"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://practice/unknown-tool"))
        assertNull(DeepLinkRouter.resolve("pomp-hsk-ai://profile/billing"))
        assertNull(DeepLinkRouter.resolve("javascript:alert(1)"))
    }

    @Test
    fun `case and trailing noise do not bypass the allowlist`() {
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
    }

    @Test
    fun `every destination round trips through its uri`() {
        val destinations = listOf(
            AppDestination.Today,
            AppDestination.Course,
            AppDestination.CurrentLesson,
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
