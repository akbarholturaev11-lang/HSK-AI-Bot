package com.pomp.hskai.feature.profile

import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
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
import com.pomp.hskai.data.api.AccountDeletionReceipt
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AccountDeletionDialogTest {
    @get:Rule val compose = createComposeRule()
    private val context = InstrumentationRegistry.getInstrumentation().targetContext
    private fun text(resource: Int) = context.getString(resource)

    @Test fun ownershipLoadingAndSubmissionDisableConfirmationWhileReadyRequiresATap() {
        val state = mutableStateOf(AccountDeletionUiState(isOpen = true, isPreparing = true))
        var confirms = 0
        compose.setContent {
            PompHskAiTheme {
                AccountDeletionDialog(state.value, { confirms++ }, {}, {}, {})
            }
        }
        compose.onNodeWithTag("accountDeletionConfirm").assertIsNotEnabled()
        assertEquals(0, confirms)
        compose.runOnIdle { state.value = AccountDeletionUiState(isOpen = true, accountLabel = "Google learner") }
        compose.onNodeWithText(context.getString(R.string.account_deletion_account, "Google learner")).assertIsDisplayed()
        compose.onNodeWithTag("accountDeletionConfirm").assertIsEnabled().performClick()
        assertEquals(1, confirms)
        compose.runOnIdle { state.value = state.value.copy(isSubmitting = true) }
        compose.onNodeWithTag("accountDeletionConfirm").assertIsNotEnabled()
        compose.onNodeWithText(text(R.string.action_cancel)).assertIsNotEnabled()
        compose.onNodeWithText(text(R.string.account_deletion_open_web)).assertIsNotEnabled()
    }

    @Test fun submittedReceiptShowsRequestNumberAndStatusWithoutRepeatingTheDeletionAction() {
        val receipt = AccountDeletionReceipt(
            true, "submitted", "806c055a-4c34-4aee-b06f-2c27a6080096",
            "2026-10-15T12:00:00Z", "2026-11-14T12:00:00Z",
        )
        var dismissed = 0
        compose.setContent {
            PompHskAiTheme {
                AccountDeletionDialog(AccountDeletionUiState(isOpen = true, receipt = receipt), {}, {}, {}, { dismissed++ })
            }
        }
        compose.onNodeWithText(text(R.string.account_deletion_received)).assertIsDisplayed()
        compose.onNodeWithText(text(R.string.account_deletion_submitted)).assertIsDisplayed()
        compose.onNodeWithTag("accountDeletionReceipt").assertIsDisplayed()
        compose.onNodeWithTag("accountDeletionConfirm").assertDoesNotExist()
        compose.onNodeWithText(text(R.string.action_close)).performClick()
        assertEquals(1, dismissed)
    }

    @Test fun profileDeleteEntryStartsTheAuthenticatedFlowAndKeepsThePublicFallbackExplicit() {
        val deletion = mutableStateOf(AccountDeletionUiState())
        val externalUrls = mutableListOf<String>()
        var prepares = 0
        compose.setContent {
            PompHskAiTheme {
                ProfileScreen(
                    account = LinkedAccount("Apple learner", AppLanguage.UZBEK, "hsk1", "free", false),
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
                    onOpenSupport = { externalUrls.add(it) },
                    onRefresh = {},
                    onLogout = {},
                    onUnlinkDevice = {},
                    accountDeletion = deletion.value,
                    onRequestAccountDeletion = {
                        prepares++
                        deletion.value = AccountDeletionUiState(isOpen = true, isPreparing = true)
                    },
                    onDismissAccountDeletion = { deletion.value = AccountDeletionUiState() },
                )
            }
        }
        compose.onNodeWithContentDescription(text(R.string.profile_mini_settings)).performClick()
        compose.onNodeWithText(text(R.string.profile_settings_section_account)).performClick()
        compose.onNodeWithTag("profile-settings-scroll")
            .performScrollToNode(hasText(text(R.string.profile_privacy_security)))
        compose.onNodeWithText(text(R.string.profile_privacy_security)).performClick()
        compose.onNodeWithText(text(R.string.profile_delete_account)).performClick()
        compose.onNodeWithTag("accountDeletionConfirm").assertIsNotEnabled()
        compose.runOnIdle {
            assertEquals(1, prepares)
            assertEquals(emptyList<String>(), externalUrls)
        }
        compose.onNodeWithText(text(R.string.account_deletion_open_web)).performClick()
        compose.runOnIdle {
            assertEquals(1, externalUrls.size)
            assertEquals("/account-deletion", java.net.URI(externalUrls.single()).path)
            assertEquals(null, java.net.URI(externalUrls.single()).query)
        }
    }
}
