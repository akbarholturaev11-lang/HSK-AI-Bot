package com.pomp.hskai.feature.offline

import android.graphics.Bitmap
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.navigation.MainScaffold
import com.pomp.hskai.core.navigation.MainTab
import com.pomp.hskai.core.settings.AppSettings
import com.pomp.hskai.core.settings.AppThemeMode
import com.pomp.hskai.feature.limit.LimitGate
import com.pomp.hskai.feature.practice.PracticeRequest
import com.pomp.hskai.feature.practice.PracticeScreen
import com.pomp.hskai.feature.practice.PracticeUiState
import java.io.File
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * The app opened without the server: the banner above the tabs, the one tool
 * that still works, and the sections that say they need the internet.
 */
@RunWith(AndroidJUnit4::class)
class OfflineModeTest {

    @get:Rule
    val compose = createComposeRule()

    private val context = InstrumentationRegistry.getInstrumentation().targetContext

    private var dictionaryOpened = 0
    private var drillsOpened = 0
    private var requestsConsumed = 0
    private var retries = 0
    private var tab by mutableStateOf(MainTab.PRACTICE)

    private fun showPractice(
        tab: MainTab = MainTab.PRACTICE,
        request: PracticeRequest? = null,
    ) {
        this.tab = tab
        compose.setContent {
            PompHskAiTheme {
                MainScaffold(
                    selectedTab = this.tab,
                    onTabSelected = {},
                    topNotice = { OfflineBanner(retrying = false, onRetry = { retries++ }) },
                ) { selected, modifier ->
                    if (selected == MainTab.PRACTICE) {
                        OfflinePractice(request, modifier)
                    } else {
                        OfflineRequired(modifier)
                    }
                }
            }
        }
        compose.waitForIdle()
    }

    @androidx.compose.runtime.Composable
    private fun OfflinePractice(request: PracticeRequest?, modifier: Modifier) {
        PracticeScreen(
            state = PracticeUiState(),
            level = "hsk1",
            language = "uz",
            limit = LimitGate(),
            onOpenDictionary = { dictionaryOpened++ },
            onStartPractice = { _, _, _ -> },
            onSelectPracticeOption = {},
            onAdvancePractice = {},
            onResetPractice = {},
            onStartMistakeReview = {},
            onAnswerReview = {},
            onAdvanceReview = {},
            onResetReview = {},
            onSpeakReview = {},
            onStartExam = {},
            onOpenDrill = { drillsOpened++ },
            onSelectExamOption = {},
            onAdvanceExam = {},
            onResetExam = {},
            request = request,
            onRequestConsumed = { requestsConsumed++ },
            offline = true,
            modifier = modifier,
        )
    }

    @Test
    fun theBannerSaysOfflineAndRetriesOnTap() {
        showPractice()

        compose.onNodeWithText(context.getString(R.string.offline_banner)).assertIsDisplayed()
        compose.onNodeWithTag(OFFLINE_BANNER_TAG).performClick()

        assertEquals(1, retries)
        save("offline_practice")
    }

    @Test
    fun onlyTheDictionaryOpensInPractice() {
        showPractice()

        compose.onNodeWithText(context.getString(R.string.offline_practice)).assertIsDisplayed()
        compose.onNodeWithText(context.getString(R.string.practice_dictionary_title)).performClick()
        compose.onNodeWithText(context.getString(R.string.practice_characters_title)).performClick()

        assertEquals(1, dictionaryOpened)
        assertEquals(0, drillsOpened)
    }

    @Test
    fun aRequestForAToolIsDroppedInsteadOfFailing() {
        showPractice(request = PracticeRequest.RECOGNITION)

        assertEquals(1, requestsConsumed)
        assertEquals(0, drillsOpened)
    }

    @Test
    fun otherSectionsSayTheyNeedTheInternet() {
        showPractice(tab = MainTab.RATING)

        compose.onNodeWithTag(OFFLINE_REQUIRED_TAG).assertIsDisplayed()
        compose.onNodeWithText(context.getString(R.string.offline_section_title)).assertIsDisplayed()
        save("offline_rating")
    }

    @Test
    fun theOfflineScreensReadInDarkMode() {
        val settings = AppSettings(context)
        val previous = runBlocking { settings.themeMode.first() }
        runBlocking { settings.setThemeMode(AppThemeMode.DARK) }
        try {
            showPractice()
            save("dark_offline_practice")
            tab = MainTab.PROFILE
            save("dark_offline_profile")
        } finally {
            runBlocking { settings.setThemeMode(previous) }
        }
    }

    /** Kept on the device for `adb pull`: files/offline-screens/<name>.png */
    private fun save(name: String) {
        compose.waitForIdle()
        val bitmap = compose.onRoot().captureToImage().asAndroidBitmap()
        val dir = File(context.filesDir, "offline-screens").apply { mkdirs() }
        File(dir, "$name.png").outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }
}
