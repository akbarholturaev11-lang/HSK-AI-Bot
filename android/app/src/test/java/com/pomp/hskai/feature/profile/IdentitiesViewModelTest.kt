package com.pomp.hskai.feature.profile

import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.storage.CredentialStore
import com.pomp.hskai.data.api.AndroidAuthApi
import com.pomp.hskai.data.api.IdentitiesResponse
import com.pomp.hskai.data.api.IdentityDto
import com.pomp.hskai.data.api.IdentityUnlinkResponse
import com.pomp.hskai.data.api.NativeOAuthApi
import com.pomp.hskai.data.api.ProvidersResponse
import com.pomp.hskai.data.api.RefreshResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
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
        private val oauthApi = Proxy.newProxyInstance(
            NativeOAuthApi::class.java.classLoader, arrayOf(NativeOAuthApi::class.java),
        ) { _, method, _ ->
            when (method.name) {
                "providers" -> Response.success(ProvidersResponse(ok = true, providers = listOf("google", "apple")))
                "identities" -> Response.success(IdentitiesResponse(ok = true,
                    telegramLinked = telegramLinked, identities = identities))
                "identityUnlink" -> {
                    unlinks++
                    unlinkError?.let { Response.error<IdentityUnlinkResponse>(409,
                        """{"ok":false,"error":"$it"}""".toResponseBody()) }
                        ?: Response.success(IdentityUnlinkResponse(ok = true))
                }
                else -> error("Unexpected identity request: ${method.name}")
            }
        } as NativeOAuthApi
        val model = IdentitiesViewModel(AuthRepository(authApi, store, "test", oauthApi = oauthApi))
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
}
