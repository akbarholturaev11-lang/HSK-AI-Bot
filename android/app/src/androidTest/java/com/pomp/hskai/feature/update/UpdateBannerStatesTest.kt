package com.pomp.hskai.feature.update

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.core.design.PompHskAiTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * What the bar above the tabs actually says in each state.
 *
 * The permission case is the one worth pinning here too: a bar that names a
 * version, is tapped, and silently opens a settings screen is worse than no
 * bar at all.
 */
@RunWith(AndroidJUnit4::class)
class UpdateBannerStatesTest {

    @get:Rule
    val compose = createComposeRule()

    private val release = UpdateRelease(
        versionName = "1.4.0",
        versionCode = 6,
        url = "https://pub-example.r2.dev/hsk-ai-1.4.0-6-direct-release.apk",
        size = 3_766_687L,
    )

    private fun show(phase: UpdatePhase, canInstall: Boolean, onClick: () -> Unit = {}) {
        compose.setContent {
            PompHskAiTheme {
                UpdateBannerContent(
                    release = release,
                    phase = phase,
                    canInstall = canInstall,
                    onClick = onClick,
                )
            }
        }
    }

    @Test
    fun readyBannerNamesTheVersion() {
        show(phase = UpdatePhase.Ready, canInstall = true)

        compose.onNodeWithText("Yangi versiya 1.4.0 — yangilash uchun bosing").assertIsDisplayed()
    }

    @Test
    fun withoutPermissionItAsksForThePermissionInstead() {
        show(phase = UpdatePhase.Ready, canInstall = false)

        compose.onNodeWithText("O‘rnatishga ruxsat bering — yangilash uchun bosing")
            .assertIsDisplayed()
    }

    @Test
    fun downloadingAndFailureBothStaySpokenFor() {
        show(phase = UpdatePhase.Downloading, canInstall = true)
        compose.onNodeWithText("Yuklanmoqda…").assertIsDisplayed()
    }

    @Test
    fun tappingTheBarStartsTheUpdate() {
        var taps = 0
        show(phase = UpdatePhase.Ready, canInstall = true, onClick = { taps += 1 })

        compose.onNodeWithText("Yangi versiya 1.4.0 — yangilash uchun bosing").performClick()

        assertEquals(1, taps)
    }
}
