package com.pomp.hskai.core.auth

import com.pomp.hskai.core.i18n.AppLanguage

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

    data class Authenticated(val account: LinkedAccount) : AuthState
}

/** A device-link attempt in progress. Secrets stay in memory only. */
data class PendingLink(
    val linkRequestId: String,
    val displayCode: String,
    val pollingSecret: String,
    val botDeepLink: String,
    val expiresAtMillis: Long,
)
