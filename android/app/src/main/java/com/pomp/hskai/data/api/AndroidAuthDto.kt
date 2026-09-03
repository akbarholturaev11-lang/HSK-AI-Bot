package com.pomp.hskai.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class LinkStartRequest(
    @SerialName("platform") val platform: String = "android",
    @SerialName("app_version") val appVersion: String,
    @SerialName("installation_key") val installationKey: String,
)

@Serializable
data class LinkStartResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("status") val status: String = "",
    @SerialName("link_request_id") val linkRequestId: String = "",
    @SerialName("display_code") val displayCode: String = "",
    @SerialName("polling_secret") val pollingSecret: String = "",
    @SerialName("bot_deep_link") val botDeepLink: String = "",
    @SerialName("expires_in") val expiresIn: Int = 0,
)

@Serializable
data class LinkStatusRequest(
    @SerialName("link_request_id") val linkRequestId: String,
    @SerialName("polling_secret") val pollingSecret: String,
)

/**
 * `status` is `pending` until the Telegram user approves. Tokens are present
 * exactly once, on the first approved poll.
 */
@Serializable
data class LinkStatusResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("status") val status: String = "",
    @SerialName("expires_in") val expiresIn: Int = 0,
    @SerialName("access_token") val accessToken: String? = null,
    @SerialName("access_expires_in") val accessExpiresIn: Int? = null,
    @SerialName("refresh_token") val refreshToken: String? = null,
    @SerialName("refresh_expires_in") val refreshExpiresIn: Int? = null,
)

@Serializable
data class RefreshRequest(
    @SerialName("refresh_token") val refreshToken: String,
)

@Serializable
data class RefreshResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("access_token") val accessToken: String = "",
    @SerialName("access_expires_in") val accessExpiresIn: Int = 0,
    @SerialName("refresh_token") val refreshToken: String = "",
    @SerialName("refresh_expires_in") val refreshExpiresIn: Int = 0,
)

@Serializable
data class RevokeRequest(
    @SerialName("revoke_device") val revokeDevice: Boolean = false,
)

/**
 * Modelled explicitly rather than using `Response<Unit>`: the endpoint returns
 * a JSON body, and kotlinx.serialization has no meaningful way to decode one
 * into `Unit`.
 */
@Serializable
data class RevokeResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("device_revoked") val deviceRevoked: Boolean = false,
)

@Serializable
data class BootstrapResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("authenticated") val authenticated: Boolean = false,
    @SerialName("first_open") val firstOpen: Boolean = false,
    @SerialName("version_upgraded") val versionUpgraded: Boolean = false,
    @SerialName("device") val device: BootstrapDevice = BootstrapDevice(),
    @SerialName("user") val user: BootstrapUser = BootstrapUser(),
)

@Serializable
data class BootstrapDevice(
    @SerialName("id") val id: String = "",
    @SerialName("platform") val platform: String = "",
    @SerialName("app_version") val appVersion: String = "",
)

@Serializable
data class BootstrapUser(
    @SerialName("name") val name: String = "",
    @SerialName("language") val language: String = "ru",
    @SerialName("level") val level: String = "hsk1",
    @SerialName("access_state") val accessState: String = "",
    @SerialName("is_paid") val isPaid: Boolean = false,
)

/** Stable error envelope: `{"ok": false, "error": "<code>"}`. */
@Serializable
data class ApiErrorBody(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("error") val error: String = "",
    /**
     * When a spent daily allowance reopens, as a server instant. Null when
     * nothing reopens, so the client must not promise a time.
     */
    @SerialName("reset_at") val resetAt: String? = null,
    /** True when the allowance is once ever, not once a day. */
    @SerialName("lifetime") val lifetime: Boolean = false,
)
