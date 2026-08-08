package com.pomp.hskai.core.auth

import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import com.pomp.hskai.core.storage.CredentialStore
import com.pomp.hskai.data.api.AndroidAuthApi
import com.pomp.hskai.data.api.LinkStartRequest
import com.pomp.hskai.data.api.LinkStatusRequest
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
    private val now: () -> Long = System::currentTimeMillis,
) {

    private val refreshMutex = Mutex()

    @Volatile
    private var accessToken: AccessToken? = null

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
                    store.saveRefreshToken(refresh)
                    accessToken = AccessToken(
                        value = access,
                        expiresAtMillis = now() + (body.accessExpiresIn ?: 0) * 1_000L,
                    )
                    ApiResult.Success(true)
                }
            }
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
                ?: return@withLock ApiResult.Failure(ApiError.SessionExpired)

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
        if (store.refreshToken() == null) {
            _state.value = AuthState.Unauthenticated
            return ApiResult.Failure(ApiError.SessionExpired)
        }
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> {
                if (result.error is ApiError.SessionExpired) {
                    _state.value = AuthState.Unauthenticated
                }
                return result
            }

            is ApiResult.Success -> result.value
        }

        return when (
            val result = apiCall { api.bootstrap("Bearer $token", appVersion) }
        ) {
            is ApiResult.Failure -> {
                if (result.error is ApiError.SessionExpired) {
                    clearLocalSession()
                    _state.value = AuthState.Unauthenticated
                }
                result
            }

            is ApiResult.Success -> {
                val body = result.value
                if (!body.authenticated) {
                    clearLocalSession()
                    _state.value = AuthState.Unauthenticated
                    ApiResult.Failure(ApiError.SessionExpired)
                } else {
                    val account = LinkedAccount(
                        displayName = body.user.name,
                        language = AppLanguage.fromBackendCode(body.user.language),
                        level = body.user.level,
                        accessState = body.user.accessState,
                        isPaid = body.user.isPaid,
                    )
                    _state.value = AuthState.Authenticated(account)
                    ApiResult.Success(account)
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
        val token = (accessToken() as? ApiResult.Success)?.value
        if (token != null) {
            apiCall { api.revoke("Bearer $token", RevokeRequest(unlinkDevice)) }
        }
        if (unlinkDevice) {
            store.clearEverything()
        } else {
            store.clearSession()
        }
        accessToken = null
        _state.value = AuthState.Unauthenticated
    }

    private suspend fun clearLocalSession() {
        accessToken = null
        store.clearSession()
    }
}
