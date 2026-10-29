package com.pomp.hskai.data.api

import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.*
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory

class AndroidSmartReminderApiTest {
    private val json=Json { ignoreUnknownKeys=true; explicitNulls=false }

    @Test fun `real HTTP uses exact native study paths and required default fields`() = runTest {
        val server=MockWebServer(); server.start()
        try {
            val api=Retrofit.Builder().baseUrl(server.url("/"))
                .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
                .build().create(AndroidSmartReminderApi::class.java)
            server.enqueue(MockResponse().setBody("""{"ok":true,"version":1,"dispatch_allowed":false,"server_claim_required":true}"""))
            assertTrue(api.mode("Bearer synthetic").body()!!.serverClaimRequired!!)
            assertEquals("/api/v3/android/smart-reminder/mode",server.takeRequest().path)
            server.enqueue(MockResponse().setBody("""{"ok":true,"version":1,"generation":2}"""))
            api.observe("Bearer synthetic",SmartStudyObservation(expectedGeneration=1,notificationsAllowed=false))
            val observation=server.takeRequest()
            assertEquals("PATCH",observation.method)
            assertEquals("Bearer synthetic",observation.getHeader("Authorization"))
            val body=json.parseToJsonElement(observation.body.readUtf8()).jsonObject
            assertEquals(setOf("expected_generation","protocol_version","autonomous_study_disabled","study_notifications_allowed"),body.keys)
            assertEquals(1,body["protocol_version"]!!.jsonPrimitive.int)
            assertTrue(body["autonomous_study_disabled"]!!.jsonPrimitive.boolean)
            assertFalse(body["study_notifications_allowed"]!!.jsonPrimitive.boolean)
            val job="00000000-0000-4000-8000-000000000001"
            server.enqueue(MockResponse().setBody("""{"ok":true,"version":1,"dispatch_allowed":false}"""))
            api.claim("Bearer synthetic",job,SmartStudyClaim(requestId=job,localEpoch=job,
                capabilityGeneration=2,preferenceRevision=3,grantEpoch=4))
            val claim=server.takeRequest()
            assertEquals("/api/v3/android/smart-reminder/jobs/$job/claim",claim.path)
            val fields=json.parseToJsonElement(claim.body.readUtf8()).jsonObject
            assertEquals(setOf("version","request_id","local_epoch","capability_generation","preference_revision","grant_epoch"),fields.keys)
            assertEquals(1,fields["version"]!!.jsonPrimitive.int)
            server.enqueue(MockResponse().setBody("""{"ok":true,"version":1}"""))
            api.receipt("Bearer synthetic",job,SmartStudyReceipt(grantId=job,receiptId=job,localEpoch=job,outcome="client_outcome_unknown"))
            val receipt=server.takeRequest()
            assertEquals("/api/v3/android/smart-reminder/jobs/$job/receipt",receipt.path)
            assertEquals("client_outcome_unknown",json.parseToJsonElement(receipt.body.readUtf8()).jsonObject["outcome"]!!.jsonPrimitive.content)
            server.enqueue(MockResponse().setBody("""{"ok":true,"version":1,"dispatch_allowed":"true"}"""))
            assertTrue(apiCall { api.due("Bearer synthetic") } is ApiResult.Failure)
            server.enqueue(MockResponse().setBody("""{"ok":true,"version":"1","server_claim_required":false}"""))
            assertTrue(apiCall { api.mode("Bearer synthetic") } is ApiResult.Failure)
        } finally { server.shutdown() }
    }
}
