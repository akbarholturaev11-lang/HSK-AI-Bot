package com.pomp.hskai.feature.update

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.core.design.PompHskAiTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class MandatoryUpdateStatesTest {

    @get:Rule
    val compose = createComposeRule()

    @Test
    fun mandatoryScreenHasOnlyTheUpdateAction() {
        val release = UpdateRelease(
            versionName = "1.7.6",
            versionCode = 37,
            url = "https://pub-example.r2.dev/hsk-ai-1.7.6-37-direct-release.apk",
        )
        var clicks = 0

        compose.setContent {
            PompHskAiTheme {
                MandatoryUpdateContent(
                    release = release,
                    phase = UpdatePhase.Ready,
                    downloadPercent = null,
                    canInstall = true,
                    onUpdate = { clicks += 1 },
                )
            }
        }

        compose.onNodeWithText("Yangi versiyani o‘rnating").assertIsDisplayed()
        compose.onNodeWithText("Ilovani yangilang").assertIsDisplayed().performClick()
        assertEquals(1, compose.onAllNodes(hasClickAction()).fetchSemanticsNodes().size)
        assertEquals(1, clicks)
    }
}
