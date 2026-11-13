package com.pomp.hskai.core.diagnostics

import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import java.io.IOException
import java.net.SocketTimeoutException
import kotlin.coroutines.cancellation.CancellationException
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.SerializationException
import okhttp3.MediaType
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody
import okio.Buffer
import okio.BufferedSource
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

/** `apiCall` reports a tagged 5xx or decode failure once, and nothing expected. */
class ApiCallDiagnosticsTest {
    private lateinit var kit: DiagnosticsKit

    @Before
    fun install() {
        kit = DiagnosticsKit()
        Diagnostics.reporter = kit.reporter
    }

    @After
    fun uninstall() {
        Diagnostics.reporter = null
    }

    private class CountingBody(private val text: String) : ResponseBody() {
        var reads = 0
        override fun contentType(): MediaType = "application/json".toMediaType()
        override fun contentLength(): Long = text.length.toLong()
        override fun source(): BufferedSource {
            reads++
            return Buffer().writeUtf8(text)
        }
    }

    private suspend fun failing(code: Int, body: String = """{"ok":false,"error":"boom"}""", tag: DiagTag? = DiagTags.LESSON_OPEN) =
        apiCall(tag) { Response.error<Unit>(code, CountingBody(body)) }

    @Test
    fun `offline, timeout, 4xx, limit, paywall and 503 are not reported`() = runTest {
        apiCall<Unit>(DiagTags.LESSON_OPEN) { throw IOException("offline") }
        apiCall<Unit>(DiagTags.LESSON_OPEN) { throw SocketTimeoutException("slow") }
        for (code in listOf(400, 401, 403, 404, 409, 422, 429)) failing(code)
        failing(403, """{"ok":false,"error":"free_feature_limit_reached","reset_at":null}""")
        failing(402, """{"ok":false,"error":"subscription_required"}""")
        failing(503, """{"ok":false,"error":"feature_unavailable"}""")
        assertEquals(emptyList<String>(), kit.codes())
    }

    @Test
    fun `a 5xx is reported once and the error body is read once`() = runTest {
        val body = CountingBody("""{"ok":false,"error":"server_error"}""")
        val result = apiCall(DiagTags.LESSON_COMPLETE) { Response.error<Unit>(500, body) }
        assertTrue(result is ApiResult.Failure)
        assertEquals(1, body.reads)
        failing(502, tag = DiagTags.PAYMENT)
        assertEquals(listOf("lessons/api_5xx/lesson_complete", "checkout_payments/api_5xx/payment"), kit.codes())
    }

    @Test
    fun `a 2xx without a body and a decode failure are api_decode`() = runTest {
        val empty = apiCall(DiagTags.PROGRESS) { Response.success<Unit>(null) }
        assertEquals(ApiError.Unknown, (empty as ApiResult.Failure).error)
        apiCall<Unit>(DiagTags.PRACTICE) { throw SerializationException("missing field") }
        assertEquals(listOf("lessons/api_decode/progress", "practice/api_decode/practice"), kit.codes())
    }

    @Test
    fun `untagged calls and cancellation report nothing`() = runTest {
        failing(500, tag = null)
        apiCall<Unit>(null) { throw SerializationException("x") }
        apiCall<Unit>(DiagTags.LOGIN) { throw CancellationException("left the screen") }
        assertEquals(emptyList<String>(), kit.codes())
    }

    @Test
    fun `the event carries codes and versions only`() = runTest {
        failing(500, tag = DiagTags.LOGIN)
        val event = kit.events().single()
        val encoded = testJson.encodeToString(DiagnosticEventDto.serializer(), event)
        val keys = testJson.parseToJsonElement(encoded).let { it as kotlinx.serialization.json.JsonObject }.keys
        assertEquals(
            setOf("event_id", "client_time", "app_version", "build", "channel", "feature_code",
                "failure_code", "site_code", "outcome"),
            keys,
        )
        assertEquals("auth_session" to "login", event.featureCode to event.siteCode)
        assertEquals("play", event.channel)
    }
}
