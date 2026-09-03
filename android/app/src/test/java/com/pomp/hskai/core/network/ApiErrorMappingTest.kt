package com.pomp.hskai.core.network

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.Response

/**
 * How a failed response becomes something the UI can show.
 *
 * The one thing worth protecting here is the reset instant: without it a
 * learner whose daily allowance is spent sees a dead end instead of the hour
 * their practice comes back.
 */
class ApiErrorMappingTest {

    private fun failure(code: Int, body: String): Response<Unit> =
        Response.error(code, body.toResponseBody("application/json".toMediaType()))

    @Test
    fun `a spent daily allowance keeps the instant it reopens`() {
        val error = failure(
            403,
            """{"ok":false,"error":"free_feature_limit_reached",""" +
                """"reset_at":"2026-09-16T00:00:00+00:00","lifetime":false}""",
        ).toApiError()

        assertTrue(error is ApiError.LimitReached)
        assertEquals("2026-09-16T00:00:00+00:00", (error as ApiError.LimitReached).resetAt)
    }

    @Test
    fun `an allowance that never reopens reports no instant`() {
        // A once-ever limit has no tomorrow, so the block must not promise one.
        val error = failure(
            403,
            """{"ok":false,"error":"free_feature_limit_reached","reset_at":null,"lifetime":true}""",
        ).toApiError()

        assertTrue(error is ApiError.LimitReached)
        assertNull((error as ApiError.LimitReached).resetAt)
    }

    @Test
    fun `an older server that sends no instant still maps to the limit`() {
        val error = failure(403, """{"ok":false,"error":"free_feature_limit_reached"}""")
            .toApiError()

        assertTrue(error is ApiError.LimitReached)
        assertNull((error as ApiError.LimitReached).resetAt)
    }

    @Test
    fun `other failures are unchanged`() {
        val error = failure(404, """{"ok":false,"error":"mistake_review_empty"}""").toApiError()
        assertTrue(error is ApiError.Server)
        assertEquals("mistake_review_empty", (error as ApiError.Server).code)
    }

    @Test
    fun `a dead session is still recognised before anything else`() {
        val error = failure(401, """{"ok":false,"error":"desktop_session_revoked"}""").toApiError()
        assertEquals(ApiError.SessionExpired, error)
    }

    @Test
    fun `an unparsable body falls back to the status code`() {
        assertEquals(ApiError.SessionExpired, failure(401, "<html>nope</html>").toApiError())
        assertEquals(ApiError.Unknown, failure(500, "").toApiError())
    }
}
