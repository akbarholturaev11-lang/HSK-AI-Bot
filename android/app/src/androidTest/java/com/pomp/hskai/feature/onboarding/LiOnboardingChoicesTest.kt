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
import org.junit.Assert.assertTrue

class LiOnboardingChoicesTest {
    @get:Rule val compose = createComposeRule()
    private fun renderChoices(lang: String, height: Int = 700) {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val configuration = Configuration(context.resources.configuration).apply { setLocale(Locale.forLanguageTag(lang)) }
        val localized = context.createConfigurationContext(configuration)
        var minutes by mutableIntStateOf(10)
        var backCalls = 0
        var nextCalls = 0
        compose.setContent {
            CompositionLocalProvider(LocalContext provides localized, LocalConfiguration provides configuration) {
                PompHskAiTheme {
                    LiOnboardingChoices(OnboardingUiState(liEnabled = true, step = 4, dailyMinutes = minutes), ProfileUiState(),
                        onGoal = {}, onMinutes = { minutes = it }, onFocus = {}, onStreak = {},
                        onBack = { backCalls++ }, onNext = { nextCalls++ }, onFinish = {}, onTrial = {}, onRetryTrial = {},
                        modifier = Modifier.size(320.dp, height.dp))
                }
            }
        }
        val question = compose.onNodeWithText(localized.getString(R.string.li_times_10_say)).assertIsDisplayed()
        val backLabel = localized.getString(R.string.li_copy_back)
        compose.onNodeWithText(backLabel).assertDoesNotExist()
        val back = compose.onNodeWithContentDescription(backLabel).assertIsDisplayed()
        val next = compose.onNodeWithText(localized.getString(R.string.li_copy_cont)).assertIsDisplayed()
        val footerTop = next.getUnclippedBoundsInRoot().top
        assertTrue(back.getUnclippedBoundsInRoot().bottom < question.getUnclippedBoundsInRoot().top)
        if (height == 700) {
            val bitmap = compose.onRoot().captureToImage().asAndroidBitmap()
            File(context.cacheDir, "native-li-$lang.png").outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
        }
        val unit = localized.getString(R.string.li_copy_min)
        if (height == 700) {
            listOf(5, 10, 15, 20, 30).forEach { value ->
                val choice = compose.onNodeWithText("$value $unit").assertIsDisplayed()
                assertTrue("Choice $value bounds ${choice.getUnclippedBoundsInRoot()} must be above footer at $footerTop",
                    choice.getUnclippedBoundsInRoot().bottom < footerTop)
            }
        } else {
            compose.onNodeWithText("30 $unit").performScrollTo().assertIsDisplayed()
            assertTrue(compose.onNodeWithText("30 $unit").getUnclippedBoundsInRoot().bottom < footerTop)
            assertEquals(footerTop, next.getUnclippedBoundsInRoot().top)
        }
        compose.onNodeWithText("20 $unit").performScrollTo().performClick()
        compose.onNodeWithText(localized.getString(R.string.li_times_20_say)).performScrollTo().assertIsDisplayed()
        back.performClick()
        next.performClick()
        compose.runOnIdle {
            assertEquals(20, minutes)
            assertEquals(1, backCalls)
            assertEquals(1, nextCalls)
        }
    }
    @Test fun uzbekChoicesAt320() = renderChoices("uz")
    @Test fun russianChoicesAt320() = renderChoices("ru")
    @Test fun tajikChoicesAt320() = renderChoices("tg")
    @Test fun shortViewportScrollsChoicesWithoutMovingFooter() = renderChoices("ru", height = 510)
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
