package com.pomp.hskai.feature.onboarding

import android.content.res.Configuration
import android.graphics.Bitmap
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.core.design.PompHskAiTheme
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class CourseVersionOnboardingTest {
    @get:Rule
    val compose = createComposeRule()

    private fun checkVersionStep(language: String, width: Int, height: Int) {
        val track = mutableStateOf("hsk30")
        val copy = OnboardingCopy.forLanguage(language)
        var density = 1f
        compose.setContent {
            val base = LocalConfiguration.current
            val configuration = remember(base) {
                Configuration(base).apply {
                    screenWidthDp = width
                    screenHeightDp = height
                }
            }
            density = LocalDensity.current.density
            CompositionLocalProvider(LocalConfiguration provides configuration) {
                PompHskAiTheme {
                    OnboardingScreen(
                        language = language,
                        state = OnboardingUiState(
                            step = 1,
                            selectedTrack = track.value,
                            hsk30Enabled = true,
                            hsk30PaymentEnabled = true,
                            hsk30PriceTjs = 10,
                            hsk30PriceDisplay = "$1.08",
                        ),
                        onTrackSelected = { track.value = it },
                        onLevelSelected = {},
                        onGoalSelected = {},
                        onBack = {},
                        onNext = {},
                        modifier = Modifier.size(width.dp, height.dp),
                    )
                }
            }
        }

        compose.onNodeWithText(copy.versionHint).assertDoesNotExist()
        val books = compose.onNodeWithContentDescription(copy.hsk30BooksDescription)
            .assertIsDisplayed().fetchSemanticsNode().boundsInRoot
        assertEquals(4f / 3f, books.width / books.height, 0.01f)
        val selector = compose.onNodeWithText(copy.hsk30).assertIsDisplayed()
            .fetchSemanticsNode().boundsInRoot
        val continueButton = compose.onNodeWithText(copy.continueLabel).assertIsDisplayed()
            .fetchSemanticsNode().boundsInRoot
        assertTrue("Book art must stay above the selector", books.bottom <= selector.top)
        assertTrue("Version choice must sit next to Continue", continueButton.top - selector.bottom < 24f * density)

        val image = compose.onRoot().captureToImage().asAndroidBitmap()
        val cache = InstrumentationRegistry.getInstrumentation().targetContext.cacheDir
        File(cache, "hsk-onboarding-version-$language.png").outputStream().use {
            image.compress(Bitmap.CompressFormat.PNG, 100, it)
        }

        compose.onNodeWithText(copy.hsk20).performClick()
        compose.onNodeWithContentDescription(copy.hsk20BooksDescription).assertIsDisplayed()
        compose.onNodeWithContentDescription(copy.hsk30BooksDescription).assertDoesNotExist()
        val after = compose.onNodeWithText(copy.hsk30).fetchSemanticsNode().boundsInRoot
        assertEquals("Track switching must keep controls stable", selector.top, after.top, 1f)
    }

    @Test
    fun fitsRegularScreen() = checkVersionStep("uz", 393, 820)

    @Test
    fun fitsSmallScreen() = checkVersionStep("tj", 320, 568)

    @Test
    fun fitsRussianCompactScreen() = checkVersionStep("ru", 360, 640)
}
