package com.pomp.hskai.core.diagnostics

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.POST

const val DIAG_SCHEMA = "diag.v1"

/**
 * One `diag.v1` event: codes, versions and time only. No message, stack, URL,
 * token, account or device identifier — the server takes the owner from the
 * bearer session and computes the fingerprint and severity itself.
 */
@Serializable
data class DiagnosticEventDto(
    @SerialName("event_id") val eventId: String,
    @SerialName("client_time") val clientTime: Long,
    @SerialName("app_version") val appVersion: String,
    @SerialName("build") val build: Long,
    @SerialName("channel") val channel: String,
    @SerialName("feature_code") val featureCode: String,
    @SerialName("failure_code") val failureCode: String,
    @SerialName("site_code") val siteCode: String,
    @SerialName("outcome") val outcome: String,
    @SerialName("category") val category: String? = null,
)

@Serializable
data class DiagnosticBatchDto(
    @SerialName("schema") val schema: String,
    @SerialName("events") val events: List<DiagnosticEventDto>,
)

@Serializable
data class DiagnosticIntakeResponse(
    @SerialName("accepted") val accepted: Int = 0,
    @SerialName("paused") val paused: Boolean = false,
)

/** A queued event, stamped with the owner (the signed-in bearer session ID). */
@Serializable
data class QueuedDiagnostic(
    @SerialName("owner") val owner: String,
    @SerialName("queued_at") val queuedAt: Long,
    @SerialName("event") val event: DiagnosticEventDto,
)

@Serializable
data class DiagnosticQueueFile(
    @SerialName("entries") val entries: List<QueuedDiagnostic> = emptyList(),
)

/** The crash handler's synchronous ≤ 1 KB record, turned into an event on the next start. */
@Serializable
data class CrashRecordDto(
    @SerialName("owner") val owner: String,
    @SerialName("at") val at: Long,
    @SerialName("feature") val feature: String,
    @SerialName("site") val site: String,
    @SerialName("category") val category: String,
)

interface AndroidDiagnosticsApi {
    @POST("api/v3/android/diagnostics")
    suspend fun send(
        @Header("Authorization") bearer: String,
        @Body batch: DiagnosticBatchDto,
    ): Response<DiagnosticIntakeResponse>
}
