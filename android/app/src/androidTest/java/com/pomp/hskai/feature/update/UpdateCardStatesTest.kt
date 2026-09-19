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
 * What the profile actually says in each state.
 *
 * The one worth pinning is the permission case: without it the card would
 * announce a version, be tapped, and do nothing visible — Android would send
 * the learner to a settings screen they never asked for.
 */
@RunWith(AndroidJUnit4::class)
class UpdateCardStatesTest {

    @get:Rule
    val compose = createComposeRule()

    private val release = UpdateRelease(
        versionName = "1.2.0",
        versionCode = 3,
        url = "https://pub-example.r2.dev/hsk-ai-1.2.0-3-direct-release.apk",
        size = 3_766_687L,
    )

    private fun show(phase: UpdatePhase, canInstall: Boolean, onClick: () -> Unit = {}) {
        compose.setContent {
            PompHskAiTheme {
                UpdateCardContent(
                    release = release,
                    phase = phase,
                    canInstall = canInstall,
                    onClick = onClick,
                )
            }
        }
    }

    @Test
    fun readyCardNamesTheVersionAndItsSize() {
        show(phase = UpdatePhase.Ready, canInstall = true)

        compose.onNodeWithText("Yangi versiya 1.2.0").assertIsDisplayed()
        compose.onNodeWithText("3.6 MB · yangilash uchun bosing").assertIsDisplayed()
    }

    @Test
    fun withoutPermissionItAsksForThePermissionInstead() {
        show(phase = UpdatePhase.Ready, canInstall = false)

        compose.onNodeWithText("O‘rnatishga ruxsat bering").assertIsDisplayed()
        compose.onNodeWithText("Android sozlamalari ochiladi").assertIsDisplayed()
    }

    @Test
    fun downloadingSaysSoWithoutLosingTheVersion() {
        show(phase = UpdatePhase.Downloading, canInstall = true)

        compose.onNodeWithText("Yangi versiya 1.2.0").assertIsDisplayed()
        compose.onNodeWithText("Yuklanmoqda…").assertIsDisplayed()
    }

    @Test
    fun aFailedDownloadInvitesAnotherTry() {
        show(phase = UpdatePhase.Failed, canInstall = true)

        compose.onNodeWithText("Yuklab bo‘lmadi — qayta urinib ko‘ring").assertIsDisplayed()
    }

    @Test
    fun theWholeRowIsTappable() {
        var taps = 0
        show(phase = UpdatePhase.Ready, canInstall = true, onClick = { taps += 1 })

        compose.onNodeWithText("Yangi versiya 1.2.0").performClick()

        assertEquals(1, taps)
    }
}
