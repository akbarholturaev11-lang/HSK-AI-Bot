package com.pomp.hskai.widget

import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneId
import java.time.ZonedDateTime
import java.util.UUID
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.*

/** The shared v1 passive allowlist. It contains no identity, bearer or grant. */
@Serializable
data class WidgetPersonalContext(
    val version: Int,
    @SerialName("policy_version") val policyVersion: String,
    val binding: String,
    @SerialName("request_epoch") val requestEpoch: String,
    val revision: Int,
    @SerialName("generated_at") val generatedAt: String,
    @SerialName("valid_until") val validUntil: String,
    val level: String,
    val track: String,
    @SerialName("local_day") val localDay: String?,
    @SerialName("timezone_name") val timezoneName: String?,
    @SerialName("completed_parts") val completedParts: Int?,
    @SerialName("total_parts") val totalParts: Int?,
    @SerialName("verified_today_xp") val verifiedTodayXp: Int?,
    @SerialName("goal_xp") val goalXp: Int?,
    @SerialName("goal_state") val goalState: String,
    @SerialName("plan_completed") val planCompleted: Boolean?,
    @SerialName("time_local") val timeLocal: String?,
    @SerialName("time_source") val timeSource: String,
    @SerialName("time_reason") val timeReason: String,
    val phase: String,
    val reason: String,
    val action: String,
    @SerialName("lesson_order") val lessonOrder: Int?,
    @SerialName("coverage_limits") val coverageLimits: List<String>,
    @SerialName("calibration_version") val calibrationVersion: String?,
    @SerialName("dispatch_allowed") val dispatchAllowed: Boolean,
    @SerialName("action_requires_authorization") val actionRequiresAuthorization: Boolean,
) {
    val generatedMillis: Long get() = Instant.parse(generatedAt).toEpochMilli()

    fun current(snapshot: WidgetSnapshot, epoch: String, now: ZonedDateTime): Boolean =
        requestEpoch == epoch && level == snapshot.level &&
            snapshot.zoneId == now.zone.id && snapshot.localDay == now.toLocalDate().toString() &&
            (timezoneName == null || timezoneName == now.zone.id && localDay == snapshot.localDay) &&
            !now.toInstant().isBefore(Instant.parse(generatedAt)) &&
            now.toInstant().isBefore(Instant.parse(validUntil))

    companion object {
        private val json = Json { ignoreUnknownKeys = false }
        private val keys = setOf("version", "policy_version", "binding", "request_epoch", "revision",
            "generated_at", "valid_until", "level", "track", "local_day", "timezone_name",
            "completed_parts", "total_parts", "verified_today_xp", "goal_xp", "goal_state",
            "plan_completed", "time_local", "time_source", "time_reason", "phase", "reason",
            "action", "lesson_order", "coverage_limits", "calibration_version", "dispatch_allowed",
            "action_requires_authorization")

        /** Malformed personalization never breaks decoding the older linked session. */
        fun parse(raw: JsonElement?): WidgetPersonalContext? = runCatching {
            val obj = raw as? JsonObject ?: error("Missing context")
            require(obj.keys == keys)
            for (key in listOf("policy_version", "binding", "request_epoch", "generated_at", "valid_until",
                "level", "track", "local_day", "timezone_name", "goal_state", "time_local", "time_source",
                "time_reason", "phase", "reason", "action", "calibration_version")) {
                val value = obj.getValue(key)
                if (value != JsonNull) require(value is JsonPrimitive && value.isString)
            }
            require(obj["coverage_limits"] is JsonArray && (obj.getValue("coverage_limits") as JsonArray)
                .all { it is JsonPrimitive && it.isString })
            for (key in listOf("version", "revision", "completed_parts", "total_parts",
                "verified_today_xp", "goal_xp", "lesson_order")) {
                val value = obj.getValue(key)
                if (value != JsonNull) require(value is JsonPrimitive && !value.isString && value.intOrNull != null)
            }
            for (key in listOf("plan_completed", "dispatch_allowed", "action_requires_authorization")) {
                val value = obj.getValue(key)
                if (value != JsonNull) require(value is JsonPrimitive && !value.isString && value.booleanOrNull != null)
            }
            val c = json.decodeFromJsonElement(serializer(), obj)
            require(c.version == 1 && c.policyVersion == "smart-widget-context-v1")
            require(!c.dispatchAllowed && c.actionRequiresAuthorization)
            require(c.binding.matches(Regex("[0-9a-f]{64}")))
            require(UUID.fromString(c.requestEpoch).toString() == c.requestEpoch && c.revision >= 0)
            require(c.level.matches(Regex("n?hsk[1-4]")))
            require(c.track == if (c.level.startsWith("n")) "hsk30" else "hsk20")
            val generated = Instant.parse(c.generatedAt)
            val until = Instant.parse(c.validUntil)
            require(generated < until)
            require((c.localDay == null) == (c.timezoneName == null))
            if (c.localDay != null) {
                require(c.timezoneName in ZoneId.getAvailableZoneIds())
                val zone = ZoneId.of(c.timezoneName)
                val day = LocalDate.parse(c.localDay)
                require(day.toString() == c.localDay && generated.atZone(zone).toLocalDate() == day)
                require(until <= day.plusDays(1).atStartOfDay(zone).toInstant())
            } else require(c.verifiedTodayXp == null && c.planCompleted == null &&
                c.goalState == "unknown" && c.phase in setOf("neutral", "unavailable"))
            require((c.completedParts == null) == (c.totalParts == null))
            require(c.completedParts == null || c.completedParts >= 0 && c.totalParts!! > 0 && c.completedParts <= c.totalParts)
            require(c.verifiedTodayXp == null || c.verifiedTodayXp >= 0)
            require(c.goalXp == null || c.goalXp > 0)
            require(c.goalState in setOf("met", "not_proven", "unknown"))
            require(c.timeSource in setOf("manual", "saved", "habit", "unknown"))
            require((c.timeLocal == null) == (c.timeSource == "unknown"))
            if (c.timeLocal != null) {
                require(c.timeLocal.matches(Regex("[0-9]{2}:[0-9]{2}")))
                LocalTime.parse(c.timeLocal)
            }
            require(c.phase in setOf("neutral", "before_study", "study_time_reached", "completed", "paused", "quiet", "unavailable"))
            require(c.action in setOf("course", "continue", "foundation", "none"))
            if (c.action == "continue") require(c.completedParts != null && c.totalParts != null && c.lessonOrder != null &&
                c.lessonOrder == c.completedParts + 1 && c.lessonOrder <= c.totalParts && c.phase != "unavailable")
            else require(c.lessonOrder == null)
            if (c.phase in setOf("before_study", "study_time_reached")) require(c.timeLocal != null)
            if (c.goalState == "met") require(c.goalXp != null && c.verifiedTodayXp != null && c.verifiedTodayXp >= c.goalXp)
            if (c.phase == "completed") require(c.goalState == "met" || c.planCompleted == true ||
                c.totalParts != null && c.completedParts == c.totalParts)
            c
        }.getOrNull()

        fun current(session: WidgetSession, now: ZonedDateTime): WidgetPersonalContext? {
            if (!session.linked) return null
            val snapshot = session.snapshot ?: return null
            val c = parse(snapshot.personalContext) ?: return null
            return c.takeIf { session.contextBinding == it.binding && it.revision >= session.contextRevision &&
                it.generatedMillis >= session.contextGeneratedMillis && it.current(snapshot, session.epoch, now) }
        }
    }
}
