package com.pomp.hskai.feature.onboarding

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.core.design.PompHskAiTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * What the ask actually says, and that both answers are real answers.
 *
 * The one worth pinning is "later": a primer with no way past it would be a
 * wall in front of the first lesson, and the flag has to be written either way
 * or the question comes back tomorrow.
 */
@RunWith(AndroidJUnit4::class)
class NotificationPrimerTest {

    @get:Rule
    val compose = createComposeRule()

    private fun show(
        language: String = "uz",
        onAllow: () -> Unit = {},
        onSkip: () -> Unit = {},
    ) {
        compose.setContent {
            PompHskAiTheme {
                NotificationPrimerScreen(
                    language = language,
                    onAllow = onAllow,
                    onSkip = onSkip,
                )
            }
        }
    }

    @Test
    fun itNamesBothKindsOfNotification() {
        show()

        compose.onNodeWithText("Bildirishnomalarni yoqing").assertIsDisplayed()
        compose.onNodeWithText("Kechqurun darsni eslatib turamiz").assertIsDisplayed()
        compose.onNodeWithText("Yangi versiya chiqqanda bir marta xabar beramiz")
            .assertIsDisplayed()
    }

    @Test
    fun allowingIsOneTap() {
        var allowed = 0
        show(onAllow = { allowed += 1 })

        compose.onNodeWithText("Yoqish").performClick()

        assertEquals(1, allowed)
    }

    @Test
    fun laterIsAlwaysAvailable() {
        var skipped = 0
        show(onSkip = { skipped += 1 })

        compose.onNodeWithText("Keyinroq").performClick()

        assertEquals(1, skipped)
    }

    @Test
    fun theRussianCopyIsTheRussianCopy() {
        show(language = "ru")

        compose.onNodeWithText("Включите уведомления").assertIsDisplayed()
        compose.onNodeWithText("Включить").assertIsDisplayed()
    }
}
