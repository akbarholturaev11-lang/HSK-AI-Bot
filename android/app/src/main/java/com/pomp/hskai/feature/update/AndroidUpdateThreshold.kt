package com.pomp.hskai.feature.update

import android.content.Context
import com.pomp.hskai.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.intOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit

/** Identical fail-safe rule for Direct and Play; only installation differs. */
object AndroidUpdateThreshold {
    const val DEFAULT_ALLOWED_VERSIONS = 4

    fun isMandatory(
        installedVersionCode: Int,
        availableVersionCode: Int,
        allowedVersions: Int,
    ): Boolean {
        // Unknown policy must never turn a store outage into an app lockout.
        if (allowedVersions !in 1..4 || availableVersionCode <= installedVersionCode) return false
        return availableVersionCode.toLong() - installedVersionCode.toLong() >= allowedVersions
    }
}

/** Settings are non-secret and read from the same authoritative BotSetting as Admin PWA. */
object UpdatePolicyClient {
    private val client: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(6, TimeUnit.SECONDS)
            .readTimeout(6, TimeUnit.SECONDS)
            .callTimeout(8, TimeUnit.SECONDS)
            .build()
    }

    suspend fun allowedVersions(context: Context): Int = withContext(Dispatchers.IO) {
        // QA deliberately does not poll production release infrastructure.
        if (BuildConfig.QA_BUILD) return@withContext AndroidUpdateThreshold.DEFAULT_ALLOWED_VERSIONS
        try {
            val request = Request.Builder()
                .url("${BuildConfig.API_ORIGIN}/api/v3/android-update/policy")
                .get()
                .build()
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) return@withContext AndroidUpdateThreshold.DEFAULT_ALLOWED_VERSIONS
                val count = response.body?.string()
                    ?.let { Json.parseToJsonElement(it).jsonObject["allowed_versions"]?.jsonPrimitive?.intOrNull }
                count?.takeIf { it in 1..4 } ?: AndroidUpdateThreshold.DEFAULT_ALLOWED_VERSIONS
            }
        } catch (_: Exception) {
            AndroidUpdateThreshold.DEFAULT_ALLOWED_VERSIONS
        }
    }
}
