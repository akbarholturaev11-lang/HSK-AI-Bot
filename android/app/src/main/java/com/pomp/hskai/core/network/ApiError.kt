package com.pomp.hskai.core.network

import com.pomp.hskai.R

/**
 * Stable server error codes mapped to user-facing copy.
 *
 * Raw exception text and raw backend payloads are never shown to the user.
 * Unknown codes fall back to a generic message instead of leaking internals.
 */
sealed interface ApiError {

    val messageRes: Int

    /** No usable connection; the request never left the device. */
    data object Offline : ApiError {
        override val messageRes = R.string.error_offline
    }

    data object Timeout : ApiError {
        override val messageRes = R.string.error_timeout
    }

    /** The session is gone; the caller must return to Telegram linking. */
    data object SessionExpired : ApiError {
        override val messageRes = R.string.error_session_expired
    }

    data class Server(val code: String, override val messageRes: Int) : ApiError

    data object Unknown : ApiError {
        override val messageRes = R.string.error_unknown
    }

    companion object {
        /**
         * Codes that mean the stored credentials are worthless. Anything here
         * must trigger a local credential wipe, not a retry loop.
         */
        val UNRECOVERABLE_SESSION_CODES = setOf(
            "desktop_access_invalid",
            "desktop_session_revoked",
            "desktop_refresh_invalid",
            "desktop_refresh_reuse_detected",
            "desktop_user_not_found",
        )

        fun fromCode(code: String?): ApiError {
            val normalized = code?.trim().orEmpty()
            if (normalized in UNRECOVERABLE_SESSION_CODES) return SessionExpired
            val messageRes = when (normalized) {
                "desktop_link_invalid",
                "desktop_link_expired",
                "desktop_link_consumed",
                "desktop_link_already_approved",
                -> R.string.error_link_invalid

                "desktop_link_rate_limited" -> R.string.error_link_rate_limited
                "desktop_device_bound_to_other_user" -> R.string.error_device_bound

                "desktop_auth_unavailable",
                "android_auth_unavailable",
                -> R.string.error_auth_unavailable

                "desktop_request_invalid",
                "desktop_request_too_large",
                "desktop_platform_invalid",
                -> R.string.error_unknown

                else -> return Unknown
            }
            return Server(normalized, messageRes)
        }
    }
}
