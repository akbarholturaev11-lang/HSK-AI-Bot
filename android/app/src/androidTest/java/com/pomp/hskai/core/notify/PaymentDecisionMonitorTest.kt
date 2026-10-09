package com.pomp.hskai.core.notify

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidPushApi
import com.pomp.hskai.data.api.PaymentDecisionStatusResponse
import java.lang.reflect.Proxy
import kotlin.coroutines.Continuation
import kotlin.coroutines.intrinsics.startCoroutineUninterceptedOrReturn
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.async
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.yield
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import retrofit2.Response

/** Actual authenticated monitor flow, with isolated storage and no real payment or notification. */
@RunWith(AndroidJUnit4::class)
class PaymentDecisionMonitorTest {
    private val app = ApplicationProvider.getApplicationContext<HskAiApplication>()
    private val prefs = app.getSharedPreferences("payment-decision-monitor-test", Context.MODE_PRIVATE)

    @Before fun setUp() {
        prefs.edit().clear().putString("device_id", "test-device").commit()
    }

    @After fun tearDown() {
        prefs.edit().clear().commit()
    }

    private inner class Fixture {
        var authenticated = true
        var access: ApiResult<String> = ApiResult.Success("test-token")
        var verified = PaymentDecisionStatusResponse()
        var delayed: CompletableDeferred<Response<PaymentDecisionStatusResponse>>? = null
        var statusCalls = 0

        @Suppress("UNCHECKED_CAST")
        private fun reply(args: Array<out Any>?): Any? {
            assertEquals("Bearer test-token", args!![0])
            statusCalls++
            val wait = delayed ?: return Response.success(verified)
            return (suspend { wait.await() }).startCoroutineUninterceptedOrReturn(
                args.last() as Continuation<Response<PaymentDecisionStatusResponse>>,
            )
        }

        private val api = Proxy.newProxyInstance(
            AndroidPushApi::class.java.classLoader, arrayOf(AndroidPushApi::class.java),
        ) { _, method, args ->
            check(method.name == "paymentStatus") { "Unexpected API call: ${method.name}" }
            reply(args)
        } as AndroidPushApi

        fun monitor() = PaymentDecisionMonitor(
            app = app,
            api = api,
            prefs = prefs,
            accessToken = { access },
            hasSession = { authenticated },
            // Denied OS notification permission must not hide verified in-app access changes.
            postNotification = { _, _ -> false },
        )

        fun response(id: Int, status: String, plan: String = "1_month") {
            verified = PaymentDecisionStatusResponse(ok = true, paymentId = id, status = status, planType = plan)
        }
    }

    private suspend fun decisions(
        monitor: PaymentDecisionMonitor,
        operation: suspend () -> Unit,
    ): List<InAppPaymentDecision> = coroutineScope {
        val values = mutableListOf<InAppPaymentDecision>()
        val collector = launch(start = CoroutineStart.UNDISPATCHED) {
            monitor.inAppPaymentDecisions.collect { values += it }
        }
        try {
            operation()
            yield()
            values.toList()
        } finally {
            collector.cancelAndJoin()
        }
    }

    @Test fun verifiedProAndHskDecisionsReachTheOpenAppWithoutNotificationPermission() = runBlocking {
        val f = Fixture()
        val monitor = f.monitor()
        val expected = mutableListOf<InAppPaymentDecision>()
        val received = decisions(monitor) {
            listOf("1_month", "hsk30_unlock").forEach { plan ->
                listOf("approved", "rejected").forEach { status ->
                    val id = expected.size + 1
                    f.response(id, status, plan)
                    assertFalse(monitor.receive("test-device", id, status))
                    expected += InAppPaymentDecision("test-device", id, status, plan)
                }
            }
        }
        assertEquals(expected, received)
        assertEquals(4, f.statusCalls)
    }

    @Test fun duplicateDeliveryAndMonitorRecreationDoNotReplayTheAccessChange() = runBlocking {
        val f = Fixture()
        f.response(7, "approved")
        val monitor = f.monitor()
        val received = decisions(monitor) {
            monitor.receive("test-device", 7, "approved")
            monitor.receive("test-device", 7, "approved")
        }
        assertEquals(listOf(InAppPaymentDecision("test-device", 7, "approved", "1_month")), received)
        val recreated = f.monitor()
        assertTrue(decisions(recreated) { recreated.receive("test-device", 7, "approved") }.isEmpty())
    }

    @Test fun unverifiedMismatchedAndUnauthenticatedHintsNeverChangeAccess() = runBlocking {
        val f = Fixture()
        val monitor = f.monitor()
        val received = decisions(monitor) {
            f.response(9, "approved")
            assertFalse(monitor.receive("another-device", 9, "approved"))
            assertFalse(monitor.receive("test-device", 0, "approved"))
            assertFalse(monitor.receive("test-device", 9, "pending"))
            f.authenticated = false
            assertFalse(monitor.receive("test-device", 9, "approved"))
            f.authenticated = true
            f.access = ApiResult.Failure(ApiError.SessionExpired)
            assertFalse(monitor.receive("test-device", 9, "approved"))
            assertEquals(0, f.statusCalls)
            f.access = ApiResult.Success("test-token")
            f.response(10, "approved")
            assertFalse(monitor.receive("test-device", 9, "approved"))
            f.response(9, "rejected")
            assertFalse(monitor.receive("test-device", 9, "approved"))
            f.verified = f.verified.copy(ok = false, status = "approved")
            assertFalse(monitor.receive("test-device", 9, "approved"))
        }
        assertTrue(received.isEmpty())
        assertEquals(3, f.statusCalls)
    }

    @Test fun logoutDuringVerificationRejectsTheLatePaymentResponse() = runBlocking {
        val f = Fixture()
        f.delayed = CompletableDeferred()
        val monitor = f.monitor()
        val received = decisions(monitor) {
            coroutineScope {
                val verification = async(start = CoroutineStart.UNDISPATCHED) {
                    monitor.receive("test-device", 11, "approved")
                }
                assertEquals(1, f.statusCalls)
                monitor.clear()
                // Logging in again on the same device cannot accept the old session's read.
                prefs.edit().putString("device_id", "test-device").commit()
                f.delayed!!.complete(Response.success(PaymentDecisionStatusResponse(
                    ok = true, paymentId = 11, status = "approved", planType = "hsk30_unlock",
                )))
                assertFalse(verification.await())
            }
        }
        assertTrue(received.isEmpty())
        assertFalse(prefs.contains("in-app:test-device:11:approved"))
    }

    @Test fun pollingAConfirmedPaymentUsesTheSameVerifiedEventAndDedupe() = runBlocking {
        val f = Fixture()
        f.response(12, "approved", "hsk30_unlock")
        prefs.edit().putInt("pending_payment_id", 12).commit()
        val monitor = f.monitor()
        val received = decisions(monitor) {
            assertFalse(monitor.pollPending())
            assertFalse(monitor.receive("test-device", 12, "approved"))
        }
        assertEquals(listOf(InAppPaymentDecision("test-device", 12, "approved", "hsk30_unlock")), received)
    }
}
