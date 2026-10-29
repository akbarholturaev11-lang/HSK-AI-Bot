package com.pomp.hskai.core.notify

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.*
import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.*
import com.pomp.hskai.widget.WidgetStore
import com.pomp.hskai.widget.WidgetSnapshot
import java.time.ZonedDateTime
import java.util.UUID
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.runTest
import org.junit.Assert.*
import org.junit.Test

private class StudyPrefs : DataStore<Preferences> {
    override val data = MutableStateFlow(emptyPreferences())
    override suspend fun updateData(transform: suspend (Preferences) -> Preferences): Preferences =
        transform(data.value).also { data.value = it }
}

class SmartStudyBridgeTest {
    private class Fixture {
        val prefs = StudyPrefs()
        var store = WidgetStore(prefs)
        val job = UUID.randomUUID().toString()
        val grantId = UUID.randomUUID().toString()
        var now = ZonedDateTime.parse("2026-10-29T21:00:00Z[Etc/UTC]")
        var elapsed = 1L
        var generation = 1L
        var allowed = true
        var posts = 0
        var claims = 0
        var observations = 0
        var required = true
        var modeFails = false
        var claimFails = false
        var ack = true
        var currentCap = SmartStudyCapability(true,1,1,1,true,true,true)
        var change: (SmartStudyGrant) -> SmartStudyGrant = { it }
        var onClaim: suspend () -> Unit = {}
        var onPost: () -> StudyPostOutcome = { StudyPostOutcome.POSTED_UNVERIFIED }
        val receipts = mutableListOf<SmartStudyReceipt>()
        suspend fun setup() { store.linked(); store.setReminder(true) }
        fun bridge() = SmartStudyBridge(store,
            session = { ApiResult.Success(AuthRepository.AuthenticatedSession("synthetic",1)) },
            commitCurrent = { gen, block -> if (gen == generation) { block(); true } else false },
            mode = { if (modeFails) ApiResult.Failure(ApiError.Offline) else ApiResult.Success(SmartStudyMode(true,1,false,required)) },
            capability = { ApiResult.Success(currentCap) },
            observe = { _, body ->
                observations++
                assertTrue(store.read().serverStudyOnly)
                ApiResult.Success(currentCap.copy(generation=currentCap.generation+1, protocolVersion=1,
                    autonomousDisabled=true,notificationsAllowed=body.notificationsAllowed,fresh=true))
            },
            due = { ApiResult.Success(SmartStudyDue(true,1,false,job,2,3,1)) },
            claim = { _, _, body ->
                claims++
                assertEquals(body.requestId,store.read().studyOperations.single().requestId)
                val grant = SmartStudyGrant(true,1,true,job,grantId,body.localEpoch,
                    now.toInstant().toString(),now.plusMinutes(5).toInstant().toString(),2,3,1,
                    now.toLocalDate().toString(),now.zone.id,"hsk1",5)
                onClaim()
                if (claimFails) ApiResult.Failure(ApiError.Offline) else ApiResult.Success(change(grant))
            },
            receipt = { _, _, body -> receipts += body; ApiResult.Success(SmartStudyReceiptAck(ack,1)) },
            permission = { allowed }, post = { posts++; onPost() }, clock = { now }, elapsed = { elapsed })
    }

    @Test fun `FCM and worker race shares one persisted claim day and notification`() = runTest {
        val f=Fixture(); f.setup(); val bridge=f.bridge()
        (1..20).map { async { bridge.run(if (it%2==0) SmartStudyHint(f.job,"2026-10-29") else null) } }.awaitAll()
        assertEquals(1,f.claims); assertEquals(1,f.posts)
        assertEquals(StudyPostOutcome.POSTED_UNVERIFIED.wire,f.receipts.single().outcome)
        assertTrue(f.store.read().studyOperations.single().acknowledged)
    }

    @Test fun `lost claim response and recreated process cannot regrant or replay`() = runTest {
        val f=Fixture(); f.setup(); f.claimFails=true
        assertEquals(SmartStudyBridge.Result.RETRY,f.bridge().run())
        f.store=WidgetStore(f.prefs); f.claimFails=false
        f.bridge().run()
        assertEquals(1,f.claims); assertEquals(0,f.posts); assertTrue(f.receipts.isEmpty())
    }

    @Test fun `receipt retries retain identity and outcome without a second notify`() = runTest {
        val f=Fixture(); f.setup(); f.ack=false
        f.bridge().run(); f.store=WidgetStore(f.prefs); f.ack=true
        f.bridge().run()
        assertEquals(1,f.posts); assertEquals(1,f.claims)
        assertEquals(1,f.receipts.toSet().size); assertEquals(2,f.receipts.size)
    }

    @Test fun `crash at OS boundary retains unknown and restart only sends receipt`() = runTest {
        val f=Fixture(); f.setup()
        f.onPost={ throw kotlinx.coroutines.CancellationException("synthetic process interruption") }
        try { f.bridge().run(); fail("interruption expected") } catch (_: kotlinx.coroutines.CancellationException) { }
        f.store=WidgetStore(f.prefs); f.store.setReminder(false); f.allowed=false
        f.bridge().run()
        assertEquals(1,f.posts); assertEquals(1,f.claims)
        assertEquals(StudyPostOutcome.UNKNOWN.wire,f.receipts.single().outcome)
    }

    @Test fun `local OFF arriving during claim refuses posting and keeps original receipt`() = runTest {
        val f=Fixture(); f.setup(); f.onClaim={ f.store.setReminder(false) }
        f.bridge().run()
        assertEquals(0,f.posts)
        assertEquals(StudyPostOutcome.DECLINED_BEFORE_POST.wire,f.receipts.single().outcome)
        f.ack=false; f.bridge().run(); assertEquals(1,f.claims)
    }

    @Test fun `permission revoked while claim waits refuses before OS call`() = runTest {
        val f=Fixture(); f.setup(); f.onClaim={ f.allowed=false }; f.bridge().run()
        assertEquals(0,f.posts)
        assertEquals(StudyPostOutcome.DECLINED_BEFORE_POST.wire,f.receipts.single().outcome)
    }

    @Test fun `logout relink cannot accept an old response into new account`() = runTest {
        val f=Fixture(); f.setup(); val epoch=f.store.read().epoch
        f.onClaim={ f.store.clear(); f.store.linked(); f.store.setReminder(true) }
        f.bridge().run()
        assertNotEquals(epoch,f.store.read().epoch); assertEquals(0,f.posts)
        assertTrue(f.store.read().studyOperations.isEmpty()); assertTrue(f.receipts.isEmpty())
    }

    @Test fun `auth generation change vetoes live grant without posting`() = runTest {
        val f=Fixture(); f.setup(); f.onClaim={ f.generation=2 }; f.bridge().run()
        assertEquals(0,f.posts); assertTrue(f.receipts.isEmpty())
    }

    @Test fun `expiry timezone day and malformed target never post`() = runTest {
        val changes: List<(SmartStudyGrant)->SmartStudyGrant> = listOf(
            { it.copy(expiresAt="2026-10-29T20:59:00Z") }, { it.copy(issuedAt="2026-10-29T21:01:00Z") },
            { it.copy(timezoneName="Asia/Tashkent") }, { it.copy(localDay="2026-10-28") },
            { it.copy(lessonOrder=0) }, { it.copy(courseKey=null) }, { it.copy(expiresAt="bad") })
        for (change in changes) {
            val f=Fixture(); f.setup(); f.change=change; f.bridge().run()
            assertEquals(0,f.posts)
            assertEquals(StudyPostOutcome.DECLINED_BEFORE_POST.wire,f.receipts.single().outcome)
        }
    }

    @Test fun `forged response bindings never become local posting authority`() = runTest {
        val changes: List<(SmartStudyGrant)->SmartStudyGrant> = listOf(
            { it.copy(version=2) }, { it.copy(jobId=UUID.randomUUID().toString()) },
            { it.copy(grantId="bad") }, { it.copy(localEpoch=UUID.randomUUID().toString()) },
            { it.copy(preferenceRevision=1) }, { it.copy(capabilityGeneration=2) }, { it.copy(grantEpoch=0) })
        for (change in changes) {
            val f=Fixture(); f.setup(); f.change=change; f.bridge().run(); f.bridge().run()
            assertEquals(0,f.posts); assertEquals(1,f.claims); assertTrue(f.receipts.isEmpty())
        }
    }

    @Test fun `monotonic elapsed deadline prevents rollback from extending grant`() = runTest {
        val f=Fixture(); f.setup(); f.onClaim={ f.elapsed+=300_000 }; f.bridge().run()
        assertEquals(0,f.posts)
    }

    @Test fun `notify exception is unknown and consumed local day is never refunded`() = runTest {
        val f=Fixture(); f.setup(); f.onPost={ error("synthetic OS failure") }; f.bridge().run(); f.bridge().run()
        assertEquals(1,f.posts); assertEquals(StudyPostOutcome.UNKNOWN.wire,f.receipts.single().outcome)
        assertEquals("2026-10-29",f.store.read().lastReminderDay)
    }

    @Test fun `completed goal detected before notify declines`() = runTest {
        val f=Fixture(); f.setup()
        f.onClaim={ f.store.save(WidgetSnapshot(1,"2026-10-29","Etc/UTC","hsk1",5,1,1,true,false), f.store.read().epoch) }
        f.bridge().run(); assertEquals(0,f.posts)
    }

    @Test fun `sticky mode persists over recreation false mode and local OFF`() = runTest {
        val f=Fixture(); f.setup(); f.allowed=false; f.bridge().run()
        f.store=WidgetStore(f.prefs); f.required=false; f.store.setReminder(false)
        assertEquals(SmartStudyBridge.Result.DONE,f.bridge().run())
        assertTrue(f.store.read().serverStudyOnly)
        assertFalse(f.store.remindOnce(f.store.read().epoch,"2026-10-29") { error("legacy") })
    }

    @Test fun `unknown mode cannot fall back but fresh non-migrated mode preserves legacy`() = runTest {
        val f=Fixture(); f.setup(); f.required=false; f.modeFails=true
        assertEquals(SmartStudyBridge.Result.RETRY,f.bridge().run())
        f.modeFails=false
        assertEquals(SmartStudyBridge.Result.LEGACY,f.bridge().run())
        assertFalse(f.store.read().serverStudyOnly); assertEquals(0,f.claims)
    }

    @Test fun `old hint and legacy hint never claim a different current job`() = runTest {
        val f=Fixture(); f.setup()
        f.bridge().run(SmartStudyHint(UUID.randomUUID().toString(),"2026-10-29"))
        f.bridge().run(SmartStudyHint(f.job,"2026-10-28"))
        f.bridge().run(legacyHint=true)
        assertEquals(0,f.claims); assertEquals(0,f.posts)
    }

    @Test fun `capability reporting follows durable autonomous disable and never grants consent`() = runTest {
        val f=Fixture(); f.setup(); f.currentCap=f.currentCap.copy(fresh=false,autonomousDisabled=null)
        f.allowed=false; f.bridge().run()
        assertEquals(1,f.observations); assertEquals(0,f.claims); assertEquals(0,f.posts)
    }

    @Test fun `FCM hint accepts only exact version canonical UUID and ISO day`() {
        val base=mapOf("version" to "1","job_id" to UUID.randomUUID().toString(),"local_day" to "2026-10-29")
        assertNotNull(SmartStudyHint.parse(base))
        for (bad in listOf(base+ ("version" to "2"),base+("job_id" to "bad"),base+("local_day" to "2026-02-30")))
            assertNull(SmartStudyHint.parse(bad))
    }
}
