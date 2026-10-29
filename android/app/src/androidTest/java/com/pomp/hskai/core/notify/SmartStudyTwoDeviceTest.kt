package com.pomp.hskai.core.notify

import android.content.Context
import android.app.NotificationManager
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import com.pomp.hskai.core.network.OriginGuardInterceptor
import com.pomp.hskai.data.api.AndroidSmartReminderApi
import com.pomp.hskai.widget.WidgetStore
import java.io.File
import java.net.URI
import java.security.KeyStore
import java.security.cert.CertificateFactory
import java.util.TimeZone
import java.util.UUID
import javax.net.ssl.SSLContext
import javax.net.ssl.TrustManagerFactory
import javax.net.ssl.X509TrustManager
import kotlinx.coroutines.*
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory

/** Driver-owned loopback TLS/native SQL fixture only; never a real learner/FCM. */
@RunWith(AndroidJUnit4::class)
class SmartStudyTwoDeviceTest {
    @Test fun selectedJobUsesLiveNativeHttpAndDurableLocalGuard() = runBlocking {
        val context=ApplicationProvider.getApplicationContext<Context>()
        check(context.packageName.endsWith(".qa"))
        val args=InstrumentationRegistry.getArguments()
        val fixture=File(args.getString("smart_fixture") ?: error("Explicit fixture required"))
        check(fixture.parentFile?.canonicalFile==context.cacheDir.canonicalFile &&
            fixture.name.startsWith("smart-two-") && fixture.name.endsWith(".json"))
        val input=JSONObject(fixture.readText())
        val origin=input.getString("origin")
        val uri=URI(origin)
        check(uri.scheme=="https" && uri.host=="127.0.0.1" && uri.port in 1024..65535 &&
            uri.userInfo==null && uri.query==null && uri.fragment==null && uri.path.isNullOrEmpty())
        val cert=CertificateFactory.getInstance("X.509").generateCertificate(input.getString("certificate_pem").byteInputStream())
        val keys=KeyStore.getInstance(KeyStore.getDefaultType()).apply { load(null); setCertificateEntry("owned-loopback",cert) }
        val trust=TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm()).apply { init(keys) }
        val manager=trust.trustManagers.single() as X509TrustManager
        val tls=SSLContext.getInstance("TLS").apply { init(null,arrayOf(manager),null) }
        // Trust only this generated fixture certificate; keep normal hostname checks and origin pin.
        val client=OkHttpClient.Builder().sslSocketFactory(tls.socketFactory,manager)
            .addInterceptor(OriginGuardInterceptor(origin)).followRedirects(false).followSslRedirects(false).build()
        val api=Retrofit.Builder().baseUrl("$origin/").client(client)
            .addConverterFactory(Json { ignoreUnknownKeys=true; explicitNulls=false }
                .asConverterFactory("application/json".toMediaType())).build().create(AndroidSmartReminderApi::class.java)
        val token=input.getString("access_token")
        val oldZone=TimeZone.getDefault()
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.IO)
        val file=File(context.cacheDir,"two-device-${UUID.randomUUID()}.preferences_pb")
        val store=WidgetStore(PreferenceDataStoreFactory.create(scope=scope,produceFile={file}))
        var posts=0
        TimeZone.setDefault(TimeZone.getTimeZone("Etc/UTC"))
        StudyNotifications.cancelReminder(context)
        try {
            assertTrue(StudyNotifications.canPost(context))
            store.linked(); store.setReminder(true)
            val bridge=SmartStudyBridge(store,
                session={ ApiResult.Success(AuthRepository.AuthenticatedSession(token,1)) },
                commitCurrent={ _, block -> block(); true },
                mode={ apiCall { api.mode(it) } },capability={ apiCall { api.capability(it) } },
                observe={ bearer,body -> apiCall { api.observe(bearer,body) } },
                due={ apiCall { api.due(it) } },claim={ bearer,job,body -> apiCall { api.claim(bearer,job,body) } },
                receipt={ bearer,job,body -> apiCall { api.receipt(bearer,job,body) } },
                permission={ StudyNotifications.canPost(context) },
                post={
                    posts++
                    val saved=runBlocking { store.read() }
                    assertEquals(StudyPostOutcome.UNKNOWN.wire,saved.studyOperations.single().outcome)
                    StudyNotifications.postReminderOutcome(context,Reminder.DAILY_GOAL)
                },elapsed=android.os.SystemClock::elapsedRealtime)
            coroutineScope {
                listOf(async { bridge.run() },async { bridge.run(SmartStudyHint(input.getString("job_id"),input.getString("local_day"))) }).awaitAll()
            }
            val expected=input.getInt("expected_posts")
            assertEquals(expected,posts)
            assertEquals(expected,context.getSystemService(NotificationManager::class.java).activeNotifications.count { it.id==4201 })
            if(expected==1) assertTrue(store.read().studyOperations.single().acknowledged)
            assertTrue(store.read().serverStudyOnly)
            println("SMART_POSTS=$posts")
        } finally {
            StudyNotifications.cancelReminder(context)
            TimeZone.setDefault(oldZone)
            scope.coroutineContext[Job]!!.cancelAndJoin()
            file.delete()
            client.connectionPool.evictAll()
            client.dispatcher.executorService.shutdown()
        }
    }
}
