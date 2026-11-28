package com.pomp.hskai.feature.limit

import android.content.res.Configuration
import android.graphics.Bitmap
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.foundation.layout.height
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.platform.*
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import java.io.File
import java.util.Locale
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

/** Shared neutral gate is the only purchase policy allowed in Play. Direct's
 * server-priced inline offer has fake-transport coverage in androidTestDirect. */
class SectionLimitOverlayTest {
    @get:Rule val compose = createComposeRule()
    private val context = InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun uzbekGateKeepsAccessOnlyAction() = neutralGate("uz")
    @Test fun russianGateKeepsAccessOnlyAction() = neutralGate("ru")
    @Test fun tajikGateKeepsAccessOnlyAction() = neutralGate("tg")

    private fun neutralGate(locale: String) {
        val visible = mutableStateOf(true)
        var checks = 0
        var closes = 0
        var presented = 0
        var dismissed = 0
        val copy = context.createConfigurationContext(Configuration(context.resources.configuration).apply {
            setLocale(Locale.forLanguageTag(locale))
        })
        compose.setContent {
            CompositionLocalProvider(LocalContext provides copy, LocalConfiguration provides copy.resources.configuration) {
                PompHskAiTheme {
                    if (visible.value) SectionLimitOverlay("Voice", "voice_limit",
                        LimitGate(actions = LimitGateActions(onRecheck = { checks++ },
                            onPresented = { presented++ }, onDismissed = { dismissed++ })),
                        resetAt = "2099-01-01T00:00:00Z", onClose = { closes++; visible.value = false })
                }
            }
        }
        InstrumentationRegistry.getInstrumentation().waitForIdleSync()
        Thread.sleep(300)
        InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()?.let { bitmap ->
            File(context.getExternalFilesDir(null), "neutral-debug-$locale.png").outputStream().use {
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)
            }
        }
        compose.onNodeWithTag("limit-support").assertIsDisplayed()
        compose.onNodeWithContentDescription(copy.getString(R.string.profile_help)).assertIsDisplayed()
        compose.onNodeWithText(copy.getString(R.string.play_limit_daily_heading)).assertIsDisplayed()
        val action = compose.onNodeWithText(copy.getString(R.string.play_limit_check_access))
        action.assertIsDisplayed().performClick()
        val root = compose.onNodeWithTag("section-limit-sheet").fetchSemanticsNode().boundsInRoot
        assertTrue(action.fetchSemanticsNode().boundsInRoot.bottom <= root.bottom)
        compose.onNodeWithText(copy.getString(R.string.limit_sheet_get_pro)).assertDoesNotExist()
        InstrumentationRegistry.getInstrumentation().waitForIdleSync()
        Thread.sleep(300)
        compose.onNodeWithTag("section-limit-sheet").captureToImage().asAndroidBitmap().let { image ->
            File(context.getExternalFilesDir(null), "checkout-neutral-$locale.png").outputStream().use {
                image.compress(Bitmap.CompressFormat.PNG, 100, it)
            }
        }
        compose.onNodeWithContentDescription(copy.getString(R.string.action_close)).performClick()
        compose.runOnIdle { assertEquals(1, checks); assertEquals(1, closes); assertEquals(1, presented); assertEquals(1, dismissed) }
    }

    @Test fun compactLargeTextKeepsThePrimaryActionInsideTheWindow() {
        compose.setContent {
            val density = LocalDensity.current
            CompositionLocalProvider(LocalDensity provides Density(density.density, fontScale = 2f)) {
                PompHskAiTheme {
                    SectionLimitOverlay("Voice", "voice_limit", LimitGate(), {}, modifier = Modifier.height(420.dp))
                }
            }
        }
        val action = compose.onNodeWithText(context.getString(R.string.play_limit_check_access))
        action.assertIsDisplayed()
        val root = compose.onNodeWithTag("section-limit-sheet").fetchSemanticsNode().boundsInRoot
        assertTrue(action.fetchSemanticsNode().boundsInRoot.bottom <= root.bottom)
        compose.onNodeWithContentDescription(context.getString(R.string.action_close)).assertIsDisplayed()
    }
    @Test fun headphonesOpenTheConfiguredSupportContact() {
        var supportOpens = 0
        compose.setContent {
            PompHskAiTheme {
                SectionLimitOverlay("Voice", "voice_limit",
                    LimitGate(state = LimitGateState(supportUrl = "https://example.invalid/support"),
                        actions = LimitGateActions(onSupport = { supportOpens++ })), {})
            }
        }
        compose.onNodeWithTag("limit-support").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(1, supportOpens) }
    }

}
