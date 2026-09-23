package com.pomp.hskai.core.auth

import android.app.Activity
import android.content.Context
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.GetCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential

/**
 * Obtains a Google ID token for a server-issued nonce.
 *
 * Behind an interface so [AuthRepository] stays testable on the JVM: the sign
 * -in orchestration and its error mapping are the parts that must not regress,
 * and they should not need an emulator or a real Google account to test.
 */
interface GoogleIdTokenProvider {

    /** Whether the build carries a Google client id at all. */
    val isAvailable: Boolean

    /**
     * [activity] owns the Credential Manager sheet. An application context
     * cannot present that UI, so callers must pass the current host activity.
     */
    suspend fun idToken(activity: Activity?, nonce: String): GoogleIdTokenResult
}

sealed interface GoogleIdTokenResult {
    data class Success(val idToken: String) : GoogleIdTokenResult

    /** The user dismissed the sheet. Not an error worth showing. */
    data object Cancelled : GoogleIdTokenResult

    /** No Google account on the device, or Play Services refused. */
    data object Unavailable : GoogleIdTokenResult

    data object Failed : GoogleIdTokenResult
}

/**
 * Credential Manager implementation.
 *
 * Uses only the WEB client id — the returned token's `aud` is that id, which
 * is exactly what the server verifies for the Android flow. That is why this
 * app needs neither the `google-services` plugin nor `google-services.json`.
 *
 * The [nonce] is server-derived and mandatory: without it a captured ID token
 * would stay replayable for its whole lifetime.
 */
class CredentialManagerGoogleIdTokenProvider(
    private val context: Context,
    private val webClientId: String,
    private val credentialManager: CredentialManager = CredentialManager.create(context),
) : GoogleIdTokenProvider {

    override val isAvailable: Boolean get() = webClientId.isNotBlank()

    override suspend fun idToken(activity: Activity?, nonce: String): GoogleIdTokenResult {
        if (!isAvailable || nonce.isBlank() || activity == null) {
            return GoogleIdTokenResult.Unavailable
        }
        val option = GetGoogleIdOption.Builder()
            .setServerClientId(webClientId)
            .setNonce(nonce)
            // false: also offer accounts that have not used this app before,
            // otherwise a first-time sign-in shows an empty sheet.
            .setFilterByAuthorizedAccounts(false)
            .build()
        val request = GetCredentialRequest.Builder().addCredentialOption(option).build()
        return try {
            val response = credentialManager.getCredential(activity, request)
            val credential = response.credential
            if (credential.type != GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
                return GoogleIdTokenResult.Failed
            }
            val token = GoogleIdTokenCredential
                .createFrom(credential.data)
                .idToken
            if (token.isBlank()) GoogleIdTokenResult.Failed
            else GoogleIdTokenResult.Success(token)
        } catch (cancelled: GetCredentialCancellationException) {
            GoogleIdTokenResult.Cancelled
        } catch (failure: GetCredentialException) {
            // No account, Play Services missing or out of date, user blocked.
            GoogleIdTokenResult.Unavailable
        } catch (unexpected: Exception) {
            // The token must never be reconstructed from an exception message.
            GoogleIdTokenResult.Failed
        }
    }
}
