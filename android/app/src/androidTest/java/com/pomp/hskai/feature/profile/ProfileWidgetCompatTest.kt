package com.pomp.hskai.feature.profile

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollToNode
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.LinkedAccount
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.i18n.AppLanguage
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ProfileWidgetCompatTest {
    @get:Rule val compose = createComposeRule()

    @Test fun legacyWidgetSignatureRendersTheProfileWithoutRecursing() {
        compose.setContent {
            PompHskAiTheme {
                // Keep only the legacy signature's arguments: passing a richer
                // overload's argument would bypass the compatibility bridge.
                ProfileScreen(
                    account = LinkedAccount("Compat learner", AppLanguage.UZBEK, "hsk1", "free", false),
                    state = ProfileUiState(isLoading = false),
                    settings = ProfileSettingsState(),
                    courseProgress = null,
                    courseUser = null,
                    onOpenFriends = {},
                    dailyXp = 0,
                    dailyGoal = 20,
                    notificationsEnabled = true,
                    onOpenGoal = {},
                    onOpenLanguage = {},
                    onToggleNotifications = {},
                    onOpenWidget = {},
                    onOpenSupport = {},
                    onRefresh = {},
                    onLogout = {},
                    onUnlinkDevice = {},
                )
            }
        }
        compose.onAllNodesWithText("Compat learner")[0].assertIsDisplayed()
    }

    @Test fun settingsCanScrollToTheLastAccountAction() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        compose.setContent {
            PompHskAiTheme {
                ProfileScreen(
                    account = LinkedAccount("Settings learner", AppLanguage.UZBEK, "hsk1", "free", false),
                    state = ProfileUiState(isLoading = false),
                    settings = ProfileSettingsState(),
                    courseProgress = null,
                    courseUser = null,
                    onOpenFriends = {},
                    dailyXp = 0,
                    dailyGoal = 20,
                    notificationsEnabled = true,
                    onOpenGoal = {},
                    onOpenLanguage = {},
                    onToggleNotifications = {},
                    onOpenWidget = {},
                    onOpenSupport = {},
                    onRefresh = {},
                    onLogout = {},
                    onUnlinkDevice = {},
                )
            }
        }

        compose.onNodeWithContentDescription(context.getString(R.string.profile_mini_settings))
            .performClick()
        val screenshot = InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()
        val statusBarColor = screenshot.getPixel(screenshot.width * 5 / 8, 8)
        assertTrue(
            "settings status bar should be light, got #${Integer.toHexString(statusBarColor)}",
            android.graphics.Color.red(statusBarColor) > 220 &&
                android.graphics.Color.green(statusBarColor) > 220 &&
                android.graphics.Color.blue(statusBarColor) > 210,
        )
        compose.onNodeWithTag("profile-settings-scroll")
            .performScrollToNode(hasText(context.getString(R.string.profile_unlink_device)))
        compose.onNodeWithText(context.getString(R.string.profile_unlink_device)).assertIsDisplayed()
    }
}
