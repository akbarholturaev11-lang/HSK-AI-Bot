package com.pomp.hskai.core.notify

import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.*
import com.pomp.hskai.widget.WidgetStore
import java.time.ZonedDateTime
import java.time.Instant
import java.time.Duration
import java.time.LocalDate
import java.util.UUID
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.Serializable

internal fun canonicalStudyUuid(value: String?): Boolean = value != null &&
    runCatching { UUID.fromString(value).toString() == value }.getOrDefault(false)

internal data class SmartStudyHint(val jobId: String, val localDay: String) {
    companion object {
        fun parse(data: Map<String, String>): SmartStudyHint? {
            if (data["version"] != "1" || !canonicalStudyUuid(data["job_id"])) return null
            val day = data["local_day"] ?: return null
            if (runCatching { LocalDate.parse(day).toString() == day }.getOrDefault(false).not()) return null
            return SmartStudyHint(data.getValue("job_id"), day)
        }
    }
}

/** No bearer, account id, private lesson data or cached posting authority. */
@Serializable data class SmartStudyOperation(
    val jobId: String,
    val requestId: String = UUID.randomUUID().toString(),
    val grantId: String? = null,
    val receiptId: String = UUID.randomUUID().toString(),
    val outcome: String = StudyPostOutcome.UNKNOWN.wire,
    val localDay: String? = null,
    val acknowledged: Boolean = false,
)

enum class StudyPostOutcome(val wire: String) {
    DECLINED_BEFORE_POST("client_declined_before_post"),
    POSTED_UNVERIFIED("client_posted_unverified"),
    UNKNOWN("client_outcome_unknown"),
}

/** One live bridge for FCM and WorkManager. Network IO never runs under auth/store locks. */
internal class SmartStudyBridge(
    private val store: WidgetStore,
    private val session: suspend () -> ApiResult<AuthRepository.AuthenticatedSession>,
    private val commitCurrent: suspend (Long, suspend () -> Unit) -> Boolean,
    private val mode: suspend (String) -> ApiResult<SmartStudyMode>,
    private val capability: suspend (String) -> ApiResult<SmartStudyCapability>,
    private val observe: suspend (String, SmartStudyObservation) -> ApiResult<SmartStudyCapability>,
    private val due: suspend (String) -> ApiResult<SmartStudyDue>,
    private val claim: suspend (String, String, SmartStudyClaim) -> ApiResult<SmartStudyGrant>,
    private val receipt: suspend (String, String, SmartStudyReceipt) -> ApiResult<SmartStudyReceiptAck>,
    private val permission: () -> Boolean,
    private val post: (String) -> StudyPostOutcome,
    private val clock: () -> ZonedDateTime = ZonedDateTime::now,
    private val elapsed: () -> Long,
) {
    enum class Result { LEGACY, DONE, RETRY }
    private val mutex = Mutex()

    suspend fun run(hint: SmartStudyHint? = null, legacyHint: Boolean = false): Result = mutex.withLock {
        val local = store.read()
        if (!local.linked || !canonicalStudyUuid(local.epoch)) return@withLock Result.DONE
        val proof = (session() as? ApiResult.Success)?.value ?: return@withLock Result.RETRY
        val bearer = "Bearer ${proof.token}"
        val state = (mode(bearer) as? ApiResult.Success)?.value ?: return@withLock Result.RETRY
        if (!state.ok || state.version != 1 || state.dispatchAllowed || state.serverClaimRequired == null) return@withLock Result.DONE
        var accepted = false
        if (!commitCurrent(proof.generation) {
            accepted = store.acceptStudyMode(local.epoch, state.serverClaimRequired)
        } || !accepted) return@withLock Result.DONE
        if (!store.read().serverStudyOnly) return@withLock if (hint == null) Result.LEGACY else Result.DONE
        if (legacyHint) return@withLock Result.DONE

        // Historical receipts are retryable even after local OFF/permission loss.
        for (op in store.read().studyOperations.filter { it.grantId != null && !it.acknowledged }) {
            var current = false
            commitCurrent(proof.generation) { current = store.read().epoch == local.epoch }
            if (!current) return@withLock Result.DONE
            val ack = (receipt(bearer, op.jobId, SmartStudyReceipt(grantId=op.grantId!!,
                receiptId=op.receiptId, localEpoch=local.epoch, outcome=op.outcome)) as? ApiResult.Success)?.value
            if (ack?.ok == true && ack.version == 1) store.acknowledgeStudy(local.epoch, op.requestId)
        }
        val allowed = permission()
        val old = (capability(bearer) as? ApiResult.Success)?.value ?: return@withLock Result.RETRY
        if (!old.ok || old.version != 1 || old.generation < 0) return@withLock Result.DONE
        val cap = if (old.fresh && old.protocolVersion == 1 && old.autonomousDisabled == true && old.notificationsAllowed == allowed) old
            else (observe(bearer, SmartStudyObservation(expectedGeneration=old.generation,
                notificationsAllowed=allowed)) as? ApiResult.Success)?.value ?: return@withLock Result.RETRY
        if (!cap.ok || cap.version != 1 || !cap.fresh || cap.protocolVersion != 1 ||
            cap.autonomousDisabled != true || cap.notificationsAllowed != true || cap.generation < 1 ||
            !store.read().reminderEnabled || !allowed) return@withLock Result.DONE
        val now = clock()
        if (hint != null && hint.localDay != now.toLocalDate().toString()) return@withLock Result.DONE
        val selected = (due(bearer) as? ApiResult.Success)?.value ?: return@withLock Result.RETRY
        val job = selected.jobId
        if (!selected.ok || selected.version != 1 || selected.dispatchAllowed || !canonicalStudyUuid(job) ||
            selected.preferenceRevision < 0 || selected.grantEpoch < 0 || selected.capabilityGeneration != cap.generation ||
            hint != null && hint.jobId != job) return@withLock Result.DONE
        var operation: SmartStudyOperation? = null
        if (!commitCurrent(proof.generation) { operation = store.reserveStudy(local.epoch, job!!, now.toLocalDate().toString()) }) return@withLock Result.DONE
        val op = operation ?: return@withLock Result.DONE
        val request = SmartStudyClaim(requestId=op.requestId, localEpoch=local.epoch,
            capabilityGeneration=cap.generation, preferenceRevision=selected.preferenceRevision, grantEpoch=selected.grantEpoch)
        val start = elapsed()
        val grant = (claim(bearer, job!!, request) as? ApiResult.Success)?.value ?: return@withLock Result.RETRY
        // Only this live HTTP response can authorize posting. Persisted journal entries cannot.
        if (!grant.ok || grant.version != 1 || !grant.dispatchAllowed || grant.jobId != job ||
            !canonicalStudyUuid(grant.grantId) || grant.localEpoch != local.epoch ||
            grant.preferenceRevision != request.preferenceRevision || grant.grantEpoch != request.grantEpoch ||
            grant.capabilityGeneration != request.capabilityGeneration) return@withLock Result.DONE
        commitCurrent(proof.generation) {
            store.postStudy(local.epoch, op.requestId, grant.grantId!!, grant.localDay,
                valid = {
                    runCatching {
                        val issued = Instant.parse(grant.issuedAt)
                        val expires = Instant.parse(grant.expiresAt)
                        val instant = clock()
                        val age = elapsed() - start
                        val ttl = Duration.between(issued, expires).toMillis()
                        expires > issued && issued <= instant.toInstant() && instant.toInstant() < expires &&
                            age >= 0 && age < ttl && instant.zone.id == now.zone.id &&
                            instant.zone.id == grant.timezoneName && grant.localDay == instant.toLocalDate().toString() &&
                            (hint == null || hint.localDay == grant.localDay) &&
                            !grant.courseKey.isNullOrBlank() && (grant.lessonOrder ?: 0) > 0 && permission()
                    }.getOrDefault(false)
                }, post = { post(grant.localDay.orEmpty()) })
        }
        // Retry later from the immutable persisted outcome; never repeat notify on ACK failure.
        val saved = store.read().takeIf { it.epoch == local.epoch }?.studyOperations?.find { it.requestId == op.requestId }
        if (saved?.grantId != null) {
            val ack = (receipt(bearer, job, SmartStudyReceipt(grantId=saved.grantId,
                receiptId=saved.receiptId, localEpoch=local.epoch, outcome=saved.outcome)) as? ApiResult.Success)?.value
            if (ack?.ok == true && ack.version == 1) store.acknowledgeStudy(local.epoch, op.requestId)
        }
        Result.DONE
    }
}
