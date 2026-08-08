package com.pomp.hskai.core.storage

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import java.security.SecureRandom
import kotlinx.coroutines.flow.first

private val Context.credentialDataStore: DataStore<Preferences> by preferencesDataStore(
    name = "pomp_credentials",
)

/**
 * The only place a refresh token or installation key is ever persisted.
 *
 * Values are encrypted with a Keystore-backed AES-GCM key before they touch
 * disk. They are never written to logs, analytics, crash reports or URLs.
 * Every write goes through DataStore's atomic [edit], so a process death in
 * the middle of a refresh rotation can never leave the device with no token
 * and no way back.
 */
class SecureCredentialStore(context: Context) : CredentialStore {

    private val appContext = context.applicationContext
    private val cipher = KeystoreCipher(KEY_ALIAS)

    override suspend fun installationKey(): String {
        read(INSTALLATION_KEY)?.let { return it }
        // 48 random bytes -> 64 Base64url chars, inside the server's 32..200
        // bound for installation_key.
        val bytes = ByteArray(INSTALLATION_KEY_BYTES)
        SecureRandom().nextBytes(bytes)
        val generated = android.util.Base64.encodeToString(
            bytes,
            android.util.Base64.NO_WRAP or
                android.util.Base64.NO_PADDING or
                android.util.Base64.URL_SAFE,
        )
        write(INSTALLATION_KEY, generated)
        return generated
    }

    override suspend fun refreshToken(): String? = read(REFRESH_TOKEN)

    /**
     * Persists a rotated refresh token. The new value replaces the old one in
     * a single atomic transaction; there is no window where both or neither
     * are stored.
     */
    override suspend fun saveRefreshToken(token: String) = write(REFRESH_TOKEN, token)

    /**
     * Clears the session but keeps the installation key, so the device stays
     * the same installation when the user links again.
     */
    override suspend fun clearSession() {
        appContext.credentialDataStore.edit { it.remove(REFRESH_TOKEN) }
    }

    /**
     * Full unlink: the next link may deliberately bind a different Telegram
     * account, so the installation identity is regenerated too.
     */
    override suspend fun clearEverything() {
        appContext.credentialDataStore.edit { it.clear() }
        cipher.deleteKey()
    }

    private suspend fun read(key: Preferences.Key<String>): String? {
        val stored = appContext.credentialDataStore.data.first()[key] ?: return null
        val decrypted = cipher.decrypt(stored)
        if (decrypted == null) {
            // The Keystore key is gone or the blob is corrupt. Drop the value
            // instead of retrying forever; the caller re-links.
            appContext.credentialDataStore.edit { it.remove(key) }
        }
        return decrypted
    }

    private suspend fun write(key: Preferences.Key<String>, value: String) {
        val encrypted = cipher.encrypt(value)
            ?: error("Keystore unavailable; refusing to persist a secret in clear text")
        appContext.credentialDataStore.edit { it[key] = encrypted }
    }

    private companion object {
        const val KEY_ALIAS = "pomp_hskai_credentials_v1"
        const val INSTALLATION_KEY_BYTES = 48
        val INSTALLATION_KEY = stringPreferencesKey("installation_key")
        val REFRESH_TOKEN = stringPreferencesKey("refresh_token")
    }
}
