package com.pomp.hskai.feature.rating

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onFirst
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.data.api.ChallengeDto
import com.pomp.hskai.data.api.ChallengeUserDto
import com.pomp.hskai.data.api.RatingEntryDto
import com.pomp.hskai.data.api.RatingResponse
import com.pomp.hskai.data.api.ReferralItemDto
import com.pomp.hskai.data.api.ReferralOverviewResponse
import org.junit.Rule
import org.junit.Test
import org.junit.Assert.assertEquals
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class RatingNavigationTest {

    @get:Rule
    val compose = createComposeRule()

    private val rival = RatingEntryDto(
        rank = 2,
        name = "Akbar Rival",
        xp = 150,
        courseLevel = "hsk3",
        challengeRef = "opaque-rival-reference",
    )
    private val state = RatingUiState(
        isLoading = false,
        rating = RatingResponse(
            ok = true,
            league = "vermilion",
            weeklyXp = 180,
            leaderboard = listOf(rival),
        ),
        challenges = listOf(
            ChallengeDto(
                id = 17,
                status = "pending",
                viewerRole = "opponent",
                otherUser = ChallengeUserDto(name = "Li Wei"),
            )
        ),
    )

    @Test
    fun bell_opens_the_challenge_inbox() {
        compose.setContent {
            PompHskAiTheme {
                var inboxOpen by remember { mutableStateOf(false) }
                if (inboxOpen) {
                    RatingChallengesScreen(
                        state = state,
                        onRespond = { _, _ -> },
                        onStartChallenge = {},
                        onBack = { inboxOpen = false },
                    )
                } else {
                    RatingScreen(
                        state = state,
                        onSelectTab = {},
                        onOpenChallenges = { inboxOpen = true },
                        onOpenUser = {},
                        onInviteFriends = {},
                        onChallenge = {},
                        onRetry = {},
                    )
                }
            }
        }

        compose.onNodeWithContentDescription("Bellashuvlar va chaqiruvlar").performClick()
        compose.onNodeWithText("Bellashuvlar").assertIsDisplayed()
        compose.onNodeWithText("Li Wei").assertIsDisplayed()
    }

    @Test
    fun leaderboard_user_opens_the_mini_app_style_profile() {
        compose.setContent {
            PompHskAiTheme {
                var selected by remember { mutableStateOf<RatingEntryDto?>(null) }
                val user = selected
                if (user != null) {
                    RatingUserScreen(
                        user = user,
                        league = state.rating?.league.orEmpty(),
                        currentWeeklyXp = state.rating?.weeklyXp ?: 0,
                        isChallengeBusy = false,
                        challengeDelivery = null,
                        challengeError = null,
                        onChallenge = {},
                        onMessage = {},
                        onBack = { selected = null },
                    )
                } else {
                    RatingScreen(
                        state = state,
                        onSelectTab = {},
                        onOpenChallenges = {},
                        onOpenUser = { selected = it },
                        onInviteFriends = {},
                        onChallenge = {},
                        onRetry = {},
                    )
                }
            }
        }

        compose.onNodeWithText("Akbar Rival").performClick()
        compose.onNodeWithText("Haftalik reyting").assertIsDisplayed()
        compose.onAllNodesWithText("HSK 3").onFirst().assertIsDisplayed()
    }

    @Test
    fun quick_challenge_button_does_not_open_the_profile() {
        val sent = mutableListOf<String>()
        compose.setContent {
            PompHskAiTheme {
                var selected by remember { mutableStateOf<RatingEntryDto?>(null) }
                RatingScreen(
                    state = state,
                    onSelectTab = {},
                    onOpenChallenges = {},
                    onOpenUser = { selected = it },
                    onInviteFriends = {},
                    onChallenge = { sent += it },
                    onRetry = {},
                )
                if (selected != null) {
                    androidx.compose.material3.Text("PROFILE_OPEN")
                }
            }
        }

        compose.onNodeWithText("战").performClick()
        compose.onNodeWithText("PROFILE_OPEN").assertDoesNotExist()
        assertEquals(listOf(rival.challengeRef), sent)
    }

    @Test
    fun profile_shows_verified_telegram_delivery() {
        compose.setContent {
            PompHskAiTheme {
                RatingUserScreen(
                    user = rival,
                    league = state.rating?.league.orEmpty(),
                    currentWeeklyXp = state.rating?.weeklyXp ?: 0,
                    isChallengeBusy = false,
                    challengeDelivery = ChallengeDelivery.TELEGRAM_SENT,
                    challengeError = null,
                    onChallenge = {},
                    onMessage = {},
                    onBack = {},
                )
            }
        }

        compose.onNodeWithText("Chaqiruv yuborildi").assertIsDisplayed()
        compose.onNodeWithText("Raqib Telegram orqali xabar oldi.").assertIsDisplayed()
    }

    @Test
    fun profile_does_not_claim_telegram_delivery_when_notification_failed() {
        compose.setContent {
            PompHskAiTheme {
                RatingUserScreen(
                    user = rival,
                    league = state.rating?.league.orEmpty(),
                    currentWeeklyXp = state.rating?.weeklyXp ?: 0,
                    isChallengeBusy = false,
                    challengeDelivery = ChallengeDelivery.APP_ONLY,
                    challengeError = null,
                    onChallenge = {},
                    onMessage = {},
                    onBack = {},
                )
            }
        }

        compose.onNodeWithText("Chaqiruv yaratildi").assertIsDisplayed()
        compose.onNodeWithText("Raqib Telegram orqali xabar oldi.").assertDoesNotExist()
    }

    @Test
    fun friends_tab_invites_and_opens_a_real_friend_profile() {
        val friend = ReferralItemDto(
            rank = 1,
            name = "Li Friend",
            username = "li_friend",
            status = "active",
            xp = 45,
            totalXp = 320,
            courseLevel = "hsk3",
            challengeRef = "opaque-friend-reference",
        )
        val friendState = state.copy(
            tab = RatingTab.FRIENDS,
            referral = ReferralOverviewResponse(
                ok = true,
                link = "https://t.me/pomp_bot?start=invite",
                invited = 1,
                activated = 1,
                trialRequired = 5,
                items = listOf(friend),
            ),
        )
        var sharedLink = ""
        var openedUser: RatingEntryDto? = null

        compose.setContent {
            PompHskAiTheme {
                RatingScreen(
                    state = friendState,
                    onSelectTab = {},
                    onOpenChallenges = {},
                    onOpenUser = { openedUser = it },
                    onInviteFriends = { sharedLink = it },
                    onChallenge = {},
                    onRetry = {},
                )
            }
        }

        compose.onNodeWithText("Do‘st taklif qilish").performClick()
        assertEquals("https://t.me/pomp_bot?start=invite", sharedLink)
        compose.onNodeWithText("Li Friend").performClick()
        assertEquals("opaque-friend-reference", openedUser?.challengeRef)
        assertEquals("li_friend", openedUser?.username)
    }

    @Test
    fun friend_profile_message_button_returns_the_telegram_username() {
        var messaged = ""
        compose.setContent {
            PompHskAiTheme {
                RatingUserScreen(
                    user = rival.copy(username = "akbar_rival"),
                    league = state.rating?.league.orEmpty(),
                    currentWeeklyXp = state.rating?.weeklyXp ?: 0,
                    isChallengeBusy = false,
                    challengeDelivery = null,
                    challengeError = null,
                    onChallenge = {},
                    onMessage = { messaged = it },
                    onBack = {},
                )
            }
        }

        compose.onNodeWithContentDescription("Telegramda yozish").performClick()
        assertEquals("akbar_rival", messaged)
    }
}
