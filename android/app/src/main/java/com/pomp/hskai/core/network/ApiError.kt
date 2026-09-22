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

    /**
     * The free allowance for a section is spent.
     *
     * [resetAt] is the server instant when it reopens, or null when nothing
     * reopens. The hour is never assumed on the client: it is shown in the
     * learner's own timezone, or not at all.
     */
    data class LimitReached(
        val limitText: String? = null,
        val resetAt: String?,
        override val messageRes: Int,
    ) : ApiError

    /** The user dismissed the provider sheet. Shown as nothing, not an error. */
    data object ProviderCancelled : ApiError {
        override val messageRes = R.string.error_provider_cancelled
    }

    /** No account on the device, or the provider refused before we asked. */
    data object ProviderUnavailable : ApiError {
        override val messageRes = R.string.error_provider_unavailable
    }

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
                "oauth_unavailable",
                -> R.string.error_auth_unavailable

                // Phase 1: a provider identity only ever attaches to an account
                // Telegram already created, so this is the one the user sees
                // most and it must point at the fix, not just fail.
                "oauth_telegram_account_required" -> R.string.error_oauth_needs_telegram
                "oauth_identity_bound_to_other_user" -> R.string.error_oauth_other_account
                "oauth_identity_already_linked" -> R.string.error_oauth_already_linked
                "oauth_last_identity" -> R.string.error_oauth_last_identity
                "oauth_identity_not_found" -> R.string.error_oauth_not_found
                "oauth_provider_unconfigured",
                "oauth_provider_unsupported",
                "oauth_mode_unsupported",
                -> R.string.error_provider_unavailable

                "oauth_cancelled" -> R.string.error_provider_cancelled

                "oauth_state_invalid",
                "oauth_token_invalid",
                "oauth_nonce_mismatch",
                "oauth_exchange_failed",
                "oauth_link_failed",
                "oidc_token_invalid",
                "oidc_token_stale",
                "oidc_nonce_mismatch",
                "oidc_alg_unsupported",
                "oidc_token_malformed",
                "oidc_key_unknown",
                "oidc_jwks_unavailable",
                "oidc_jwks_invalid",
                "oidc_key_unsupported",
                "oidc_provider_unconfigured",
                -> R.string.error_oauth_failed

                "oauth_link_rate_limited" -> R.string.error_link_rate_limited

                "free_feature_limit_reached",
                "LIMIT_EXCEEDED",
                "PRONOUNCE_LIMIT_EXCEEDED",
                -> R.string.error_feature_limit

                "android_foundation_required" -> R.string.error_foundation_required

                "mistake_review_empty" -> R.string.error_no_mistakes

                "challenge_cooldown" -> R.string.error_challenge_cooldown

                "challenge_opponent_not_found",
                "challenge_user_not_found",
                "challenge_self_not_allowed",
                -> R.string.error_challenge_opponent

                "practice_questions_not_found" -> R.string.error_challenge_questions

                "android_challenge_unavailable" -> R.string.error_challenge_unavailable

                "android_referral_unavailable",
                "desktop_referral_unavailable",
                -> R.string.error_referral_unavailable

                "android_subscription_handoff_unavailable",
                -> R.string.limit_unlock_unavailable

                "AI_UNAVAILABLE",
                "AI_FAILED",
                "AI_TIMEOUT",
                "ANDROID_VOICE_REQUEST_INVALID",
                "DESKTOP_VOICE_REQUEST_INVALID",
                "android_voice_unavailable",
                -> R.string.error_voice_unavailable

                // Admin-blocked account. The Telegram flow never reaches the
                // approval step while blocked; a provider flow is refused here
                // instead, so the reason must be stated rather than shown as a
                // generic failure.
                "user_blocked" -> R.string.error_account_blocked

                "desktop_request_invalid",
                "desktop_request_too_large",
                "desktop_platform_invalid",
                "desktop_link_flow_invalid",
                "desktop_link_intent_invalid",
                "android_request_invalid",
                "android_request_too_large",
                -> R.string.error_unknown

                else -> return Unknown
            }
            return Server(normalized, messageRes)
        }
    }
}
