package com.pomp.hskai.feature.hint

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.data.api.AndroidHintDto
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * The explanation is a marker, not a card.
 *
 * It was a card once: a block of text sitting in the section's own list,
 * pushing the content down and demanding to be dealt with. What is pinned
 * here is the shape it has instead — nothing on screen until asked, the text
 * on tap, and gone for good on the X.
 */
@RunWith(AndroidJUnit4::class)
class SectionHintTest {

    @get:Rule
    val compose = createComposeRule()

    private val hint = AndroidHintDto(
        key = "hint_section_practice",
        title = "Mashq bo'limi",
        body = "Har kuni bitta bepul mashq.",
        section = "mashq",
    )

    private fun show(
        hints: List<AndroidHintDto> = listOf(hint),
        section: String = "mashq",
        onDismiss: (String) -> Unit = {},
    ) {
        compose.setContent {
            PompHskAiTheme {
                SectionHint(hints = hints, section = section, onDismiss = onDismiss)
            }
        }
    }

    @Test
    fun the_text_is_not_on_screen_until_the_marker_is_tapped() {
        show()

        compose.onNodeWithText(hint.body).assertDoesNotExist()
        compose.onNodeWithContentDescription(hint.title).performClick()
        compose.onNodeWithText(hint.body).assertIsDisplayed()
    }

    @Test
    fun closing_it_reports_the_dismissal_and_takes_the_text_away() {
        val closed = mutableListOf<String>()
        show(onDismiss = { closed += it })

        compose.onNodeWithContentDescription(hint.title).performClick()
        compose.onAllNodesWithContentDescriptionMatchingClose().performClick()

        compose.onNodeWithText(hint.body).assertDoesNotExist()
        assertEquals(listOf(hint.key), closed)
    }

    @Test
    fun a_section_with_no_hint_draws_nothing_at_all() {
        show(hints = listOf(hint), section = "voice")

        compose.onNodeWithContentDescription(hint.title).assertDoesNotExist()
    }
}

/** The X carries the shared "close" label, so it is found by that. */
private fun androidx.compose.ui.test.junit4.ComposeContentTestRule
    .onAllNodesWithContentDescriptionMatchingClose() =
    onNodeWithContentDescription(
        androidx.test.platform.app.InstrumentationRegistry.getInstrumentation()
            .targetContext.getString(com.pomp.hskai.R.string.hint_close)
    )
