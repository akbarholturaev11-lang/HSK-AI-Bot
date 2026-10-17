package com.pomp.hskai.core.auth

import android.app.Activity
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.storage.CredentialStore
import com.pomp.hskai.data.api.AndroidAuthApi
import com.pomp.hskai.data.api.BootstrapResponse
import com.pomp.hskai.data.api.IdentitiesResponse
import com.pomp.hskai.data.api.IdentityDto
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
import kotlinx.coroutines.async
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.Response

private open class OauthFakeStore : CredentialStore {
    var storedRefresh: String? = null
    override suspend fun installationKey(): String = "installation-key-" + "k".repeat(40)
    override suspend fun refreshToken(): String? = storedRefresh
    override suspend fun saveRefreshToken(token: String) { storedRefresh = token }
    override suspend fun cachedAccount(): String? = null
    override suspend fun saveCachedAccount(value: String) = Unit
    override suspend fun clearSession() { storedRefresh = null }
    override suspend fun clearEverything() { storedRefresh = null }
}

private open class OauthFakeAuthApi : AndroidAuthApi {
    var linkStatusCalls = 0

    override suspend fun startLink(body: LinkStartRequest): Response<LinkStartResponse> =
        throw NotImplementedError()

    override suspend fun linkStatus(body: LinkStatusRequest): Response<LinkStatusResponse> {
        linkStatusCalls++
        return Response.success(
            LinkStatusResponse(
                ok = true,
                status = "linked",
                accessToken = "access-token",
                accessExpiresIn = 900,
                refreshToken = "pomp_r1_refresh",
                refreshExpiresIn = 2_592_000,
            )
        )
    }

    override suspend fun refresh(body: RefreshRequest): Response<RefreshResponse> =
        Response.success(
            RefreshResponse(
                ok = true,
                accessToken = "access-token",
                accessExpiresIn = 900,
                refreshToken = "pomp_r1_rotated",
                refreshExpiresIn = 2_592_000,
            )
        )

    override suspend fun revoke(
        authorization: String,
        body: RevokeRequest,
    ): Response<RevokeResponse> = Response.success(RevokeResponse(ok = true))

    override suspend fun bootstrap(
        authorization: String,
        appVersion: String,
    ): Response<BootstrapResponse> = throw NotImplementedError()
}

private open class OauthFakeApi : NativeOAuthApi {
    var startCalls = 0
    var linkStartCalls = 0
    var lastAssert: OAuthAssertRequest? = null
    var lastStart: OAuthStartRequest? = null

    override suspend fun providers(platform: String): Response<ProvidersResponse> =
        Response.success(ProvidersResponse(ok = true, providers = listOf("google", "apple")))

    override suspend fun oauthStart(body: OAuthStartRequest): Response<OAuthStartResponse> {
        startCalls++
        lastStart = body
        return Response.success(
            OAuthStartResponse(
                ok = true,
                status = "pending",
                linkRequestId = "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
                pollingSecret = "s".repeat(43),
                expiresIn = 600,
                nonce = if (body.mode == "native_id_token") "n".repeat(64) else "",
                authorizeUrl = if (body.mode == "browser_redirect") {
                    "https://appleid.apple.com/auth/authorize?client_id=x"
                } else {
                    ""
                },
            )
        )
    }

    override suspend fun oauthAssert(body: OAuthAssertRequest): Response<OAuthAssertResponse> {
        lastAssert = body
        return Response.success(OAuthAssertResponse(ok = true, status = "approved", provider = "google"))
    }

    override suspend fun identities(authorization: String): Response<IdentitiesResponse> =
        Response.success(
            IdentitiesResponse(
                ok = true,
                telegramLinked = true,
                identities = listOf(
                    IdentityDto(id = "id-1", provider = "google", emailMasked = "a***e@example.com"),
                    IdentityDto(id = "id-2", provider = "unknown-provider"),
                ),
            )
        )

    override suspend fun identityLinkStart(
        authorization: String,
        body: OAuthStartRequest,
    ): Response<OAuthStartResponse> {
        linkStartCalls++
        return oauthStart(body)
    }

    override suspend fun identityLinkStatus(
        authorization: String,
        body: IdentityLinkStatusRequest,
    ): Response<IdentityLinkStatusResponse> =
        Response.success(IdentityLinkStatusResponse(ok = true, status = "linked", provider = "google"))

    override suspend fun identityUnlink(
        authorization: String,
        body: IdentityUnlinkRequest,
    ): Response<IdentityUnlinkResponse> =
        Response.success(IdentityUnlinkResponse(ok = true, provider = "google", sessionsRevoked = 2))
}

private class FakeGoogleIdTokens(
    private val result: GoogleIdTokenResult,
    override val isAvailable: Boolean = true,
) : GoogleIdTokenProvider {
    var lastNonce: String? = null
    override suspend fun idToken(activity: Activity?, nonce: String): GoogleIdTokenResult {
        lastNonce = nonce
        return result
    }
}

@Suppress("UNCHECKED_CAST")
private fun <T> ApiResult<T>.success(): T = (this as ApiResult.Success<T>).value
private fun ApiResult<*>.failure(): ApiError = (this as ApiResult.Failure).error

@OptIn(ExperimentalCoroutinesApi::class)
class AuthRepositoryOauthTest {

    private var clock = 1_000_000L

    private fun repository(
        oauth: NativeOAuthApi = OauthFakeApi(),
        google: GoogleIdTokenProvider? = FakeGoogleIdTokens(GoogleIdTokenResult.Success("id-token")),
        auth: AndroidAuthApi = OauthFakeAuthApi(),
        store: CredentialStore = OauthFakeStore(),
    ) = AuthRepository(
        api = auth,
        store = store,
        appVersion = "1.5.3",
        oauthApi = oauth,
        googleIdTokens = google,
        now = { clock },
    )

    @Test
    fun `google sign-in passes the server nonce to credential manager`() = runTest {
        val google = FakeGoogleIdTokens(GoogleIdTokenResult.Success("id-token"))
        val oauth = OauthFakeApi()

        val pending = repository(oauth = oauth, google = google).startGoogleSignIn().success()

        // Without the server nonce a captured ID token stays replayable.
        assertEquals("n".repeat(64), google.lastNonce)
        assertEquals("id-token", oauth.lastAssert?.idToken)
        assertEquals(AuthProvider.GOOGLE, pending.provider)
        assertEquals(clock + 600_000L, pending.expiresAtMillis)
    }

    @Test
    fun `oauth start always serializes its required platform`() {
        val payload = Json.encodeToString(
            OAuthStartRequest(
                platform = "android",
                appVersion = "1.6.6",
                installationKey = "k".repeat(64),
                provider = "google",
                mode = "native_id_token",
            )
        )

        assertTrue(payload.contains("\"platform\":\"android\""))
    }

    @Test
    fun `google sign-in still collects its session from the existing link endpoint`() = runTest {
        val auth = OauthFakeAuthApi()
        val store = OauthFakeStore()
        val repo = repository(auth = auth, store = store)

        val pending = repo.startGoogleSignIn().success()
        val linked = repo.pollLink(pending).success()

        assertTrue(linked)
        assertEquals(1, auth.linkStatusCalls)
        // The one place a session is ever created stays the same.
        assertEquals("pomp_r1_refresh", store.storedRefresh)
    }

    @Test
    fun `a dismissed google sheet is reported as cancelled, not as a failure`() = runTest {
        val repo = repository(google = FakeGoogleIdTokens(GoogleIdTokenResult.Cancelled))
        assertEquals(ApiError.ProviderCancelled, repo.startGoogleSignIn().failure())
    }

    @Test
    fun `no google account on the device is reported as unavailable`() = runTest {
        val repo = repository(google = FakeGoogleIdTokens(GoogleIdTokenResult.Unavailable))
        assertEquals(ApiError.ProviderUnavailable, repo.startGoogleSignIn().failure())
    }

    @Test
    fun `google is hidden when the build carries no client id`() = runTest {
        val repo = repository(
            google = FakeGoogleIdTokens(GoogleIdTokenResult.Unavailable, isAvailable = false)
        )
        assertEquals(listOf(AuthProvider.APPLE), repo.availableProviders())
    }

    @Test
    fun `providers are empty when the oauth api is absent`() = runTest {
        val repo = AuthRepository(
            api = OauthFakeAuthApi(),
            store = OauthFakeStore(),
            appVersion = "1.5.3",
            now = { clock },
        )
        assertTrue(repo.availableProviders().isEmpty())
    }

    @Test
    fun `apple sign-in returns an https authorize url and no nonce`() = runTest {
        val pending = repository().startAppleSignIn().success()

        assertTrue(pending.authorizeUrl.startsWith("https://appleid.apple.com/"))
        assertEquals(AuthProvider.APPLE, pending.provider)
        assertTrue(pending.nonce.isEmpty())
        // Telegram artefacts must never appear on a provider flow.
        assertTrue(pending.displayCode.isEmpty())
        assertTrue(pending.botDeepLink.isEmpty())
    }

    @Test
    fun `linking uses the bearer endpoint, signing in does not`() = runTest {
        val oauth = OauthFakeApi()
        val store = OauthFakeStore().apply { storedRefresh = "pomp_r1_existing" }
        val repo = repository(oauth = oauth, store = store)

        repo.startGoogleSignIn(bindToCurrentAccount = false).success()
        assertEquals(1, oauth.startCalls)
        assertEquals(0, oauth.linkStartCalls)

        repo.startGoogleSignIn(bindToCurrentAccount = true).success()
        assertEquals(1, oauth.linkStartCalls)
    }

    @Test
    fun `both provider signups carry the chosen language while linking leaves preferences unchanged`() = runTest {
        val oauth = OauthFakeApi()
        val store = OauthFakeStore().apply { storedRefresh = "pomp_r1_existing" }
        val repo = repository(oauth = oauth, store = store)

        repo.startGoogleSignIn(language = AppLanguage.UZBEK).success()
        assertEquals("uz", oauth.lastStart?.language)
        repo.startAppleSignIn(language = AppLanguage.TAJIK).success()
        assertEquals("tj", oauth.lastStart?.language)
        repo.startGoogleSignIn(bindToCurrentAccount = true, language = AppLanguage.UZBEK).success()
        assertEquals(null, oauth.lastStart?.language)
        repo.startAppleSignIn(bindToCurrentAccount = true, language = AppLanguage.TAJIK).success()
        assertEquals(null, oauth.lastStart?.language)
    }

    @Test
    fun `invite metadata reaches both signup providers but never explicit identity linking`() = runTest {
        val oauth = OauthFakeApi()
        val store = OauthFakeStore().apply { storedRefresh = "pomp_r1_existing" }
        val repo = repository(oauth = oauth, store = store)
        repo.updateSignupReferralCode("ra_abcdef12")
        repo.startGoogleSignIn().success()
        assertEquals("ra_abcdef12", oauth.lastStart?.referralCode)
        repo.startAppleSignIn().success()
        assertEquals("ra_abcdef12", oauth.lastStart?.referralCode)
        repo.startGoogleSignIn(bindToCurrentAccount = true).success()
        assertEquals(null, oauth.lastStart?.referralCode)
        assertFalse(Json.encodeToString(oauth.lastStart!!).contains("referral_code"))
        repo.startAppleSignIn(bindToCurrentAccount = true).success()
        assertEquals(null, oauth.lastStart?.referralCode)
    }

    @Test
    fun `invite is captured before the first suspension and cleared only after login`() = runTest {
        val installation = CompletableDeferred<Unit>()
        val store = object : OauthFakeStore() {
            override suspend fun installationKey(): String {
                installation.await()
                return "k".repeat(64)
            }
        }
        val oauth = OauthFakeApi()
        val repo = repository(oauth = oauth, store = store)
        repo.updateSignupReferralCode("ref_abcdef12")
        val attempt = async { repo.startAppleSignIn().success() }
        runCurrent()
        repo.updateSignupReferralCode("ra_12345678")
        installation.complete(Unit)
        val pending = attempt.await()
        assertEquals("ref_abcdef12", oauth.lastStart?.referralCode)
        assertEquals("ra_12345678", repo.signupReferralCode.value)
        assertTrue(repo.pollLink(pending).success())
        assertEquals("", repo.signupReferralCode.value)
        repo.updateSignupReferralCode("abcdef12")
        assertEquals("", repo.signupReferralCode.value)
    }

    @Test
    fun `provider only identities retain the absence of Telegram and malformed envelopes fail closed`() = runTest {
        val store = OauthFakeStore().apply { storedRefresh = "pomp_r1_existing" }
        val oauth = object : OauthFakeApi() {
            var ok = true
            override suspend fun identities(authorization: String): Response<IdentitiesResponse> =
                Response.success(IdentitiesResponse(ok = ok, telegramLinked = false,
                    identities = listOf(IdentityDto(id = "google-only", provider = "google"))))
        }
        val repo = repository(oauth = oauth, store = store)
        val methods = repo.linkedIdentities().success()
        assertFalse(methods.telegramLinked)
        assertEquals("google-only", methods.identities.single().id)
        oauth.ok = false
        assertEquals(ApiError.Unknown, repo.linkedIdentities().failure())
    }

    @Test
    fun `unknown providers are dropped instead of being rendered`() = runTest {
        val store = OauthFakeStore().apply { storedRefresh = "pomp_r1_existing" }
        val linked = repository(store = store).linkedIdentities().success()
        val identities = linked.identities

        assertTrue(linked.telegramLinked)
        assertEquals(1, identities.size)
        assertEquals(AuthProvider.GOOGLE, identities.first().provider)
        assertEquals("a***e@example.com", identities.first().emailMasked)
    }

    @Test
    fun `unlink reports how many other sessions were revoked`() = runTest {
        val store = OauthFakeStore().apply { storedRefresh = "pomp_r1_existing" }
        assertEquals(2, repository(store = store).unlinkIdentity("id-1").success())
    }

    @Test
    fun `a failed link status is surfaced as its stable server code`() = runTest {
        val oauth = object : OauthFakeApi() {
            override suspend fun identityLinkStatus(
                authorization: String,
                body: IdentityLinkStatusRequest,
            ): Response<IdentityLinkStatusResponse> = Response.success(
                IdentityLinkStatusResponse(
                    ok = true,
                    status = "failed",
                    provider = "google",
                    error = "oauth_identity_bound_to_other_user",
                )
            )
        }
        val store = OauthFakeStore().apply { storedRefresh = "pomp_r1_existing" }
        val repo = repository(oauth = oauth, store = store)
        val pending = repo.startGoogleSignIn(bindToCurrentAccount = true).success()

        val error = repo.pollIdentityLink(pending).failure()
        assertTrue(error is ApiError.Server)
        assertEquals("oauth_identity_bound_to_other_user", (error as ApiError.Server).code)
    }

    @Test
    fun `a start response without the piece its mode needs is refused`() = runTest {
        val oauth = object : OauthFakeApi() {
            override suspend fun oauthStart(body: OAuthStartRequest): Response<OAuthStartResponse> =
                Response.success(
                    OAuthStartResponse(
                        ok = true,
                        status = "pending",
                        linkRequestId = "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
                        pollingSecret = "s".repeat(43),
                        expiresIn = 600,
                        // Neither a nonce nor an authorize url.
                    )
                )
        }
        val repo = repository(oauth = oauth)
        assertEquals(ApiError.Unknown, repo.startGoogleSignIn().failure())
        assertEquals(ApiError.Unknown, repo.startAppleSignIn().failure())
    }

    @Test
    fun `a non-https authorize url is refused`() = runTest {
        val oauth = object : OauthFakeApi() {
            override suspend fun oauthStart(body: OAuthStartRequest): Response<OAuthStartResponse> =
                Response.success(
                    OAuthStartResponse(
                        ok = true,
                        status = "pending",
                        linkRequestId = "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
                        pollingSecret = "s".repeat(43),
                        expiresIn = 600,
                        authorizeUrl = "http://appleid.apple.com/auth/authorize",
                    )
                )
        }
        assertEquals(ApiError.Unknown, repository(oauth = oauth).startAppleSignIn().failure())
    }

    @Test
    fun `a rejected assertion does not produce a usable pending link`() = runTest {
        val oauth = object : OauthFakeApi() {
            override suspend fun oauthAssert(
                body: OAuthAssertRequest,
            ): Response<OAuthAssertResponse> = Response.error(
                409,
                """{"ok":false,"error":"oauth_telegram_account_required"}"""
                    .toResponseBody("application/json".toMediaType()),
            )
        }
        val error = repository(oauth = oauth).startGoogleSignIn().failure()

        assertTrue(error is ApiError.Server)
        assertEquals("oauth_telegram_account_required", (error as ApiError.Server).code)
        assertFalse(error.messageRes == 0)
    }
}
