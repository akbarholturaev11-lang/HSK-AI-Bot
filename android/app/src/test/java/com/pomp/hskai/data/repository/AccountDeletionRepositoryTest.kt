package com.pomp.hskai.data.repository

import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AccountDeletionApi
import com.pomp.hskai.data.api.AccountDeletionPrepared
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit

class AccountDeletionRepositoryTest {
    private val server = MockWebServer()
    private val json = Json { ignoreUnknownKeys = true; explicitNulls = false }
    private var sessionExpired = 0
    private var tokenReads = 0
    private lateinit var repository: AccountDeletionRepository

    @Before fun setUp() {
        server.start()
        val api = Retrofit.Builder().baseUrl(server.url("/"))
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build().create(AccountDeletionApi::class.java)
        repository = AccountDeletionRepository(
            api, { tokenReads++; ApiResult.Success("provider-session") }, { sessionExpired++ },
        )
    }

    @After fun tearDown() = server.shutdown()

    @Test fun `provider only account prepares ownership then explicitly submits without leaking proof`() = runTest {
        respond(preparedBody())
        val prepared = (repository.prepare() as ApiResult.Success).value
        val prepareRequest = requireNotNull(server.takeRequest(1, TimeUnit.SECONDS))
        assertEquals("/api/account-deletion/prepare", prepareRequest.path)
        assertEquals("POST", prepareRequest.method)
        assertEquals("Bearer provider-session", prepareRequest.getHeader("Authorization"))
        assertEquals("{}", prepareRequest.body.readUtf8())
        assertFalse(prepared.accountLabel.contains("telegram", ignoreCase = true))
        assertEquals(1, server.requestCount)

        respond(receiptBody())
        val receipt = (repository.confirm(prepared) as ApiResult.Success).value
        val confirmRequest = requireNotNull(server.takeRequest(1, TimeUnit.SECONDS))
        assertEquals("/api/account-deletion/confirm", confirmRequest.path)
        assertEquals("POST", confirmRequest.method)
        assertNull(confirmRequest.getHeader("Authorization"))
        val body = json.parseToJsonElement(confirmRequest.body.readUtf8()).jsonObject
        assertEquals(requestId, body["request_id"]!!.jsonPrimitive.content)
        assertEquals(secret, body["secret"]!!.jsonPrimitive.content)
        assertEquals("DELETE", body["confirmation"]!!.jsonPrimitive.content)
        assertEquals("submitted", receipt.status)
        assertEquals(1, tokenReads)
        assertEquals(0, sessionExpired)
    }

    @Test fun `invalid native session follows existing credential invalidation handling`() = runTest {
        respond("""{"ok":false,"error":"desktop_access_invalid"}""", 401)
        assertEquals(ApiResult.Failure(ApiError.SessionExpired), repository.prepare())
        assertEquals(1, sessionExpired)
        assertEquals(1, server.requestCount)
    }

    @Test fun `unverified incomplete or malformed ownership cannot be confirmed`() = runTest {
        for (body in listOf(
            preparedBody().replace("\"ok\":true", "\"ok\":false"),
            preparedBody().replace("verified", "pending"),
            preparedBody().replace(secret, "short"),
            preparedBody().replace(requestId, "untrusted-id"),
            preparedBody().replace("Provider learner", ""),
        )) {
            respond(body)
            assertEquals(ApiResult.Failure(ApiError.Unknown), repository.prepare())
        }
        assertEquals(ApiResult.Failure(ApiError.Unknown), repository.confirm(AccountDeletionPrepared()))
        assertEquals(5, server.requestCount)
    }

    @Test fun `receipt must prove the submitted request and valid processing interval`() = runTest {
        val prepared = AccountDeletionPrepared(true, requestId, secret, "verified", "Provider learner")
        for (body in listOf(
            receiptBody().replace("\"ok\":true", "\"ok\":false"),
            receiptBody().replace("submitted", "verified"),
            receiptBody().replace(requestId, "a52c8d00-c4b1-4d76-978d-7d086ebd83a3"),
            receiptBody().replace("2026-11-14", "2026-10-13"),
            """{"ok":true,"status":"submitted","request_id":"$requestId"}""",
        )) {
            respond(body)
            assertEquals(ApiResult.Failure(ApiError.Unknown), repository.confirm(prepared))
        }
        assertEquals(0, tokenReads)
        assertEquals(0, sessionExpired)
    }

    @Test fun `confirmation refusal stays a failure and never wipes the existing login`() = runTest {
        respond("""{"ok":false,"error":"deletion_expired"}""", 410)
        val result = repository.confirm(AccountDeletionPrepared(true, requestId, secret, "verified", "Learner"))
        assertTrue(result is ApiResult.Failure)
        assertEquals(0, sessionExpired)
    }

    private fun respond(body: String, status: Int = 200) {
        server.enqueue(MockResponse().setResponseCode(status).setHeader("Content-Type", "application/json").setBody(body))
    }

    private fun preparedBody() = """{"ok":true,"status":"verified","request_id":"$requestId","secret":"$secret","account_label":"Provider learner"}"""
    private fun receiptBody() = """{"ok":true,"status":"submitted","request_id":"$requestId","requested_at":"2026-10-15T12:00:00Z","due_at":"2026-11-14T12:00:00Z"}"""

    companion object {
        private const val requestId = "806c055a-4c34-4aee-b06f-2c27a6080096"
        private val secret = "s".repeat(43)
    }
}
