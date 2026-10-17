package com.pomp.hskai.feature.profile

import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.auth.AuthProvider
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.storage.CredentialStore
import com.pomp.hskai.data.api.AndroidAuthApi
import com.pomp.hskai.data.api.IdentitiesResponse
import com.pomp.hskai.data.api.IdentityDto
import com.pomp.hskai.data.api.IdentityUnlinkResponse
import com.pomp.hskai.data.api.IdentityLinkStatusRequest
import com.pomp.hskai.data.api.IdentityLinkStatusResponse
import com.pomp.hskai.data.api.IdentityUnlinkRequest
import com.pomp.hskai.data.api.OAuthStartRequest
import com.pomp.hskai.data.api.OAuthStartResponse
import com.pomp.hskai.data.api.OAuthAssertRequest
import com.pomp.hskai.data.api.OAuthAssertResponse
import com.pomp.hskai.data.api.NativeOAuthApi
import com.pomp.hskai.data.api.ProvidersResponse
import com.pomp.hskai.data.api.RefreshResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import java.lang.reflect.Proxy

@OptIn(ExperimentalCoroutinesApi::class)
class IdentitiesViewModelTest {
    private val dispatcher = StandardTestDispatcher()
    @Before fun setUp() = Dispatchers.setMain(dispatcher)
    @After fun tearDown() = Dispatchers.resetMain()

    private class Fixture(var telegramLinked: Boolean, providers: List<String>) {
        var unlinks = 0
        var unlinkError: String? = null
        var identitiesError = false
        var linkStarts = 0
        var linkPolls = 0
        var linkCancels = 0
        var linkedCallbacks = 0
        var startGate: CompletableDeferred<Unit>? = null
        var pollGate: CompletableDeferred<Unit>? = null
        var status = "pending"
        var linkError: String? = null
        var clock = 1_000L
        var provider = "telegram"
        val identities = providers.map { IdentityDto(id = it, provider = it) }
        private val store = object : CredentialStore {
            override suspend fun installationKey() = "k".repeat(64)
            override suspend fun refreshToken() = "existing-refresh"
            override suspend fun saveRefreshToken(token: String) = Unit
            override suspend fun cachedAccount(): String? = null
            override suspend fun saveCachedAccount(value: String) = Unit
            override suspend fun clearSession() = Unit
            override suspend fun clearEverything() = Unit
        }
        private val authApi = Proxy.newProxyInstance(
            AndroidAuthApi::class.java.classLoader, arrayOf(AndroidAuthApi::class.java),
        ) { _, method, _ ->
            when (method.name) {
                "refresh" -> Response.success(RefreshResponse(ok = true, accessToken = "access", accessExpiresIn = 900,
                    refreshToken = "rotated"))
                else -> error("Unexpected auth request: ${method.name}")
            }
        } as AndroidAuthApi
        private val oauthApi = object : NativeOAuthApi {
            override suspend fun providers(platform: String) =
                Response.success(ProvidersResponse(ok = true, providers = listOf("google", "apple")))
            override suspend fun identities(authorization: String): Response<IdentitiesResponse> =
                if (identitiesError) Response.error(503, "{}".toResponseBody())
                else Response.success(IdentitiesResponse(ok = true, telegramLinked = telegramLinked, identities = identities))
            override suspend fun identityUnlink(authorization: String, body: IdentityUnlinkRequest): Response<IdentityUnlinkResponse> {
                unlinks++
                return unlinkError?.let { Response.error(409,
                    """{"ok":false,"error":"$it"}""".toResponseBody()) }
                    ?: Response.success(IdentityUnlinkResponse(ok = true))
            }
            override suspend fun identityLinkStart(authorization: String, body: OAuthStartRequest): Response<OAuthStartResponse> {
                linkStarts++
                val requestedProvider = body.provider
                provider = requestedProvider
                startGate?.await()
                return Response.success(OAuthStartResponse(ok = true, status = "pending",
                    linkRequestId = "3f2504e0-4f89-11d3-9a0c-0305e82c3301", pollingSecret = "s".repeat(43),
                    expiresIn = 600, authorizeUrl = if (requestedProvider == "telegram") TELEGRAM_URL
                    else "https://appleid.apple.com/auth/authorize?client_id=x"))
            }
            override suspend fun identityLinkStatus(authorization: String, body: IdentityLinkStatusRequest): Response<IdentityLinkStatusResponse> {
                linkPolls++
                pollGate?.await()
                if (status == "linked" && provider == "telegram") telegramLinked = true
                return Response.success(IdentityLinkStatusResponse(ok = true, status = status, provider = provider, error = linkError))
            }
            override suspend fun identityLinkCancel(authorization: String, body: IdentityLinkStatusRequest): Response<IdentityLinkStatusResponse> {
                linkCancels++
                return Response.success(IdentityLinkStatusResponse(ok = true, status = "denied", provider = provider))
            }
            override suspend fun oauthStart(body: OAuthStartRequest): Response<OAuthStartResponse> = error("Linking must not sign in")
            override suspend fun oauthAssert(body: OAuthAssertRequest): Response<OAuthAssertResponse> = error("Telegram does not assert OAuth")
        }
        val model = IdentitiesViewModel(
            AuthRepository(authApi, store, "test", oauthApi = oauthApi, now = { clock }),
            onLinked = { linkedCallbacks++ },
            now = { clock },
        )
        fun load() { model.refresh() }

    }

    @Test fun promosWaitForAnAuthoritativeReadAndHideAgainAfterARefreshFailure() = runTest(dispatcher) {
        val f = Fixture(false, listOf("google"))
        assertFalse(f.model.state.value.hasLoaded)
        assertEquals(listOf(ProfilePromoPage.HSK30), profilePromoPages(false, f.model.state.value))
        f.load()
        assertFalse(f.model.state.value.hasLoaded)
        runCurrent()
        assertTrue(f.model.state.value.hasLoaded)
        assertEquals(listOf(ProfilePromoPage.HSK30, ProfilePromoPage.TELEGRAM, ProfilePromoPage.APPLE),
            profilePromoPages(false, f.model.state.value))
        f.identitiesError = true
        f.load()
        assertFalse(f.model.state.value.hasLoaded)
        runCurrent()
        assertFalse(f.model.state.value.hasLoaded)
        assertEquals(listOf(ProfilePromoPage.HSK30), profilePromoPages(false, f.model.state.value))
    }

    @Test fun providerOnlyAccountKeepsItsSoleSignInMethodAndLearnsTheRealTelegramState() = runTest(dispatcher) {
        val f = Fixture(telegramLinked = false, providers = listOf("google"))
        f.model.refresh()
        runCurrent()
        assertFalse(f.model.state.value.telegramLinked)
        assertFalse(f.model.state.value.canUnlinkProvider)
        f.model.disconnect("google")
        runCurrent()
        assertEquals(0, f.unlinks)
        assertEquals(ApiError.fromCode("oauth_last_identity"), f.model.state.value.error)
    }

    @Test fun telegramOrAnotherProviderPermitsUnlinkingAfterMetadataLoads() = runTest(dispatcher) {
        for (f in listOf(Fixture(true, listOf("google")), Fixture(false, listOf("google", "apple")))) {
            f.model.refresh()
            f.model.disconnect("google")
            runCurrent()
            assertEquals(0, f.unlinks)
            assertTrue(f.model.state.value.canUnlinkProvider)
            f.model.disconnect("google")
            runCurrent()
            assertEquals(1, f.unlinks)
        }
    }

    @Test fun rapidUnlinkTapsMakeOneRequestAndServerLastIdentityDenialRemainsVisible() = runTest(dispatcher) {
        val f = Fixture(false, listOf("google", "apple"))
        f.model.refresh()
        runCurrent()
        f.unlinkError = "oauth_last_identity"
        f.model.disconnect("google")
        f.model.disconnect("apple")
        runCurrent()
        assertEquals(1, f.unlinks)
        assertEquals(ApiError.fromCode("oauth_last_identity"), f.model.state.value.error)
        assertNull(f.model.state.value.busyProvider)
    }
    @Test fun nativeOnlyAccountCanAttachTelegramAndRefreshesItsExistingProfile() = runTest(dispatcher) {
        val f = Fixture(false, listOf("google"))
        f.load(); runCurrent()
        f.model.connect(AuthProvider.TELEGRAM, null); runCurrent()
        assertEquals(1, f.linkStarts)
        assertEquals(AuthProvider.TELEGRAM, f.model.state.value.busyProvider)
        assertEquals(TELEGRAM_URL, f.model.state.value.pendingBrowserUrl)
        f.model.browserUrlOpened()
        assertNull(f.model.state.value.pendingBrowserUrl)
        f.model.reopenTelegram()
        assertEquals(TELEGRAM_URL, f.model.state.value.pendingBrowserUrl)
        f.status = "linked"
        advanceTimeBy(2_000); runCurrent()
        assertTrue(f.model.state.value.telegramLinked)
        assertEquals(1, f.linkedCallbacks)
        assertEquals("google", f.model.state.value.identities.single().id)
        assertNull(f.model.state.value.busyProvider)
        assertNull(f.model.state.value.telegramApprovalUrl)
        assertEquals(0, f.linkCancels)
    }

    @Test fun anAlreadyLinkedTelegramIdentityCannotBeReplaced() = runTest(dispatcher) {
        val f = Fixture(true, listOf("google"))
        f.load(); runCurrent()
        f.model.connect(AuthProvider.TELEGRAM, null); runCurrent()
        assertEquals(0, f.linkStarts)
        assertTrue(f.model.state.value.telegramLinked)
    }

    @Test fun conflictingTelegramIdentityReportsTheCollisionWithoutChangingOwnership() = runTest(dispatcher) {
        val f = Fixture(false, listOf("apple"))
        f.load(); runCurrent()
        f.status = "denied"; f.linkError = "oauth_identity_bound_to_other_user"
        f.model.connect(AuthProvider.TELEGRAM, null); runCurrent()
        assertEquals(ApiError.fromCode("oauth_identity_bound_to_other_user"), f.model.state.value.error)
        assertFalse(f.model.state.value.telegramLinked)
        assertEquals("apple", f.model.state.value.identities.single().id)
        assertEquals(0, f.linkedCallbacks)
        assertNull(f.model.state.value.busyProvider)
        assertNull(f.model.state.value.pendingBrowserUrl)
    }

    @Test fun deniedAndExpiredProofsStopPollingAndClearTheirBrowserActions() = runTest(dispatcher) {
        for ((status, code) in listOf("denied" to "oauth_cancelled", "expired" to "desktop_link_expired")) {
            val f = Fixture(false, listOf("google"))
            f.load(); runCurrent()
            f.status = status
            f.model.connect(AuthProvider.TELEGRAM, null); runCurrent()
            assertEquals(ApiError.fromCode(code), f.model.state.value.error)
            assertNull(f.model.state.value.busyProvider)
            assertNull(f.model.state.value.pendingBrowserUrl)
            assertNull(f.model.state.value.telegramApprovalUrl)
            val polls = f.linkPolls
            advanceTimeBy(4_000); runCurrent()
            assertEquals(polls, f.linkPolls)
        }
    }

    @Test fun localExpiryStopsEvenIfTheServerNeverChangesPendingStatus() = runTest(dispatcher) {
        val f = Fixture(false, listOf("google"))
        f.load(); runCurrent()
        f.model.connect(AuthProvider.TELEGRAM, null); runCurrent()
        f.clock += 600_001
        advanceTimeBy(2_000); runCurrent()
        assertEquals(ApiError.fromCode("desktop_link_expired"), f.model.state.value.error)
        assertEquals(1, f.linkPolls)
        assertNull(f.model.state.value.busyProvider)
    }

    @Test fun dismissCancelsTheProofAndCannotReopenIt() = runTest(dispatcher) {
        val f = Fixture(false, listOf("google"))
        f.load(); runCurrent()
        f.model.connect(AuthProvider.TELEGRAM, null); runCurrent()
        f.model.cancelConnection(); runCurrent()
        assertEquals(1, f.linkCancels)
        assertNull(f.model.state.value.busyProvider)
        assertNull(f.model.state.value.pendingBrowserUrl)
        f.model.reopenTelegram()
        assertNull(f.model.state.value.pendingBrowserUrl)
        val polls = f.linkPolls
        advanceTimeBy(4_000); runCurrent()
        assertEquals(polls, f.linkPolls)
    }

    @Test fun dismissedStartResponseIsCancelledWithoutOpeningTelegramOrStartingPolls() = runTest(dispatcher) {
        val f = Fixture(false, listOf("google"))
        f.load(); runCurrent()
        val gate = CompletableDeferred<Unit>(); f.startGate = gate
        f.model.connect(AuthProvider.TELEGRAM, null); runCurrent()
        f.model.cancelConnection()
        gate.complete(Unit); runCurrent()
        assertEquals(1, f.linkCancels)
        assertEquals(0, f.linkPolls)
        assertNull(f.model.state.value.pendingBrowserUrl)
        assertNull(f.model.state.value.busyProvider)
        assertEquals(0, f.linkedCallbacks)
    }

    @Test fun lateOldProofCannotOverwriteANewerProviderAttempt() = runTest(dispatcher) {
        val f = Fixture(false, listOf("google"))
        f.load(); runCurrent()
        val gate = CompletableDeferred<Unit>(); f.startGate = gate
        f.model.connect(AuthProvider.TELEGRAM, null); runCurrent()
        f.model.cancelConnection()
        f.startGate = null
        f.model.connect(AuthProvider.APPLE, null); runCurrent()
        gate.complete(Unit); runCurrent()
        assertEquals(AuthProvider.APPLE, f.model.state.value.busyProvider)
        assertEquals("https://appleid.apple.com/auth/authorize?client_id=x", f.model.state.value.pendingBrowserUrl)
        assertEquals(1, f.linkCancels)
        assertEquals(0, f.linkedCallbacks)
        f.model.cancelConnection(); runCurrent()
    }

    @Test fun rapidProviderTapsCannotCreateParallelAttachmentProofs() = runTest(dispatcher) {
        val f = Fixture(false, listOf("google"))
        f.load(); runCurrent()
        f.model.connect(AuthProvider.TELEGRAM, null)
        f.model.connect(AuthProvider.TELEGRAM, null)
        f.model.connect(AuthProvider.APPLE, null)
        runCurrent()
        assertEquals(1, f.linkStarts)
        assertEquals(AuthProvider.TELEGRAM, f.model.state.value.busyProvider)
        f.model.cancelConnection(); runCurrent()
    }

    private companion object {
        const val TELEGRAM_URL = "https://t.me/HSKAI_bot?start=tg_identity_3f2504e0-4f89-11d3-9a0c-0305e82c3301"
    }

}
