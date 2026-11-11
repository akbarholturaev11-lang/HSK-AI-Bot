package com.pomp.hskai.feature.onboarding

import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.*
import com.pomp.hskai.data.repository.OnboardingRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.*
import org.junit.*
import org.junit.Assert.*
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class OnboardingViewModelTest {
    private val dispatcher = StandardTestDispatcher()
    @Before fun setup() = Dispatchers.setMain(dispatcher)
    @After fun teardown() = Dispatchers.resetMain()
    private class Fake(private val li: Boolean, private val completed: Boolean = false) : AndroidOnboardingApi {
        var request: AndroidOnboardingRequestDto? = null
        var writes = 0
        override suspend fun status(authorization: String) = Response.success(AndroidOnboardingStatusDto(ok = true, completed = completed, liEnabled = li))
        override suspend fun complete(authorization: String, body: AndroidOnboardingRequestDto): Response<AndroidOnboardingCompleteDto> {
            writes++; request = body
            return Response.success(AndroidOnboardingCompleteDto(ok = true, level = "hsk1", lesson = 1))
        }
        fun model() = OnboardingViewModel(OnboardingRepository(this, { ApiResult.Success("token") }, timezoneOffsetMinutes = { 480 }), "tj")
    }
    @Test fun legacyFlagOffKeepsFourStepsAndNoOptionalPayload() = runTest(dispatcher) {
        val fake = Fake(false); val vm = fake.model(); runCurrent()
        repeat(4) { vm.next() }; runCurrent()
        assertTrue(vm.state.value.completed)
        assertNull(fake.request?.goals)
        assertNull(fake.request?.streakTargetDays)
        assertEquals(1, fake.writes)
    }
    @Test fun nativeChoicesHaveStablePrimaryAndSaveOnceBeforeRealProIntro() = runTest(dispatcher) {
        val fake = Fake(true); val vm = fake.model(); runCurrent()
        vm.selectGoal("travel"); vm.selectGoal("hsk_exam")
        vm.selectDailyMinutes(20); vm.selectFocus("listening"); vm.selectStreak(30)
        repeat(8) { vm.next() }; runCurrent()
        assertEquals(listOf("travel"), fake.request?.goals)
        assertEquals("travel", fake.request?.goal)
        assertEquals(20, fake.request?.dailyMinutes)
        assertEquals("listening", fake.request?.preferredFocus)
        assertEquals(30, fake.request?.streakTargetDays)
        assertFalse(vm.state.value.completed)
        assertEquals(8, vm.state.value.ui.step)
        vm.next(); vm.back(); runCurrent(); assertEquals(1, fake.writes)
        vm.finishIntro(); assertTrue(vm.state.value.completed)
    }
    @Test fun returningAccountSkipsDraftAndCannotResubmit() = runTest(dispatcher) {
        val fake = Fake(true, completed = true); val vm = fake.model(); runCurrent()
        repeat(9) { vm.next() }; runCurrent()
        assertEquals(0, fake.writes)
        assertTrue(vm.state.value.completed)
    }
}
