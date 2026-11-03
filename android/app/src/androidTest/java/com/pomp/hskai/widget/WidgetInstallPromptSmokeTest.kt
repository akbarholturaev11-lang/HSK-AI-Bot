package com.pomp.hskai.widget

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onNodeWithTag
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** The in-app preview uses Compose, separately from the launcher's Glance host. */
@RunWith(AndroidJUnit4::class)
class WidgetInstallPromptSmokeTest {
    @get:Rule val compose = createComposeRule()
    @Test fun fullInstallPromptLoadsItsRealGradientPreviewWithoutCrashing() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        compose.setContent { PompHskAiTheme { WidgetInstallPromptScreen(onDismiss = {}) } }
        compose.onNodeWithText(context.getString(R.string.widget_prompt_title)).assertIsDisplayed()
        compose.onNodeWithTag("widget-install-preview").assertIsDisplayed()
    }
}
