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
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.net.URI

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
    private val onAuthenticated: suspend (String) -> Unit = {},
) {

    private val refreshMutex = Mutex()

    @Volatile
    private var accessToken: AccessToken? = null
    private var sessionGeneration = 0L // Guarded by refreshMutex, including late bootstrap responses.

    private val _state = MutableStateFlow<AuthState>(AuthState.Unknown)
    val state: StateFlow<AuthState> = _state.asStateFlow()

    private val _signupReferralCode = MutableStateFlow("")
    val signupReferralCode: StateFlow<String> = _signupReferralCode.asStateFlow()

    fun updateSignupReferralCode(value: String) {
        if (_state.value is AuthState.SignedIn || accessToken != null) return
        _signupReferralCode.value = value.take(64)
    }

    // ---------------------------------------------------------------- linking

    suspend fun startLink(language: AppLanguage? = null): ApiResult<PendingLink> {
        val referralCode = SignupReferral.code(_signupReferralCode.value)
        val installationKey = store.installationKey()
        return when (
            val result = apiCall {
                api.startLink(
                    LinkStartRequest(
                        appVersion = appVersion,
                        installationKey = installationKey,
                        language = language?.backendCode,
                        referralCode = referralCode,
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
        // A dismissed provider attempt must not install credentials from a late response.
        currentCoroutineContext().ensureActive()
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
                        _signupReferralCode.value = ""
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
            is ApiResult.Success -> if (result.value.ok) result.value.providers else return emptyList()
        }
        return offered.mapNotNull(AuthProvider::fromWire).filter { provider ->
            // Google additionally needs a client id compiled into this build;
            // without one the sheet would open and immediately fail.
            provider != AuthProvider.GOOGLE || googleIdTokens?.isAvailable == true
        }
    }

    /**
     * Browser-based Google sign-in for the shipped Android UI.
     *
     * The server exchanges Google's authorization code using the confidential
     * web client and approves a pending link. The browser gets no HSK token;
     * the existing pollLink / refresh-token flow remains the only mint path.
     *
     * Unlike Credential Manager, this remains usable when Google Play Services
     * is unavailable on the device.
     */
    suspend fun startGoogleBrowserSignIn(
        bindToCurrentAccount: Boolean = false,
        language: AppLanguage? = null,
    ): ApiResult<PendingLink> {
        val oauth = oauthApi ?: return ApiResult.Failure(ApiError.Unknown)
        return startProviderLink(
            oauth = oauth,
            provider = AuthProvider.GOOGLE,
            mode = MODE_BROWSER_REDIRECT,
            bindToCurrentAccount = bindToCurrentAccount,
            language = language,
        )
    }

    /**
     * Providers offered by the Android browser flow. A Google browser
     * redirect needs the server's web-client pair, not the APK's optional
     * Credential Manager client ID. Desktop discovery uses this exact flow.
     */
    suspend fun availableBrowserProviders(): List<AuthProvider> {
        val oauth = oauthApi ?: return emptyList()
        return when (val result = apiCall { oauth.providers("macos") }) {
            is ApiResult.Failure -> emptyList()
            is ApiResult.Success -> result.value.providers.mapNotNull(AuthProvider::fromWire)
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
        language: AppLanguage? = null,
    ): ApiResult<PendingLink> {
        val oauth = oauthApi ?: return ApiResult.Failure(ApiError.Unknown)
        val google = googleIdTokens ?: return ApiResult.Failure(ApiError.Unknown)
        val pending = when (
            val started = startProviderLink(
                oauth = oauth,
                provider = AuthProvider.GOOGLE,
                mode = MODE_NATIVE_ID_TOKEN,
                bindToCurrentAccount = bindToCurrentAccount,
                language = language,
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

        currentCoroutineContext().ensureActive()
        if (pending.sessionGeneration != null && !sessionIsCurrent(pending.sessionGeneration)) {
            return ApiResult.Failure(ApiError.SessionExpired)
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
        currentCoroutineContext().ensureActive()
        if (pending.sessionGeneration != null && !sessionIsCurrent(pending.sessionGeneration)) {
            return ApiResult.Failure(ApiError.SessionExpired)
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
    suspend fun startAppleSignIn(
        bindToCurrentAccount: Boolean = false,
        language: AppLanguage? = null,
    ): ApiResult<PendingLink> {
        val oauth = oauthApi ?: return ApiResult.Failure(ApiError.Unknown)
        return startProviderLink(
            oauth = oauth,
            provider = AuthProvider.APPLE,
            mode = MODE_BROWSER_REDIRECT,
            bindToCurrentAccount = bindToCurrentAccount,
            language = language,
        )
    }

    /** Telegram is attached only through the authenticated bot-confirmation flow. */
    suspend fun startTelegramIdentityLink(): ApiResult<PendingLink> {
        val oauth = oauthApi ?: return ApiResult.Failure(ApiError.Unknown)
        return startProviderLink(
            oauth = oauth,
            provider = AuthProvider.TELEGRAM,
            mode = MODE_TELEGRAM_APPROVAL,
            bindToCurrentAccount = true,
            language = null,
        )
    }

    private suspend fun startProviderLink(
        oauth: NativeOAuthApi,
        provider: AuthProvider,
        mode: String,
        bindToCurrentAccount: Boolean,
        language: AppLanguage?,
    ): ApiResult<PendingLink> {
        val referralCode = SignupReferral.code(_signupReferralCode.value).takeUnless { bindToCurrentAccount }
        val body = OAuthStartRequest(
            platform = "android",
            appVersion = appVersion,
            installationKey = store.installationKey(),
            provider = provider.wire,
            mode = mode,
            language = language?.backendCode.takeUnless { bindToCurrentAccount },
            referralCode = referralCode,
        )
        val session = if (bindToCurrentAccount) {
            when (val proof = authenticatedSession()) {
                is ApiResult.Failure -> return proof
                is ApiResult.Success -> proof.value
            }
        } else null
        val result = if (session != null) {
            apiCall { oauth.identityLinkStart("Bearer ${session.token}", body) }
        } else {
            apiCall { oauth.oauthStart(body) }
        }
        currentCoroutineContext().ensureActive()
        if (session != null && !sessionIsCurrent(session.generation)) {
            return ApiResult.Failure(ApiError.SessionExpired)
        }
        return when (result) {
            is ApiResult.Failure -> result
            is ApiResult.Success -> {
                val payload = result.value
                val usable = payload.ok &&
                    payload.linkRequestId.isNotEmpty() &&
                    payload.pollingSecret.isNotEmpty() && payload.expiresIn > 0 &&
                    when (mode) {
                        MODE_NATIVE_ID_TOKEN -> payload.nonce.isNotEmpty()
                        MODE_TELEGRAM_APPROVAL -> isTelegramIdentityLinkUrl(payload.authorizeUrl, payload.linkRequestId)
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
                            sessionGeneration = session?.generation,
                        )
                    )
                }
            }
        }
    }

    // ------------------------------------------------------ linked identities

    suspend fun linkedIdentities(): ApiResult<LinkedAccountIdentities> {
        val oauth = oauthApi ?: return ApiResult.Success(LinkedAccountIdentities(false, emptyList()))
        val token = when (val access = accessToken()) {
            is ApiResult.Failure -> return access
            is ApiResult.Success -> access.value
        }
        return when (val result = apiCall { oauth.identities("Bearer $token") }) {
            is ApiResult.Failure -> result
            is ApiResult.Success -> if (!result.value.ok) ApiResult.Failure(ApiError.Unknown) else ApiResult.Success(
                LinkedAccountIdentities(
                    telegramLinked = result.value.telegramLinked,
                    identities = result.value.identities.mapNotNull { dto ->
                        AuthProvider.fromWire(dto.provider)?.let { provider ->
                            LinkedIdentity(
                                id = dto.id,
                                provider = provider,
                                emailMasked = dto.emailMasked,
                                displayName = dto.displayName,
                            )
                        }
                    },
                )
            )
        }
    }

    /** One poll of an `intent=link` attempt. Never returns a session token. */
    suspend fun pollIdentityLink(pending: PendingLink): ApiResult<String> {
        val oauth = oauthApi ?: return ApiResult.Failure(ApiError.Unknown)
        val session = when (val proof = authenticatedSession()) {
            is ApiResult.Failure -> return proof
            is ApiResult.Success -> proof.value
        }
        if (pending.sessionGeneration != null && pending.sessionGeneration != session.generation) {
            return ApiResult.Failure(ApiError.SessionExpired)
        }
        val result = apiCall {
            oauth.identityLinkStatus(
                "Bearer ${session.token}",
                IdentityLinkStatusRequest(
                    linkRequestId = pending.linkRequestId,
                    pollingSecret = pending.pollingSecret,
                ),
            )
        }
        currentCoroutineContext().ensureActive()
        if (!sessionIsCurrent(session.generation)) return ApiResult.Failure(ApiError.SessionExpired)
        return when (result) {
            is ApiResult.Failure -> result
            is ApiResult.Success -> {
                val body = result.value
                if (!body.ok || body.provider != pending.provider.wire) {
                    ApiResult.Failure(ApiError.Unknown)
                } else if (body.status == "failed" || (body.status == "denied" && body.error != null)) {
                    ApiResult.Failure(ApiError.fromCode(body.error))
                } else if (body.status in setOf("pending", "linked", "expired", "denied")) {
                    ApiResult.Success(body.status)
                } else {
                    ApiResult.Failure(ApiError.Unknown)
                }
            }
        }
    }

    /** Cancels only a pending attachment; an approved identity is never removed. */
    suspend fun cancelIdentityLink(pending: PendingLink): ApiResult<String> {
        val oauth = oauthApi ?: return ApiResult.Failure(ApiError.Unknown)
        val session = when (val proof = authenticatedSession()) {
            is ApiResult.Failure -> return proof
            is ApiResult.Success -> proof.value
        }
        if (pending.sessionGeneration != null && pending.sessionGeneration != session.generation) {
            return ApiResult.Failure(ApiError.SessionExpired)
        }
        return when (val result = apiCall {
            oauth.identityLinkCancel(
                "Bearer ${session.token}",
                IdentityLinkStatusRequest(pending.linkRequestId, pending.pollingSecret),
            )
        }) {
            is ApiResult.Failure -> result
            is ApiResult.Success -> if (result.value.ok) ApiResult.Success(result.value.status)
                else ApiResult.Failure(ApiError.Unknown)
        }
    }

    private data class AuthenticatedSession(val token: String, val generation: Long)

    private suspend fun authenticatedSession(): ApiResult<AuthenticatedSession> {
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return result
            is ApiResult.Success -> result.value
        }
        return refreshMutex.withLock {
            if (accessToken?.value != token) ApiResult.Failure(ApiError.SessionExpired)
            else ApiResult.Success(AuthenticatedSession(token, sessionGeneration))
        }
    }

    private suspend fun sessionIsCurrent(generation: Long): Boolean =
        refreshMutex.withLock { sessionGeneration == generation && accessToken != null }

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

    /**
     * Restores the session on cold start and refreshes the canonical account.
     *
     * Also the way back from [AuthState.Offline]: the state stays offline
     * until this succeeds, so the screen underneath never blinks.
     */
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
                refreshMutex.withLock {
                    when {
                        result.error is ApiError.SessionExpired -> _state.value = AuthState.Unauthenticated
                        // A logout while the refresh was in flight has the last word.
                        sessionGeneration == generation -> _state.value = unreachable(result.error)
                    }
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
                        _state.value = unreachable(result.error)
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
                        store.saveCachedAccount(AccountCache.encode(account))
                        onAuthenticated(body.device.id)
                        _state.value = AuthState.Authenticated(account)
                        _signupReferralCode.value = ""
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
        const val MODE_TELEGRAM_APPROVAL = "telegram_approval"
    }

    /**
     * Where a start goes when the account could not be refreshed. Called under
     * [refreshMutex].
     *
     * Only a missing connection opens the app on the remembered account. A
     * server that answered — with an error, a block, anything — is shown as
     * the error it is.
     */
    private suspend fun unreachable(error: ApiError): AuthState {
        val remembered = if (error is ApiError.Offline || error is ApiError.Timeout) {
            AccountCache.decode(store.cachedAccount())
        } else {
            null
        }
        return remembered?.let { AuthState.Offline(it, error) } ?: AuthState.BootstrapFailed(error)
    }

    private suspend fun clearLocalSession(unlinkDevice: Boolean = false) {
        sessionGeneration++
        accessToken = null
        if (unlinkDevice) store.clearEverything() else store.clearSession()
        onSessionCleared()
        _state.value = AuthState.Unauthenticated
    }
}

/** The account-attachment URL cannot become a generic external navigation. */
internal fun isTelegramIdentityLinkUrl(value: String, requestId: String? = null): Boolean = runCatching {
    val uri = URI(value)
    uri.scheme == "https" && uri.rawAuthority == "t.me" && uri.rawFragment == null &&
        Regex("/[A-Za-z0-9_]{5,32}").matches(uri.rawPath.orEmpty()) &&
        Regex("start=tg_identity_[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
            .matches(uri.rawQuery.orEmpty()) &&
        (requestId == null || uri.rawQuery == "start=tg_identity_$requestId")
}.getOrDefault(false)
