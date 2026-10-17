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

    /** No usable refresh token; the user must choose a sign-in method. */
    data object Unauthenticated : AuthState

    /**
     * Credentials may still be valid, but the canonical account could not be
     * refreshed. The UI shows a retry instead of staying on an endless splash
     * or forcing an unnecessary Telegram relink.
     */
    data class BootstrapFailed(val error: ApiError) : AuthState

    /** A session the app is running with: live, or remembered while offline. */
    sealed interface SignedIn : AuthState {
        val account: LinkedAccount
    }

    data class Authenticated(override val account: LinkedAccount) : SignedIn

    /**
     * The server could not be reached, but this phone was signed in before.
     *
     * [account] is the last one the server confirmed. The app opens with it
     * so what works without a connection — the dictionary, the course map —
     * is not locked behind a retry screen; everything else says it needs the
     * internet. Nothing here is a new grant: the server was already asked
     * for all of it while it was reachable.
     */
    data class Offline(override val account: LinkedAccount, val error: ApiError) : SignedIn
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
 * Sign-in attempts collect their session through `android-auth/link/status`.
 * Authenticated account attachments instead poll `identities/link/status` and
 * never replace the current account's session.
 *
 * [displayCode] and [botDeepLink] are filled only for Telegram sign-in; [nonce]
 * only for Credential Manager. [authorizeUrl] is used for an Apple browser
 * flow or an explicit Telegram attachment confirmation. Secrets stay in memory.
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
    /** Local guard for account-link attempts; never sent to the server or persisted. */
    internal val sessionGeneration: Long? = null,
)

/** An identity attached to the current account, as the server reports it. */
data class LinkedIdentity(
    val id: String,
    val provider: AuthProvider,
    val emailMasked: String?,
    val displayName: String?,
)

/** Sign-in methods belong to one internal HSK AI account; Telegram is optional. */
data class LinkedAccountIdentities(
    val telegramLinked: Boolean,
    val identities: List<LinkedIdentity>,
)
