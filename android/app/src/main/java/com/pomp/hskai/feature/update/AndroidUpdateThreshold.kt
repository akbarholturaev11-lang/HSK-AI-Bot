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

/** Channel's minimum supported PUBLISHED release, not a versionCode gap. */
object AndroidUpdateThreshold {
    fun isMandatory(
        installedVersionCode: Int,
        availableVersionCode: Int,
        minimumSupportedVersionCode: Int?,
    ): Boolean = minimumSupportedVersionCode != null &&
        minimumSupportedVersionCode > 0 &&
        availableVersionCode >= minimumSupportedVersionCode &&
        installedVersionCode < minimumSupportedVersionCode
}

object UpdatePolicyClient {
    private val client: OkHttpClient by lazy {
        OkHttpClient.Builder().connectTimeout(6, TimeUnit.SECONDS)
            .readTimeout(6, TimeUnit.SECONDS)
            .callTimeout(8, TimeUnit.SECONDS).build()
    }

    /** Null: publication history unavailable/incomplete; leave access open. */
    suspend fun minimumSupportedVersion(context: Context, channel: String): Int? =
        withContext(Dispatchers.IO) {
            if (BuildConfig.QA_BUILD || channel !in setOf("direct", "play")) return@withContext null
            try {
                val request = Request.Builder()
                    .url("${BuildConfig.API_ORIGIN}/api/v3/android-update/policy?channel=$channel")
                    .get().build()
                client.newCall(request).execute().use { response ->
                    if (!response.isSuccessful) return@withContext null
                    val code = response.body?.string()?.let {
                        Json.parseToJsonElement(it).jsonObject["minimum_version_code"]
                            ?.jsonPrimitive?.intOrNull
                    }
                    code?.takeIf { it > 0 }
                }
            } catch (_: Exception) {
                null
            }
        }
}
