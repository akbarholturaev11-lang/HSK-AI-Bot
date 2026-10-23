package com.pomp.hskai.feature.limit

import android.graphics.Bitmap
import android.content.res.Configuration
import java.util.Locale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.key
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.layout.LayoutCoordinates
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.hasAnyDescendant
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.isRoot
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.feature.assistant.AssistantBinding
import com.pomp.hskai.feature.assistant.AssistantScreen
import com.pomp.hskai.feature.assistant.LocalAssistant
import com.pomp.hskai.feature.assistant.ScreenContext
import com.pomp.hskai.feature.assistant.ScreenRegistry
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SectionLimitOverlayTest {
    @get:Rule val compose = createComposeRule()

    @Test fun compactLargeTextPaywallKeepsItsActionVisibleAndSuppressesTheAssistant() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val registry = ScreenRegistry()
        val binding = AssistantBinding(
            registry, (context.applicationContext as HskAiApplication).assistant, {}, { _, _ -> },
        )
        val visible = mutableStateOf(true)
        var openedSource = ""
        var viewportHeight = 0f
        compose.setContent {
            val density = LocalDensity.current
            viewportHeight = with(density) { 420.dp.toPx() }
            CompositionLocalProvider(
                LocalAssistant provides binding,
                LocalDensity provides Density(density.density, fontScale = 2f),
            ) {
                PompHskAiTheme {
                    AssistantScreen(ScreenContext(screen = "voice"))
                    if (visible.value) SectionLimitOverlay(
                        sectionTitle = "AI Voice", sourceKey = "ai_voice",
                        limit = LimitGate(
                            state = LimitGateState(canSubscribe = true),
                            actions = LimitGateActions(onUnlock = { openedSource = it }),
                        ),
                        reason = "Лимит закончился. ".repeat(25),
                        onClose = { visible.value = false },
                        modifier = Modifier.height(420.dp),
                    )
                }
            }
        }
        val action = compose.onNodeWithText(context.getString(R.string.limit_sheet_get_pro))
        action.performScrollTo()
        action.assertIsDisplayed()
        val bounds = action.fetchSemanticsNode().boundsInRoot
        assertTrue("Entire Pro action must stay inside the viewport", bounds.bottom <= viewportHeight + 1f)
        compose.runOnIdle { assertTrue(registry.current!!.hidesAssistant) }
        val image = compose.onNode(isRoot() and hasAnyDescendant(hasText(context.getString(R.string.limit_sheet_get_pro))))
            .captureToImage().asAndroidBitmap()
        File(context.getExternalFilesDir(null), "ui-fix-limit-large-text.png").outputStream().use {
            image.compress(Bitmap.CompressFormat.PNG, 100, it)
        }
        action.performClick()
        compose.runOnIdle { assertEquals("ai_voice", openedSource) }
        compose.onNodeWithContentDescription(context.getString(R.string.action_close)).performClick()
        compose.runOnIdle { assertTrue(registry.current!!.showsButton) }
    }

    @Test fun proActionFollowsTheOfferCardWithoutALargeSpacer() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val registry = ScreenRegistry()
        val binding = AssistantBinding(
            registry, (context.applicationContext as HskAiApplication).assistant, {}, { _, _ -> },
        )
        compose.setContent {
            CompositionLocalProvider(LocalAssistant provides binding) {
                PompHskAiTheme {
                    SectionLimitOverlay(
                        sectionTitle = "AI Voice", sourceKey = "ai_voice",
                        limit = LimitGate(state = LimitGateState(canSubscribe = true)),
                        onClose = {},
                    )
                }
            }
        }

        val offerDescription = compose.onNodeWithText(context.getString(R.string.limit_sheet_voice_desc))
        val action = compose.onNodeWithText(context.getString(R.string.limit_sheet_get_pro))
        offerDescription.assertIsDisplayed()
        action.assertIsDisplayed()
        val gap = action.fetchSemanticsNode().boundsInRoot.top - offerDescription.fetchSemanticsNode().boundsInRoot.bottom
        val maximumGap = 100 * context.resources.displayMetrics.density
        assertTrue("Pro action should sit directly below the offer card; gap=$gap px", gap in 0f..maximumGap)
    }

    @Test fun dialogWrapsItsContentOnTallScreens() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        var coordinates: LayoutCoordinates? = null
        compose.setContent {
            PompHskAiTheme {
                SectionLimitOverlay(
                    sectionTitle = "AI Voice", sourceKey = "ai_voice",
                    limit = LimitGate(state = LimitGateState(canSubscribe = true)),
                    onClose = {},
                    modifier = Modifier.onGloballyPositioned { coordinates = it },
                )
            }
        }
        compose.onNodeWithText(context.getString(R.string.limit_sheet_get_pro)).assertIsDisplayed()
        val sheetHeight = compose.onNodeWithTag("section-limit-sheet").fetchSemanticsNode().boundsInRoot.height
        val displayHeight = context.resources.displayMetrics.heightPixels.toFloat()
        assertTrue(
            "The sheet must wrap its content instead of stretching to the full viewport",
            sheetHeight < displayHeight * 0.82f,
        )
        compose.runOnIdle {
            val layout = requireNotNull(coordinates)
            val origin = layout.localToScreen(Offset.Zero)
            assertTrue("Dialog must start inside the display", origin.y >= -1f)
            assertTrue("Dialog must fit its visible device window", origin.y + layout.size.height <= displayHeight + 1f)
        }
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        // Wait for the native dialog window to reach the display compositor.
        instrumentation.waitForIdleSync()
        Thread.sleep(500)
        val image = requireNotNull(instrumentation.uiAutomation.takeScreenshot())
        File(context.getExternalFilesDir(null), "ui-fix-limit-content-height.png")
            .outputStream().use {
                image.compress(Bitmap.CompressFormat.PNG, 100, it)
            }
    }
    @Test fun playLimitCopyIsLocalizedAndOnlyOffersAnAccessRecheck() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val locale = mutableStateOf("uz")
        val daily = mutableStateOf(true)
        var checks = 0
        compose.setContent {
            val localized = context.createConfigurationContext(
                Configuration(context.resources.configuration).apply { setLocale(Locale.forLanguageTag(locale.value)) },
            )
            CompositionLocalProvider(
                LocalContext provides localized,
                LocalConfiguration provides localized.resources.configuration,
            ) {
                key(locale.value) { PompHskAiTheme {
                    SectionLimitOverlay(
                        sectionTitle = "AI Voice", sourceKey = "voice_limit",
                        limit = LimitGate(actions = LimitGateActions(onRecheck = { checks++ })),
                        resetAt = if (daily.value) "2099-01-01T00:00:00Z" else null,
                        onClose = {},
                    )
                } }
            }
        }
        for (language in listOf("uz", "ru", "tg")) {
            compose.runOnIdle { locale.value = language }
            val localized = context.createConfigurationContext(
                Configuration(context.resources.configuration).apply { setLocale(Locale.forLanguageTag(language)) },
            )
            compose.onNodeWithText(localized.getString(R.string.play_limit_daily_heading)).assertIsDisplayed()
            compose.onNodeWithText(localized.getString(R.string.play_limit_required)).performScrollTo().assertIsDisplayed()
            val action = compose.onNodeWithText(localized.getString(R.string.play_limit_check_access))
            action.performScrollTo().assertIsDisplayed()
            action.performClick()
            compose.onNodeWithText(localized.getString(R.string.limit_sheet_get_pro)).assertDoesNotExist()
            compose.onNodeWithText(localized.getString(R.string.limit_sheet_voice_desc)).assertDoesNotExist()
            InstrumentationRegistry.getInstrumentation().waitForIdleSync()
            val image = requireNotNull(InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot())
            File(context.getExternalFilesDir(null), "play-limit-$language.png").outputStream().use {
                image.compress(Bitmap.CompressFormat.PNG, 100, it)
            }
        }
        compose.runOnIdle { assertEquals(3, checks); daily.value = false }
        val localized = context.createConfigurationContext(
            Configuration(context.resources.configuration).apply { setLocale(Locale.forLanguageTag("tg")) },
        )
        compose.onNodeWithText(localized.getString(R.string.play_limit_heading)).performScrollTo().assertIsDisplayed()
        compose.onNodeWithText(localized.getString(R.string.play_limit_renewal), substring = true).assertDoesNotExist()
    }

}
