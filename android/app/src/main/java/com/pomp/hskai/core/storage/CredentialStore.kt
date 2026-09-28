package com.pomp.hskai.core.storage

/**
 * Persistence contract for the two secrets the client ever stores, plus the
 * last account the server confirmed.
 *
 * Extracted so [com.pomp.hskai.core.auth.AuthRepository] can be covered by
 * plain JVM unit tests: token rotation and reuse handling are exactly the
 * logic that must not regress, and they should not need an emulator to test.
 */
interface CredentialStore {

    /** Stable per-installation identity. Survives logout, not unlink. */
    suspend fun installationKey(): String

    suspend fun refreshToken(): String?

    /** Atomic replace; there is never a moment with two valid tokens stored. */
    suspend fun saveRefreshToken(token: String)

    /**
     * The last account the server confirmed, as written by [saveCachedAccount].
     * Only read when the server cannot be reached, so the app can still open.
     */
    suspend fun cachedAccount(): String?

    /** Best effort: a phone that cannot store it simply cannot start offline. */
    suspend fun saveCachedAccount(value: String)

    /** Logout: drop the session and its cached account, keep the installation identity. */
    suspend fun clearSession()

    /** Unlink: drop everything, so the next link may bind another account. */
    suspend fun clearEverything()
}
