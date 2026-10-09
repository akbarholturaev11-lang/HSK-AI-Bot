package com.pomp.hskai.feature.profile

import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidFeatureApi
import com.pomp.hskai.data.api.AndroidProfileResponse
import com.pomp.hskai.data.api.AndroidProfileSubscriptionDto
import com.pomp.hskai.data.api.AndroidProfileUserDto
import com.pomp.hskai.data.api.AndroidTrialDto
import com.pomp.hskai.data.api.AndroidTrialStartResponse
import com.pomp.hskai.data.api.AndroidTrialStatusResponse
import com.pomp.hskai.data.repository.FeatureRepository
import java.lang.reflect.Proxy
import kotlin.coroutines.Continuation
import kotlin.coroutines.intrinsics.startCoroutineUninterceptedOrReturn
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class ProfileViewModelTest {
    private val dispatcher = StandardTestDispatcher()
    @Before fun setUp() = Dispatchers.setMain(dispatcher)
    @After fun tearDown() = Dispatchers.resetMain()

    private fun profile(level: String = "hsk2", paid: Boolean = false, name: String = "Learner") =
        AndroidProfileResponse(
            ok = true,
            user = AndroidProfileUserDto(level = level, name = name),
            subscription = AndroidProfileSubscriptionDto(isPaid = paid),
        )

    private class Read {
        val profile = CompletableDeferred<Response<AndroidProfileResponse>>()
        val trial = CompletableDeferred<Response<AndroidTrialStatusResponse>>()

        fun complete(profile: AndroidProfileResponse, activeTrial: Boolean = false) {
            this.profile.complete(Response.success(profile))
            trial.complete(Response.success(AndroidTrialStatusResponse(
                ok = true, trial = AndroidTrialDto(active = activeTrial, eligible = !activeTrial),
            )))
        }
    }

    private class Fixture {
        val profileReads = ArrayDeque<Read>()
        val trialReads = ArrayDeque<Read>()
        val saveReply = CompletableDeferred<Response<AndroidProfileResponse>>()
        val startReply = CompletableDeferred<Response<AndroidTrialStartResponse>>()

        fun nextRead() = Read().also { profileReads.add(it); trialReads.add(it) }

        @Suppress("UNCHECKED_CAST")
        private fun <T> respond(reply: CompletableDeferred<T>, args: Array<out Any>?): Any? =
            (suspend { reply.await() }).startCoroutineUninterceptedOrReturn(args!!.last() as Continuation<T>)

        val api = Proxy.newProxyInstance(
            AndroidFeatureApi::class.java.classLoader, arrayOf(AndroidFeatureApi::class.java),
        ) { _, method, args ->
            when (method.name) {
                "profile" -> respond(profileReads.removeFirst().profile, args)
                "trialStatus" -> respond(trialReads.removeFirst().trial, args)
                "updateProfile" -> respond(saveReply, args)
                "trialStart" -> respond(startReply, args)
                else -> error("Unexpected API call: ${method.name}")
            }
        } as AndroidFeatureApi

        fun model() = ProfileViewModel(FeatureRepository(api, { ApiResult.Success("test-token") }))
    }

    @Test fun olderCourseAndAccessResponseCannotOverwriteTheLatestRefresh() = runTest(dispatcher) {
        val f = Fixture()
        val old = f.nextRead()
        val vm = f.model()
        runCurrent()
        val fresh = f.nextRead()
        vm.load()
        runCurrent()

        fresh.complete(profile("nhsk3", paid = true))
        runCurrent()
        old.complete(profile("hsk2", paid = false))
        runCurrent()

        assertEquals("nhsk3", vm.state.value.profile!!.user.level)
        assertTrue(vm.state.value.profile!!.subscription.isPaid)
        assertFalse(vm.state.value.isLoading)
    }

    @Test fun loadKeepsPendingMutationsAndCompletedProfileRevision() = runTest(dispatcher) {
        val f = Fixture()
        f.nextRead().complete(profile())
        val vm = f.model()
        runCurrent()
        vm.saveProfile("Updated", "panda")
        vm.startTrial()
        runCurrent()
        val refresh = f.nextRead()
        vm.load()
        runCurrent()
        refresh.complete(profile())
        runCurrent()

        assertTrue(vm.state.value.profileSaving)
        assertTrue(vm.state.value.trialStarting)
        f.nextRead().complete(profile(name = "Updated"))
        f.saveReply.complete(Response.success(profile(name = "Updated")))
        f.startReply.complete(Response.success(AndroidTrialStartResponse(ok = false, error = "trial_used")))
        runCurrent()
        assertFalse(vm.state.value.profileSaving)
        assertFalse(vm.state.value.trialStarting)
        assertEquals("trial_used", vm.state.value.trialError)
        assertEquals(1, vm.state.value.profileRevision)

        f.nextRead().complete(profile(name = "Updated"))
        vm.load()
        runCurrent()
        assertEquals(1, vm.state.value.profileRevision)
        assertEquals("trial_used", vm.state.value.trialError)
    }

    @Test fun lateReadCannotUndoASuccessfulProfileSave() = runTest(dispatcher) {
        val f = Fixture()
        val delayed = f.nextRead()
        val vm = f.model()
        runCurrent()
        vm.saveProfile("Updated", "panda")
        runCurrent()
        f.saveReply.complete(Response.success(profile(name = "Updated")))
        runCurrent()
        delayed.complete(profile(name = "Old"))
        runCurrent()

        assertEquals("Updated", vm.state.value.profile!!.user.name)
        assertEquals(1, vm.state.value.profileRevision)
        assertFalse(vm.state.value.profileSaving)
        assertFalse(vm.state.value.isLoading)
    }

    @Test fun lateSuccessfulReadCannotHideAFailedProfileSave() = runTest(dispatcher) {
        val f = Fixture()
        val delayed = f.nextRead()
        val vm = f.model()
        runCurrent()
        vm.saveProfile("Updated", "panda")
        runCurrent()
        f.saveReply.complete(Response.error(503, "unavailable".toResponseBody()))
        runCurrent()
        val error = vm.state.value.error
        assertTrue(error != null)
        delayed.complete(profile())
        runCurrent()

        assertEquals(error, vm.state.value.error)
        assertFalse(vm.state.value.profileSaving)
        assertFalse(vm.state.value.isLoading)
    }

    @Test fun olderProfileSaveCannotUndoANewerCourseAndAccessRead() = runTest(dispatcher) {
        val f = Fixture()
        f.nextRead().complete(profile())
        val vm = f.model()
        runCurrent()
        vm.saveProfile("Updated", "panda")
        runCurrent()
        val switched = f.nextRead()
        vm.load()
        runCurrent()
        switched.complete(profile("nhsk3", paid = true))
        runCurrent()

        val authoritative = f.nextRead()
        f.saveReply.complete(Response.success(profile("hsk2", paid = false, name = "Updated")))
        runCurrent()
        assertEquals("nhsk3", vm.state.value.profile!!.user.level)
        assertTrue(vm.state.value.profile!!.subscription.isPaid)
        assertEquals(1, vm.state.value.profileRevision)
        assertFalse(vm.state.value.profileSaving)

        authoritative.complete(profile("nhsk3", paid = true, name = "Updated"))
        runCurrent()
        assertEquals("Updated", vm.state.value.profile!!.user.name)
        assertEquals("nhsk3", vm.state.value.profile!!.user.level)
        assertTrue(vm.state.value.profile!!.subscription.isPaid)
        assertFalse(vm.state.value.isLoading)
    }

    @Test fun olderFailedSaveCannotCancelANewerApprovedCourseAndAccessRead() = runTest(dispatcher) {
        val f = Fixture()
        f.nextRead().complete(profile("hsk2", paid = false))
        val vm = f.model()
        runCurrent()
        vm.saveProfile("Updated", "panda")
        runCurrent()
        val approved = f.nextRead()
        vm.load()
        runCurrent()

        f.saveReply.complete(Response.error(503, "unavailable".toResponseBody()))
        runCurrent()
        assertTrue(vm.state.value.error != null)
        assertTrue(vm.state.value.isLoading)
        assertFalse(vm.state.value.profileSaving)
        assertEquals(0, vm.state.value.profileRevision)
        assertEquals("hsk2", vm.state.value.profile!!.user.level)

        approved.complete(profile("nhsk3", paid = true))
        runCurrent()
        assertEquals("nhsk3", vm.state.value.profile!!.user.level)
        assertTrue(vm.state.value.profile!!.subscription.isPaid)
        assertTrue(vm.state.value.error == null)
        assertFalse(vm.state.value.isLoading)
    }

    @Test fun successfulTrialRefreshSupersedesTheOldInactiveTrial() = runTest(dispatcher) {
        val f = Fixture()
        val old = f.nextRead()
        val vm = f.model()
        runCurrent()
        vm.startTrial()
        runCurrent()
        val active = f.nextRead()
        f.startReply.complete(Response.success(AndroidTrialStartResponse(ok = true)))
        runCurrent()
        active.complete(profile(), activeTrial = true)
        runCurrent()
        old.complete(profile(), activeTrial = false)
        runCurrent()

        assertTrue(vm.state.value.trial!!.active)
        assertFalse(vm.state.value.trialStarting)
        assertFalse(vm.state.value.isLoading)
    }
}
