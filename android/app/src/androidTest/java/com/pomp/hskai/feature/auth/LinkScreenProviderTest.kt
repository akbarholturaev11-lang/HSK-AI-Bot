package com.pomp.hskai.feature.auth

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.AuthProvider
import com.pomp.hskai.core.auth.PendingLink
import com.pomp.hskai.core.design.PompHskAiTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * The login screen must never promise a way in that it does not show.
 *
 * A build or deployment without OAuth credentials offers no providers, and
 * then the screen has to look exactly as it did before this feature existed —
 * Telegram only, down to the subtitle. That is the state that actually ships
 * until credentials are registered, so it is the one worth pinning.
 */
@RunWith(AndroidJUnit4::class)
class LinkScreenProviderTest {

    @get:Rule
    val compose = createComposeRule()

    private val strings =
        InstrumentationRegistry.getInstrumentation().targetContext.resources

    private val pending = PendingLink(
        linkRequestId = "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
        displayCode = "HSK4827X",
        pollingSecret = "s".repeat(43),
        botDeepLink = "https://t.me/darsi_chini_bot?start=desktop_link",
        expiresAtMillis = System.currentTimeMillis() + 600_000L,
    )

    private fun show(
        providers: List<AuthProvider> = emptyList(),
        busyProvider: AuthProvider? = null,
        onGoogle: () -> Unit = {},
        onApple: () -> Unit = {},
        onBrowserOpened: () -> Unit = {},
    ) {
        compose.setContent {
            PompHskAiTheme {
                LinkScreen(
                    state = LinkUiState(
                        pending = pending,
                        secondsRemaining = 600,
                        isWaitingForApproval = true,
                        providers = providers,
                        busyProvider = busyProvider,
                    ),
                    onRequestCode = {},
                    onSignInWithGoogle = onGoogle,
                    onSignInWithApple = onApple,
                    onBrowserUrlOpened = onBrowserOpened,
                )
            }
        }
    }

    @Test
    fun withoutProvidersTheScreenIsTelegramOnly() {
        show(providers = emptyList())

        compose.onNodeWithText(strings.getString(R.string.auth_single_subtitle))
            .assertIsDisplayed()
        compose.onNodeWithText(strings.getString(R.string.auth_continue_google))
            .assertDoesNotExist()
        compose.onNodeWithText(strings.getString(R.string.auth_continue_apple))
            .assertDoesNotExist()
        compose.onNodeWithText(strings.getString(R.string.auth_provider_divider))
            .assertDoesNotExist()
        // The Telegram flow itself is untouched.
        compose.onNodeWithText("HSK4827X").assertIsDisplayed()
        compose.onNodeWithText(strings.getString(R.string.auth_login))
            .assertIsDisplayed()
    }

    @Test
    fun withProvidersBothButtonsAppearAndTheSubtitleSaysSo() {
        show(providers = listOf(AuthProvider.GOOGLE, AuthProvider.APPLE))

        compose.onNodeWithText(strings.getString(R.string.auth_multi_subtitle))
            .assertIsDisplayed()
        compose.onNodeWithText(strings.getString(R.string.auth_continue_google))
            .assertIsDisplayed()
        compose.onNodeWithText(strings.getString(R.string.auth_continue_apple))
            .assertIsDisplayed()
        // Telegram stays the primary action, not something the providers replace.
        compose.onNodeWithText("HSK4827X").assertIsDisplayed()
    }

    @Test
    fun onlyTheOfferedProviderIsShown() {
        show(providers = listOf(AuthProvider.GOOGLE))

        compose.onNodeWithText(strings.getString(R.string.auth_continue_google))
            .assertIsDisplayed()
        compose.onNodeWithText(strings.getString(R.string.auth_continue_apple))
            .assertDoesNotExist()
    }

    @Test
    fun tappingAProviderReportsThatExactProvider() {
        var tapped: String? = null
        show(
            providers = listOf(AuthProvider.GOOGLE, AuthProvider.APPLE),
            onGoogle = { tapped = "google" },
            onApple = { tapped = "apple" },
        )

        compose.onNodeWithText(strings.getString(R.string.auth_continue_apple))
            .performClick()
        assertEquals("apple", tapped)
    }

    @Test
    fun whileOneProviderIsRunningTheOthersAreNotTappable() {
        var tapped: String? = null
        show(
            providers = listOf(AuthProvider.GOOGLE, AuthProvider.APPLE),
            busyProvider = AuthProvider.GOOGLE,
            onGoogle = { tapped = "google" },
            onApple = { tapped = "apple" },
        )

        compose.onNodeWithText(strings.getString(R.string.auth_provider_waiting))
            .assertIsDisplayed()
        compose.onNodeWithText(strings.getString(R.string.auth_continue_apple))
            .assertIsNotEnabled()
        compose.onNodeWithText(strings.getString(R.string.auth_continue_apple))
            .performClick()
        assertNull(tapped)
    }
}
