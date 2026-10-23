package com.pomp.hskai.feature.profile

import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performScrollToNode
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.AuthProvider
import com.pomp.hskai.core.auth.LinkedIdentity
import com.pomp.hskai.core.auth.LinkedAccount
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.data.api.AndroidProfileResponse
import com.pomp.hskai.data.api.AndroidProfileUserDto
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ProviderOnlyAccountTest {
    @get:Rule val compose = createComposeRule()
    private val context = InstrumentationRegistry.getInstrumentation().targetContext
    private fun text(resource: Int) = context.getString(resource)
    private fun identity(provider: AuthProvider) = LinkedIdentity(provider.wire, provider, "n***@example.com", "Learner")

    @Test fun appleOnlyProfileOpensItsAccountWithoutATelegramField() {
        compose.setContent {
            PompHskAiTheme {
                ProfileScreen(
                    account = LinkedAccount("Apple learner", AppLanguage.UZBEK, "hsk1", "free", false),
                    state = ProfileUiState(isLoading = false, profile = AndroidProfileResponse(
                        ok = true, user = AndroidProfileUserDto(name = "Apple learner"),
                    )),
                    settings = ProfileSettingsState(), courseProgress = null, courseUser = null,
                    onOpenFriends = {}, dailyXp = 0, dailyGoal = 20, notificationsEnabled = true,
                    onOpenGoal = {}, onOpenLanguage = {}, onToggleNotifications = {}, onOpenWidget = {},
                    onOpenSupport = {}, onRefresh = {}, onLogout = {}, onUnlinkDevice = {},
                    identities = IdentitiesUiState(telegramLinked = false,
                        identities = listOf(identity(AuthProvider.APPLE)), available = listOf(AuthProvider.APPLE)),
                )
            }
        }
        compose.onAllNodesWithText("Apple learner")[0].assertIsDisplayed()
        compose.onNodeWithContentDescription(text(R.string.profile_mini_settings)).performClick()
        compose.onNodeWithTag("profile-settings-scroll")
            .performScrollToNode(hasText(text(R.string.profile_account_title)))
        compose.onNodeWithText(text(R.string.profile_account_title)).performClick()
        compose.onNodeWithText(text(R.string.profile_account_telegram)).assertDoesNotExist()
        compose.onNodeWithText(text(R.string.profile_account_apple)).performScrollTo().assertIsDisplayed()
        compose.onNodeWithText(text(R.string.profile_account_disconnect)).performScrollTo().assertIsNotEnabled()
        compose.onNodeWithText(text(R.string.profile_account_save)).assertIsDisplayed()
    }

    @Test fun soleProviderCannotBeRemovedAndTelegramIsShownOnlyWhenActuallyLinked() {
        val state = mutableStateOf(IdentitiesUiState(
            telegramLinked = false, identities = listOf(identity(AuthProvider.GOOGLE)),
            available = listOf(AuthProvider.GOOGLE, AuthProvider.APPLE),
        ))
        val disconnected = mutableListOf<String>()
        compose.setContent {
            PompHskAiTheme {
                IdentitiesSheet(
                    state = state.value,
                    profile = AndroidProfileResponse(ok = true, user = AndroidProfileUserDto(name = "Google learner", telegramUsername = "linked_learner")),
                    savingProfile = false,
                    onSaveProfile = { _, _ -> },
                    onConnect = { _, _ -> },
                    onDisconnect = { disconnected.add(it) },
                    onBrowserUrlOpened = {},
                    onDismiss = {},
                )
            }
        }
        compose.onNodeWithText(text(R.string.profile_account_telegram)).assertDoesNotExist()
        compose.onNodeWithText("@linked_learner").assertDoesNotExist()
        compose.onNodeWithText(text(R.string.error_oauth_last_identity)).performScrollTo().assertIsDisplayed()
        compose.onNodeWithText(text(R.string.profile_account_disconnect)).performScrollTo().assertIsNotEnabled()
        compose.onNodeWithText(text(R.string.profile_account_save)).assertIsDisplayed()
        assertEquals(emptyList<String>(), disconnected)

        compose.runOnIdle { state.value = state.value.copy(telegramLinked = true) }
        compose.onNodeWithText(text(R.string.profile_account_telegram)).assertDoesNotExist()
        compose.onNodeWithText("@linked_learner").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText(text(R.string.profile_account_disconnect)).performScrollTo().assertIsEnabled().performClick()
        assertEquals(listOf("google"), disconnected)

        compose.runOnIdle {
            state.value = state.value.copy(telegramLinked = false,
                identities = listOf(identity(AuthProvider.GOOGLE), identity(AuthProvider.APPLE)))
        }
        compose.onNodeWithText(text(R.string.profile_account_telegram)).assertDoesNotExist()
        compose.onAllNodesWithText(text(R.string.profile_account_disconnect))[1].performScrollTo().assertIsEnabled().performClick()
        assertEquals(listOf("google", "apple"), disconnected)
    }
}
