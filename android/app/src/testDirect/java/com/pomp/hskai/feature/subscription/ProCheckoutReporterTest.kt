package com.pomp.hskai.feature.subscription

import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.*
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ProCheckoutReporterTest {
    @Test fun boundedQueueNeverWaitsForNetworkAndCloseDrainsOnlyUiStages() = runTest {
        val gate = CompletableDeferred<Unit>()
        val sent = mutableListOf<ProUiEvent>()
        val session = ProEventSession("first", 1)
        val reporter = ProCheckoutReporter("native-attempt", "course_limit", this,
            { session }, { session }, { true }, { _, event -> gate.await(); sent += event })
        reporter.record("opened")
        runCurrent()
        repeat(100) { reporter.record("plan_selected", "1_month", "lava") }
        reporter.record("checkout_started"); reporter.record("checkout_paid")
        reporter.close()
        assertTrue(sent.isEmpty()) // record/close returned while send is suspended
        gate.complete(Unit)
        advanceUntilIdle()
        assertEquals(33, sent.size) // one in flight plus 32 queued, no unbounded jobs
        assertTrue(sent.all { it.event in setOf("android_pro_opened", "android_pro_plan_selected") })
        assertEquals("native-attempt:opened", sent.first().event_id)
        assertTrue(sent.all { it.attempt_id == "native-attempt" && it.source == "course_limit" })
        assertTrue(reporter.ownsSession("first")); assertFalse(reporter.ownsSession("replacement"))
    }

    @Test fun replacementSessionCannotReceiveQueuedObservations() = runTest {
        var session = ProEventSession("first", 1)
        val sent = mutableListOf<String>()
        val reporter = ProCheckoutReporter("attempt", "voice_limit", this,
            { session }, { session }, { it == session.generation }, { token, _ -> sent += token })
        reporter.record("opened"); runCurrent()
        session = ProEventSession("replacement", 2)
        reporter.record("dismissed"); reporter.close(); advanceUntilIdle()
        assertEquals(listOf("first"), sent)
        assertFalse(reporter.ownsSession("replacement"))
    }

    @Test fun failedOrChangedOpeningProofDropsAllEventsWithoutThrowing() = runTest {
        for (fail in listOf(false, true)) {
            var sent = 0
            val reporter = ProCheckoutReporter("attempt", "course_limit", this,
                { if (fail) error("fixture network failure") else null }, { ProEventSession("new", 2) },
                { true }, { _, _ -> sent++ })
            reporter.record("opened"); reporter.record("dismissed"); reporter.close(); advanceUntilIdle()
            assertEquals(0, sent)
        }
    }

    @Test fun sendFailureAndTimeoutDoNotStopFollowingEventsOrCheckout() = runTest {
        var calls = 0
        val session = ProEventSession("owner", 1)
        val reporter = ProCheckoutReporter("attempt", "course_limit", this,
            { session }, { session }, { true }, { _, _ ->
                calls++
                if (calls == 1) error("fixture server failure")
                if (calls == 2) CompletableDeferred<Unit>().await()
            })
        reporter.record("opened"); reporter.record("more_opened"); reporter.record("dismissed")
        reporter.close(); advanceUntilIdle()
        assertEquals(3, calls)
    }
}
