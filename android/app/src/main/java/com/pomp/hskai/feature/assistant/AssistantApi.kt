package com.pomp.hskai.feature.assistant

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject
import retrofit2.Response
import retrofit2.http.*

@Serializable
data class ScreenContext(
    val screen: String = "general",
    val title: String = "",
    val details: String = "",
    @SerialName("material_ref") val materialRef: String = "",
    @SerialName("attempt_id") val attemptId: String = "",
    val revision: String = "",
    @SerialName("answer_state") val answerState: String = "",
)

@Serializable
data class AssistantInput(
    @SerialName("client_message_id") val clientMessageId: String,
    val text: String = "",
    val kind: String = "text",
    @SerialName("media_data_url") val mediaDataUrl: String = "",
    val context: ScreenContext = ScreenContext(),
)

@Serializable data class AssistantAction(val label: String = "", val destination: String = "")
@Serializable data class AssistantSource(val label: String = "", @SerialName("material_ref") val materialRef: String = "")
@Serializable data class AssistantConversation(val id: String, val title: String)
@Serializable data class AssistantTurn(
    @SerialName("client_message_id") val clientMessageId: String = "",
    @SerialName("conversation_id") val conversationId: String = "",
    @SerialName("user_text") val userText: String = "",
    val kind: String = "text",
    val status: String = "",
    val phase: String = "",
    val error: String = "",
    val context: ScreenContext = ScreenContext(),
    val text: String = "",
    val transcript: String = "",
    val actions: List<AssistantAction> = emptyList(),
    val sources: List<AssistantSource> = emptyList(),
)
@Serializable data class AssistantEnvelope(
    val ok: Boolean = false,
    val enabled: Boolean = false,
    val error: String = "",
    val entitlements: JsonObject? = null,
    val conversation: AssistantConversation? = null,
    val conversations: List<AssistantConversation> = emptyList(),
    val messages: List<AssistantTurn> = emptyList(),
    @SerialName("next_cursor") val nextCursor: String = "",
    @SerialName("assessment_active") val assessmentActive: Boolean = false,
)
@Serializable data class AbandonAssessment(@SerialName("session_id") val sessionId: String)

interface AssistantApi {
    @GET("api/v3/android/assistant/status")
    suspend fun status(@Header("Authorization") token: String, @Query("channel") channel: String): Response<AssistantEnvelope>
    @GET("api/v3/android/assistant/conversations")
    suspend fun conversations(@Header("Authorization") token: String): Response<AssistantEnvelope>
    @POST("api/v3/android/assistant/conversations")
    suspend fun create(@Header("Authorization") token: String): Response<AssistantEnvelope>
    @GET("api/v3/android/assistant/conversations/{id}/messages")
    suspend fun history(@Header("Authorization") token: String, @Path("id") id: String, @Query("before") before: String = ""): Response<AssistantEnvelope>
    @POST("api/v3/android/assistant/conversations/{id}/messages")
    suspend fun send(@Header("Authorization") token: String, @Path("id") id: String, @Body data: AssistantInput): Response<AssistantTurn>
    @GET("api/v3/android/assistant/requests/{id}")
    suspend fun lookup(@Header("Authorization") token: String, @Path("id") id: String): Response<AssistantTurn>
    @POST("api/v3/android/assistant/assessments/abandon")
    suspend fun abandon(@Header("Authorization") token: String, @Body data: AbandonAssessment): Response<AssistantEnvelope>
}
