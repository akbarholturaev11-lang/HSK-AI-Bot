package com.pomp.hskai.data.repository

import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidFeatureApi
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit

class CheckoutOverviewAnalyticsTest {
    @Test fun `legacy request omits receipt and manual fallback passes only committed receipt`() = runTest {
        val server = MockWebServer()
        server.start()
        try {
            val json = Json { ignoreUnknownKeys = true }
            val api = Retrofit.Builder().baseUrl(server.url("/"))
                .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
                .build().create(AndroidFeatureApi::class.java)
            val repository = FeatureRepository(api, { ApiResult.Success("test-token") })
            for (entry in listOf(null, 42)) {
                server.enqueue(MockResponse().setBody("""{"ok":true}""").setHeader("Content-Type", "application/json"))
                assertTrue(repository.checkoutOverview("course_limit", entry) is ApiResult.Success)
                val request = requireNotNull(server.takeRequest(1, TimeUnit.SECONDS))
                val url = requireNotNull(request.requestUrl)
                assertEquals("/api/v3/android/subscription/checkout/overview", url.encodedPath)
                assertEquals("course_limit", url.queryParameter("origin"))
                if (entry == null) assertNull(url.queryParameter("provider_entry_id"))
                else assertEquals("42", url.queryParameter("provider_entry_id"))
                assertEquals("Bearer test-token", request.getHeader("Authorization"))
            }
        } finally {
            server.shutdown()
        }
    }
}
