@file:OptIn(kotlinx.serialization.ExperimentalSerializationApi::class)
@file:kotlinx.serialization.UseSerializers(StrictStudyBoolean::class, StrictStudyInt::class)

package com.pomp.hskai.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.EncodeDefault
import kotlinx.serialization.KSerializer
import kotlinx.serialization.SerializationException
import kotlinx.serialization.descriptors.*
import kotlinx.serialization.encoding.*
import kotlinx.serialization.json.*
import retrofit2.Response
import retrofit2.http.*

/** Default JSON decoding accepts quoted booleans/numbers; authority requires exact types. */
internal object StrictStudyBoolean : KSerializer<Boolean> {
    override val descriptor = PrimitiveSerialDescriptor("StrictStudyBoolean", PrimitiveKind.BOOLEAN)
    override fun serialize(encoder: Encoder, value: Boolean) = encoder.encodeBoolean(value)
    override fun deserialize(decoder: Decoder): Boolean {
        val value = (decoder as JsonDecoder).decodeJsonElement() as? JsonPrimitive
        if (value == null || value.isString || value.content !in setOf("true", "false"))
            throw SerializationException("Invalid study boolean")
        return value.content == "true"
    }
}
internal object StrictStudyInt : KSerializer<Int> {
    override val descriptor = PrimitiveSerialDescriptor("StrictStudyInt", PrimitiveKind.INT)
    override fun serialize(encoder: Encoder, value: Int) = encoder.encodeInt(value)
    override fun deserialize(decoder: Decoder): Int {
        val value = (decoder as JsonDecoder).decodeJsonElement() as? JsonPrimitive
        if (value == null || value.isString) throw SerializationException("Invalid study integer")
        return value.content.toIntOrNull() ?: throw SerializationException("Invalid study integer")
    }
}

/** Study authority is separate from account-notice ACKs and ordinary widget data. */
interface AndroidSmartReminderApi {
    @GET("api/v3/android/smart-reminder/mode")
    suspend fun mode(@Header("Authorization") bearer: String): Response<SmartStudyMode>
    @GET("api/v3/android/smart-reminder/capability")
    suspend fun capability(@Header("Authorization") bearer: String): Response<SmartStudyCapability>
    @PATCH("api/v3/android/smart-reminder/capability")
    suspend fun observe(@Header("Authorization") bearer: String, @Body body: SmartStudyObservation): Response<SmartStudyCapability>
    @GET("api/v3/android/smart-reminder/due")
    suspend fun due(@Header("Authorization") bearer: String): Response<SmartStudyDue>
    @POST("api/v3/android/smart-reminder/jobs/{job}/claim")
    suspend fun claim(@Header("Authorization") bearer: String, @Path("job") job: String, @Body body: SmartStudyClaim): Response<SmartStudyGrant>
    @POST("api/v3/android/smart-reminder/jobs/{job}/receipt")
    suspend fun receipt(@Header("Authorization") bearer: String, @Path("job") job: String, @Body body: SmartStudyReceipt): Response<SmartStudyReceiptAck>
}

@Serializable data class SmartStudyMode(
    val ok: Boolean = false, val version: Int = 0,
    @SerialName("dispatch_allowed") val dispatchAllowed: Boolean = false,
    @SerialName("server_claim_required") val serverClaimRequired: Boolean? = null,
)
@Serializable data class SmartStudyCapability(
    val ok: Boolean = false, val version: Int = 0, val generation: Int = -1,
    @SerialName("protocol_version") val protocolVersion: Int = 0,
    @SerialName("autonomous_study_disabled") val autonomousDisabled: Boolean? = null,
    @SerialName("study_notifications_allowed") val notificationsAllowed: Boolean? = null,
    val fresh: Boolean = false,
)
@Serializable data class SmartStudyObservation(
    @SerialName("expected_generation") val expectedGeneration: Int,
    @EncodeDefault @SerialName("protocol_version") val protocolVersion: Int = 1,
    @EncodeDefault @SerialName("autonomous_study_disabled") val autonomousDisabled: Boolean = true,
    @SerialName("study_notifications_allowed") val notificationsAllowed: Boolean,
)
@Serializable data class SmartStudyDue(
    val ok: Boolean = false, val version: Int = 0,
    @SerialName("dispatch_allowed") val dispatchAllowed: Boolean = false,
    @SerialName("job_id") val jobId: String? = null,
    @SerialName("preference_revision") val preferenceRevision: Int = -1,
    @SerialName("grant_epoch") val grantEpoch: Int = -1,
    @SerialName("capability_generation") val capabilityGeneration: Int = -1,
)
@Serializable data class SmartStudyClaim(
    @EncodeDefault val version: Int = 1,
    @SerialName("request_id") val requestId: String,
    @SerialName("local_epoch") val localEpoch: String,
    @SerialName("capability_generation") val capabilityGeneration: Int,
    @SerialName("preference_revision") val preferenceRevision: Int,
    @SerialName("grant_epoch") val grantEpoch: Int,
)
@Serializable data class SmartStudyGrant(
    val ok: Boolean = false, val version: Int = 0,
    @SerialName("dispatch_allowed") val dispatchAllowed: Boolean = false,
    @SerialName("job_id") val jobId: String? = null,
    @SerialName("grant_id") val grantId: String? = null,
    @SerialName("local_epoch") val localEpoch: String? = null,
    @SerialName("issued_at") val issuedAt: String? = null,
    @SerialName("expires_at") val expiresAt: String? = null,
    @SerialName("preference_revision") val preferenceRevision: Int = -1,
    @SerialName("grant_epoch") val grantEpoch: Int = -1,
    @SerialName("capability_generation") val capabilityGeneration: Int = -1,
    @SerialName("local_day") val localDay: String? = null,
    @SerialName("timezone_name") val timezoneName: String? = null,
    @SerialName("course_key") val courseKey: String? = null,
    @SerialName("lesson_order") val lessonOrder: Int? = null,
)
@Serializable data class SmartStudyReceipt(
    @EncodeDefault val version: Int = 1,
    @SerialName("grant_id") val grantId: String,
    @SerialName("receipt_id") val receiptId: String,
    @SerialName("local_epoch") val localEpoch: String,
    val outcome: String,
)
@Serializable data class SmartStudyReceiptAck(val ok: Boolean = false, val version: Int = 0)
