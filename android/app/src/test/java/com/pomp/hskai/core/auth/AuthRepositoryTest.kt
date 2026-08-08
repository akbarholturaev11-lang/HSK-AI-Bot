package com.pomp.hskai.core.auth

import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.storage.CredentialStore
import com.pomp.hskai.data.api.AndroidAuthApi
import com.pomp.hskai.data.api.BootstrapResponse
import com.pomp.hskai.data.api.BootstrapUser
import com.pomp.hskai.data.api.LinkStartRequest
import com.pomp.hskai.data.api.LinkStartResponse
import com.pomp.hskai.data.api.LinkStatusRequest
import com.pomp.hskai.data.api.LinkStatusResponse
import com.pomp.hskai.data.api.RefreshRequest
import com.pomp.hskai.data.api.RefreshResponse
import com.pomp.hskai.data.api.RevokeRequest
import com.pomp.hskai.data.api.RevokeResponse
import java.util.concurrent.atomic.AtomicInteger
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.delay
import kotlinx.coroutines.test.runTest
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.Response

private class FakeCredentialStore(
    var storedRefresh: String? = null,
) : CredentialStore {
    var clearSessionCalls = 0
    var clearEverythingCalls = 0
    val savedTokens = mutableListOf<String>()

    override suspend fun installationKey(): String = "installation-key-" + "k".repeat(40)

    override suspend fun refreshToken(): String? = storedRefresh

    override suspend fun saveRefreshToken(token: String) {
        savedTokens += token
        storedRefresh = token
    }

    override suspend fun clearSession() {
        clearSessionCalls++
        storedRefresh = null
    }

    override suspend fun clearEverything() {
        clearEverythingCalls++
        storedRefresh = null
    }
}

private fun <T> errorResponse(code: Int, body: String): Response<T> =
    Response.error(code, body.toResponseBody("application/json".toMediaType()))

private open class FakeAuthApi : AndroidAuthApi {
    override suspend fun startLink(body: LinkStartRequest): Response<LinkStartResponse> =
        throw NotImplementedError()

    override suspend fun linkStatus(body: LinkStatusRequest): Response<LinkStatusResponse> =
        throw NotImplementedError()

    override suspend fun refresh(body: RefreshRequest): Response<RefreshResponse> =
        throw NotImplementedError()

    override suspend fun revoke(
        authorization: String,
        body: RevokeRequest,
    ): Response<RevokeResponse> = Response.success(RevokeResponse(ok = true))

    override suspend fun bootstrap(
        authorization: String,
        appVersion: String,
    ): Response<BootstrapResponse> = throw NotImplementedError()
}

/**
 * `as ApiResult.Success` needs an explicit type argument, so these helpers keep
 * the assertions readable without repeating it at every call site.
 */
@Suppress("UNCHECKED_CAST")
private fun <T> ApiResult<T>.success(): T = (this as ApiResult.Success<T>).value

private fun ApiResult<*>.failure(): ApiError = (this as ApiResult.Failure).error

@OptIn(ExperimentalCoroutinesApi::class)
class AuthRepositoryTest {

    private var clock = 1_000_000L

    private fun repository(api: AndroidAuthApi, store: CredentialStore) =
        AuthRepository(api, store, appVersion = "1.0.0", now = { clock })

    @Test
    fun `link start surfaces the display code without leaking the polling secret into it`() =
        runTest {
            val api = object : FakeAuthApi() {
                override suspend fun startLink(
                    body: LinkStartRequest,
                ): Response<LinkStartResponse> {
                    assertEquals("android", body.platform)
                    return Response.success(
                        LinkStartResponse(
                            ok = true,
                            status = "pending",
                            linkRequestId = "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
                            displayCode = "HSK4827X",
                            pollingSecret = "s".repeat(43),
                            botDeepLink = "https://t.me/darsi_chini_bot?start=desktop_link",
                            expiresIn = 600,
                        )
                    )
                }
            }

            val result = repository(api, FakeCredentialStore()).startLink()

            val pending = result.success()
            assertEquals("HSK4827X", pending.displayCode)
            // The security property the desktop flow established.
            assertTrue(pending.displayCode !in pending.botDeepLink)
            assertEquals(clock + 600_000L, pending.expiresAtMillis)
        }

    @Test
    fun `pending poll does not persist anything`() = runTest {
        val store = FakeCredentialStore()
        val api = object : FakeAuthApi() {
            override suspend fun linkStatus(
                body: LinkStatusRequest,
            ): Response<LinkStatusResponse> = Response.success(
                LinkStatusResponse(ok = true, status = "pending", expiresIn = 540)
            )
        }

        val result = repository(api, store).pollLink(pendingLink())

        assertEquals(false, result.success())
        assertTrue(store.savedTokens.isEmpty())
        assertNull(store.storedRefresh)
    }

    @Test
    fun `approved poll persists the refresh token before returning`() = runTest {
        val store = FakeCredentialStore()
        val api = object : FakeAuthApi() {
            override suspend fun linkStatus(
                body: LinkStatusRequest,
            ): Response<LinkStatusResponse> = Response.success(
                LinkStatusResponse(
                    ok = true,
                    status = "linked",
                    accessToken = "access-1",
                    accessExpiresIn = 900,
                    refreshToken = "pomp_r1_first",
                    refreshExpiresIn = 2_592_000,
                )
            )
        }

        val result = repository(api, store).pollLink(pendingLink())

        assertEquals(true, result.success())
        assertEquals(listOf("pomp_r1_first"), store.savedTokens)
    }

    @Test
    fun `a valid access token is reused instead of refreshing again`() = runTest {
        val store = FakeCredentialStore(storedRefresh = "pomp_r1_first")
        val refreshes = AtomicInteger()
        val api = object : FakeAuthApi() {
            override suspend fun refresh(body: RefreshRequest): Response<RefreshResponse> {
                refreshes.incrementAndGet()
                return Response.success(
                    RefreshResponse(
                        ok = true,
                        accessToken = "access-1",
                        accessExpiresIn = 900,
                        refreshToken = "pomp_r1_second",
                        refreshExpiresIn = 2_592_000,
                    )
                )
            }
        }
        val repository = repository(api, store)

        assertEquals("access-1", repository.accessToken().success())
        assertEquals("access-1", repository.accessToken().success())

        assertEquals(1, refreshes.get())
        assertEquals(listOf("pomp_r1_second"), store.savedTokens)
    }

    @Test
    fun `an expiring access token is refreshed early`() = runTest {
        val store = FakeCredentialStore(storedRefresh = "pomp_r1_first")
        val issued = AtomicInteger()
        val api = object : FakeAuthApi() {
            override suspend fun refresh(body: RefreshRequest): Response<RefreshResponse> =
                Response.success(
                    RefreshResponse(
                        ok = true,
                        accessToken = "access-${issued.incrementAndGet()}",
                        accessExpiresIn = 900,
                        refreshToken = "pomp_r1_${issued.get()}",
                        refreshExpiresIn = 2_592_000,
                    )
                )
        }
        val repository = repository(api, store)

        assertEquals("access-1", repository.accessToken().success())
        // Inside the 30s safety skew before expiry.
        clock += 880_000L
        assertEquals("access-2", repository.accessToken().success())
        assertEquals(2, issued.get())
    }

    @Test
    fun `concurrent callers trigger exactly one refresh`() = runTest {
        val store = FakeCredentialStore(storedRefresh = "pomp_r1_first")
        val refreshes = AtomicInteger()
        val api = object : FakeAuthApi() {
            override suspend fun refresh(body: RefreshRequest): Response<RefreshResponse> {
                refreshes.incrementAndGet()
                delay(50)
                return Response.success(
                    RefreshResponse(
                        ok = true,
                        accessToken = "access-1",
                        accessExpiresIn = 900,
                        refreshToken = "pomp_r1_second",
                        refreshExpiresIn = 2_592_000,
                    )
                )
            }
        }
        val repository = repository(api, store)

        val results = (1..8).map { async { repository.accessToken() } }.awaitAll()

        assertEquals(1, refreshes.get())
        results.forEach {
            assertEquals("access-1", it.success())
        }
        // Reusing a rotated token would revoke the session server-side, so
        // exactly one rotation must have been persisted.
        assertEquals(listOf("pomp_r1_second"), store.savedTokens)
    }

    @Test
    fun `refresh reuse detection clears the local session`() = runTest {
        val store = FakeCredentialStore(storedRefresh = "pomp_r1_replayed")
        val api = object : FakeAuthApi() {
            override suspend fun refresh(body: RefreshRequest): Response<RefreshResponse> =
                errorResponse(
                    401,
                    """{"ok":false,"error":"desktop_refresh_reuse_detected"}""",
                )
        }

        val repository = repository(api, store)
        val result = repository.accessToken()

        assertEquals(ApiError.SessionExpired, result.failure())
        assertEquals(1, store.clearSessionCalls)
        assertNull(store.storedRefresh)
        assertEquals(AuthState.Unauthenticated, repository.state.value)
    }

    @Test
    fun `bootstrap without a stored token reports unauthenticated`() = runTest {
        val repository = repository(FakeAuthApi(), FakeCredentialStore())

        val result = repository.bootstrap()

        assertEquals(ApiError.SessionExpired, result.failure())
        assertEquals(AuthState.Unauthenticated, repository.state.value)
    }

    @Test
    fun `offline cold start keeps credentials and succeeds when retried`() = runTest {
        val store = FakeCredentialStore(storedRefresh = "pomp_r1_first")
        var offline = true
        val api = object : FakeAuthApi() {
            override suspend fun refresh(body: RefreshRequest): Response<RefreshResponse> {
                if (offline) throw java.io.IOException("offline")
                return Response.success(
                    RefreshResponse(
                        ok = true,
                        accessToken = "access-1",
                        accessExpiresIn = 900,
                        refreshToken = "pomp_r1_second",
                        refreshExpiresIn = 2_592_000,
                    )
                )
            }

            override suspend fun bootstrap(
                authorization: String,
                appVersion: String,
            ): Response<BootstrapResponse> = Response.success(
                BootstrapResponse(
                    ok = true,
                    authenticated = true,
                    user = BootstrapUser(name = "Akbar", language = "uz", level = "hsk1"),
                )
            )
        }
        val repository = repository(api, store)

        assertEquals(ApiError.Offline, repository.bootstrap().failure())
        assertEquals(AuthState.BootstrapFailed(ApiError.Offline), repository.state.value)
        assertEquals("pomp_r1_first", store.storedRefresh)

        offline = false
        val account = repository.bootstrap().success()
        assertEquals("Akbar", account.displayName)
        assertEquals(AuthState.Authenticated(account), repository.state.value)
    }

    @Test
    fun `bootstrap publishes the canonical account`() = runTest {
        val store = FakeCredentialStore(storedRefresh = "pomp_r1_first")
        val api = object : FakeAuthApi() {
            override suspend fun refresh(body: RefreshRequest): Response<RefreshResponse> =
                Response.success(
                    RefreshResponse(
                        ok = true,
                        accessToken = "access-1",
                        accessExpiresIn = 900,
                        refreshToken = "pomp_r1_second",
                        refreshExpiresIn = 2_592_000,
                    )
                )

            override suspend fun bootstrap(
                authorization: String,
                appVersion: String,
            ): Response<BootstrapResponse> {
                assertEquals("Bearer access-1", authorization)
                return Response.success(
                    BootstrapResponse(
                        ok = true,
                        authenticated = true,
                        user = BootstrapUser(
                            name = "Akbar",
                            language = "tj",
                            level = "hsk4",
                            accessState = "active",
                            isPaid = true,
                        ),
                    )
                )
            }
        }
        val repository = repository(api, store)

        val account = repository.bootstrap().success()

        assertEquals("Akbar", account.displayName)
        assertEquals("hsk4", account.level)
        assertTrue(account.isPaid)
        assertEquals("tj", account.language.backendCode)
        assertEquals(AuthState.Authenticated(account), repository.state.value)
    }

    @Test
    fun `a protected endpoint revocation invalidates the authenticated state`() = runTest {
        val store = FakeCredentialStore(storedRefresh = "pomp_r1_first")
        val api = object : FakeAuthApi() {
            override suspend fun refresh(body: RefreshRequest): Response<RefreshResponse> =
                Response.success(
                    RefreshResponse(
                        ok = true,
                        accessToken = "access-1",
                        accessExpiresIn = 900,
                        refreshToken = "pomp_r1_second",
                        refreshExpiresIn = 2_592_000,
                    )
                )

            override suspend fun bootstrap(
                authorization: String,
                appVersion: String,
            ): Response<BootstrapResponse> = Response.success(
                BootstrapResponse(
                    ok = true,
                    authenticated = true,
                    user = BootstrapUser(name = "Akbar", language = "uz", level = "hsk1"),
                )
            )
        }
        val repository = repository(api, store)
        repository.bootstrap().success()

        repository.invalidateSession()

        assertEquals(AuthState.Unauthenticated, repository.state.value)
        assertNull(store.storedRefresh)
        assertEquals(1, store.clearSessionCalls)
    }

    @Test
    fun `logout clears credentials even when the server cannot be reached`() = runTest {
        val store = FakeCredentialStore(storedRefresh = "pomp_r1_first")
        val api = object : FakeAuthApi() {
            override suspend fun refresh(body: RefreshRequest): Response<RefreshResponse> =
                Response.success(
                    RefreshResponse(
                        ok = true,
                        accessToken = "access-1",
                        accessExpiresIn = 900,
                        refreshToken = "pomp_r1_second",
                        refreshExpiresIn = 2_592_000,
                    )
                )

            override suspend fun revoke(
                authorization: String,
                body: RevokeRequest,
            ): Response<RevokeResponse> = throw java.io.IOException("offline")
        }
        val repository = repository(api, store)

        repository.logout()

        assertNull(store.storedRefresh)
        assertEquals(1, store.clearSessionCalls)
        assertEquals(AuthState.Unauthenticated, repository.state.value)
    }

    @Test
    fun `unlink wipes the installation identity too`() = runTest {
        val store = FakeCredentialStore(storedRefresh = "pomp_r1_first")
        val api = object : FakeAuthApi() {
            override suspend fun refresh(body: RefreshRequest): Response<RefreshResponse> =
                Response.success(
                    RefreshResponse(
                        ok = true,
                        accessToken = "access-1",
                        accessExpiresIn = 900,
                        refreshToken = "pomp_r1_second",
                        refreshExpiresIn = 2_592_000,
                    )
                )
        }
        val repository = repository(api, store)

        repository.logout(unlinkDevice = true)

        assertEquals(1, store.clearEverythingCalls)
        assertEquals(0, store.clearSessionCalls)
        assertEquals(AuthState.Unauthenticated, repository.state.value)
    }

    private fun pendingLink() = PendingLink(
        linkRequestId = "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
        displayCode = "HSK4827X",
        pollingSecret = "s".repeat(43),
        botDeepLink = "https://t.me/darsi_chini_bot?start=desktop_link",
        expiresAtMillis = clock + 600_000L,
    )
}
