package com.pomp.hskai.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ProvidersResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("providers") val providers: List<String> = emptyList(),
)

@Serializable
data class OAuthStartRequest(
    @SerialName("platform") val platform: String = "android",
    @SerialName("app_version") val appVersion: String,
    @SerialName("installation_key") val installationKey: String,
    @SerialName("provider") val provider: String,
    /** `native_id_token` for Google (Credential Manager), `browser_redirect` for Apple. */
    @SerialName("mode") val mode: String,
)

@Serializable
data class OAuthStartResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("status") val status: String = "",
    @SerialName("link_request_id") val linkRequestId: String = "",
    @SerialName("polling_secret") val pollingSecret: String = "",
    @SerialName("expires_in") val expiresIn: Int = 0,
    /** Present for `native_id_token`; must be passed to Credential Manager. */
    @SerialName("nonce") val nonce: String = "",
    /** Present for `browser_redirect`; opened in a Custom Tab, never rendered. */
    @SerialName("authorize_url") val authorizeUrl: String = "",
)

@Serializable
data class OAuthAssertRequest(
    @SerialName("link_request_id") val linkRequestId: String,
    @SerialName("polling_secret") val pollingSecret: String,
    @SerialName("provider") val provider: String = "google",
    @SerialName("id_token") val idToken: String,
)

@Serializable
data class OAuthAssertResponse(
    @SerialName("ok") val ok: Boolean = false,
    /** `approved` for a sign-in, `linked` when attaching to the current account. */
    @SerialName("status") val status: String = "",
    @SerialName("provider") val provider: String = "",
)

@Serializable
data class IdentitiesResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("telegram_linked") val telegramLinked: Boolean = false,
    @SerialName("identities") val identities: List<IdentityDto> = emptyList(),
)

@Serializable
data class IdentityDto(
    @SerialName("id") val id: String = "",
    @SerialName("provider") val provider: String = "",
    /** Already masked by the server; the raw address never reaches the client. */
    @SerialName("email_masked") val emailMasked: String? = null,
    @SerialName("display_name") val displayName: String? = null,
    @SerialName("linked_at") val linkedAt: String? = null,
    @SerialName("last_login_at") val lastLoginAt: String? = null,
)

@Serializable
data class IdentityLinkStatusRequest(
    @SerialName("link_request_id") val linkRequestId: String,
    @SerialName("polling_secret") val pollingSecret: String,
)

@Serializable
data class IdentityLinkStatusResponse(
    @SerialName("ok") val ok: Boolean = false,
    /** `pending` | `linked` | `failed` | `expired`. Never carries a token. */
    @SerialName("status") val status: String = "",
    @SerialName("provider") val provider: String = "",
    @SerialName("error") val error: String? = null,
)

@Serializable
data class IdentityUnlinkRequest(
    @SerialName("identity_id") val identityId: String,
)

@Serializable
data class IdentityUnlinkResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("provider") val provider: String = "",
    /** Other devices signed out, so the UI can say so honestly. */
    @SerialName("sessions_revoked") val sessionsRevoked: Int = 0,
)
