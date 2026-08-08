package com.pomp.hskai

import android.app.Application
import androidx.room.Room
import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.network.OriginGuardInterceptor
import com.pomp.hskai.core.storage.SecureCredentialStore
import com.pomp.hskai.data.api.AndroidAuthApi
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.local.HskAiDatabase
import com.pomp.hskai.data.repository.CourseRepository
import java.util.concurrent.TimeUnit
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
            // Auth and course calls are not blindly retried; the repositories
            // decide what is safe to repeat.
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

    val credentialStore: SecureCredentialStore by lazy { SecureCredentialStore(this) }

    val authRepository: AuthRepository by lazy {
        AuthRepository(
            api = retrofit.create(AndroidAuthApi::class.java),
            store = credentialStore,
            appVersion = BuildConfig.VERSION_NAME,
        )
    }

    private val database: HskAiDatabase by lazy {
        Room.databaseBuilder(this, HskAiDatabase::class.java, HskAiDatabase.NAME)
            // The cache is a disposable snapshot of server state, so a schema
            // change may simply drop it rather than carry a migration.
            .fallbackToDestructiveMigration(dropAllTables = true)
            .build()
    }

    val courseRepository: CourseRepository by lazy {
        CourseRepository(
            api = retrofit.create(AndroidCourseApi::class.java),
            accessToken = authRepository::accessToken,
            dao = database.courseMapDao(),
            json = json,
        )
    }

    /** Session end: credentials are cleared by auth, cached progress here. */
    suspend fun clearLocalData() {
        courseRepository.clearCache()
    }

    private companion object {
        const val CONNECT_TIMEOUT_SECONDS = 15L
        const val READ_TIMEOUT_SECONDS = 30L
        const val CALL_TIMEOUT_SECONDS = 60L
    }
}
