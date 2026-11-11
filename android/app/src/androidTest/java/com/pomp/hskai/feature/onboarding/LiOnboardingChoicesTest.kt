package com.pomp.hskai.feature.onboarding

import android.content.res.Configuration
import android.graphics.Bitmap
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.unit.dp
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.data.api.AndroidTrialDto
import com.pomp.hskai.feature.profile.ProfileUiState
import java.io.File
import java.util.Locale
import org.junit.Rule
import org.junit.Test
import org.junit.Assert.assertEquals

class LiOnboardingChoicesTest {
    @get:Rule val compose = createComposeRule()
    private fun renderChoices(lang: String) {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val configuration = Configuration(context.resources.configuration).apply { setLocale(Locale.forLanguageTag(lang)) }
        val localized = context.createConfigurationContext(configuration)
        var minutes = 10
        compose.setContent {
            CompositionLocalProvider(LocalContext provides localized, LocalConfiguration provides configuration) {
                PompHskAiTheme {
                    LiOnboardingChoices(OnboardingUiState(liEnabled = true, step = 4), ProfileUiState(),
                        onGoal = {}, onMinutes = { minutes = it }, onFocus = {}, onStreak = {},
                        onBack = {}, onNext = {}, onFinish = {}, onTrial = {}, onRetryTrial = {},
                        modifier = Modifier.size(320.dp, 700.dp))
                }
            }
        }
        compose.onNodeWithText(localized.getString(R.string.li_copy_timeq)).assertIsDisplayed()
        compose.onNodeWithText("20 " + localized.getString(R.string.li_copy_min)).performClick()
        assertEquals(20, minutes)
        compose.onNodeWithText(localized.getString(R.string.li_copy_cont)).assertIsDisplayed()
        val bitmap = compose.onRoot().captureToImage().asAndroidBitmap()
        File(context.cacheDir, "native-li-$lang.png").outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG,100,it) }
    }
    @Test fun uzbekChoicesAt320() = renderChoices("uz")
    @Test fun russianChoicesAt320() = renderChoices("ru")
    @Test fun tajikChoicesAt320() = renderChoices("tg")
    @Test fun ineligibleServerTrialNeverDisplaysFreeTrialOffer() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        compose.setContent {
            PompHskAiTheme {
                LiOnboardingChoices(OnboardingUiState(liEnabled = true, step = 8),
                    ProfileUiState(trialLoading = false, trial = AndroidTrialDto(eligible = false)),
                    onGoal = {}, onMinutes = {}, onFocus = {}, onStreak = {}, onBack = {}, onNext = {},
                    onFinish = {}, onTrial = {}, onRetryTrial = {})
            }
        }
        compose.onNodeWithText(context.getString(R.string.li_copy_procta)).assertDoesNotExist()
        compose.onNodeWithText(context.getString(R.string.li_copy_protitle)).assertDoesNotExist()
        compose.onNodeWithText(context.getString(R.string.li_copy_first)).assertIsDisplayed()
    }
}
