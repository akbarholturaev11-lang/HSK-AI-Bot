package com.pomp.hskai.core.auth

import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError

/** In-memory only. The access token is never persisted to disk. */
data class AccessToken(
    val value: String,
    val expiresAtMillis: Long,
) {
    fun isUsable(nowMillis: Long, skewMillis: Long = REFRESH_SKEW_MILLIS): Boolean =
        value.isNotEmpty() && nowMillis < expiresAtMillis - skewMillis

    companion object {
        /** Refresh slightly early so a request never dies on a fresh token. */
        const val REFRESH_SKEW_MILLIS = 30_000L
    }
}

/** The canonical account, exactly as the server reports it. */
data class LinkedAccount(
    val displayName: String,
    val language: AppLanguage,
    val level: String,
    val accessState: String,
    val isPaid: Boolean,
)

sealed interface AuthState {
    /** Credentials not yet read from disk. */
    data object Unknown : AuthState

    /** No usable refresh token; the user must link through Telegram. */
    data object Unauthenticated : AuthState

    /**
     * Credentials may still be valid, but the canonical account could not be
     * refreshed. The UI shows a retry instead of staying on an endless splash
     * or forcing an unnecessary Telegram relink.
     */
    data class BootstrapFailed(val error: ApiError) : AuthState

    data class Authenticated(val account: LinkedAccount) : AuthState
}

/** How the account is being proven. */
enum class AuthProvider(val wire: String) {
    TELEGRAM("telegram"),
    GOOGLE("google"),
    APPLE("apple"),
    ;

    companion object {
        fun fromWire(value: String?): AuthProvider? =
            entries.firstOrNull { it.wire == value?.trim()?.lowercase() }
    }
}

/**
 * A link attempt in progress. Secrets stay in memory only.
 *
 * All three providers share this type on purpose: whichever way the account is
 * proven, the session is always collected by polling the same
 * `android-auth/link/status` endpoint, so there is one polling path in the app.
 *
 * [displayCode] and [botDeepLink] are filled only for Telegram; [nonce] only
 * for a Credential Manager flow; [authorizeUrl] only for a browser flow. None
 * of them is ever logged.
 */
data class PendingLink(
    val linkRequestId: String,
    val displayCode: String,
    val pollingSecret: String,
    val botDeepLink: String,
    val expiresAtMillis: Long,
    val provider: AuthProvider = AuthProvider.TELEGRAM,
    val nonce: String = "",
    val authorizeUrl: String = "",
)

/** An identity attached to the current account, as the server reports it. */
data class LinkedIdentity(
    val id: String,
    val provider: AuthProvider,
    val emailMasked: String?,
    val displayName: String?,
)
