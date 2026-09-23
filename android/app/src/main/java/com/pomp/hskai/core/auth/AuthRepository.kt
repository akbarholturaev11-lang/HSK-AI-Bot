package com.pomp.hskai.core.auth

import android.app.Activity
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import com.pomp.hskai.core.storage.CredentialStore
import com.pomp.hskai.data.api.AndroidAuthApi
import com.pomp.hskai.data.api.IdentityLinkStatusRequest
import com.pomp.hskai.data.api.IdentityUnlinkRequest
import com.pomp.hskai.data.api.LinkStartRequest
import com.pomp.hskai.data.api.LinkStatusRequest
import com.pomp.hskai.data.api.NativeOAuthApi
import com.pomp.hskai.data.api.OAuthAssertRequest
import com.pomp.hskai.data.api.OAuthStartRequest
import com.pomp.hskai.data.api.RefreshRequest
import com.pomp.hskai.data.api.RevokeRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/**
 * Owns the Android session: device linking, token rotation and sign-out.
 *
 * Invariants:
 *  - the access token lives only in memory;
 *  - the refresh token is written only through [CredentialStore];
 *  - concurrent callers never refresh twice (single-flight [refreshMutex]);
 *  - a revoked or reused session clears local credentials instead of retrying.
 */
class AuthRepository(
    private val api: AndroidAuthApi,
    private val store: CredentialStore,
    private val appVersion: String,
    private val oauthApi: NativeOAuthApi? = null,
    private val googleIdTokens: GoogleIdTokenProvider? = null,
    private val now: () -> Long = System::currentTimeMillis,
    private val onSessionCleared: suspend () -> Unit = {},
    private val onSessionLinked: suspend () -> Unit = {},
    private val onAuthenticated: suspend () -> Unit = {},
) {

    private val refreshMutex = Mutex()

    @Volatile
    private var accessToken: AccessToken? = null
    private var sessionGeneration = 0L // Guarded by refreshMutex, including late bootstrap responses.

    private val _state = MutableStateFlow<AuthState>(AuthState.Unknown)
    val state: StateFlow<AuthState> = _state.asStateFlow()

    // ---------------------------------------------------------------- linking

    suspend fun startLink(): ApiResult<PendingLink> {
        val installationKey = store.installationKey()
        return when (
            val result = apiCall {
                api.startLink(
                    LinkStartRequest(
                        appVersion = appVersion,
                        installationKey = installationKey,
                    )
                )
            }
        ) {
            is ApiResult.Failure -> result
            is ApiResult.Success -> {
                val body = result.value
                if (!body.ok || body.linkRequestId.isEmpty() || body.displayCode.isEmpty()) {
                    ApiResult.Failure(ApiError.Unknown)
                } else {
                    ApiResult.Success(
                        PendingLink(
                            linkRequestId = body.linkRequestId,
                            displayCode = body.displayCode,
                            pollingSecret = body.pollingSecret,
                            botDeepLink = body.botDeepLink,
                            expiresAtMillis = now() + body.expiresIn * 1_000L,
                        )
                    )
                }
            }
        }
    }

    /**
     * One poll of the pending link.
     *
     * Returns `false` while the Telegram user has not approved yet. On the
     * first approved poll the server consumes the code and hands over the
     * token pair exactly once, so the refresh token is persisted before this
     * function returns.
     */
    suspend fun pollLink(pending: PendingLink): ApiResult<Boolean> {
        val generation = refreshMutex.withLock { sessionGeneration }
        val result = apiCall {
            api.linkStatus(
                LinkStatusRequest(
                    linkRequestId = pending.linkRequestId,
                    pollingSecret = pending.pollingSecret,
                )
            )
        }
        return when (result) {
            is ApiResult.Failure -> result
            is ApiResult.Success -> {
                val body = result.value
                val refresh = body.refreshToken
                val access = body.accessToken
                if (body.status != "linked" || refresh.isNullOrEmpty() || access.isNullOrEmpty()) {
                    ApiResult.Success(false)
                } else {
                    // Persist first: the server will never return these again.
                    val accepted = refreshMutex.withLock {
                        if (sessionGeneration != generation) return@withLock false
                        store.saveRefreshToken(refresh)
                        sessionGeneration++
                        onSessionLinked()
                        accessToken = AccessToken(
                            value = access,
                            expiresAtMillis = now() + (body.accessExpiresIn ?: 0) * 1_000L,
                        )
                        true
                    }
                    ApiResult.Success(accepted)
                }
            }
        }
    }

    // -------------------------------------------------------- provider login

    /** Providers this build and this server can actually offer, in UI order. */
    suspend fun availableProviders(): List<AuthProvider> {
        val oauth = oauthApi ?: return emptyList()
        val result = apiCall { oauth.providers() }
        val offered = when (result) {
            is ApiResult.Failure -> return emptyList()
            is ApiResult.Success -> result.value.providers
        }
        return offered.mapNotNull(AuthProvider::fromWire).filter { provider ->
            // Google additionally needs a client id compiled into this build;
            // without one the sheet would open and immediately fail.
            provider != AuthProvider.GOOGLE || googleIdTokens?.isAvailable == true
        }
    }

    /**
     * Signs in with Google through Credential Manager.
     *
     * Ends by returning a [PendingLink] the caller polls exactly like the
     * Telegram flow — the tokens still come from `link/status`, never from an
     * OAuth endpoint.
     */
    suspend fun startGoogleSignIn(
        activity: Activity? = null,
        bindToCurrentAccount: Boolean = false,
    ): ApiResult<PendingLink> {
        val oauth = oauthApi ?: return ApiResult.Failure(ApiError.Unknown)
        val google = googleIdTokens ?: return ApiResult.Failure(ApiError.Unknown)
        val pending = when (
            val started = startProviderLink(
                oauth = oauth,
                provider = AuthProvider.GOOGLE,
                mode = MODE_NATIVE_ID_TOKEN,
                bindToCurrentAccount = bindToCurrentAccount,
            )
        ) {
            is ApiResult.Failure -> return started
            is ApiResult.Success -> started.value
        }

        val idToken = when (val token = google.idToken(activity, pending.nonce)) {
            is GoogleIdTokenResult.Success -> token.idToken
            GoogleIdTokenResult.Cancelled -> return ApiResult.Failure(ApiError.ProviderCancelled)
            GoogleIdTokenResult.Unavailable -> return ApiResult.Failure(ApiError.ProviderUnavailable)
            GoogleIdTokenResult.Failed -> return ApiResult.Failure(ApiError.Unknown)
        }

        val asserted = apiCall {
            oauth.oauthAssert(
                OAuthAssertRequest(
                    linkRequestId = pending.linkRequestId,
                    pollingSecret = pending.pollingSecret,
                    provider = AuthProvider.GOOGLE.wire,
                    idToken = idToken,
                )
            )
        }
        return when (asserted) {
            is ApiResult.Failure -> asserted
            is ApiResult.Success ->
                if (!asserted.value.ok) ApiResult.Failure(ApiError.Unknown)
                else ApiResult.Success(pending)
        }
    }

    /**
     * Starts an Apple sign-in. The caller opens [PendingLink.authorizeUrl] in a
     * Custom Tab and keeps polling; the browser leg finishes on the server, so
     * no inbound deep link and no new allowlisted destination are needed.
     */
    suspend fun startAppleSignIn(bindToCurrentAccount: Boolean = false): ApiResult<PendingLink> {
        val oauth = oauthApi ?: return ApiResult.Failure(ApiError.Unknown)
        return startProviderLink(
            oauth = oauth,
            provider = AuthProvider.APPLE,
            mode = MODE_BROWSER_REDIRECT,
            bindToCurrentAccount = bindToCurrentAccount,
        )
    }

    private suspend fun startProviderLink(
        oauth: NativeOAuthApi,
        provider: AuthProvider,
        mode: String,
        bindToCurrentAccount: Boolean,
    ): ApiResult<PendingLink> {
        val body = OAuthStartRequest(
            platform = "android",
            appVersion = appVersion,
            installationKey = store.installationKey(),
            provider = provider.wire,
            mode = mode,
        )
        val result = if (bindToCurrentAccount) {
            val token = when (val access = accessToken()) {
                is ApiResult.Failure -> return access
                is ApiResult.Success -> access.value
            }
            apiCall { oauth.identityLinkStart("Bearer $token", body) }
        } else {
            apiCall { oauth.oauthStart(body) }
        }
        return when (result) {
            is ApiResult.Failure -> result
            is ApiResult.Success -> {
                val payload = result.value
                val usable = payload.ok &&
                    payload.linkRequestId.isNotEmpty() &&
                    payload.pollingSecret.isNotEmpty() &&
                    when (mode) {
                        MODE_NATIVE_ID_TOKEN -> payload.nonce.isNotEmpty()
                        else -> payload.authorizeUrl.startsWith("https://")
                    }
                if (!usable) {
                    ApiResult.Failure(ApiError.Unknown)
                } else {
                    ApiResult.Success(
                        PendingLink(
                            linkRequestId = payload.linkRequestId,
                            displayCode = "",
                            pollingSecret = payload.pollingSecret,
                            botDeepLink = "",
                            expiresAtMillis = now() + payload.expiresIn * 1_000L,
                            provider = provider,
                            nonce = payload.nonce,
                            authorizeUrl = payload.authorizeUrl,
                        )
                    )
                }
            }
        }
    }

    // ------------------------------------------------------ linked identities

    suspend fun linkedIdentities(): ApiResult<List<LinkedIdentity>> {
        val oauth = oauthApi ?: return ApiResult.Success(emptyList())
        val token = when (val access = accessToken()) {
            is ApiResult.Failure -> return access
            is ApiResult.Success -> access.value
        }
        return when (val result = apiCall { oauth.identities("Bearer $token") }) {
            is ApiResult.Failure -> result
            is ApiResult.Success -> ApiResult.Success(
                result.value.identities.mapNotNull { dto ->
                    AuthProvider.fromWire(dto.provider)?.let { provider ->
                        LinkedIdentity(
                            id = dto.id,
                            provider = provider,
                            emailMasked = dto.emailMasked,
                            displayName = dto.displayName,
                        )
                    }
                }
            )
        }
    }

    /** One poll of an `intent=link` attempt. Never returns a session token. */
    suspend fun pollIdentityLink(pending: PendingLink): ApiResult<String> {
        val oauth = oauthApi ?: return ApiResult.Failure(ApiError.Unknown)
        val token = when (val access = accessToken()) {
            is ApiResult.Failure -> return access
            is ApiResult.Success -> access.value
        }
        val result = apiCall {
            oauth.identityLinkStatus(
                "Bearer $token",
                IdentityLinkStatusRequest(
                    linkRequestId = pending.linkRequestId,
                    pollingSecret = pending.pollingSecret,
                ),
            )
        }
        return when (result) {
            is ApiResult.Failure -> result
            is ApiResult.Success -> {
                val body = result.value
                if (body.status == "failed") {
                    ApiResult.Failure(ApiError.fromCode(body.error))
                } else {
                    ApiResult.Success(body.status)
                }
            }
        }
    }

    /**
     * Removes a provider identity.
     *
     * Returns how many other sessions the server revoked, so the UI can tell
     * the user they were signed out elsewhere instead of letting that happen
     * silently.
     */
    suspend fun unlinkIdentity(identityId: String): ApiResult<Int> {
        val oauth = oauthApi ?: return ApiResult.Failure(ApiError.Unknown)
        val token = when (val access = accessToken()) {
            is ApiResult.Failure -> return access
            is ApiResult.Success -> access.value
        }
        val result = apiCall {
            oauth.identityUnlink("Bearer $token", IdentityUnlinkRequest(identityId))
        }
        return when (result) {
            is ApiResult.Failure -> result
            is ApiResult.Success ->
                if (!result.value.ok) ApiResult.Failure(ApiError.Unknown)
                else ApiResult.Success(result.value.sessionsRevoked)
        }
    }

    // ----------------------------------------------------------------- tokens

    /**
     * A usable access token, refreshing when needed. Only one refresh runs at
     * a time; callers that arrive during a refresh reuse its result.
     */
    suspend fun accessToken(): ApiResult<String> {
        accessToken?.takeIf { it.isUsable(now()) }?.let {
            return ApiResult.Success(it.value)
        }
        return refreshMutex.withLock {
            // Another caller may have refreshed while we waited for the lock.
            accessToken?.takeIf { it.isUsable(now()) }?.let {
                return@withLock ApiResult.Success(it.value)
            }
            val stored = store.refreshToken()
            if (stored == null) {
                clearLocalSession()
                return@withLock ApiResult.Failure(ApiError.SessionExpired)
            }

            when (val result = apiCall { api.refresh(RefreshRequest(stored)) }) {
                is ApiResult.Failure -> {
                    if (result.error is ApiError.SessionExpired) {
                        clearLocalSession()
                    }
                    result
                }

                is ApiResult.Success -> {
                    val body = result.value
                    if (!body.ok || body.accessToken.isEmpty() || body.refreshToken.isEmpty()) {
                        clearLocalSession()
                        ApiResult.Failure(ApiError.SessionExpired)
                    } else {
                        // Atomic replace: the rotated token is durable before
                        // the previous one is considered gone.
                        store.saveRefreshToken(body.refreshToken)
                        val token = AccessToken(
                            value = body.accessToken,
                            expiresAtMillis = now() + body.accessExpiresIn * 1_000L,
                        )
                        accessToken = token
                        ApiResult.Success(token.value)
                    }
                }
            }
        }
    }

    // -------------------------------------------------------------- lifecycle

    /** Restores the session on cold start and refreshes the canonical account. */
    suspend fun bootstrap(): ApiResult<LinkedAccount> {
        val generation = refreshMutex.withLock {
            if (store.refreshToken() == null) {
                clearLocalSession()
                return ApiResult.Failure(ApiError.SessionExpired)
            }
            sessionGeneration
        }
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> {
                if (result.error is ApiError.SessionExpired) {
                    _state.value = AuthState.Unauthenticated
                } else {
                    _state.value = AuthState.BootstrapFailed(result.error)
                }
                return result
            }

            is ApiResult.Success -> result.value
        }

        val result = apiCall { api.bootstrap("Bearer $token", appVersion) }
        return refreshMutex.withLock {
            if (sessionGeneration != generation) return@withLock ApiResult.Failure(ApiError.SessionExpired)
            when (result) {
                is ApiResult.Failure -> {
                    if (result.error is ApiError.SessionExpired) {
                        clearLocalSession()
                    } else {
                        _state.value = AuthState.BootstrapFailed(result.error)
                    }
                    result
                }

                is ApiResult.Success -> {
                    val body = result.value
                    if (!body.authenticated) {
                        clearLocalSession()
                        ApiResult.Failure(ApiError.SessionExpired)
                    } else {
                        val account = LinkedAccount(
                            displayName = body.user.name,
                            language = AppLanguage.fromBackendCode(body.user.language),
                            level = body.user.level,
                            accessState = body.user.accessState,
                            isPaid = body.user.isPaid,
                        )
                        onAuthenticated()
                        _state.value = AuthState.Authenticated(account)
                        ApiResult.Success(account)
                    }
                }
            }
        }
    }

    /**
     * Signs out. The server revoke is best effort: local credentials are
     * always cleared, even offline, so the device never keeps a usable token
     * after the user asked to leave.
     */
    suspend fun logout(unlinkDevice: Boolean = false) {
        when (val result = accessToken()) {
            is ApiResult.Success -> {
                apiCall {
                    api.revoke("Bearer ${result.value}", RevokeRequest(unlinkDevice))
                }
            }
            // No usable token (offline, or the session is already gone). The
            // local wipe below still has to happen.
            is ApiResult.Failure -> Unit
        }
        refreshMutex.withLock {
            clearLocalSession(unlinkDevice)
        }
    }

    /**
     * Called by bearer repositories when an otherwise valid access token is
     * rejected as revoked/expired by a protected endpoint.
     */
    suspend fun invalidateSession() {
        refreshMutex.withLock { clearLocalSession() }
    }

    private companion object {
        const val MODE_NATIVE_ID_TOKEN = "native_id_token"
        const val MODE_BROWSER_REDIRECT = "browser_redirect"
    }

    private suspend fun clearLocalSession(unlinkDevice: Boolean = false) {
        sessionGeneration++
        accessToken = null
        if (unlinkDevice) store.clearEverything() else store.clearSession()
        onSessionCleared()
        _state.value = AuthState.Unauthenticated
    }
}
