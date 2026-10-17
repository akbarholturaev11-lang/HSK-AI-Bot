package com.pomp.hskai.feature.profile

import android.app.Activity
import android.content.ContextWrapper
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.view.ContextThemeWrapper
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.platform.LocalContext

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.AuthProvider
import com.pomp.hskai.core.auth.authActivity
import com.pomp.hskai.core.auth.LinkedIdentity
import com.pomp.hskai.core.design.PompHskAiTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertSame
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** The existing methods sheet exposes safe Telegram attachment for provider-only accounts. */
@RunWith(AndroidJUnit4::class)
class IdentitiesSheetTest {
    @get:Rule val compose = createComposeRule()
    private val strings = InstrumentationRegistry.getInstrumentation().targetContext.resources

    @Test fun browserProviderButtonRetainsTheActivityInsideNestedThemeContexts() {
        var selected: Activity? = null
        var host: Activity? = null
        compose.setContent {
            val original = LocalContext.current
            host = original.authActivity()
            val wrapped = ContextWrapper(ContextThemeWrapper(original, com.pomp.hskai.R.style.Theme_PompHskAi))
            CompositionLocalProvider(LocalContext provides wrapped) {
                PompHskAiTheme {
                    IdentitiesSheet(state = IdentitiesUiState(telegramLinked = true, hasLoaded = true,
                        available = listOf(AuthProvider.GOOGLE)),
                        profile = null, savingProfile = false, onSaveProfile = { _, _ -> },
                        onConnect = { _, activity -> selected = activity }, onDisconnect = {},
                        onBrowserUrlOpened = {}, onDismiss = {})
                }
            }
        }
        compose.onNodeWithTag("google-identity-connect").performScrollTo().assertIsDisplayed().performClick()
        compose.runOnIdle {
            assertNotNull(host)
            assertSame(host, selected)
        }
    }

    @Test fun oauthReturnManifestResolvesToTheExistingSingleTaskActivity() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse("${com.pomp.hskai.BuildConfig.DEEP_LINK_SCHEME}://oauth-return"))
            .addCategory(Intent.CATEGORY_BROWSABLE).setPackage(context.packageName)
        val resolved = context.packageManager.resolveActivity(intent, PackageManager.MATCH_DEFAULT_ONLY)
        assertNotNull(resolved)
        assertEquals("com.pomp.hskai.MainActivity", resolved?.activityInfo?.name)
        assertEquals(android.content.pm.ActivityInfo.LAUNCH_SINGLE_TASK, resolved?.activityInfo?.launchMode)
    }

    private fun show(
        state: IdentitiesUiState,
        onConnect: (AuthProvider) -> Unit = {},
        onCancel: () -> Unit = {},
        onReopen: () -> Unit = {},
    ) {
        compose.setContent {
            PompHskAiTheme {
                IdentitiesSheet(state = state, profile = null, savingProfile = false,
                    onSaveProfile = { _, _ -> }, onConnect = { provider, _ -> onConnect(provider) },
                    onDisconnect = {}, onBrowserUrlOpened = {}, onDismiss = {},
                    onCancelConnection = onCancel, onReopenTelegram = onReopen)
            }
        }
    }

    @Test fun providerOnlyAccountCanChooseTelegramInTheExistingMethodsCard() {
        var selected: AuthProvider? = null
        show(IdentitiesUiState(identities = listOf(LinkedIdentity("google-id", AuthProvider.GOOGLE, null, null))),
            onConnect = { selected = it })
        compose.onNodeWithTag("telegram-identity-connect").performScrollTo().assertIsDisplayed().performClick()
        assertEquals(AuthProvider.TELEGRAM, selected)
    }

    @Test fun linkedTelegramRemainsReadOnlyAndHasNoReplacementAction() {
        show(IdentitiesUiState(telegramLinked = true))
        compose.onNodeWithTag("telegram-identity-connect").assertDoesNotExist()
        compose.onNodeWithText(strings.getString(R.string.profile_identity_connected))
            .performScrollTo().assertIsDisplayed()
    }

    @Test fun pendingBotApprovalExplainsConfirmationAndAllowsReopenOrCancel() {
        var cancels = 0
        var reopens = 0
        show(IdentitiesUiState(busyProvider = AuthProvider.TELEGRAM,
            telegramApprovalUrl = "https://t.me/HSKAI_bot?start=tg_identity_3f2504e0-4f89-11d3-9a0c-0305e82c3301"),
            onCancel = { cancels++ }, onReopen = { reopens++ })
        compose.onNodeWithTag("telegram-identity-connect").performScrollTo().assertIsNotEnabled()
        compose.onNodeWithText(strings.getString(R.string.profile_telegram_link_waiting))
            .performScrollTo().assertIsDisplayed()
        compose.onNodeWithTag("telegram-link-reopen").performScrollTo().performClick()
        compose.onNodeWithTag("telegram-link-cancel").performScrollTo().performClick()
        assertEquals(1, reopens)
        assertEquals(1, cancels)
    }
}
