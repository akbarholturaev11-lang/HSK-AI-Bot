package com.pomp.hskai.core.notify

import android.content.Context
import android.app.NotificationManager
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.*
import com.pomp.hskai.widget.WidgetStore
import java.io.File
import java.time.ZonedDateTime
import java.util.UUID
import kotlinx.coroutines.*
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith

/** Isolated .qa app only, synthetic network; no learner account or actual FCM. */
@RunWith(AndroidJUnit4::class)
class SmartStudyProtocolTest {
    @Test fun concurrentTriggersPersistBeforeActualNotify() = runBlocking {
        checkProtocol(expectPermission=true)
    }

    @Test fun deniedPermissionNeverReachesActualNotify() = runBlocking {
        checkProtocol(expectPermission=false)
    }

    private suspend fun checkProtocol(expectPermission: Boolean) {
        val context=ApplicationProvider.getApplicationContext<Context>()
        assumeTrue(context.packageName.endsWith(".qa"))
        assertEquals(expectPermission,StudyNotifications.canPost(context))
        val file=File(context.cacheDir,"smart-protocol-${UUID.randomUUID()}.preferences_pb")
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.IO)
        val store=WidgetStore(PreferenceDataStoreFactory.create(scope=scope,produceFile={file}))
        val job=UUID.randomUUID().toString()
        val grant=UUID.randomUUID().toString()
        var claims=0; var posts=0
        val receipts=mutableListOf<SmartStudyReceipt>()
        store.linked(); store.setReminder(true)
        val bridge=SmartStudyBridge(store,
            session={ ApiResult.Success(AuthRepository.AuthenticatedSession("synthetic-no-network",1)) },
            commitCurrent={ _, block -> block(); true },
            mode={ ApiResult.Success(SmartStudyMode(true,1,false,true)) },
            capability={ ApiResult.Success(SmartStudyCapability(true,1,1,1,true,expectPermission,true)) },
            observe={ _, _ -> error("unexpected observation") },
            due={ ApiResult.Success(SmartStudyDue(true,1,false,job,2,3,1)) },
            claim={ _, _, body ->
                claims++
                val now=ZonedDateTime.now()
                ApiResult.Success(SmartStudyGrant(true,1,true,job,grant,body.localEpoch,
                    now.toInstant().toString(),now.plusMinutes(1).toInstant().toString(),2,3,1,
                    now.toLocalDate().toString(),now.zone.id,"hsk1",5))
            },
            receipt={ _, _, body -> receipts+=body; ApiResult.Success(SmartStudyReceiptAck(true,1)) },
            permission={ StudyNotifications.canPost(context) },
            post={
                posts++
                val persisted=runBlocking { store.read() }
                assertEquals(StudyPostOutcome.UNKNOWN.wire,persisted.studyOperations.single().outcome)
                assertEquals(grant,persisted.studyOperations.single().grantId)
                assertEquals(ZonedDateTime.now().toLocalDate().toString(),persisted.lastReminderDay)
                StudyNotifications.postReminderOutcome(context,Reminder.DAILY_GOAL)
            },elapsed=android.os.SystemClock::elapsedRealtime)
        try {
            coroutineScope { listOf(async { bridge.run() },async { bridge.run() }).awaitAll() }
            assertEquals(if(expectPermission) 1 else 0,claims)
            assertEquals(if(expectPermission) 1 else 0,posts)
            if(expectPermission) {
                assertEquals(StudyPostOutcome.POSTED_UNVERIFIED.wire,receipts.single().outcome)
                assertTrue(context.getSystemService(NotificationManager::class.java).activeNotifications.any { it.id==4201 })
                assertTrue(store.read().studyOperations.single().acknowledged)
            } else {
                assertTrue(receipts.isEmpty())
                assertEquals(StudyPostOutcome.DECLINED_BEFORE_POST,
                    StudyNotifications.postReminderOutcome(context,Reminder.DAILY_GOAL))
            }
        } finally {
            StudyNotifications.cancelReminder(context)
            scope.coroutineContext[Job]!!.cancelAndJoin()
            file.delete()
        }
    }
}
