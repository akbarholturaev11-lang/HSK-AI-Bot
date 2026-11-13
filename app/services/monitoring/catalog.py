"""Server-owned failure catalog for unified error monitoring (design D1).

Data only, stdlib only: the CI coverage check reads this file by path without
importing the app. Feature IDs reuse the Analytics flow IDs in
``docs/analytics/FEATURE_ANALYTICS_COVERAGE.json``; monitoring-only IDs exist
only where no Analytics flow does. Expected outcomes (limit, paywall, cancel,
401/403/409/429, offline) are deliberately absent so they cannot be reported.
"""

CATALOG_VERSION = "v1"
SCHEMA = "diag.v1"
PLATFORMS = ("android", "iphone_pwa", "telegram", "server")
CLIENT_PLATFORMS = ("android", "iphone_pwa", "telegram")
SEVERITIES = ("normal", "high", "critical")
OUTCOMES = ("failed", "recovered")

MONITORING_ONLY_FEATURES = {
    "app_shell": "Global crash, unknown screen, app shell and settings routes",
    "auth_session": "Sign-in, session restore and account-session failures",
    "monitoring": "Self-checks of the monitor: dropped or refused reports",
}

# Analytics flow IDs used by monitoring, plus the monitoring-only IDs.
FEATURES = frozenset({
    "assessments", "chat_ai", "checkout_payments", "client_activity", "course_ads",
    "course_track_selection", "distribution_handoff", "feedback", "foundation",
    "learning_rewards", "lessons", "mistake_review", "notifications",
    "onboarding_activation", "practice", "pwa_pro_checkout", "referrals",
    "subscription_entries", "voice_practice",
    *MONITORING_ONLY_FEATURES,
})

# A failure in these features is raised one severity step (never above critical).
CRITICAL_FEATURES = frozenset({"checkout_payments", "pwa_pro_checkout", "auth_session"})

# failure_code -> (default severity, Admin catalog key for the explanation)
FAILURES = {
    "crash_uncaught": ("critical", "diagFailureCrashUncaught"),
    "crash_native": ("critical", "diagFailureCrashNative"),
    "anr": ("high", "diagFailureAnr"),
    "js_uncaught": ("high", "diagFailureJsUncaught"),
    "js_rejection": ("normal", "diagFailureJsRejection"),
    "api_5xx": ("high", "diagFailureApi5xx"),
    "api_decode": ("high", "diagFailureApiDecode"),
    "load_failed": ("high", "diagFailureLoadFailed"),
    "save_unconfirmed": ("high", "diagFailureSaveUnconfirmed"),
    "restore_failed": ("normal", "diagFailureRestoreFailed"),
    "live_session_failed": ("normal", "diagFailureLiveSession"),
    "server_5xx": ("high", "diagFailureServer5xx"),
    "server_exception": ("high", "diagFailureServerException"),
    "provider_failed": ("high", "diagFailureProviderFailed"),
    "queue_dropped": ("normal", "diagFailureQueueDropped"),
    "self_dropped": ("normal", "diagFailureSelfDropped"),
}
CLIENT_FAILURES = frozenset(FAILURES) - {"server_5xx", "server_exception", "provider_failed", "self_dropped"}
SERVER_FAILURES = frozenset({"server_5xx", "server_exception", "provider_failed", "self_dropped"})

# Safe technical categories (stored on the receipt, never part of the fingerprint).
CATEGORIES = frozenset({
    "type", "reference", "range", "syntax", "state", "argument", "null", "index",
    "memory", "security", "network", "serialization", "abort", "other",
})

# Client sites: Android screens and API call tags, web page IDs, crash buckets,
# live-voice reasons and self-check sites. Server sites come from ROUTE_MAP and
# INTEGRATION_SITES.
CLIENT_SITES = frozenset({
    # Android crash and exit buckets
    "exc_state", "exc_argument", "exc_null", "exc_index", "exc_memory", "exc_security",
    "exc_network", "exc_serialization", "exc_other", "process",
    # Android tagged API calls and screens
    "login", "session_restore", "onboarding", "lesson_open", "lesson_complete", "practice",
    "progress", "subscription", "payment", "handoff", "app",
    # learner web pages
    "course_v3", "li_onboarding", "memorize", "mistakes", "pwa_onboarding", "pronunciation",
    "recognition", "test", "voice", "pwa_handoff", "pwa_login", "pwa_voice", "checkout",
    # Mini App onboarding (mirrors the Inbox technical explanation codes)
    "onboarding_save", "onboarding_timeout", "onboarding_placement", "tts_fallback", "mic_unavailable",
    # live voice client-side reasons (server-sent codes are never reported)
    "live_connection_lost", "live_message_invalid", "live_message_too_large", "live_send_failed",
    "live_connection_timeout", "live_response_invalid", "live_audio_invalid", "live_socket_closed",
    # self-checks
    "queue", "backend_writer",
})
INTEGRATION_SITES = frozenset({"lava_webhook", "lava_ledger", "ai_provider", "voice_provider", "tts_provider"})

# Exact learner route path -> (feature_code, site_code). Generated once from the
# source inventory (task 1.1) and reviewed; each new learner route adds one line.
# The coverage check fails on a missing or stale entry.
ROUTE_MAP = {
    "/api/v3/monitoring-guard-fixture": ("lessons", "v3_monitoring_guard_fixture"),
    "/api/account-deletion/confirm": ("auth_session", "account_deletion_confirm"),
    "/api/account-deletion/prepare": ("auth_session", "account_deletion_prepare"),
    "/api/account-deletion/providers": ("auth_session", "account_deletion_providers"),
    "/api/account-deletion/start": ("auth_session", "account_deletion_start"),
    "/api/account-deletion/status": ("auth_session", "account_deletion_status"),
    "/api/miniapp/access": ("app_shell", "miniapp_access"),
    "/api/miniapp/challenges": ("practice", "miniapp_challenges"),
    "/api/miniapp/challenges/{challenge_id}/respond": ("practice", "miniapp_challenges_x_respond"),
    "/api/miniapp/challenges/{challenge_id}/start": ("practice", "miniapp_challenges_x_start"),
    "/api/miniapp/challenges/{challenge_id}/submit": ("practice", "miniapp_challenges_x_submit"),
    "/api/miniapp/course-lesson": ("lessons", "miniapp_course_lesson"),
    "/api/miniapp/course-lesson/complete": ("lessons", "miniapp_course_lesson_complete"),
    "/api/miniapp/course-lesson/jump": ("lessons", "miniapp_course_lesson_jump"),
    "/api/miniapp/course-section-plan": ("lessons", "miniapp_course_section_plan"),
    "/api/miniapp/event": ("app_shell", "miniapp_event"),
    "/api/miniapp/gamification": ("learning_rewards", "miniapp_gamification"),
    "/api/miniapp/lesson": ("lessons", "miniapp_lesson"),
    "/api/miniapp/mistakes": ("mistake_review", "miniapp_mistakes"),
    "/api/miniapp/mistakes/review/answer": ("mistake_review", "miniapp_mistakes_review_answer"),
    "/api/miniapp/mistakes/review/complete": ("mistake_review", "miniapp_mistakes_review_complete"),
    "/api/miniapp/mistakes/review/start": ("mistake_review", "miniapp_mistakes_review_start"),
    "/api/miniapp/onboarding": ("onboarding_activation", "miniapp_onboarding"),
    "/api/miniapp/onboarding/status": ("onboarding_activation", "miniapp_onboarding_status"),
    "/api/miniapp/practice/complete": ("practice", "miniapp_practice_complete"),
    "/api/miniapp/practice/start": ("practice", "miniapp_practice_start"),
    "/api/miniapp/profile": ("app_shell", "miniapp_profile"),
    "/api/miniapp/reward-chest/open": ("learning_rewards", "miniapp_reward_chest_open"),
    "/api/payments/lava/webhook": ("checkout_payments", "payments_lava_webhook"),
    "/api/subscription-miniapp/discount-start": ("subscription_entries", "subscription_miniapp_discount_start"),
    "/api/subscription-miniapp/event": ("subscription_entries", "subscription_miniapp_event"),
    "/api/subscription-miniapp/lava/cancel": ("checkout_payments", "subscription_miniapp_lava_cancel"),
    "/api/subscription-miniapp/lava/start": ("checkout_payments", "subscription_miniapp_lava_start"),
    "/api/subscription-miniapp/lava/status": ("checkout_payments", "subscription_miniapp_lava_status"),
    "/api/subscription-miniapp/overview": ("subscription_entries", "subscription_miniapp_overview"),
    "/api/subscription-miniapp/payment-status": ("checkout_payments", "subscription_miniapp_payment_status"),
    "/api/subscription-miniapp/quote": ("checkout_payments", "subscription_miniapp_quote"),
    "/api/subscription-miniapp/submit": ("checkout_payments", "subscription_miniapp_submit"),
    "/api/v3/ad": ("course_ads", "v3_ad"),
    "/api/v3/ad/status": ("course_ads", "v3_ad_status"),
    "/api/v3/ad/view": ("course_ads", "v3_ad_view"),
    "/api/v3/android-auth/link/start": ("auth_session", "v3_android_auth_link_start"),
    "/api/v3/android-auth/link/status": ("auth_session", "v3_android_auth_link_status"),
    "/api/v3/android-auth/refresh": ("auth_session", "v3_android_auth_refresh"),
    "/api/v3/android-auth/revoke": ("auth_session", "v3_android_auth_revoke"),
    "/api/v3/android-update/check": ("distribution_handoff", "v3_android_update_check"),
    "/api/v3/android-update/policy": ("distribution_handoff", "v3_android_update_policy"),
    "/api/v3/android/ad": ("course_ads", "v3_android_ad"),
    "/api/v3/android/ad/view": ("course_ads", "v3_android_ad_view"),
    "/api/v3/android/assistant/assessments/abandon": ("chat_ai", "v3_android_assistant_assessments_abandon"),
    "/api/v3/android/assistant/conversations": ("chat_ai", "v3_android_assistant_conversations"),
    "/api/v3/android/assistant/conversations/{conversation_id}/messages": ("chat_ai", "v3_android_assistant_conversations_x_messages"),
    "/api/v3/android/assistant/requests/{client_message_id}": ("chat_ai", "v3_android_assistant_requests_x"),
    "/api/v3/android/assistant/status": ("chat_ai", "v3_android_assistant_status"),
    "/api/v3/android/bootstrap": ("client_activity", "v3_android_bootstrap"),
    "/api/v3/android/bug-report": ("feedback", "v3_android_bug_report"),
    "/api/v3/android/challenges": ("practice", "v3_android_challenges"),
    "/api/v3/android/challenges/{challenge_id}/respond": ("practice", "v3_android_challenges_x_respond"),
    "/api/v3/android/challenges/{challenge_id}/start": ("practice", "v3_android_challenges_x_start"),
    "/api/v3/android/challenges/{challenge_id}/submit": ("practice", "v3_android_challenges_x_submit"),
    "/api/v3/android/course/complete": ("lessons", "v3_android_course_complete"),
    "/api/v3/android/course/foundation": ("foundation", "v3_android_course_foundation"),
    "/api/v3/android/course/foundation/complete": ("foundation", "v3_android_course_foundation_complete"),
    "/api/v3/android/course/hsk30/promo-shown": ("course_track_selection", "v3_android_course_hsk30_promo_shown"),
    "/api/v3/android/course/lesson/{lesson_order}": ("lessons", "v3_android_course_lesson_x"),
    "/api/v3/android/course/map": ("lessons", "v3_android_course_map"),
    "/api/v3/android/course/onboarding": ("onboarding_activation", "v3_android_course_onboarding"),
    "/api/v3/android/course/onboarding/preview": ("onboarding_activation", "v3_android_course_onboarding_preview"),
    "/api/v3/android/course/reward-chest/open": ("lessons", "v3_android_course_reward_chest_open"),
    "/api/v3/android/course/skip-test/{lesson_order}": ("lessons", "v3_android_course_skip_test_x"),
    "/api/v3/android/course/tracks/switch": ("course_track_selection", "v3_android_course_tracks_switch"),
    "/api/v3/android/diagnostics": ("monitoring", "v3_android_diagnostics"),
    "/api/v3/android/dictionary": ("lessons", "v3_android_dictionary"),
    "/api/v3/android/events": ("app_shell", "v3_android_events"),
    "/api/v3/android/exams/complete": ("assessments", "v3_android_exams_complete"),
    "/api/v3/android/exams/start": ("assessments", "v3_android_exams_start"),
    "/api/v3/android/feedback/prepare": ("feedback", "v3_android_feedback_prepare"),
    "/api/v3/android/feedback/submit": ("feedback", "v3_android_feedback_submit"),
    "/api/v3/android/hints/dismiss": ("app_shell", "v3_android_hints_dismiss"),
    "/api/v3/android/lesson/unlock": ("lessons", "v3_android_lesson_unlock"),
    "/api/v3/android/mistakes": ("mistake_review", "v3_android_mistakes"),
    "/api/v3/android/mistakes/review/answer": ("mistake_review", "v3_android_mistakes_review_answer"),
    "/api/v3/android/mistakes/review/complete": ("mistake_review", "v3_android_mistakes_review_complete"),
    "/api/v3/android/mistakes/review/start": ("mistake_review", "v3_android_mistakes_review_start"),
    "/api/v3/android/notices/{notice_id}": ("notifications", "v3_android_notices_x"),
    "/api/v3/android/notices/{notice_id}/ack": ("notifications", "v3_android_notices_x_ack"),
    "/api/v3/android/practice/complete": ("practice", "v3_android_practice_complete"),
    "/api/v3/android/practice/gate": ("practice", "v3_android_practice_gate"),
    "/api/v3/android/practice/report": ("practice", "v3_android_practice_report"),
    "/api/v3/android/practice/start": ("practice", "v3_android_practice_start"),
    "/api/v3/android/practice/words": ("practice", "v3_android_practice_words"),
    "/api/v3/android/preferences/language": ("app_shell", "v3_android_preferences_language"),
    "/api/v3/android/preferences/notifications": ("app_shell", "v3_android_preferences_notifications"),
    "/api/v3/android/preferences/study": ("app_shell", "v3_android_preferences_study"),
    "/api/v3/android/profile": ("app_shell", "v3_android_profile"),
    "/api/v3/android/push/preferences": ("notifications", "v3_android_push_preferences"),
    "/api/v3/android/push/register": ("notifications", "v3_android_push_register"),
    "/api/v3/android/push/unregister": ("notifications", "v3_android_push_unregister"),
    "/api/v3/android/rating/leaderboard": ("app_shell", "v3_android_rating_leaderboard"),
    "/api/v3/android/referral/overview": ("app_shell", "v3_android_referral_overview"),
    "/api/v3/android/smart-reminder/capability": ("notifications", "v3_android_smart_reminder_capability"),
    "/api/v3/android/smart-reminder/due": ("notifications", "v3_android_smart_reminder_due"),
    "/api/v3/android/smart-reminder/jobs/{job_id}/claim": ("notifications", "v3_android_smart_reminder_jobs_x_claim"),
    "/api/v3/android/smart-reminder/jobs/{job_id}/open": ("notifications", "v3_android_smart_reminder_jobs_x_open"),
    "/api/v3/android/smart-reminder/jobs/{job_id}/receipt": ("notifications", "v3_android_smart_reminder_jobs_x_receipt"),
    "/api/v3/android/smart-reminder/mode": ("notifications", "v3_android_smart_reminder_mode"),
    "/api/v3/android/smart-reminder/preferences": ("notifications", "v3_android_smart_reminder_preferences"),
    "/api/v3/android/stroke": ("lessons", "v3_android_stroke"),
    "/api/v3/android/subscription/checkout/discount-start": ("subscription_entries", "v3_android_subscription_checkout_discount_start"),
    "/api/v3/android/subscription/checkout/event": ("subscription_entries", "v3_android_subscription_checkout_event"),
    "/api/v3/android/subscription/checkout/overview": ("subscription_entries", "v3_android_subscription_checkout_overview"),
    "/api/v3/android/subscription/checkout/quote": ("checkout_payments", "v3_android_subscription_checkout_quote"),
    "/api/v3/android/subscription/checkout/submit": ("checkout_payments", "v3_android_subscription_checkout_submit"),
    "/api/v3/android/subscription/currency-preference": ("subscription_entries", "v3_android_subscription_currency_preference"),
    "/api/v3/android/subscription/lava/cancel": ("checkout_payments", "v3_android_subscription_lava_cancel"),
    "/api/v3/android/subscription/lava/exit-offer": ("checkout_payments", "v3_android_subscription_lava_exit_offer"),
    "/api/v3/android/subscription/lava/overview": ("checkout_payments", "v3_android_subscription_lava_overview"),
    "/api/v3/android/subscription/lava/start": ("checkout_payments", "v3_android_subscription_lava_start"),
    "/api/v3/android/subscription/lava/status": ("checkout_payments", "v3_android_subscription_lava_status"),
    "/api/v3/android/subscription/open": ("subscription_entries", "v3_android_subscription_open"),
    "/api/v3/android/subscription/overview": ("subscription_entries", "v3_android_subscription_overview"),
    "/api/v3/android/subscription/payments/{payment_id}/status": ("checkout_payments", "v3_android_subscription_payments_x_status"),
    "/api/v3/android/trial/start": ("subscription_entries", "v3_android_trial_start"),
    "/api/v3/android/trial/status": ("subscription_entries", "v3_android_trial_status"),
    "/api/v3/android/tts": ("lessons", "v3_android_tts"),
    "/api/v3/android/voice/message": ("voice_practice", "v3_android_voice_message"),
    "/api/v3/android/voice/pronounce": ("voice_practice", "v3_android_voice_pronounce"),
    "/api/v3/android/voice/session/end": ("voice_practice", "v3_android_voice_session_end"),
    "/api/v3/android/voice/session/start": ("voice_practice", "v3_android_voice_session_start"),
    "/api/v3/android/voice/status": ("voice_practice", "v3_android_voice_status"),
    "/api/v3/apps/public-status": ("distribution_handoff", "v3_apps_public_status"),
    "/api/v3/avatar/{telegram_id}": ("app_shell", "v3_avatar_x"),
    "/api/v3/clientlog": ("app_shell", "v3_clientlog"),
    "/api/v3/course-tracks": ("course_track_selection", "v3_course_tracks"),
    "/api/v3/course-tracks/promo-shown": ("course_track_selection", "v3_course_tracks_promo_shown"),
    "/api/v3/course-tracks/switch": ("course_track_selection", "v3_course_tracks_switch"),
    "/api/v3/exams/complete": ("assessments", "v3_exams_complete"),
    "/api/v3/exams/start": ("assessments", "v3_exams_start"),
    "/api/v3/exit": ("client_activity", "v3_exit"),
    "/api/v3/hints/dismiss": ("app_shell", "v3_hints_dismiss"),
    "/api/v3/invite": ("referrals", "v3_invite"),
    "/api/v3/language": ("app_shell", "v3_language"),
    "/api/v3/lesson/complete": ("lessons", "v3_lesson_complete"),
    "/api/v3/lesson/content/{level}/{lesson_order}": ("lessons", "v3_lesson_content_x_x"),
    "/api/v3/lesson/foundation": ("foundation", "v3_lesson_foundation"),
    "/api/v3/lesson/foundation/complete": ("foundation", "v3_lesson_foundation_complete"),
    "/api/v3/lesson/sales-preview": ("lessons", "v3_lesson_sales_preview"),
    "/api/v3/lesson/skip-test": ("lessons", "v3_lesson_skip_test"),
    "/api/v3/lesson/start": ("lessons", "v3_lesson_start"),
    "/api/v3/lesson/unlock": ("lessons", "v3_lesson_unlock"),
    "/api/v3/limits/status": ("lessons", "v3_limits_status"),
    "/api/v3/map": ("lessons", "v3_map"),
    "/api/v3/native-auth/identities": ("auth_session", "v3_native_auth_identities"),
    "/api/v3/native-auth/identities/link/cancel": ("auth_session", "v3_native_auth_identities_link_cancel"),
    "/api/v3/native-auth/identities/link/start": ("auth_session", "v3_native_auth_identities_link_start"),
    "/api/v3/native-auth/identities/link/status": ("auth_session", "v3_native_auth_identities_link_status"),
    "/api/v3/native-auth/identities/unlink": ("auth_session", "v3_native_auth_identities_unlink"),
    "/api/v3/native-auth/oauth/assert": ("auth_session", "v3_native_auth_oauth_assert"),
    "/api/v3/native-auth/oauth/callback/apple": ("auth_session", "v3_native_auth_oauth_callback_apple"),
    "/api/v3/native-auth/oauth/callback/google": ("auth_session", "v3_native_auth_oauth_callback_google"),
    "/api/v3/native-auth/oauth/start": ("auth_session", "v3_native_auth_oauth_start"),
    "/api/v3/native-auth/providers": ("auth_session", "v3_native_auth_providers"),
    "/api/v3/native/course-tracks": ("course_track_selection", "v3_native_course_tracks"),
    "/api/v3/native/course-tracks/promo-shown": ("course_track_selection", "v3_native_course_tracks_promo_shown"),
    "/api/v3/native/course-tracks/switch": ("course_track_selection", "v3_native_course_tracks_switch"),
    "/api/v3/notify": ("notifications", "v3_notify"),
    "/api/v3/practice/ad-gate": ("practice", "v3_practice_ad_gate"),
    "/api/v3/practice/complete": ("practice", "v3_practice_complete"),
    "/api/v3/practice/daily-gate": ("practice", "v3_practice_daily_gate"),
    "/api/v3/practice/report": ("practice", "v3_practice_report"),
    "/api/v3/practice/start": ("practice", "v3_practice_start"),
    "/api/v3/practice/words": ("practice", "v3_practice_words"),
    "/api/v3/preferences": ("app_shell", "v3_preferences"),
    "/api/v3/pwa-auth/handoff/redeem": ("distribution_handoff", "v3_pwa_auth_handoff_redeem"),
    "/api/v3/pwa-auth/handoff/start": ("distribution_handoff", "v3_pwa_auth_handoff_start"),
    "/api/v3/pwa-auth/logout": ("auth_session", "v3_pwa_auth_logout"),
    "/api/v3/pwa-auth/providers": ("auth_session", "v3_pwa_auth_providers"),
    "/api/v3/pwa-auth/session": ("auth_session", "v3_pwa_auth_session"),
    "/api/v3/pwa-auth/start": ("auth_session", "v3_pwa_auth_start"),
    "/api/v3/pwa-auth/telegram/claim": ("auth_session", "v3_pwa_auth_telegram_claim"),
    "/api/v3/pwa-auth/telegram/start": ("auth_session", "v3_pwa_auth_telegram_start"),
    "/api/v3/pwa/account-notices": ("app_shell", "v3_pwa_account_notices"),
    "/api/v3/pwa/ad": ("course_ads", "v3_pwa_ad"),
    "/api/v3/pwa/ad/view": ("course_ads", "v3_pwa_ad_view"),
    "/api/v3/pwa/bug-report": ("feedback", "v3_pwa_bug_report"),
    "/api/v3/pwa/course-tracks": ("course_track_selection", "v3_pwa_course_tracks"),
    "/api/v3/pwa/course-tracks/promo-shown": ("course_track_selection", "v3_pwa_course_tracks_promo_shown"),
    "/api/v3/pwa/course-tracks/switch": ("course_track_selection", "v3_pwa_course_tracks_switch"),
    "/api/v3/pwa/diagnostics": ("monitoring", "v3_pwa_diagnostics"),
    "/api/v3/pwa/event": ("app_shell", "v3_pwa_event"),
    "/api/v3/pwa/exams/complete": ("assessments", "v3_pwa_exams_complete"),
    "/api/v3/pwa/exams/start": ("assessments", "v3_pwa_exams_start"),
    "/api/v3/pwa/feedback/available": ("feedback", "v3_pwa_feedback_available"),
    "/api/v3/pwa/feedback/lesson/prepare": ("feedback", "v3_pwa_feedback_lesson_prepare"),
    "/api/v3/pwa/feedback/ordinary/prepare": ("feedback", "v3_pwa_feedback_ordinary_prepare"),
    "/api/v3/pwa/feedback/ordinary/submit": ("feedback", "v3_pwa_feedback_ordinary_submit"),
    "/api/v3/pwa/feedback/release/comment": ("feedback", "v3_pwa_feedback_release_comment"),
    "/api/v3/pwa/feedback/release/respond": ("feedback", "v3_pwa_feedback_release_respond"),
    "/api/v3/pwa/gamification": ("app_shell", "v3_pwa_gamification"),
    "/api/v3/pwa/hints/dismiss": ("app_shell", "v3_pwa_hints_dismiss"),
    "/api/v3/pwa/invite": ("app_shell", "v3_pwa_invite"),
    "/api/v3/pwa/language": ("app_shell", "v3_pwa_language"),
    "/api/v3/pwa/lesson/complete": ("lessons", "v3_pwa_lesson_complete"),
    "/api/v3/pwa/lesson/content/{level}/{lesson_order}": ("lessons", "v3_pwa_lesson_content_x_x"),
    "/api/v3/pwa/lesson/foundation": ("foundation", "v3_pwa_lesson_foundation"),
    "/api/v3/pwa/lesson/foundation/complete": ("foundation", "v3_pwa_lesson_foundation_complete"),
    "/api/v3/pwa/lesson/start": ("lessons", "v3_pwa_lesson_start"),
    "/api/v3/pwa/limits/status": ("lessons", "v3_pwa_limits_status"),
    "/api/v3/pwa/map": ("lessons", "v3_pwa_map"),
    "/api/v3/pwa/mistakes": ("mistake_review", "v3_pwa_mistakes"),
    "/api/v3/pwa/mistakes/review/answer": ("mistake_review", "v3_pwa_mistakes_review_answer"),
    "/api/v3/pwa/mistakes/review/complete": ("mistake_review", "v3_pwa_mistakes_review_complete"),
    "/api/v3/pwa/mistakes/review/start": ("mistake_review", "v3_pwa_mistakes_review_start"),
    "/api/v3/pwa/notifications": ("app_shell", "v3_pwa_notifications"),
    "/api/v3/pwa/notify": ("app_shell", "v3_pwa_notify"),
    "/api/v3/pwa/onboarding": ("onboarding_activation", "v3_pwa_onboarding"),
    "/api/v3/pwa/onboarding/li/resume": ("onboarding_activation", "v3_pwa_onboarding_li_resume"),
    "/api/v3/pwa/onboarding/public-tracks": ("onboarding_activation", "v3_pwa_onboarding_public_tracks"),
    "/api/v3/pwa/onboarding/status": ("onboarding_activation", "v3_pwa_onboarding_status"),
    "/api/v3/pwa/practice/daily-gate": ("practice", "v3_pwa_practice_daily_gate"),
    "/api/v3/pwa/practice/profile": ("practice", "v3_pwa_practice_profile"),
    "/api/v3/pwa/practice/report": ("practice", "v3_pwa_practice_report"),
    "/api/v3/pwa/practice/words": ("practice", "v3_pwa_practice_words"),
    "/api/v3/pwa/preferences": ("app_shell", "v3_pwa_preferences"),
    "/api/v3/pwa/profile": ("app_shell", "v3_pwa_profile"),
    "/api/v3/pwa/push/revoke": ("app_shell", "v3_pwa_push_revoke"),
    "/api/v3/pwa/push/status": ("app_shell", "v3_pwa_push_status"),
    "/api/v3/pwa/push/subscribe": ("app_shell", "v3_pwa_push_subscribe"),
    "/api/v3/pwa/subscription/discount-start": ("subscription_entries", "v3_pwa_subscription_discount_start"),
    "/api/v3/pwa/subscription/event": ("subscription_entries", "v3_pwa_subscription_event"),
    "/api/v3/pwa/subscription/exit-offer": ("subscription_entries", "v3_pwa_subscription_exit_offer"),
    "/api/v3/pwa/subscription/inline-event": ("subscription_entries", "v3_pwa_subscription_inline_event"),
    "/api/v3/pwa/subscription/lava/cancel": ("pwa_pro_checkout", "v3_pwa_subscription_lava_cancel"),
    "/api/v3/pwa/subscription/lava/start": ("pwa_pro_checkout", "v3_pwa_subscription_lava_start"),
    "/api/v3/pwa/subscription/lava/status": ("pwa_pro_checkout", "v3_pwa_subscription_lava_status"),
    "/api/v3/pwa/subscription/overview": ("subscription_entries", "v3_pwa_subscription_overview"),
    "/api/v3/pwa/subscription/payment-status": ("checkout_payments", "v3_pwa_subscription_payment_status"),
    "/api/v3/pwa/subscription/quote": ("checkout_payments", "v3_pwa_subscription_quote"),
    "/api/v3/pwa/subscription/submit": ("checkout_payments", "v3_pwa_subscription_submit"),
    "/api/v3/pwa/trial/start": ("subscription_entries", "v3_pwa_trial_start"),
    "/api/v3/pwa/trial/status": ("subscription_entries", "v3_pwa_trial_status"),
    "/api/v3/pwa/voice/me": ("voice_practice", "v3_pwa_voice_me"),
    "/api/v3/pwa/voice/message": ("voice_practice", "v3_pwa_voice_message"),
    "/api/v3/pwa/voice/pronounce": ("voice_practice", "v3_pwa_voice_pronounce"),
    "/api/v3/pwa/voice/session/end": ("voice_practice", "v3_pwa_voice_session_end"),
    "/api/v3/pwa/voice/session/mode": ("voice_practice", "v3_pwa_voice_session_mode"),
    "/api/v3/pwa/voice/session/start": ("voice_practice", "v3_pwa_voice_session_start"),
    "/api/v3/smart-reminder/jobs/{job_id}/open": ("notifications", "v3_smart_reminder_jobs_x_open"),
    "/api/v3/smart-reminder/preferences": ("notifications", "v3_smart_reminder_preferences"),
    "/api/v3/stroke": ("lessons", "v3_stroke"),
    "/api/v3/trial/start": ("lessons", "v3_trial_start"),
    "/api/v3/trial/status": ("lessons", "v3_trial_status"),
    "/api/v3/tts": ("lessons", "v3_tts"),
    "/api/voice-practice/me": ("voice_practice", "voice_practice_me"),
    "/api/voice-practice/message": ("voice_practice", "voice_practice_message"),
    "/api/voice-practice/pronounce": ("voice_practice", "voice_practice_pronounce"),
    "/api/voice-practice/session/end": ("voice_practice", "voice_practice_session_end"),
    "/api/voice-practice/session/mode": ("voice_practice", "voice_practice_session_mode"),
    "/api/voice-practice/session/start": ("voice_practice", "voice_practice_session_start"),
}

ALL_SITES = CLIENT_SITES | INTEGRATION_SITES | frozenset(site for _, site in ROUTE_MAP.values())

# Numeric defaults (catalog constants, tunable after the owners stage).
MAX_BODY_BYTES = 16 * 1024
MAX_EVENTS_PER_BATCH = 20
MAX_VERSION_LENGTH = 40
CLOCK_SKEW_DAYS = 7
HOURLY_CAP_PER_ACCOUNT = 60
RECEIPT_RETENTION_DAYS = 30
RESOLVED_INCIDENT_RETENTION_DAYS = 180
PURGE_BATCH = 1000
ALERT_COOLDOWN_HOURS = 6
ALERT_GLOBAL_CAP_PER_HOUR = 6
ESCALATION_ACCOUNTS = 5
ESCALATION_WINDOW_MINUTES = 60
BACKEND_WRITE_CONCURRENCY = 8
BACKEND_PENDING_FINGERPRINTS = 128
BACKEND_COALESCE_SECONDS = 10


def severity_for(feature_code, failure_code, *, recovered=False):
    """Server-owned severity: catalog default, one step up for critical
    features, one step down when the client confirmed recovery."""
    base = SEVERITIES.index(FAILURES[failure_code][0])
    if feature_code in CRITICAL_FEATURES:
        base = min(base + 1, len(SEVERITIES) - 1)
    if recovered:
        base = max(base - 1, 0)
    return SEVERITIES[base]
