package com.pomp.hskai

import android.app.Application
import androidx.room.Room
import com.pomp.hskai.core.audio.AndroidLessonAudioPlayer
import com.pomp.hskai.core.audio.AndroidVoiceRecorder
import com.pomp.hskai.core.audio.DiskTtsCache
import com.pomp.hskai.core.audio.LessonAudioPlayer
import com.pomp.hskai.core.audio.TtsCache
import com.pomp.hskai.core.audio.VoiceRecorder
import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.network.OriginGuardInterceptor
import com.pomp.hskai.core.settings.AppSettings
import com.pomp.hskai.core.storage.SecureCredentialStore
import com.pomp.hskai.core.auth.CredentialManagerGoogleIdTokenProvider
import com.pomp.hskai.data.api.AndroidAuthApi
import com.pomp.hskai.data.api.NativeOAuthApi
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.api.AndroidFeatureApi
import com.pomp.hskai.data.api.AndroidFoundationApi
import com.pomp.hskai.data.api.AndroidOnboardingApi
import com.pomp.hskai.data.api.AndroidStudyPreferencesApi
import com.pomp.hskai.data.local.BundledStrokes
import com.pomp.hskai.data.local.HskAiDatabase
import com.pomp.hskai.data.repository.AssetBundledDictionarySource
import com.pomp.hskai.data.repository.CourseRepository
import com.pomp.hskai.data.repository.DictionaryRepository
import com.pomp.hskai.data.repository.FeatureRepository
import com.pomp.hskai.data.repository.OnboardingRepository
import com.pomp.hskai.data.repository.StudyPreferencesRepository
import java.io.File
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import com.pomp.hskai.widget.*
import com.pomp.hskai.core.notify.StudyReminderScheduler
import com.pomp.hskai.feature.update.UpdateWatch
import com.pomp.hskai.core.notify.StudyNotifications
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory

/**
 * Manual service locator.
 *
 * A DI framework would add a second annotation processor and a lot of build
 * surface for a single-module app; this stays explicit and easy to follow.
 */
class HskAiApplication : Application() {

    val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    val widgetStore by lazy { WidgetStore(this) }
    val widgetCoordinator by lazy { WidgetCoordinator(this, retrofit.create(AndroidEventsApi::class.java)) }

    override fun onCreate() {
        super.onCreate()
        applicationScope.launch {
            // Whether a newer build exists is asked here rather than from a
            // screen: the profile card only ever spoke to someone who opened
            // the profile. The Play build schedules nothing — Play updates
            // itself, and its flavour has an empty [UpdateWatch].
            UpdateWatch.schedule(this@HskAiApplication)
            if (widgetStore.read().linked) WidgetScheduler.schedule(this@HskAiApplication)
            // Migrate the old Telegram-coupled reminder: local reminders now default OFF.
            if (widgetStore.read().reminderEnabled) StudyReminderScheduler.schedule(this@HskAiApplication)
            else StudyReminderScheduler.cancel(this@HskAiApplication)
        }
    }

    private suspend fun clearWidgetSession() {
        kotlinx.coroutines.withContext(Dispatchers.Main.immediate) { assistant.reset() }
        widgetStore.clear()
        StudyNotifications.cancelReminder(this)
        applicationScope.launch { widgetCoordinator.render() }
        WidgetScheduler.cancel(this)
        StudyReminderScheduler.cancel(this)
    }

    val json: Json by lazy {
        Json {
            ignoreUnknownKeys = true
            explicitNulls = false
        }
    }

    private val httpClient: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .addInterceptor(OriginGuardInterceptor(BuildConfig.API_ORIGIN))
            .connectTimeout(CONNECT_TIMEOUT_SECONDS, TimeUnit.SECONDS)
            .readTimeout(READ_TIMEOUT_SECONDS, TimeUnit.SECONDS)
            .writeTimeout(READ_TIMEOUT_SECONDS, TimeUnit.SECONDS)
            .callTimeout(CALL_TIMEOUT_SECONDS, TimeUnit.SECONDS)
            .retryOnConnectionFailure(false)
            .followRedirects(false)
            .followSslRedirects(false)
            .build()
    }

    private val retrofit: Retrofit by lazy {
        Retrofit.Builder()
            .baseUrl("${BuildConfig.API_ORIGIN}/")
            .client(httpClient)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
    }

    /**
     * The assistant carries a photo inside its request body, so its upload is
     * megabytes where every other call is kilobytes.
     *
     * On a phone's uplink those megabytes take longer than the 30s write
     * budget that suits a lesson fetch, and the failure surfaced as "no
     * connection" on a working connection. It gets its own timeouts rather
     * than making every screen in the app wait three minutes before giving
     * up. `newBuilder` shares the connection pool and dispatcher, so this is
     * one more set of timeouts, not one more HTTP stack.
     */
    private val assistantRetrofit: Retrofit by lazy {
        retrofit.newBuilder()
            .client(
                httpClient.newBuilder()
                    .writeTimeout(ASSISTANT_WRITE_TIMEOUT_SECONDS, TimeUnit.SECONDS)
                    .callTimeout(ASSISTANT_CALL_TIMEOUT_SECONDS, TimeUnit.SECONDS)
                    .build()
            )
            .build()
    }

    val credentialStore: SecureCredentialStore by lazy { SecureCredentialStore(this) }

    val appSettings: AppSettings by lazy { AppSettings(this) }

    val lessonAudioPlayer: LessonAudioPlayer by lazy { AndroidLessonAudioPlayer(this) }

    val ttsCache: TtsCache by lazy { DiskTtsCache(File(cacheDir, "tts")) }

    val voiceRecorder: VoiceRecorder by lazy { AndroidVoiceRecorder(this) }

    val authRepository: AuthRepository by lazy {
        AuthRepository(
            api = retrofit.create(AndroidAuthApi::class.java),
            store = credentialStore,
            appVersion = BuildConfig.VERSION_NAME,
            oauthApi = retrofit.create(NativeOAuthApi::class.java),
            // A blank client id leaves the provider reporting itself
            // unavailable, so the Google button is simply never shown.
            googleIdTokens = CredentialManagerGoogleIdTokenProvider(
                context = this,
                webClientId = BuildConfig.GOOGLE_WEB_CLIENT_ID,
            ),
            onSessionCleared = ::clearWidgetSession,
            onSessionLinked = { widgetStore.linked(newSession = true) },
            onAuthenticated = {
                widgetStore.linked()
                WidgetScheduler.schedule(this)
            },
        )
    }

    private val courseApi: AndroidCourseApi by lazy {
        retrofit.create(AndroidCourseApi::class.java)
    }

    private val foundationApi: AndroidFoundationApi by lazy {
        retrofit.create(AndroidFoundationApi::class.java)
    }

    private val onboardingApi: AndroidOnboardingApi by lazy {
        retrofit.create(AndroidOnboardingApi::class.java)
    }

    private val studyPreferencesApi: AndroidStudyPreferencesApi by lazy {
        retrofit.create(AndroidStudyPreferencesApi::class.java)
    }

    private val database: HskAiDatabase by lazy {
        Room.databaseBuilder(this, HskAiDatabase::class.java, HskAiDatabase.NAME)
            .fallbackToDestructiveMigration(dropAllTables = true)
            .build()
    }

    val courseRepository: CourseRepository by lazy {
        CourseRepository(
            api = courseApi,
            accessToken = authRepository::accessToken,
            dao = database.courseMapDao(),
            lessonDao = database.lessonCacheDao(),
            json = json,
            foundationApi = foundationApi,
            onSessionExpired = authRepository::invalidateSession,
            ttsCache = ttsCache,
            bundledStrokes = bundledStrokes,
        )
    }

    val onboardingRepository: OnboardingRepository by lazy {
        OnboardingRepository(
            api = onboardingApi,
            accessToken = authRepository::accessToken,
            onSessionExpired = authRepository::invalidateSession,
        )
    }

    val studyPreferencesRepository: StudyPreferencesRepository by lazy {
        StudyPreferencesRepository(
            api = studyPreferencesApi,
            accessToken = authRepository::accessToken,
            onSessionExpired = authRepository::invalidateSession,
            readLastSetupPromptAskedAtMillis = {
                appSettings.lastStudySetupAskedAtMillis.first()
            },
            writeLastSetupPromptAskedAtMillis = appSettings::setLastStudySetupAskedAtMillis,
        )
    }

    val dictionaryRepository: DictionaryRepository by lazy {
        DictionaryRepository(
            api = courseApi,
            accessToken = authRepository::accessToken,
            dao = database.dictionaryDao(),
            onSessionExpired = authRepository::invalidateSession,
            bundledSource = AssetBundledDictionarySource(this, json),
            clientVersionCode = BuildConfig.VERSION_CODE,
            readLastCheckedAtMillis = appSettings::dictionaryLastCheckedAtMillis,
            readLastCheckedClientVersion = appSettings::dictionaryLastCheckedClientVersion,
            writeLastChecked = appSettings::setDictionaryLastChecked,
        )
    }

    /**
     * The writing order that ships with the app. The word list has its own
     * source (`AssetBundledDictionarySource`); together they are what makes
     * the dictionary work with no connection.
     */
    private val bundledStrokes: BundledStrokes by lazy {
        BundledStrokes(context = this, json = json)
    }

    val featureRepository: FeatureRepository by lazy {
        FeatureRepository(
            api = retrofit.create(AndroidFeatureApi::class.java),
            accessToken = authRepository::accessToken,
            onSessionExpired = authRepository::invalidateSession,
        )
    }

    val assistant by lazy {
        com.pomp.hskai.feature.assistant.AssistantController(
            this,
            com.pomp.hskai.feature.assistant.AssistantRepository(
                assistantRetrofit.create(com.pomp.hskai.feature.assistant.AssistantApi::class.java),
                authRepository::accessToken,
                authRepository::invalidateSession,
                json,
            ),
            json,
        )
    }

    suspend fun clearLocalData() {
        courseRepository.clearCache()
        dictionaryRepository.clearCache()
        voiceRecorder.cancel()
    }

    private companion object {
        const val CONNECT_TIMEOUT_SECONDS = 15L
        const val READ_TIMEOUT_SECONDS = 30L
        const val CALL_TIMEOUT_SECONDS = 60L

        // A photo upload on a slow uplink, not a slow server: the answer
        // itself is written in the background and collected by polling.
        const val ASSISTANT_WRITE_TIMEOUT_SECONDS = 120L
        const val ASSISTANT_CALL_TIMEOUT_SECONDS = 180L
    }
}
