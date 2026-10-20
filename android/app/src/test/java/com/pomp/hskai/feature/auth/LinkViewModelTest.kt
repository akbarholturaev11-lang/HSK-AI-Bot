package com.pomp.hskai.feature.auth

import com.pomp.hskai.core.auth.AuthProvider
import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.storage.CredentialStore
import com.pomp.hskai.data.api.AndroidAuthApi
import com.pomp.hskai.data.api.BootstrapResponse
import com.pomp.hskai.data.api.IdentitiesResponse
import com.pomp.hskai.data.api.IdentityLinkStatusRequest
import com.pomp.hskai.data.api.IdentityLinkStatusResponse
import com.pomp.hskai.data.api.IdentityUnlinkRequest
import com.pomp.hskai.data.api.IdentityUnlinkResponse
import com.pomp.hskai.data.api.LinkStartRequest
import com.pomp.hskai.data.api.LinkStartResponse
import com.pomp.hskai.data.api.LinkStatusRequest
import com.pomp.hskai.data.api.LinkStatusResponse
import com.pomp.hskai.data.api.NativeOAuthApi
import com.pomp.hskai.data.api.OAuthAssertRequest
import com.pomp.hskai.data.api.OAuthAssertResponse
import com.pomp.hskai.data.api.OAuthStartRequest
import com.pomp.hskai.data.api.OAuthStartResponse
import com.pomp.hskai.data.api.ProvidersResponse
import com.pomp.hskai.data.api.RefreshRequest
import com.pomp.hskai.data.api.RefreshResponse
import com.pomp.hskai.data.api.RevokeRequest
import com.pomp.hskai.data.api.RevokeResponse
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlinx.coroutines.withContext
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class LinkViewModelTest {
    private val dispatcher = StandardTestDispatcher()
    @Before fun setUp() = Dispatchers.setMain(dispatcher)
    @After fun tearDown() = Dispatchers.resetMain()

    @Test fun googleSigninUsesGoogleBrowserPageAndStopsOnTerminalStatus() = runTest(dispatcher) {
        val f = Fixture()
        f.model.signInWithGoogle(null, AppLanguage.UZBEK)
        runCurrent()
        assertEquals("browser_redirect", f.lastProviderStart?.mode)
        assertEquals("google", f.lastProviderStart?.provider)
        assertTrue(f.model.state.value.pendingBrowserUrl.orEmpty().startsWith("https://accounts.google.com/o/oauth2/v2/auth?"))
        f.model.browserUrlOpened()
        assertNull(f.model.state.value.pendingBrowserUrl)
        f.linkStatus = { Response.success(LinkStatusResponse(ok = true, status = "denied")) }
        advanceTimeBy(2_000); runCurrent()
        assertFalse(f.model.state.value.isWaitingForApproval)
        assertNull(f.model.state.value.busyProvider)
        assertNull(f.savedRefresh)
        assertEquals("oauth_cancelled", (f.model.state.value.error as com.pomp.hskai.core.network.ApiError.Server).code)
        val polls = f.polls
        advanceTimeBy(4_000); runCurrent()
        assertEquals(polls, f.polls)
        f.model.dismissWaiting()
    }

    @Test fun dismissedAppleStartCannotReplaceTheNewTelegramAttempt() = runTest(dispatcher) {
        val f = Fixture()
        val lateApple = CompletableDeferred<Response<OAuthStartResponse>>()
        f.providerStart = { withContext(NonCancellable) { lateApple.await() } }
        f.model.signInWithApple(AppLanguage.RUSSIAN)
        runCurrent()
        f.model.dismissWaiting()
        f.model.continueWithTelegram(AppLanguage.TAJIK)
        runCurrent()
        assertEquals("tj", f.lastTelegramStart?.language)
        assertEquals(AuthProvider.TELEGRAM, f.model.state.value.pending?.provider)

        lateApple.complete(providerPending())
        runCurrent()
        assertEquals(AuthProvider.TELEGRAM, f.model.state.value.busyProvider)
        assertNull(f.model.state.value.pendingBrowserUrl)
        assertTrue(f.model.state.value.pendingTelegramUrl.orEmpty().startsWith("https://t.me/"))
        f.model.dismissWaiting()
    }

    @Test fun dismissedProviderPollCannotPersistItsLateSessionTokens() = runTest(dispatcher) {
        val f = Fixture()
        val lateTokens = CompletableDeferred<Response<LinkStatusResponse>>()
        f.linkStatus = { withContext(NonCancellable) { lateTokens.await() } }
        f.model.signInWithApple(AppLanguage.UZBEK)
        runCurrent()
        assertEquals(1, f.polls)
        f.model.dismissWaiting()
        lateTokens.complete(Response.success(LinkStatusResponse(
            ok = true, status = "linked", accessToken = "late-access",
            accessExpiresIn = 900, refreshToken = "late-refresh",
        )))
        runCurrent()
        assertNull(f.savedRefresh)
        assertNull(f.model.state.value.pending)
        assertNull(f.model.state.value.pendingBrowserUrl)
        assertNull(f.model.state.value.error)
        assertFalse(f.model.state.value.isLinked)
    }

    @Test fun preparingTelegramBlocksOtherCardsAndDismissalStartsANewProviderWithItsLanguage() = runTest(dispatcher) {
        val f = Fixture()
        val lateTelegram = CompletableDeferred<Response<LinkStartResponse>>()
        f.telegramStart = { withContext(NonCancellable) { lateTelegram.await() } }
        f.model.continueWithTelegram(AppLanguage.UZBEK)
        f.model.signInWithGoogle(null, AppLanguage.RUSSIAN)
        assertTrue(f.model.state.value.isRequestingCode)
        runCurrent()
        assertEquals(0, f.providerStarts)
        f.model.dismissWaiting()
        f.model.signInWithApple(AppLanguage.TAJIK)
        runCurrent()
        assertEquals("tj", f.lastProviderStart?.language)
        lateTelegram.complete(telegramPending())
        runCurrent()
        f.model.continueWithTelegram(AppLanguage.RUSSIAN)
        assertEquals(1, f.telegramStarts)
        assertEquals(AuthProvider.APPLE, f.model.state.value.pending?.provider)
        assertNull(f.model.state.value.pendingTelegramUrl)
        f.model.dismissWaiting()
    }

    @Test fun invalidInvitationBlocksAllSigninStartsWithoutNetworkCalls() = runTest(dispatcher) {
        val f = Fixture()
        f.model.updateReferralCode("ra_abcdef12?admin=true")
        f.model.continueWithTelegram(AppLanguage.UZBEK)
        f.model.signInWithApple(AppLanguage.RUSSIAN)
        runCurrent()
        assertTrue(f.model.state.value.referralInvalid)
        assertEquals(0, f.telegramStarts)
        assertEquals(0, f.providerStarts)
        f.model.updateReferralCode("")
        f.model.continueWithTelegram(AppLanguage.UZBEK)
        runCurrent()
        assertEquals(1, f.telegramStarts)
        assertNull(f.lastTelegramStart?.referralCode)
        f.model.dismissWaiting()
    }

    @Test fun invitationCanChangeForANewAttemptButNotDuringActiveApproval() = runTest(dispatcher) {
        val f = Fixture()
        f.model.updateReferralCode("ref_abcdef12")
        f.model.continueWithTelegram(AppLanguage.UZBEK)
        runCurrent()
        assertEquals("ref_abcdef12", f.lastTelegramStart?.referralCode)
        f.model.updateReferralCode("ra_12345678")
        assertEquals("ref_abcdef12", f.model.state.value.referralCode)
        f.model.dismissWaiting()
        f.model.updateReferralCode("ra_12345678")
        f.model.signInWithApple(AppLanguage.RUSSIAN)
        runCurrent()
        assertEquals("ra_12345678", f.lastProviderStart?.referralCode)
        f.model.dismissWaiting()
    }

    private class Fixture {
        var savedRefresh: String? = null
        var telegramStarts = 0
        var providerStarts = 0
        var polls = 0
        var lastTelegramStart: LinkStartRequest? = null
        var lastProviderStart: OAuthStartRequest? = null
        var telegramStart: suspend () -> Response<LinkStartResponse> = { telegramPending() }
        var providerStart: suspend (OAuthStartRequest) -> Response<OAuthStartResponse> = { providerPending(it.provider) }
        var linkStatus: suspend () -> Response<LinkStatusResponse> = {
            Response.success(LinkStatusResponse(ok = true, status = "pending"))
        }
        private val store = object : CredentialStore {
            override suspend fun installationKey() = "k".repeat(64)
            override suspend fun refreshToken() = savedRefresh
            override suspend fun saveRefreshToken(token: String) { savedRefresh = token }
            override suspend fun cachedAccount(): String? = null
            override suspend fun saveCachedAccount(value: String) = Unit
            override suspend fun clearSession() { savedRefresh = null }
            override suspend fun clearEverything() = clearSession()
        }
        private val authApi = object : AndroidAuthApi {
            override suspend fun startLink(body: LinkStartRequest): Response<LinkStartResponse> {
                telegramStarts++
                lastTelegramStart = body
                return telegramStart()
            }
            override suspend fun linkStatus(body: LinkStatusRequest): Response<LinkStatusResponse> {
                polls++
                return linkStatus()
            }
            override suspend fun refresh(body: RefreshRequest): Response<RefreshResponse> = error("Unexpected refresh")
            override suspend fun revoke(authorization: String, body: RevokeRequest): Response<RevokeResponse> = error("Unexpected revoke")
            override suspend fun bootstrap(authorization: String, appVersion: String): Response<BootstrapResponse> = error("Unexpected bootstrap")
        }
        private val oauthApi = object : NativeOAuthApi {
            override suspend fun providers(platform: String) = Response.success(ProvidersResponse(ok = true, providers = listOf("apple")))
            override suspend fun oauthStart(body: OAuthStartRequest): Response<OAuthStartResponse> {
                providerStarts++
                lastProviderStart = body
                return providerStart(body)
            }
            override suspend fun oauthAssert(body: OAuthAssertRequest): Response<OAuthAssertResponse> = error("Unexpected assert")
            override suspend fun identities(authorization: String): Response<IdentitiesResponse> = error("Unexpected identities")
            override suspend fun identityLinkStart(authorization: String, body: OAuthStartRequest): Response<OAuthStartResponse> = error("Unexpected linking")
            override suspend fun identityLinkStatus(authorization: String, body: IdentityLinkStatusRequest): Response<IdentityLinkStatusResponse> = error("Unexpected linking poll")
            override suspend fun identityLinkCancel(
                authorization: String,
                body: IdentityLinkStatusRequest,
            ): Response<IdentityLinkStatusResponse> = Response.success(
                IdentityLinkStatusResponse(ok = true, status = "denied", provider = "telegram"),
            )

            override suspend fun identityUnlink(authorization: String, body: IdentityUnlinkRequest): Response<IdentityUnlinkResponse> = error("Unexpected unlink")
        }
        val model = LinkViewModel(AuthRepository(authApi, store, "test", oauthApi = oauthApi, now = { 0L }), now = { 0L })
    }

    private companion object {
        fun providerPending(provider: String = "apple") = Response.success(OAuthStartResponse(
            ok = true, status = "pending", linkRequestId = "3f2504e0-4f89-11d3-9a0c-0305e82c3301", pollingSecret = "s".repeat(43),
            expiresIn = 600, authorizeUrl = if (provider == "google") "https://accounts.google.com/o/oauth2/v2/auth?state=opaque"
                else "https://appleid.apple.com/auth/authorize?state=opaque",
        ))
        fun telegramPending() = Response.success(LinkStartResponse(
            ok = true, status = "pending", linkRequestId = "4f2504e0-4f89-11d3-9a0c-0305e82c3301", displayCode = "HSK12345",
            pollingSecret = "t".repeat(43), botDeepLink = "https://t.me/example_bot?start=android_link_example", expiresIn = 600,
        ))
    }
}
