package com.pomp.hskai.data.api

import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit

/** Exercise the real Retrofit encoder; a fake API skips the request wire contract. */
class FoundationCompleteContractTest {
    // Match HskAiApplication.json, including its default encodeDefaults = false.
    private val json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
    }

    @Test
    fun `completion sends mandatory foundation identity without a speaking bonus`() = runTest {
        assertCompletionContract(speakingBonus = false)
    }

    @Test
    fun `completion sends mandatory foundation identity with a speaking bonus`() = runTest {
        assertCompletionContract(speakingBonus = true)
    }

    private suspend fun assertCompletionContract(speakingBonus: Boolean) {
        val server = MockWebServer()
        server.start()
        try {
            server.enqueue(
                MockResponse()
                    .setHeader("Content-Type", "application/json")
                    .setBody("""{"ok":true,"duplicate":false,"foundation":{"required":true,"completed":true,"status":"completed"}}"""),
            )
            val api = Retrofit.Builder()
                .baseUrl(server.url("/"))
                .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
                .build()
                .create(AndroidFoundationApi::class.java)
            val eventId = "android:foundation:" + "a".repeat(32)

            val response = api.completeFoundation(
                "Bearer test-token",
                FoundationCompleteRequest(
                    foundationId = "starter0_hsk1",
                    foundationVersion = 1,
                    speakingBonus = speakingBonus,
                    eventId = eventId,
                ),
            )

            val request = requireNotNull(server.takeRequest(1, TimeUnit.SECONDS))
            val body = json.parseToJsonElement(request.body.readUtf8()).jsonObject
            assertEquals("POST", request.method)
            assertEquals("/api/v3/android/course/foundation/complete", request.path)
            assertEquals("Bearer test-token", request.getHeader("Authorization"))
            assertEquals("starter0_hsk1", body["foundation_id"]?.jsonPrimitive?.content)
            assertEquals("1", body["foundation_version"]?.jsonPrimitive?.content)
            assertEquals(eventId, body["event_id"]?.jsonPrimitive?.content)
            if (speakingBonus) assertEquals("true", body["speaking_bonus"]?.jsonPrimitive?.content)
            assertTrue(response.isSuccessful)
            assertTrue(requireNotNull(response.body()).foundation.completed)
        } finally {
            server.shutdown()
        }
    }
}
