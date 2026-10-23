package com.pomp.hskai.feature.profile

import android.content.res.Configuration
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollToNode
import androidx.compose.ui.test.performTextReplacement
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.test.swipeDown
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.AuthProvider
import com.pomp.hskai.core.auth.LinkedIdentity
import com.pomp.hskai.core.settings.DailyGoal
import com.pomp.hskai.core.auth.LinkedAccount
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.settings.AppSettings
import com.pomp.hskai.core.settings.AppThemeMode
import com.pomp.hskai.data.api.AndroidProfileResponse
import com.pomp.hskai.data.api.AndroidProfileUserDto
import java.io.File
import java.util.Locale
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ProfileSettingsUxTest {
    @get:Rule val compose = createComposeRule()
    private val context = InstrumentationRegistry.getInstrumentation().targetContext
    private fun text(id: Int) = context.getString(id)

    @Composable
    private fun Profile(
        onRefresh: () -> Unit = {},
        onSave: (String, String) -> Unit = { _, _ -> },
        loading: Boolean = false,
        onSelectLanguage: ((AppLanguage) -> Unit)? = null,
        onSelectGoal: ((Int) -> Unit)? = null,
    ) {
        ProfileScreen(
            account = LinkedAccount("Test learner", AppLanguage.UZBEK, "hsk1", "pro", true),
            state = ProfileUiState(isLoading = loading, profile = AndroidProfileResponse(
                ok = true, user = AndroidProfileUserDto(name = "Test learner", phone = "+998000000000"),
            )),
            settings = ProfileSettingsState(), courseProgress = null, courseUser = null,
            dailyXp = 10, dailyGoal = 20, notificationsEnabled = true,
            onOpenFriends = {}, onOpenGoal = {}, onOpenLanguage = {}, onToggleNotifications = {},
            onOpenWidget = {}, onOpenSupport = {}, onRefresh = onRefresh,
            onLogout = {}, onUnlinkDevice = {}, onSaveProfile = onSave,
            onSelectLanguage = onSelectLanguage, onSelectGoal = onSelectGoal,
            identities = IdentitiesUiState(hasLoaded = true, telegramLinked = true,
                identities = listOf(LinkedIdentity("test-google", AuthProvider.GOOGLE, "l***@example.com", "Learner")),
                available = listOf(AuthProvider.GOOGLE, AuthProvider.APPLE)),
        )
    }

    @Test fun settingsExposePreferencesDirectlyAndBackReturnsToTheSameList() {
        compose.setContent { PompHskAiTheme { Profile() } }
        compose.onNodeWithContentDescription(text(R.string.profile_mini_settings)).performClick()
        compose.onNodeWithText(text(R.string.hsk_course_lang)).assertIsDisplayed()
        compose.onNodeWithText(text(R.string.profile_mini_daily_goal)).assertIsDisplayed()
        compose.onNodeWithText(text(R.string.profile_appearance)).performClick()
        compose.onNodeWithText(text(R.string.profile_theme_dark)).assertIsDisplayed()
        compose.onNodeWithContentDescription(text(R.string.hsk_common_action_back)).performClick()
        compose.onNodeWithText(text(R.string.hsk_course_lang)).assertIsDisplayed()
        compose.onNodeWithText(text(R.string.profile_settings_intro)).assertDoesNotExist()
    }

    @Test fun accountHasEditableDetailsWithoutTechnicalFieldsAndClosesBackToSettings() {
        val saves = mutableListOf<Pair<String, String>>()
        compose.setContent { PompHskAiTheme { Profile(onSave = { name, avatar -> saves.add(name to avatar) }) } }
        compose.onNodeWithContentDescription(text(R.string.profile_mini_settings)).performClick()
        compose.onNodeWithTag("profile-settings-scroll").performScrollToNode(hasText(text(R.string.profile_account_title)))
        compose.onNodeWithText(text(R.string.profile_account_title)).performClick()
        compose.onNodeWithText(text(R.string.profile_account_subtitle)).assertDoesNotExist()
        compose.onNodeWithText(text(R.string.profile_security_note)).assertDoesNotExist()
        compose.onNodeWithText("+998000000000").assertDoesNotExist()
        compose.onNodeWithText(text(R.string.profile_account_telegram)).assertDoesNotExist()
        compose.onNodeWithText(text(R.string.profile_account_name)).performTextReplacement("  Renamed learner  ")
        compose.onNodeWithText(text(R.string.profile_account_save)).assertIsEnabled().performClick()
        compose.runOnIdle { assertEquals(listOf("Renamed learner" to ""), saves) }
        compose.onNodeWithContentDescription(text(R.string.hsk_common_action_close)).performClick()
        compose.onNodeWithTag("profile-settings-scroll").assertIsDisplayed()
        compose.onNodeWithText(text(R.string.profile_account_title)).assertIsDisplayed()
    }

    @Test fun languageAndGoalPickersReturnToSettingsAfterChoosing() {
        val languages = mutableListOf<AppLanguage>()
        val goals = mutableListOf<Int>()
        compose.setContent {
            PompHskAiTheme { Profile(onSelectLanguage = { languages.add(it) }, onSelectGoal = { goals.add(it) }) }
        }
        compose.onNodeWithContentDescription(text(R.string.profile_mini_settings)).performClick()
        compose.onNodeWithText(text(R.string.hsk_course_lang)).performClick()
        compose.onNodeWithText(text(R.string.language_ru)).performClick()
        compose.onNodeWithTag("profile-settings-scroll").assertIsDisplayed()
        compose.runOnIdle { assertEquals(listOf(AppLanguage.RUSSIAN), languages) }
        compose.onNodeWithText(text(R.string.profile_mini_daily_goal)).performClick()
        val goal = DailyGoal.CHOICES.last()
        compose.onNodeWithText(context.getString(R.string.profile_goal_option, goal)).performClick()
        compose.onNodeWithTag("profile-settings-scroll").assertIsDisplayed()
        compose.runOnIdle { assertEquals(listOf(goal), goals) }
    }

    @Test fun proBadgeSitsAtTheTrailingEdgeBesideTheName() {
        compose.setContent { PompHskAiTheme { Profile() } }
        val name = compose.onNodeWithText("Test learner").fetchSemanticsNode().boundsInRoot
        val badge = compose.onNodeWithTag("profile-access-badge").fetchSemanticsNode().boundsInRoot
        assertTrue(badge.left >= name.right)
        assertTrue(badge.top < name.bottom && badge.bottom > name.top)
    }

    @Test fun pullDownRefreshesTheProfileWithoutOpeningSettingsOrWritingTheAccount() {
        var refreshes = 0
        var saves = 0
        compose.setContent { PompHskAiTheme { Profile(onRefresh = { refreshes++ }, onSave = { _, _ -> saves++ }) } }
        compose.onNodeWithTag("profile-refresh").performTouchInput {
            swipeDown(startY = height * .05f, endY = height * .85f, durationMillis = 600)
        }
        compose.waitUntil(5_000) { refreshes == 1 }
        compose.runOnIdle { assertEquals(0, saves) }
        compose.onNodeWithTag("profile-settings-scroll").assertDoesNotExist()
    }

    @Test fun profileSettingsAndAccountRenderInAllLocalesAndBothThemes() {
        val locale = mutableStateOf("uz")
        val appSettings = AppSettings(context)
        val folder = File(context.getExternalFilesDir(null), "profile-settings-qa").apply { mkdirs() }
        compose.setContent {
            val configuration = Configuration(context.resources.configuration).apply {
                setLocale(Locale.forLanguageTag(locale.value))
            }
            val localized = context.createConfigurationContext(configuration)
            CompositionLocalProvider(LocalContext provides localized, LocalConfiguration provides configuration) {
                key(locale.value) { PompHskAiTheme { Profile() } }
            }
        }
        try {
            for (dark in listOf(false, true)) {
                runBlocking { appSettings.setThemeMode(if (dark) AppThemeMode.DARK else AppThemeMode.LIGHT) }
                compose.waitUntil(5_000) { PompColors.IsDark == dark }
                for (language in listOf("uz", "ru", "tg")) {
                    // Recreate the screen even when the first locale repeats.
                    compose.runOnIdle { locale.value = "en" }
                    compose.waitForIdle()
                    compose.runOnIdle { locale.value = language }
                    compose.waitForIdle()
                    val config = Configuration(context.resources.configuration).apply { setLocale(Locale.forLanguageTag(language)) }
                    val strings = context.createConfigurationContext(config)
                    fun shot(tag: String, name: String) {
                        val bitmap = compose.onNodeWithTag(tag).captureToImage().asAndroidBitmap()
                        File(folder, "$language-${if (dark) "dark" else "light"}-$name.png").outputStream().use {
                            bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, it)
                        }
                    }
                    shot("profile-refresh", "profile")
                    compose.onNodeWithContentDescription(strings.getString(R.string.profile_mini_settings)).performClick()
                    compose.onNodeWithTag("profile-settings-scroll").performScrollToNode(hasText(strings.getString(R.string.hsk_course_lang)))
                    compose.onNodeWithText(strings.getString(R.string.hsk_course_lang)).assertIsDisplayed()
                    shot("profile-settings-surface", "settings")
                    compose.onNodeWithTag("profile-settings-scroll").performScrollToNode(hasText(strings.getString(R.string.profile_account_title)))
                    compose.onNodeWithText(strings.getString(R.string.profile_account_title)).performClick()
                    compose.onNodeWithText(strings.getString(R.string.profile_account_name)).assertIsDisplayed()
                    compose.onNodeWithText(strings.getString(R.string.profile_account_save)).assertIsDisplayed()
                    shot("profile-account", "account")
                    compose.onNodeWithContentDescription(strings.getString(R.string.hsk_common_action_close)).performClick()
                    compose.onNodeWithContentDescription(strings.getString(R.string.hsk_common_action_back)).performClick()
                }
            }
        } finally {
            runBlocking { appSettings.setThemeMode(AppThemeMode.LIGHT) }
        }
    }
}
