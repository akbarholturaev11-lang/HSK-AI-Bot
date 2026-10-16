package com.pomp.hskai.core.auth

import android.app.Activity
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import com.pomp.hskai.core.storage.CredentialStore
import com.pomp.hskai.data.api.AndroidAuthApi
import com.pomp.hskai.data.api.AndroidFeatureApi
import com.pomp.hskai.data.api.AndroidOnboardingApi
import com.pomp.hskai.data.api.AndroidPushApi
import com.pomp.hskai.data.api.NativeOAuthApi
import com.pomp.hskai.data.api.PushTokenRequest
import com.pomp.hskai.data.repository.FeatureRepository
import com.pomp.hskai.data.repository.OnboardingRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit

/** Real native transport contract: provider signup must never need a Telegram identity. */
class ProviderSignupContractTest {
    private val server = MockWebServer()
    private val json = Json { ignoreUnknownKeys = true; explicitNulls = false }
    private lateinit var retrofit: Retrofit

    @Before fun setUp() {
        server.start()
        retrofit = Retrofit.Builder().baseUrl(server.url("/"))
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType())).build()
    }

    @After fun tearDown() = server.shutdown()

    @Test fun googleSignupReachesLearningAndAccountFeaturesWithoutTelegram() = runTest {
        exerciseProvider(AuthProvider.GOOGLE, AppLanguage.UZBEK)
    }

    @Test fun appleSignupUsesTheSameSessionAndLearningContractWithoutTelegram() = runTest {
        exerciseProvider(AuthProvider.APPLE, AppLanguage.TAJIK)
    }

    private suspend fun exerciseProvider(provider: AuthProvider, language: AppLanguage) {
        val store = SignupCredentialStore()
        var authenticatedDevice: String? = null
        var googleTokenCalls = 0
        val auth = AuthRepository(
            api = retrofit.create(AndroidAuthApi::class.java),
            store = store,
            appVersion = "test-signup",
            oauthApi = retrofit.create(NativeOAuthApi::class.java),
            googleIdTokens = object : GoogleIdTokenProvider {
                override val isAvailable: Boolean = true
                override suspend fun idToken(activity: Activity?, nonce: String): GoogleIdTokenResult {
                    googleTokenCalls++
                    assertEquals("nonce-from-server", nonce)
                    return GoogleIdTokenResult.Success("verified-by-server")
                }
            },
            onAuthenticated = { authenticatedDevice = it },
        )
        val nativeGoogle = provider == AuthProvider.GOOGLE
        respond("""{"ok":true,"status":"pending","link_request_id":"$requestId","polling_secret":"${"s".repeat(43)}","expires_in":600,"nonce":"nonce-from-server","authorize_url":"https://appleid.apple.com/auth/authorize?state=opaque"}""")
        if (nativeGoogle) respond("""{"ok":true,"status":"approved","provider":"google"}""")
        val pending = when (provider) {
            AuthProvider.GOOGLE -> auth.startGoogleSignIn(language = language)
            AuthProvider.APPLE -> auth.startAppleSignIn(language = language)
            else -> error("This contract covers native Google and browser Apple")
        }.success()
        val start = request("POST", "/api/v3/native-auth/oauth/start", bearer = false)
        val startBody = json.parseToJsonElement(start.body.readUtf8()).jsonObject
        assertEquals(provider.wire, startBody["provider"]?.jsonPrimitive?.content)
        assertEquals(language.backendCode, startBody["language"]?.jsonPrimitive?.content)
        assertFalse(startBody.containsKey("telegram_id"))
        assertEquals(if (nativeGoogle) "native_id_token" else "browser_redirect", startBody["mode"]?.jsonPrimitive?.content)
        if (nativeGoogle) {
            val assertion = request("POST", "/api/v3/native-auth/oauth/assert", bearer = false)
            assertEquals("verified-by-server", json.parseToJsonElement(assertion.body.readUtf8())
                .jsonObject["id_token"]?.jsonPrimitive?.content)
        } else {
            assertTrue(pending.authorizeUrl.startsWith("https://appleid.apple.com/"))
        }
        assertNull(store.storedRefresh)
        assertEquals(if (nativeGoogle) 1 else 0, googleTokenCalls)
        assertTrue(pending.botDeepLink.isEmpty())

        // The server has verified the provider and created its internal user.
        // Android still receives tokens only through the shared one-use poll.
        respond("""{"ok":true,"status":"linked","access_token":"provider-access","access_expires_in":900,"refresh_token":"provider-refresh","refresh_expires_in":2592000}""")
        assertTrue(auth.pollLink(pending).success())
        request("POST", "/api/v3/android-auth/link/status", bearer = false)
        assertEquals("provider-refresh", store.storedRefresh)

        respond("""{"ok":true,"authenticated":true,"device":{"id":"internal-device","platform":"android"},"user":{"id":923,"telegram_id":null,"name":"New learner","language":"${language.backendCode}","level":"hsk1","access_state":"free","is_paid":false}}""")
        val account = auth.bootstrap().success()
        request("GET", "/api/v3/android/bootstrap")
        assertEquals("New learner", account.displayName)
        assertEquals(language, account.language)
        assertFalse(account.isPaid)
        assertEquals(AuthState.Authenticated(account), auth.state.value)
        assertEquals("internal-device", authenticatedDevice)
        assertTrue(store.cached.orEmpty().contains("New learner"))

        val onboarding = OnboardingRepository(retrofit.create(AndroidOnboardingApi::class.java), auth::accessToken)
        respond("""{"ok":true,"completed":false,"level":"hsk1"}""")
        assertFalse(onboarding.status().success().completed)
        request("GET", "/api/v3/android/course/onboarding")
        respond("""{"ok":true,"level":"hsk1","lesson":1,"profile":{"onboarding_completed":true}}""")
        // Real Retrofit I/O must use a real clock: runTest would otherwise
        // advance the repository's 12-second timeout before the callback runs.
        val completed = withContext(Dispatchers.IO) {
            onboarding.complete("hsk1", "hsk_exam", language.backendCode)
        }
        assertTrue(completed.success().ok)
        val complete = request("POST", "/api/v3/android/course/onboarding")
        val onboardingBody = json.parseToJsonElement(complete.body.readUtf8()).jsonObject
        assertEquals(language.backendCode, onboardingBody["language"]?.jsonPrimitive?.content)
        assertFalse(onboardingBody.containsKey("telegram_id"))

        val features = FeatureRepository(retrofit.create(AndroidFeatureApi::class.java), auth::accessToken)
        respond("""{"ok":true,"user":{"name":"New learner","avatar":"","avatar_key":"panda_cheer","telegram_username":"","phone":"","level":"hsk1","language":"${language.backendCode}"},"subscription":{"is_paid":false}}""")
        assertEquals("", features.profile().success().user.telegramUsername)
        request("GET", "/api/v3/android/profile")
        respond("""{"ok":true,"telegram_linked":false,"identities":[{"id":"provider-id","provider":"${provider.wire}","email_masked":"n***@example.com"}]}""")
        val identities = auth.linkedIdentities().success()
        request("GET", "/api/v3/native-auth/identities")
        assertFalse(identities.telegramLinked)
        assertEquals(provider, identities.identities.single().provider)

        respond("""{"ok":true}""")
        val push = retrofit.create(AndroidPushApi::class.java)
        assertTrue(apiCall { push.register("Bearer ${auth.accessToken().success()}", PushTokenRequest("test-fcm")) }.success().ok)
        val pushBody = json.parseToJsonElement(request("POST", "/api/v3/android/push/register").body.readUtf8()).jsonObject
        assertEquals(setOf("token"), pushBody.keys)
        respond("""{"ok":true,"code":"internal-referral","link":"https://example.com/invite/internal-referral","invited":0,"activated":0}""")
        assertEquals("internal-referral", features.referral().success().code)
        request("GET", "/api/v3/android/referral/overview")
        respond("""{"ok":true,"checkout_allowed":false,"access":{"is_paid":false}}""")
        assertFalse(features.subscriptionOverview().success().checkoutAllowed)
        request("GET", "/api/v3/android/subscription/overview")
    }

    private fun request(method: String, path: String, bearer: Boolean = true): RecordedRequest {
        val request = requireNotNull(server.takeRequest(1, TimeUnit.SECONDS))
        assertEquals(method, request.method)
        assertEquals(path, request.requestUrl?.encodedPath)
        assertEquals(if (bearer) "Bearer provider-access" else null, request.getHeader("Authorization"))
        assertFalse(request.path.orEmpty().contains("provider-access"))
        return request
    }

    private fun respond(body: String) {
        server.enqueue(MockResponse().setHeader("Content-Type", "application/json").setBody(body))
    }

    private fun <T> ApiResult<T>.success(): T {
        assertTrue("Expected a decoded successful response", this is ApiResult.Success)
        return (this as ApiResult.Success).value
    }

    companion object { private const val requestId = "3f2504e0-4f89-11d3-9a0c-0305e82c3301" }
}

private class SignupCredentialStore : CredentialStore {
    var storedRefresh: String? = null
    var cached: String? = null
    override suspend fun installationKey(): String = "k".repeat(64)
    override suspend fun refreshToken(): String? = storedRefresh
    override suspend fun saveRefreshToken(token: String) { storedRefresh = token }
    override suspend fun cachedAccount(): String? = cached
    override suspend fun saveCachedAccount(value: String) { cached = value }
    override suspend fun clearSession() { storedRefresh = null; cached = null }
    override suspend fun clearEverything() = clearSession()
}
