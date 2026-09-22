package com.pomp.hskai.feature.profile

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * The official HSK AI pages, reachable from the profile.
 *
 * Each button must open its own page: a row of look-alike buttons is exactly
 * where a copy-paste mistake hides, and a learner who taps TikTok and lands on
 * Instagram would never report it as a bug.
 */
@RunWith(AndroidJUnit4::class)
class SocialLinksTest {

    @get:Rule
    val compose = createComposeRule()

    private val strings =
        InstrumentationRegistry.getInstrumentation().targetContext.resources

    private fun show(onOpen: (String) -> Unit = {}) {
        compose.setContent { PompHskAiTheme { SocialLinksRow(onOpen = onOpen) } }
    }

    @Test
    fun theSectionAndAllThreePagesAreListed() {
        show()

        compose.onNodeWithText(strings.getString(R.string.profile_social_title))
            .assertIsDisplayed()
        listOf("Instagram", "TikTok", "YouTube").forEach { label ->
            compose.onNodeWithText(label).assertIsDisplayed()
        }
    }

    @Test
    fun eachButtonOpensItsOwnPage() {
        val opened = mutableListOf<String>()
        show(onOpen = { opened += it })

        listOf(
            "Instagram" to "https://www.instagram.com/hskai.app",
            "TikTok" to "https://www.tiktok.com/@hsk.ai",
            "YouTube" to "https://youtube.com/@hskai_app",
        ).forEach { (label, expected) ->
            opened.clear()
            compose.onNodeWithText(label).performClick()
            assertEquals(listOf(expected), opened)
        }
    }

    @Test
    fun everyLinkIsAnHttpsUrlAndDistinct() {
        val urls = SOCIAL_LINKS.map { it.second }
        assertEquals(urls.size, urls.toSet().size)
        urls.forEach { assertEquals(true, it.startsWith("https://")) }
        // No tracking or session parameters: those are personal to whoever
        // copied the link, not something to hand to every learner.
        urls.forEach { assertEquals(false, it.contains("?")) }
    }
}
