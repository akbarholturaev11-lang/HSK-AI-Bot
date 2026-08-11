package com.pomp.hskai.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable
data class AndroidProfileResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("support_url") val supportUrl: String = "",
    @SerialName("user") val user: AndroidProfileUserDto = AndroidProfileUserDto(),
    @SerialName("stats") val stats: AndroidProfileStatsDto = AndroidProfileStatsDto(),
    @SerialName("subscription") val subscription: AndroidProfileSubscriptionDto =
        AndroidProfileSubscriptionDto(),
)

@Serializable
data class AndroidProfileUserDto(
    @SerialName("name") val name: String = "",
    @SerialName("avatar") val avatar: String = "",
    @SerialName("level") val level: String = "hsk1",
    @SerialName("language") val language: String = "uz",
)

@Serializable
data class AndroidProfileStatsDto(
    @SerialName("xp") val xp: Int = 0,
    @SerialName("streak") val streak: Int = 0,
    @SerialName("league") val league: String = "",
    @SerialName("weekly_xp") val weeklyXp: Int = 0,
    @SerialName("completed_lessons") val completedLessons: Int = 0,
    @SerialName("mistakes") val mistakes: Int = 0,
)

@Serializable
data class AndroidProfileSubscriptionDto(
    @SerialName("status") val status: String = "",
    @SerialName("is_paid") val isPaid: Boolean = false,
    @SerialName("until") val until: String? = null,
)

@Serializable
data class AndroidSubscriptionOverviewResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("checkout_allowed") val checkoutAllowed: Boolean = false,
    @SerialName("read_only_reason") val readOnlyReason: String = "",
    @SerialName("access") val access: AndroidSubscriptionAccessDto =
        AndroidSubscriptionAccessDto(),
    @SerialName("billing") val billing: AndroidBillingDto = AndroidBillingDto(),
)

@Serializable
data class AndroidSubscriptionAccessDto(
    @SerialName("state") val state: String = "",
    @SerialName("is_paid") val isPaid: Boolean = false,
    @SerialName("expires_at") val expiresAt: String? = null,
)

@Serializable
data class AndroidBillingDto(
    @SerialName("provider") val provider: String = "",
    @SerialName("configured") val configured: Boolean = false,
    @SerialName("required_external_config") val requiredExternalConfig: List<String> =
        emptyList(),
)

@Serializable
data class PracticeStartRequest(
    @SerialName("mode") val mode: String,
    @SerialName("level") val level: String,
    @SerialName("language") val language: String,
    @SerialName("skill") val skill: String = "",
)

@Serializable
data class PracticeCompleteRequest(
    @SerialName("mode") val mode: String,
    @SerialName("level") val level: String,
    @SerialName("language") val language: String,
    @SerialName("skill") val skill: String = "",
    @SerialName("session_id") val sessionId: String,
    @SerialName("answers") val answers: List<PracticeAnswerDto>,
)

@Serializable
data class PracticeAnswerDto(
    @SerialName("question_id") val questionId: String,
    @SerialName("selected") val selected: Int,
)

@Serializable
data class PracticeStartResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("session") val session: PracticeSessionDto? = null,
)

@Serializable
data class PracticeSessionDto(
    @SerialName("id") val id: String = "",
    @SerialName("mode") val mode: String = "",
    @SerialName("skill") val skill: String = "",
    @SerialName("level") val level: String = "",
    @SerialName("questions") val questions: List<PracticeQuestionDto> = emptyList(),
)

@Serializable
data class PracticeQuestionDto(
    @SerialName("id") val id: String = "",
    @SerialName("level") val level: String = "",
    @SerialName("lesson") val lesson: Int = 0,
    @SerialName("type") val type: String = "",
    @SerialName("subtype") val subtype: String = "",
    @SerialName("prompt") val prompt: String = "",
    @SerialName("sentence") val sentence: String = "",
    @SerialName("audio_text") val audioText: String = "",
    @SerialName("pinyin") val pinyin: String = "",
    @SerialName("options") val options: List<String> = emptyList(),
    @SerialName("answer_index") val answerIndex: Int = -1,
    @SerialName("explanation") val explanation: String = "",
)

@Serializable
data class PracticeCompleteResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("score") val score: Int = 0,
    @SerialName("total") val total: Int = 0,
    @SerialName("percent") val percent: Int = 0,
    @SerialName("recommendation") val recommendation: String = "",
    @SerialName("wrong_items") val wrongItems: List<PracticeWrongDto> = emptyList(),
    @SerialName("reward") val reward: JsonObject? = null,
)

@Serializable
data class PracticeWrongDto(
    @SerialName("question") val question: String = "",
    @SerialName("selected_answer") val selectedAnswer: String = "",
    @SerialName("correct_answer") val correctAnswer: String = "",
    @SerialName("explanation") val explanation: String = "",
    @SerialName("pinyin") val pinyin: String = "",
)

@Serializable
data class MistakesOverviewResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("summary") val summary: MistakeSummaryDto = MistakeSummaryDto(),
    @SerialName("items") val items: List<MistakeItemDto> = emptyList(),
)

@Serializable
data class MistakeSummaryDto(
    @SerialName("total") val total: Int = 0,
    @SerialName("categories") val categories: Map<String, Int> = emptyMap(),
)

@Serializable
data class MistakeItemDto(
    @SerialName("id") val id: Int = 0,
    @SerialName("category") val category: String = "",
    @SerialName("level") val level: String? = null,
    @SerialName("lesson") val lesson: Int? = null,
    @SerialName("question") val question: String = "",
    @SerialName("sentence") val sentence: String = "",
    @SerialName("audio_text") val audioText: String = "",
    @SerialName("pinyin") val pinyin: String = "",
    @SerialName("user_answer") val userAnswer: String? = null,
    @SerialName("correct_answer") val correctAnswer: String = "",
    @SerialName("explanation") val explanation: String? = null,
    @SerialName("count") val count: Int = 0,
)

@Serializable
data class MistakeReviewStartRequest(
    @SerialName("ad_supported") val adSupported: Boolean = false,
    @SerialName("access_ref") val accessRef: String = "",
)

@Serializable
data class MistakeReviewStartResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("session") val session: MistakeReviewSessionDto? = null,
)

@Serializable
data class MistakeReviewSessionDto(
    @SerialName("id") val id: String = "",
    @SerialName("questions") val questions: List<MistakeReviewQuestionDto> = emptyList(),
)

@Serializable
data class MistakeReviewQuestionDto(
    @SerialName("id") val id: String = "",
    @SerialName("category") val category: String = "",
    @SerialName("prompt") val prompt: String = "",
    @SerialName("options") val options: List<String> = emptyList(),
    @SerialName("sentence") val sentence: String = "",
    @SerialName("audio_text") val audioText: String = "",
    @SerialName("pinyin") val pinyin: String = "",
)

@Serializable
data class MistakeReviewAnswerRequest(
    @SerialName("session_id") val sessionId: String,
    @SerialName("question_id") val questionId: String,
    @SerialName("selected_index") val selectedIndex: Int,
)

@Serializable
data class MistakeReviewAnswerResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("question_id") val questionId: String = "",
    @SerialName("selected_index") val selectedIndex: Int = -1,
    @SerialName("correct") val correct: Boolean = false,
    @SerialName("correct_index") val correctIndex: Int = -1,
    @SerialName("correct_answer") val correctAnswer: String = "",
    @SerialName("explanation") val explanation: String = "",
)

@Serializable
data class MistakeReviewCompleteRequest(
    @SerialName("session_id") val sessionId: String,
    @SerialName("answers") val answers: List<MistakeReviewCompleteAnswerDto>,
)

@Serializable
data class MistakeReviewCompleteAnswerDto(
    @SerialName("question_id") val questionId: String,
    @SerialName("selected_index") val selectedIndex: Int,
)

@Serializable
data class MistakeReviewCompleteResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("score") val score: Int = 0,
    @SerialName("total") val total: Int = 0,
    @SerialName("percent") val percent: Int = 0,
    @SerialName("remaining") val remaining: Int = 0,
    @SerialName("reward") val reward: JsonObject? = null,
)

@Serializable
data class RatingResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("rank") val rank: Int = 0,
    @SerialName("league") val league: String = "",
    @SerialName("weekly_xp") val weeklyXp: Int = 0,
    @SerialName("daily_xp") val dailyXp: Int = 0,
    @SerialName("streak") val streak: Int = 0,
    @SerialName("leaderboard") val leaderboard: List<RatingEntryDto> = emptyList(),
)

@Serializable
data class RatingEntryDto(
    @SerialName("rank") val rank: Int = 0,
    @SerialName("name") val name: String = "",
    @SerialName("xp") val xp: Int = 0,
    @SerialName("is_current_user") val isCurrentUser: Boolean = false,
)

@Serializable
data class ReferralOverviewResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("code") val code: String = "",
    @SerialName("link") val link: String = "",
    @SerialName("invited") val invited: Int = 0,
    @SerialName("activated") val activated: Int = 0,
    @SerialName("trial_progress") val trialProgress: Int = 0,
    @SerialName("trial_required") val trialRequired: Int = 0,
    @SerialName("items") val items: List<ReferralItemDto> = emptyList(),
)

@Serializable
data class ReferralItemDto(
    @SerialName("name") val name: String = "",
    @SerialName("status") val status: String = "",
    @SerialName("course_level") val courseLevel: String = "",
    @SerialName("completed_lessons") val completedLessons: Int = 0,
    @SerialName("is_paid") val isPaid: Boolean = false,
)

@Serializable
data class VoiceStatusResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("is_paid") val isPaid: Boolean = false,
    @SerialName("plan") val plan: String = "",
    @SerialName("remaining_voice_limit") val remainingVoiceLimit: Int = 0,
    @SerialName("level") val level: String = "hsk1",
    @SerialName("language") val language: String = "uz",
    @SerialName("completed_lessons") val completedLessons: Int = 0,
)

@Serializable
data class VoiceStartRequest(
    @SerialName("role") val role: String,
    @SerialName("level") val level: String,
    @SerialName("language") val language: String,
    @SerialName("voice") val voice: String = "female",
)

@Serializable
data class VoiceStartResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("session_id") val sessionId: String = "",
    @SerialName("remaining_limit") val remainingLimit: Int = 0,
    @SerialName("character") val character: String = "",
    @SerialName("opening_message") val openingMessage: VoiceReplyDto =
        VoiceReplyDto(),
    @SerialName("max_dialogs") val maxDialogs: Int = 7,
)

@Serializable
data class VoiceMessageRequest(
    @SerialName("session_id") val sessionId: String,
    @SerialName("audio_data_url") val audioDataUrl: String,
)

@Serializable
data class VoiceMessageResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("transcription") val transcription: String = "",
    @SerialName("chinese_reply") val chineseReply: String = "",
    @SerialName("pinyin") val pinyin: String = "",
    @SerialName("translation") val translation: String = "",
    @SerialName("correction") val correction: String? = null,
    @SerialName("remaining_limit") val remainingLimit: Int = 0,
    @SerialName("turn_count") val turnCount: Int = 0,
    @SerialName("max_dialogs") val maxDialogs: Int = 7,
    @SerialName("session_should_end") val sessionShouldEnd: Boolean = false,
)

@Serializable
data class VoiceEndRequest(
    @SerialName("session_id") val sessionId: String,
)

@Serializable
data class VoiceEndResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("duration_seconds") val durationSeconds: Int = 0,
    @SerialName("message_count") val messageCount: Int = 0,
    @SerialName("good_count") val goodCount: Int = 0,
    @SerialName("mistake_count") val mistakeCount: Int = 0,
    @SerialName("transcript") val transcript: List<VoiceTranscriptDto> = emptyList(),
    @SerialName("reward") val reward: JsonObject? = null,
)

@Serializable
data class VoiceReplyDto(
    @SerialName("chinese_reply") val chineseReply: String = "",
    @SerialName("pinyin") val pinyin: String = "",
    @SerialName("translation") val translation: String = "",
    @SerialName("correction") val correction: String? = null,
)

@Serializable
data class VoiceTranscriptDto(
    @SerialName("user") val user: String = "",
    @SerialName("assistant") val assistant: String = "",
    @SerialName("pinyin") val pinyin: String = "",
    @SerialName("translation") val translation: String = "",
    @SerialName("correction") val correction: String? = null,
    @SerialName("good") val good: Boolean = false,
)
