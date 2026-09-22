package com.pomp.hskai.feature.auth

import androidx.compose.ui.test.assertIsDisplayed
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
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * The login screen must never promise a way in that it does not show.
 *
 * A build or deployment without OAuth credentials offers no providers, and
 * then the screen has to be Telegram-only — that is the state that actually
 * ships until credentials are registered, so it is the one worth pinning.
 *
 * The second thing pinned here is the absence of the display code: the bot
 * reads the link request out of the deep link and asks for one confirmation,
 * so a code on this screen would be something the learner is never asked for.
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
        botDeepLink = "https://t.me/darsi_chini_bot?start=android_link_3f2504e0",
        expiresAtMillis = System.currentTimeMillis() + 600_000L,
    )

    private fun show(
        providers: List<AuthProvider> = emptyList(),
        busyProvider: AuthProvider? = null,
        waiting: Boolean = false,
        onTelegram: () -> Unit = {},
        onGoogle: () -> Unit = {},
        onApple: () -> Unit = {},
    ) {
        compose.setContent {
            PompHskAiTheme {
                LinkScreen(
                    state = LinkUiState(
                        pending = pending,
                        secondsRemaining = 600,
                        isWaitingForApproval = waiting,
                        providers = providers,
                        busyProvider = busyProvider,
                    ),
                    onContinueWithTelegram = onTelegram,
                    onSignInWithGoogle = onGoogle,
                    onSignInWithApple = onApple,
                )
            }
        }
    }

    @Test
    fun withoutProvidersTheScreenIsTelegramOnly() {
        show(providers = emptyList())

        compose.onNodeWithText(strings.getString(R.string.auth_choose_method))
            .assertIsDisplayed()
        compose.onNodeWithText(strings.getString(R.string.auth_continue_telegram))
            .assertIsDisplayed()
        compose.onNodeWithText(strings.getString(R.string.auth_continue_google_short))
            .assertDoesNotExist()
        compose.onNodeWithText(strings.getString(R.string.auth_continue_apple_short))
            .assertDoesNotExist()
    }

    @Test
    fun theDisplayCodeIsNeverShown() {
        show(providers = listOf(AuthProvider.GOOGLE, AuthProvider.APPLE))

        compose.onNodeWithText("HSK4827X").assertDoesNotExist()
    }

    @Test
    fun everyOfferedProviderGetsACard() {
        show(providers = listOf(AuthProvider.GOOGLE, AuthProvider.APPLE))

        compose.onNodeWithText(strings.getString(R.string.auth_continue_telegram))
            .assertIsDisplayed()
        compose.onNodeWithText(strings.getString(R.string.auth_continue_google_short))
            .assertIsDisplayed()
        compose.onNodeWithText(strings.getString(R.string.auth_continue_apple_short))
            .assertIsDisplayed()
    }

    @Test
    fun onlyTheOfferedProviderIsShown() {
        show(providers = listOf(AuthProvider.GOOGLE))

        compose.onNodeWithText(strings.getString(R.string.auth_continue_google_short))
            .assertIsDisplayed()
        compose.onNodeWithText(strings.getString(R.string.auth_continue_apple_short))
            .assertDoesNotExist()
    }

    @Test
    fun tappingACardReportsThatExactProvider() {
        var tapped: String? = null
        show(
            providers = listOf(AuthProvider.GOOGLE, AuthProvider.APPLE),
            onTelegram = { tapped = "telegram" },
            onGoogle = { tapped = "google" },
            onApple = { tapped = "apple" },
        )

        compose.onNodeWithText(strings.getString(R.string.auth_continue_apple_short))
            .performClick()
        assertEquals("apple", tapped)

        compose.onNodeWithText(strings.getString(R.string.auth_continue_telegram))
            .performClick()
        assertEquals("telegram", tapped)
    }

    @Test
    fun whileTelegramIsRunningTheCardsGiveWayToTheWait() {
        show(
            providers = listOf(AuthProvider.GOOGLE, AuthProvider.APPLE),
            busyProvider = AuthProvider.TELEGRAM,
            waiting = true,
        )

        compose.onNodeWithText(strings.getString(R.string.auth_waiting_telegram))
            .assertIsDisplayed()
        compose.onNodeWithText(strings.getString(R.string.auth_continue_google_short))
            .assertDoesNotExist()
        compose.onNodeWithText(strings.getString(R.string.auth_continue_apple_short))
            .assertDoesNotExist()
    }

    @Test
    fun aProviderThatIsRunningSaysSoWithoutNamingTelegram() {
        show(
            providers = listOf(AuthProvider.GOOGLE),
            busyProvider = AuthProvider.GOOGLE,
            waiting = true,
        )

        compose.onNodeWithText(strings.getString(R.string.auth_provider_waiting))
            .assertIsDisplayed()
        compose.onNodeWithText(strings.getString(R.string.auth_open_telegram_again))
            .assertDoesNotExist()
    }
}
