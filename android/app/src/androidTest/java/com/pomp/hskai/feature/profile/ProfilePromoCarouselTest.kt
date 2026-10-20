package com.pomp.hskai.feature.profile

import androidx.compose.runtime.MutableState
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.input.key.Key
import androidx.compose.ui.layout.positionInRoot
import androidx.compose.ui.semantics.SemanticsActions
import androidx.compose.ui.test.performKeyInput
import androidx.compose.ui.test.performSemanticsAction
import androidx.compose.ui.test.pressKey
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.assertIsSelected
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.test.swipeLeft
import androidx.compose.ui.test.swipeRight
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.AuthProvider
import com.pomp.hskai.core.auth.LinkedAccount
import com.pomp.hskai.core.auth.LinkedIdentity
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.data.api.AndroidTrialDto
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@OptIn(ExperimentalTestApi::class)
@RunWith(AndroidJUnit4::class)
class ProfilePromoCarouselTest {
    @get:Rule val compose = createComposeRule()
    private val loaded = IdentitiesUiState(hasLoaded = true,
        available = listOf(AuthProvider.GOOGLE, AuthProvider.APPLE))
    private fun identity(provider: AuthProvider) = LinkedIdentity(provider.wire, provider, null, null)

    private fun show(
        state: MutableState<IdentitiesUiState> = mutableStateOf(loaded),
        checkout: Boolean = false,
        onConnect: (AuthProvider) -> Unit = {},
        onHsk30: () -> Unit = {},
        profile: ProfileUiState = ProfileUiState(isLoading = false),
        accountIsPaid: Boolean = false,
        onSubscription: (Boolean) -> Unit = {},
        onTrial: () -> Unit = {},
    ) {
        compose.setContent {
            PompHskAiTheme {
                ProfilePromoCarousel(state = profile, accountIsPaid = accountIsPaid,
                    checkoutAvailable = checkout, onOpenHsk30 = onHsk30, onOpenSubscription = onSubscription,
                    onStartTrial = onTrial, identities = state.value, onConnectIdentity = onConnect)
            }
        }
    }

    @Test fun swipesMoveBetweenSeparateCardsAndUseTheExistingProviderAction() {
        val connected = mutableListOf<AuthProvider>()
        var books = 0
        show(onConnect = { connected.add(it) }, onHsk30 = { books++ })
        compose.onNodeWithTag("profile-promo-action-hsk30").performClick()
        assertEquals(1, books)
        compose.onNodeWithTag("profile-promo-pager").performTouchInput { swipeLeft() }
        compose.onNodeWithTag("profile-promo-action-telegram").assertIsDisplayed().performClick()
        assertEquals(listOf(AuthProvider.TELEGRAM), connected)
        compose.onNodeWithTag("profile-promo-pager").performTouchInput { swipeLeft() }
        compose.onNodeWithTag("profile-promo-action-google").assertIsDisplayed().performClick()
        compose.onNodeWithTag("profile-promo-pager").performTouchInput { swipeLeft() }
        compose.onNodeWithTag("profile-promo-action-apple").assertIsDisplayed().performClick()
        assertEquals(listOf(AuthProvider.TELEGRAM, AuthProvider.GOOGLE, AuthProvider.APPLE), connected)
        compose.onNodeWithTag("profile-promo-pager").performTouchInput { swipeRight() }
        compose.onNodeWithTag("profile-promo-dot-google").assertIsSelected()
    }

    @Test fun keyboardArrowsSlideBetweenPagesAndDotsExposeTheSelection() {
        show()
        compose.onNodeWithTag("profile-promo-pager")
            .performSemanticsAction(SemanticsActions.RequestFocus) { it() }
            .performKeyInput { pressKey(Key.DirectionRight) }
        compose.onNodeWithTag("profile-promo-dot-telegram").assertIsSelected()
        compose.onNodeWithTag("profile-promo-action-telegram").assertIsDisplayed()
        compose.onNodeWithTag("profile-promo-pager")
            .performKeyInput { pressKey(Key.DirectionLeft) }
        compose.onNodeWithTag("profile-promo-dot-hsk30").assertIsSelected()
    }

    @Test fun aCardTracksTheFingerBeforeTheSwipeIsReleased() {
        show()
        val first = compose.onNodeWithTag("profile-promo-card-hsk30")
        val initialLeft = first.fetchSemanticsNode().layoutInfo.coordinates.positionInRoot().x
        compose.onNodeWithTag("profile-promo-pager").performTouchInput {
            down(center)
            moveBy(Offset(-width * .1f, 0f))
            moveBy(Offset(-width * .25f, 0f))
        }
        val draggedLeft = first.fetchSemanticsNode().layoutInfo.coordinates.positionInRoot().x
        assertTrue("card must slide while the finger is held down", draggedLeft < initialLeft - 25f)
        compose.onNodeWithTag("profile-promo-pager").performTouchInput { up() }
    }

    @Test fun aNewlyLinkedFinalCardDisappearsWithoutAnInvalidPage() {
        val state = mutableStateOf(loaded.copy(telegramLinked = true,
            identities = listOf(identity(AuthProvider.GOOGLE))))
        show(state)
        compose.onNodeWithTag("profile-promo-dot-apple").performClick()
        compose.onNodeWithTag("profile-promo-action-apple").assertIsDisplayed()
        compose.runOnIdle { state.value = state.value.copy(identities =
            listOf(identity(AuthProvider.GOOGLE), identity(AuthProvider.APPLE))) }
        compose.onNodeWithTag("profile-promo-action-apple").assertDoesNotExist()
        compose.onNodeWithTag("profile-promo-dot-apple").assertDoesNotExist()
        compose.onNodeWithTag("profile-promo-action-hsk30").assertIsDisplayed()
    }

    @Test fun playKeepsLinkCardsAndNeverShowsTheProPurchaseCard() {
        show(checkout = false)
        compose.onNodeWithTag("profile-promo-dot-pro").assertDoesNotExist()
        compose.onNodeWithTag("profile-promo-dot-google").performClick().assertIsSelected()
        compose.onNodeWithTag("profile-promo-action-google").assertIsDisplayed()
        compose.onNodeWithTag("profile-promo-action-pro").assertDoesNotExist()
    }

    @Test fun directProCardKeepsTheExistingEligibleTrialAction() {
        var trials = 0
        val checkouts = mutableListOf<Boolean>()
        show(checkout = true, profile = ProfileUiState(isLoading = false,
            trial = AndroidTrialDto(eligible = true)), onTrial = { trials++ },
            onSubscription = { checkouts.add(it) })
        compose.onNodeWithTag("profile-promo-dot-pro").performClick()
        compose.onNodeWithTag("profile-promo-action-pro").performClick()
        assertEquals(1, trials)
        assertTrue(checkouts.isEmpty())
    }

    @Test fun directPaidProCardKeepsTheExistingRenewalAction() {
        val checkouts = mutableListOf<Boolean>()
        show(checkout = true, accountIsPaid = true, onSubscription = { checkouts.add(it) })
        compose.onNodeWithTag("profile-promo-dot-pro").performClick()
        compose.onNodeWithTag("profile-promo-action-pro").performClick()
        assertEquals(listOf(true), checkouts)
    }

    @Test fun pendingConnectionsDisableAdditionalLinkActions() {
        show(mutableStateOf(loaded.copy(busyProvider = AuthProvider.TELEGRAM)))
        compose.onNodeWithTag("profile-promo-dot-apple").performClick()
        compose.onNodeWithTag("profile-promo-action-apple").assertIsNotEnabled()
    }

    @Test fun profileCardOpensTheExistingSheetAndPassesAnActivityToTheConnectFlow() {
        val selected = mutableListOf<AuthProvider>()
        var activityAvailable = false
        var loads = 0
        compose.setContent {
            PompHskAiTheme {
                ProfileScreen(
                    account = LinkedAccount("Native learner", AppLanguage.UZBEK, "hsk1", "free", false),
                    state = ProfileUiState(isLoading = false), settings = ProfileSettingsState(),
                    courseProgress = null, courseUser = null, onOpenFriends = {},
                    dailyXp = 0, dailyGoal = 20, notificationsEnabled = true,
                    onOpenGoal = {}, onOpenLanguage = {}, onToggleNotifications = {}, onOpenWidget = {},
                    onOpenSupport = {}, onRefresh = {}, onLogout = {}, onUnlinkDevice = {}, courseTrack = "hsk20",
                    identities = loaded, onLoadIdentities = { loads++ },
                    onConnectIdentity = { provider, activity -> selected.add(provider); activityAvailable = activity != null },
                    subscriptionCheckoutAvailable = false,
                )
            }
        }
        compose.onNodeWithTag("profile-promo-pager").performScrollTo()
        compose.onNodeWithTag("profile-promo-dot-telegram").performScrollTo().performClick()
        compose.onNodeWithTag("profile-promo-action-telegram").performScrollTo().performClick()
        assertEquals(listOf(AuthProvider.TELEGRAM), selected)
        assertTrue(activityAvailable)
        assertTrue("identity state should load when the profile resumes", loads > 0)
        val title = InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.profile_account_title)
        compose.onNodeWithText(title).assertIsDisplayed()
    }
}
