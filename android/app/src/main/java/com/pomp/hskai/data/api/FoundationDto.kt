package com.pomp.hskai.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

/**
 * Starter 0 uses the exact checked-in Mini App card schema. Cards intentionally
 * stay as JsonObject here because each card type has a different shape
 * (choice, builder, tones, listen, speak, result). The feature layer projects
 * them into native UI models without maintaining a second curriculum copy.
 */
@Serializable
data class FoundationPayloadDto(
    @SerialName("id") val id: String = "starter0_hsk1",
    @SerialName("version") val version: Int = 1,
    @SerialName("required_objectives") val requiredObjectives: List<String> = emptyList(),
    @SerialName("cards") val cards: List<JsonObject> = emptyList(),
)

@Serializable
data class FoundationResponseDto(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("foundation") val foundation: FoundationPayloadDto = FoundationPayloadDto(),
    @SerialName("status") val status: CourseFoundationDto = CourseFoundationDto(),
)

@Serializable
data class FoundationCompleteRequest(
    @SerialName("foundation_id") val foundationId: String = "starter0_hsk1",
    @SerialName("foundation_version") val foundationVersion: Int = 1,
    @SerialName("speaking_bonus") val speakingBonus: Boolean = false,
    @SerialName("event_id") val eventId: String,
)

@Serializable
data class FoundationCompleteResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("duplicate") val duplicate: Boolean = false,
    @SerialName("foundation") val foundation: CourseFoundationDto = CourseFoundationDto(),
)
