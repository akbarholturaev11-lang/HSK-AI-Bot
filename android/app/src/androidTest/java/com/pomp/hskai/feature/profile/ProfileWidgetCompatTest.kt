package com.pomp.hskai.feature.profile

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.core.auth.LinkedAccount
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.i18n.AppLanguage
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
        compose.onNodeWithText("Compat learner").assertIsDisplayed()
    }
}
