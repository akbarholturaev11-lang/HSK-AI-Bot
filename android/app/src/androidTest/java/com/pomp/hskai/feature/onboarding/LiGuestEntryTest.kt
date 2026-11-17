package com.pomp.hskai.feature.onboarding

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.lifecycle.viewmodel.compose.LocalViewModelStoreOwner
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.data.api.AndroidOnboardingApi
import com.pomp.hskai.data.api.AndroidOnboardingCompleteDto
import com.pomp.hskai.data.api.AndroidOnboardingRequestDto
import com.pomp.hskai.data.api.AndroidOnboardingStatusDto
import com.pomp.hskai.data.repository.OnboardingRepository
import com.pomp.hskai.feature.auth.LinkScreen
import com.pomp.hskai.feature.auth.LinkUiState
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import retrofit2.Response

class LiGuestEntryTest {
    @get:Rule val compose = createComposeRule()
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private val anonymousRepo = OnboardingRepository(object : AndroidOnboardingApi {
        override suspend fun status(authorization: String): Response<AndroidOnboardingStatusDto> =
            error("No authenticated status before login")
        override suspend fun complete(authorization: String, body: AndroidOnboardingRequestDto): Response<AndroidOnboardingCompleteDto> =
            error("No authenticated save before login")
    }, { error("No bearer before login") })

    private fun show(save: suspend (GuestLiDraft) -> Unit) {
        compose.setContent {
            PompHskAiTheme {
                LiGuestEntry(
                    anonymousRepo, AndroidOnboardingStatusDto(ok = true, liEnabled = true),
                    initialDraft = null, owner = checkNotNull(LocalViewModelStoreOwner.current),
                    language = AppLanguage.UZBEK, onLanguageSelected = {}, saveDraft = save,
                    provider = { signup, back -> LinkScreen(LinkUiState(), signup = signup, onBack = back) },
                )
            }
        }
    }

    private fun text(id: Int) = compose.onNodeWithText(context.getString(id))

    @Test fun newLearnerAnswersBeforeProviderCardsAndCanEditDraft() {
        var saved: GuestLiDraft? = null
        show { saved = it }
        text(R.string.li_copy_firsttime).assertIsDisplayed().performClick()
        text(R.string.auth_choose_method).assertDoesNotExist()
        text(R.string.li_copy_cont).performClick()
        repeat(2) { text(R.string.hsk_course_onboarding_cont).performClick() }
        text(R.string.li_copy_cont).performClick()
        compose.onNodeWithText("20 " + context.getString(R.string.li_copy_min)).performClick()
        repeat(3) { text(R.string.li_copy_cont).performClick() }
        text(R.string.li_copy_signuptitle).performClick()
        text(R.string.li_copy_signupsub).assertIsDisplayed()
        compose.runOnIdle { assertEquals(20, saved?.minutes) }
        compose.onNodeWithContentDescription(context.getString(R.string.li_copy_back)).performClick()
        text(R.string.li_copy_signuptitle).assertIsDisplayed()
    }

    @Test fun returningLearnerGoesStraightToLogin() {
        show { error("Existing learner must not save a guest draft") }
        text(R.string.li_copy_haveaccount).performClick()
        text(R.string.auth_choose_method).assertIsDisplayed()
        text(R.string.li_copy_signupsub).assertDoesNotExist()
    }
}
