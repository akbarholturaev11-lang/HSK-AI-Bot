package com.pomp.hskai.core.notify

import com.pomp.hskai.R
import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.SmartStudyPreferenceAck
import com.pomp.hskai.data.api.SmartStudyPreferencePatch
import com.pomp.hskai.data.api.SmartStudyPreferences
import com.pomp.hskai.widget.WidgetStore
import java.time.ZoneId
import java.util.UUID
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/** Current-device intent only. Passive reads and OS permission never grant consent. */
internal class SmartPreferenceBridge(
    private val store: WidgetStore,
    private val session: suspend () -> ApiResult<AuthRepository.AuthenticatedSession>,
    private val commitCurrent: suspend (Long, suspend () -> Unit) -> Boolean,
    private val invalidate: suspend (Long) -> Unit,
    private val read: suspend (String) -> ApiResult<SmartStudyPreferences>,
    private val patch: suspend (String, SmartStudyPreferencePatch) -> ApiResult<SmartStudyPreferenceAck>,
    private val stopLocal: suspend () -> Unit,
    private val queueSync: (String) -> Unit = {},
    private val zone: () -> String = { ZoneId.systemDefault().id },
) {
    private val mutex = Mutex()

    suspend fun setEnabled(enabled: Boolean, expectedEpoch: String? = null): ApiResult<Unit> {
        val local = store.read()
        if (!local.linked || expectedEpoch != null && expectedEpoch != local.epoch)
            return ApiResult.Failure(ApiError.SessionExpired)
        val intent = store.requestStudyPreference(local.epoch, enabled)
            ?: return ApiResult.Failure(ApiError.SessionExpired)
        if (!intent.enabled && store.read().epoch == local.epoch) stopLocal()
        queueSync(local.epoch)
        return sync(local.epoch, enabled)
    }

    suspend fun sync(expectedEpoch: String? = null, requestedEnabled: Boolean? = null): ApiResult<Unit> = mutex.withLock {
        val local = store.read()
        if (!local.linked || expectedEpoch != null && expectedEpoch != local.epoch)
            return@withLock if (requestedEnabled == null) ApiResult.Success(Unit) else ApiResult.Failure(ApiError.SessionExpired)
        val proof = when (val result = session()) {
            is ApiResult.Success -> result.value
            is ApiResult.Failure -> return@withLock result
        }
        val bearer = "Bearer ${proof.token}"
        suspend fun current(): Boolean {
            var same = false
            return commitCurrent(proof.generation) { same = store.read().epoch == local.epoch } && same
        }
        suspend fun failed(error: ApiError): ApiResult<Unit> {
            if (error is ApiError.SessionExpired) invalidate(proof.generation)
            if ((error as? ApiError.Server)?.code == "smart_account_deletion_pending") {
                commitCurrent(proof.generation) {
                    val latest = store.read()
                    if (latest.epoch == local.epoch) {
                        latest.pendingStudyPreference?.takeIf { it.enabled }?.let {
                            store.finishStudyPreference(local.epoch, it.requestId, false)
                        }
                        store.reconcileStudyPreference(local.epoch, latest.studyPreferenceRevision, false)
                        stopLocal()
                    }
                }
            }
            return ApiResult.Failure(error)
        }
        suspend fun stopIfCurrent() {
            commitCurrent(proof.generation) {
                if (store.read().epoch == local.epoch && !store.read().reminderEnabled) stopLocal()
            }
        }
        suspend fun load(): ApiResult<SmartStudyPreferences> = read(bearer)
        fun confirmed(pref: SmartStudyPreferences): ApiResult<Unit> = when {
            requestedEnabled == true && pref.masterEnabled == false -> ApiResult.Failure(
                ApiError.Server("smart_master_off", R.string.smart_preferences_account_off))
            requestedEnabled != null && pref.channels?.android?.thisDeviceConsent !=
                if (requestedEnabled) "on" else "off" -> ApiResult.Failure(ApiError.Unknown)
            else -> ApiResult.Success(Unit)
        }
        // One safe OFF rebase after a definite CAS refusal; uncertain bodies
        // keep their original UUID/revision. ON is never automatically rebased.
        for (attempt in 0..1) {
            if (!current()) return@withLock ApiResult.Failure(ApiError.SessionExpired)
            val pref = when (val result = load()) {
                is ApiResult.Success -> result.value
                is ApiResult.Failure -> return@withLock failed(result.error)
            }
            if (!pref.valid()) return@withLock ApiResult.Failure(ApiError.Unknown)
            if (!current()) return@withLock ApiResult.Failure(ApiError.SessionExpired)
            val latest = store.read().pendingStudyPreference
            if (latest?.enabled == true && pref.masterEnabled == false) {
                commitCurrent(proof.generation) {
                    store.finishStudyPreference(local.epoch, latest.requestId, false)
                    store.reconcileStudyPreference(local.epoch, pref.revision, false)
                }
                stopIfCurrent()
                return@withLock ApiResult.Failure(ApiError.Server("smart_master_off", R.string.smart_preferences_account_off))
            }
            val observedZone = zone().takeIf { it in ZoneId.getAvailableZoneIds() }
            if (latest == null && pref.timezoneName != null) {
                commitCurrent(proof.generation) {
                    store.reconcileStudyPreference(local.epoch, pref.revision, pref.phoneEnabled())
                }
                stopIfCurrent()
                return@withLock confirmed(pref)
            }
            val frozen = latest?.let {
                store.freezeStudyPreference(local.epoch, it.requestId, pref.revision,
                    observedZone.takeIf { pref.timezoneName == null })
            }
            if (latest != null && frozen == null) return@withLock ApiResult.Success(Unit)
            if (frozen == null && observedZone == null) return@withLock ApiResult.Success(Unit)
            val body = if (frozen != null) SmartStudyPreferencePatch(frozen.requestId,
                frozen.expectedRevision!!, frozen.enabled, frozen.timezoneName)
                else SmartStudyPreferencePatch(UUID.randomUUID().toString(), pref.revision, timezoneName = observedZone)
            if (!current()) return@withLock ApiResult.Failure(ApiError.SessionExpired)
            when (val result = patch(bearer, body)) {
                is ApiResult.Failure -> {
                    if ((result.error as? ApiError.Server)?.code == "smart_revision_conflict") {
                        if (frozen != null) commitCurrent(proof.generation) {
                            if (frozen.enabled) store.finishStudyPreference(local.epoch, frozen.requestId, frozen.previousEnabled)
                            else if (attempt == 0 && store.read().pendingStudyPreference?.requestId == frozen.requestId)
                                store.requestStudyPreference(local.epoch, false)
                        }
                        if (frozen?.enabled == true) {
                            val fresh = load()
                            if (fresh is ApiResult.Success && fresh.value.valid()) commitCurrent(proof.generation) {
                                store.reconcileStudyPreference(local.epoch, fresh.value.revision, fresh.value.phoneEnabled())
                            }
                            stopIfCurrent()
                            return@withLock failed(result.error)
                        }
                        if (attempt == 0) continue
                    }
                    return@withLock failed(result.error)
                }
                is ApiResult.Success -> {
                    val ack = result.value
                    if (!ack.ok || ack.dispatchAllowed || ack.requestId != body.requestId ||
                        ack.appliedRevision != body.expectedRevision + 1)
                        return@withLock ApiResult.Failure(ApiError.Unknown)
                    if (!current()) return@withLock ApiResult.Failure(ApiError.SessionExpired)
                    if (frozen != null) commitCurrent(proof.generation) {
                        store.finishStudyPreference(local.epoch, frozen.requestId, frozen.enabled)
                        store.reconcileStudyPreference(local.epoch, ack.appliedRevision, null)
                    }
                    // Fetch fresh effective state: a concurrent global OFF wins
                    // even when the original command has an immutable ACK.
                    var finalState: SmartStudyPreferences? = null
                    when (val fresh = load()) {
                        is ApiResult.Success -> if (fresh.value.valid()) {
                            commitCurrent(proof.generation) {
                                store.reconcileStudyPreference(local.epoch, fresh.value.revision, fresh.value.phoneEnabled())
                                finalState = fresh.value
                            }
                        }
                        is ApiResult.Failure -> if (fresh.error is ApiError.SessionExpired) return@withLock failed(fresh.error)
                    }
                    stopIfCurrent()
                    return@withLock finalState?.let(::confirmed) ?: ApiResult.Success(Unit)
                }
            }
        }
        ApiResult.Failure(ApiError.Unknown)
    }
}
