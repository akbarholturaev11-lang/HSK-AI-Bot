package com.pomp.hskai.core.notify

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.*
import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.*
import com.pomp.hskai.widget.WidgetStore
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.runTest
import org.junit.Assert.*
import org.junit.Test

private class SettingPrefs : DataStore<Preferences> {
    override val data = MutableStateFlow(emptyPreferences())
    override suspend fun updateData(transform: suspend (Preferences) -> Preferences): Preferences =
        transform(data.value).also { data.value = it }
}

class SmartPreferenceBridgeTest {
    private class Fixture {
        val disk = SettingPrefs()
        var store = WidgetStore(disk)
        var generation = 1L
        var online = true
        var lostAck = false
        var stops = 0
        var queued = 0
        var reads = 0
        var pref = SmartStudyPreferences(true, 0, null, "auto", null,
            SmartStudyPreferenceChannels(SmartStudyPhonePreference("unknown")))
        val bodies = mutableListOf<SmartStudyPreferencePatch>()
        val receipts = mutableMapOf<String, Pair<SmartStudyPreferencePatch, SmartStudyPreferenceAck>>()
        var beforePatch: suspend (SmartStudyPreferencePatch) -> Unit = {}
        suspend fun setup() { store.linked() }
        fun bridge() = SmartPreferenceBridge(store,
            session = { ApiResult.Success(AuthRepository.AuthenticatedSession("synthetic", generation)) },
            commitCurrent = { gen, action -> if (gen == generation) { action(); true } else false },
            invalidate = { if (it == generation) { generation++; store.clear() } },
            read = {
                reads++
                if (online) ApiResult.Success(pref) else ApiResult.Failure(ApiError.Offline)
            },
            patch = { _, body ->
                bodies += body
                beforePatch(body)
                val old = receipts[body.requestId]
                if (old != null) {
                    assertEquals(old.first, body)
                    ApiResult.Success(old.second)
                } else if (body.expectedRevision != pref.revision) {
                    ApiResult.Failure(ApiError.Server("smart_revision_conflict", 0))
                } else {
                    pref = pref.copy(revision = pref.revision + 1,
                        timezoneName = body.timezoneName ?: pref.timezoneName,
                        channels = body.studyEnabled?.let { SmartStudyPreferenceChannels(
                            SmartStudyPhonePreference(if (it) "on" else "off")) } ?: pref.channels)
                    val ack = SmartStudyPreferenceAck(true, body.requestId, pref.revision, false)
                    receipts[body.requestId] = body to ack
                    if (lostAck) ApiResult.Failure(ApiError.Timeout) else ApiResult.Success(ack)
                }
            },
            stopLocal = { stops++ }, queueSync = { queued++ }, zone = { "Asia/Tashkent" })
    }

    @Test fun `first use initializes actual zone without importing legacy local ON`() = runTest {
        val f = Fixture(); f.setup(); f.store.setReminder(true)
        assertTrue(f.bridge().sync() is ApiResult.Success)
        assertEquals("Asia/Tashkent", f.pref.timezoneName)
        assertEquals("unknown", f.pref.channels!!.android!!.thisDeviceConsent)
        assertNull(f.bodies.single().studyEnabled)
        assertNull(f.pref.masterEnabled)
        assertTrue(f.store.read().reminderEnabled)
        f.bridge().sync(); assertEquals(1, f.bodies.size)
    }

    @Test fun `existing manual zone and time mode are preserved on explicit phone intent`() = runTest {
        val f = Fixture(); f.setup()
        f.pref = f.pref.copy(timeMode = "manual_locked", timezoneName = "Asia/Tokyo")
        f.bridge().sync(); assertTrue(f.bodies.isEmpty())
        f.bridge().setEnabled(true)
        assertNull(f.bodies.single().timezoneName)
        assertEquals("manual_locked", f.pref.timeMode)
        assertEquals("Asia/Tokyo", f.pref.timezoneName)
        assertTrue(f.store.read().reminderEnabled)
    }

    @Test fun `offline OFF stops now and survives process restart without a widget`() = runTest {
        val f = Fixture(); f.setup(); f.store.setReminder(true); f.online = false
        assertTrue(f.bridge().setEnabled(false) is ApiResult.Failure)
        assertFalse(f.store.read().reminderEnabled)
        assertEquals(1, f.stops); assertEquals(1, f.queued)
        assertNotNull(f.store.read().pendingStudyPreference)
        f.store = WidgetStore(f.disk); f.online = true
        f.bridge().sync()
        assertEquals("off", f.pref.channels!!.android!!.thisDeviceConsent)
        assertNull(f.store.read().pendingStudyPreference)
    }

    @Test fun `lost response retries original UUID body and revision without another mutation`() = runTest {
        val f = Fixture(); f.setup(); f.lostAck = true
        f.bridge().setEnabled(true)
        assertFalse(f.store.read().reminderEnabled)
        f.store = WidgetStore(f.disk); f.lostAck = false
        f.bridge().sync()
        assertEquals(2, f.bodies.size); assertEquals(f.bodies[0], f.bodies[1])
        assertEquals(1, f.pref.revision); assertTrue(f.store.read().reminderEnabled)
    }

    @Test fun `pending ON does not enable posting before acknowledgement`() = runTest {
        val f = Fixture(); f.setup()
        val sent = CompletableDeferred<Unit>(); val release = CompletableDeferred<Unit>()
        f.beforePatch = { sent.complete(Unit); release.await() }
        val request = async { f.bridge().setEnabled(true) }
        sent.await(); assertFalse(f.store.read().reminderEnabled)
        release.complete(Unit); request.await()
        assertTrue(f.store.read().reminderEnabled)
    }

    @Test fun `late ON acknowledgement cannot erase a newer explicit OFF`() = runTest {
        val f = Fixture(); f.setup(); val bridge = f.bridge()
        val sent = CompletableDeferred<Unit>(); val release = CompletableDeferred<Unit>()
        f.beforePatch = { if (it.studyEnabled == true) { sent.complete(Unit); release.await() } }
        val on = async { bridge.setEnabled(true) }; sent.await()
        val off = async { bridge.setEnabled(false) }
        kotlinx.coroutines.yield()
        assertFalse(f.store.read().reminderEnabled)
        release.complete(Unit); on.await(); off.await()
        assertFalse(f.store.read().reminderEnabled)
        assertEquals("off", f.pref.channels!!.android!!.thisDeviceConsent)
        assertNull(f.store.read().pendingStudyPreference)
    }

    @Test fun `global OFF cannot be cleared by phone ON or timezone initialization`() = runTest {
        val f = Fixture(); f.setup(); f.pref = f.pref.copy(masterEnabled = false)
        f.bridge().sync()
        assertFalse(f.pref.masterEnabled!!); assertNull(f.bodies.single().studyEnabled)
        val result = f.bridge().setEnabled(true) as ApiResult.Failure
        assertEquals("smart_master_off", (result.error as ApiError.Server).code)
        assertEquals(1, f.bodies.size)
        assertFalse(f.store.read().reminderEnabled)
    }

    @Test fun `stale ON is not rebased over a concurrent global OFF`() = runTest {
        val f = Fixture(); f.setup()
        f.beforePatch = { f.pref = f.pref.copy(revision = 1, masterEnabled = false) }
        assertTrue(f.bridge().setEnabled(true) is ApiResult.Failure)
        assertEquals(1, f.bodies.size); assertNull(f.store.read().pendingStudyPreference)
        assertFalse(f.store.read().reminderEnabled)
    }

    @Test fun `OFF safely replaces only a definitely refused revision not an unknown attempt`() = runTest {
        val f = Fixture(); f.setup()
        f.beforePatch = { if (f.bodies.size == 1) f.pref = f.pref.copy(revision = 3) }
        assertTrue(f.bridge().setEnabled(false) is ApiResult.Success)
        assertEquals(2, f.bodies.size)
        assertNotEquals(f.bodies[0].requestId, f.bodies[1].requestId)
        assertEquals(3, f.bodies[1].expectedRevision)
        assertEquals("off", f.pref.channels!!.android!!.thisDeviceConsent)
    }

    @Test fun `foreground confirms worker handled intent against current effective state`() = runTest {
        val f = Fixture(); f.setup(); val bridge = f.bridge()
        val epoch = f.store.read().epoch
        f.store.requestStudyPreference(epoch, true)
        assertTrue(bridge.sync(epoch) is ApiResult.Success)
        assertNull(f.store.read().pendingStudyPreference)
        assertTrue(bridge.sync(epoch, true) is ApiResult.Success)
        assertEquals(1, f.bodies.size)
        f.pref = f.pref.copy(revision = 2, masterEnabled = false)
        val result = bridge.sync(epoch, true) as ApiResult.Failure
        assertEquals("smart_master_off", (result.error as ApiError.Server).code)
        assertFalse(f.store.read().reminderEnabled)
        assertEquals(1, f.bodies.size)
    }

    @Test fun `old account callback and queued epoch cannot affect replacement login`() = runTest {
        val f = Fixture(); f.setup(); val oldEpoch = f.store.read().epoch
        val sent = CompletableDeferred<Unit>(); val release = CompletableDeferred<Unit>()
        f.beforePatch = { sent.complete(Unit); release.await() }
        val request = async { f.bridge().setEnabled(true, oldEpoch) }; sent.await()
        f.generation++; f.store.clear(); f.store.linked()
        release.complete(Unit); assertTrue(request.await() is ApiResult.Failure)
        assertFalse(f.store.read().reminderEnabled); assertNull(f.store.read().pendingStudyPreference)
        val count = f.reads
        f.bridge().sync(oldEpoch)
        assertEquals(count, f.reads)
        assertTrue(f.bridge().setEnabled(true, oldEpoch) is ApiResult.Failure)
    }

    @Test fun `foreground uses known server OFF while unknown legacy consent is left alone`() = runTest {
        val f = Fixture(); f.setup(); f.store.setReminder(true)
        f.pref = f.pref.copy(timezoneName = "Asia/Tashkent",
            channels = SmartStudyPreferenceChannels(SmartStudyPhonePreference("off")))
        f.bridge().sync(); assertFalse(f.store.read().reminderEnabled)
        assertTrue(f.bodies.isEmpty()); assertTrue(f.stops > 0)
    }
}
