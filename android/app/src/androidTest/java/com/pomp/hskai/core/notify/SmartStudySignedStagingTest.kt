package com.pomp.hskai.core.notify

import android.app.NotificationManager
import android.content.pm.ApplicationInfo
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.BuildConfig
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.ApiError
import java.io.File
import java.net.URL
import java.net.InetAddress
import javax.net.ssl.HttpsURLConnection
import java.time.LocalDate
import java.time.ZoneOffset
import java.util.TimeZone
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.runBlocking
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith

/** Explicit private synthetic staging fixture; ordinary signed app/TLS/auth/OS path. */
@RunWith(AndroidJUnit4::class)
class SmartStudySignedStagingTest {
    @Test fun qaTransportUsesOrdinaryTrustedHttps() {
        assumeTrue(BuildConfig.QA_BUILD && BuildConfig.BUILD_TYPE == "qaRelease")
        val app = ApplicationProvider.getApplicationContext<HskAiApplication>()
        check(BuildConfig.API_ORIGIN == "https://smart-qa-api-qa.up.railway.app")
        println("SMART_QA_DNS=" + InetAddress.getAllByName(URL(BuildConfig.API_ORIGIN).host)
            .joinToString { it.hostAddress.orEmpty() })
        val connection = URL(BuildConfig.API_ORIGIN + "/health").openConnection() as HttpsURLConnection
        connection.connectTimeout = 5_000
        connection.readTimeout = 5_000
        try {
            assertEquals(200, connection.responseCode)
            println("SMART_QA_TRUSTED_HTTPS_PASS")
        } catch (error: Exception) {
            fail("QA HTTPS transport: " + error.javaClass.simpleName)
        } finally { connection.disconnect() }
    }

    @Test fun signedAppRefreshesAndRunsItsActualCoordinator() = runBlocking {
        val app = ApplicationProvider.getApplicationContext<HskAiApplication>()
        assumeTrue(BuildConfig.QA_BUILD && BuildConfig.BUILD_TYPE == "qaRelease")
        check(BuildConfig.QA_BUILD && app.packageName == "com.pomp.hskai.qa")
        check(BuildConfig.BUILD_TYPE == "qaRelease" && !BuildConfig.DEBUG)
        check(app.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE == 0)
        check(BuildConfig.API_ORIGIN == "https://smart-qa-api-qa.up.railway.app")
        check(listOf(BuildConfig.FIREBASE_APP_ID, BuildConfig.FIREBASE_SENDER_ID,
            BuildConfig.FIREBASE_PROJECT_ID, BuildConfig.FIREBASE_API_KEY).all { it.isEmpty() })
        val args = InstrumentationRegistry.getArguments()
        val fixture = File(args.getString("smart_fixture") ?: error("Explicit private fixture required"))
        check(fixture.parentFile?.canonicalFile == app.getExternalFilesDir(null)?.canonicalFile &&
            fixture.name == "smart-signed-input.json")
        val input = JSONObject(fixture.readText())
        check(fixture.delete())
        check(input.getString("fixture_version") in setOf("smart-qa-synthetic-v1","smart-qa-synthetic-v1:positive","smart-qa-synthetic-v1:clock"))
        check(input.getString("local_day") == LocalDate.now(ZoneOffset.UTC).toString())
        val oldZone = TimeZone.getDefault()
        TimeZone.setDefault(TimeZone.getTimeZone("Etc/UTC"))
        StudyNotifications.cancelReminder(app)
        try {
            assertTrue(StudyNotifications.canPost(app))
            if (input.optBoolean("replace_link",false)) {
                check(app.widgetStore.read().studyOperations.all { it.acknowledged })
                app.authRepository.logout(unlinkDevice=true)
            }
            if (input.getBoolean("initial")) {
                check(app.credentialStore.refreshToken() == null)
                app.credentialStore.saveRefreshToken(input.getString("refresh_token"))
            } else check(app.credentialStore.refreshToken() != null)
            // Uses the production Keystore store and app-owned Retrofit/client:
            // no injected access token, HTTP mock or custom TLS trust manager.
            val restored = app.authRepository.bootstrap()
            if (restored is ApiResult.Failure) {
                // Error accessors may be inlined out of the host APK. This
                // diagnostic reads only its error type/resource, never tokens.
                val field = restored.javaClass.declaredFields.single { ApiError::class.java.isAssignableFrom(it.type) }
                field.isAccessible = true
                val error = field.get(restored) as ApiError
                fail("Native refresh/bootstrap failed: " + app.resources.getResourceEntryName(error.messageRes))
            }
            assertTrue(restored is ApiResult.Success)
            assertTrue(app.widgetStore.read().linked)
            app.widgetStore.setReminder(true)
            coroutineScope {
                listOf(async { app.studyReminderCoordinator.run() },
                    async { app.studyReminderCoordinator.run() }).forEach {
                    assertEquals(StudyReminderCoordinator.Outcome.DONE, it.await())
                }
            }
            val state = app.widgetStore.read()
            val posted = app.getSystemService(NotificationManager::class.java)
                .activeNotifications.count { it.id == 4201 }
            val evidence = JSONObject().put("fixture_version", input.getString("fixture_version"))
                .put("distribution", BuildConfig.DISTRIBUTION_CHANNEL).put("debuggable", false)
                .put("active_notifications", posted).put("operations", state.studyOperations.size)
                .put("acknowledged", state.studyOperations.all { it.acknowledged })
                .put("server_study_only", state.serverStudyOnly)
                .put("granted_operations",state.studyOperations.count { it.grantId != null })
                .put("outcomes",org.json.JSONArray(state.studyOperations.map { it.outcome }))
            File(app.getExternalFilesDir(null), "smart-signed-result.json").writeText(evidence.toString())
            println("SMART_QA_LOCAL="+evidence.toString())
            assertTrue(state.serverStudyOnly)
            assertEquals(input.getInt("expected_active"), posted)
            assertEquals(input.getInt("expected_operations"), state.studyOperations.size)
            assertTrue(state.studyOperations.all { it.acknowledged })
            println("SMART_SIGNED_STAGING_PASS")
        } finally {
            StudyNotifications.cancelReminder(app)
            TimeZone.setDefault(oldZone)
        }
    }
}
