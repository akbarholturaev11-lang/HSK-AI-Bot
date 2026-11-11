package com.pomp.hskai.feature.onboarding

import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.*
import com.pomp.hskai.data.repository.OnboardingRepository
import kotlinx.coroutines.CompletableDeferred
import okhttp3.ResponseBody.Companion.toResponseBody
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
    private class Fake(private var li: Boolean, private val completed: Boolean = false) : AndroidOnboardingApi {
        var request: AndroidOnboardingRequestDto? = null
        var statusReads = 0
        var writeAuthorization: String? = null
        var writes = 0
        var disableOnSave = false
        var track = AndroidHsk30OnboardingDto()
        override suspend fun status(authorization: String): Response<AndroidOnboardingStatusDto> {
            statusReads++
            return Response.success(AndroidOnboardingStatusDto(ok = true, completed = completed, liEnabled = li, hsk30 = track))
        }
        override suspend fun complete(authorization: String, body: AndroidOnboardingRequestDto): Response<AndroidOnboardingCompleteDto> {
            writes++; request = body; writeAuthorization = authorization
            if (disableOnSave) {
                disableOnSave = false; li = false
                return Response.error(422, """{"ok":false,"error":"android_li_onboarding_disabled"}""".toResponseBody())
            }
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
    @Test fun rolloutDisabledDuringChoicesReturnsToUsableLegacyForm() = runTest(dispatcher) {
        val fake=Fake(true); val vm=fake.model(); runCurrent()
        fake.disableOnSave=true
        repeat(8) { vm.next() }; runCurrent()
        assertFalse(vm.state.value.ui.liEnabled)
        assertEquals(3,vm.state.value.ui.step)
        assertFalse(vm.state.value.completed)
        vm.next(); runCurrent()
        assertNull(fake.request?.goals)
        assertTrue(vm.state.value.completed)
    }
    @Test fun olderStatusCannotUndoACommittedOnboardingSave() = runTest(dispatcher) {
        val late=CompletableDeferred<Response<AndroidOnboardingStatusDto>>()
        var reads=0
        val api=object:AndroidOnboardingApi {
            override suspend fun status(authorization:String):Response<AndroidOnboardingStatusDto> =
                if (++reads==1) Response.success(AndroidOnboardingStatusDto(ok=true)) else late.await()
            override suspend fun complete(authorization:String,body:AndroidOnboardingRequestDto)=
                Response.success(AndroidOnboardingCompleteDto(ok=true,level="hsk1",lesson=1))
        }
        val vm=OnboardingViewModel(OnboardingRepository(api,{ ApiResult.Success("test") }),"uz")
        runCurrent(); vm.loadStatus(showSplash=false); runCurrent()
        repeat(4) { vm.next() }; runCurrent(); assertTrue(vm.state.value.completed)
        late.complete(Response.success(AndroidOnboardingStatusDto(ok=true,completed=false)))
        runCurrent(); assertTrue(vm.state.value.completed); assertEquals(1,vm.state.value.launch?.lesson)
    }

    @Test fun guestFinishesChoicesWithoutReadingBearerOrWritingProfile() = runTest(dispatcher) {
        val api = Fake(true)
        var saved: GuestLiDraft? = null
        val model = OnboardingViewModel(
            OnboardingRepository(api, { error("Guest cannot read an access token") }), "uz",
            guestPreview = AndroidOnboardingStatusDto(ok = true, liEnabled = true),
            onGuestReady = { saved = it },
        )
        model.selectDailyMinutes(20)
        repeat(8) { model.next() }
        runCurrent()
        assertEquals(20, saved?.minutes)
        assertEquals(0, api.statusReads)
        assertEquals(0, api.writes)
        assertNull(model.state.value.launch)
    }

    @Test fun guestDraftResumesOnceUsingTheSameVerifiedBearer() = runTest(dispatcher) {
        val api = Fake(true)
        var tokens = 0
        var claims = 0
        val model = OnboardingViewModel(
            OnboardingRepository(api, { ApiResult.Success("session-${++tokens}") }), "uz",
            claimGuestDraft = {
                claims++
                GuestLiDraft.from(OnboardingUiState(dailyMinutes = 20))
            },
        )
        model.loadStatus()
        runCurrent()
        assertEquals(1, claims)
        assertEquals(1, tokens)
        assertEquals(1, api.writes)
        assertEquals("Bearer session-1", api.writeAuthorization)
        assertEquals("native_li_guest_v1", api.request?.activationVariant)
        assertEquals(20, api.request?.dailyMinutes)
        assertEquals(8, model.state.value.ui.step)
    }

    @Test fun savedAccountAndDisabledFlagNeverReplayGuestDraft() = runTest(dispatcher) {
        listOf(Fake(true, completed = true), Fake(false)).forEach { api ->
            var claims = 0
            val model = OnboardingViewModel(
                OnboardingRepository(api, { ApiResult.Success("verified") }), "uz",
                claimGuestDraft = { claims++; GuestLiDraft.from(OnboardingUiState()) },
            )
            runCurrent()
            assertEquals(1, claims)
            assertEquals(0, api.writes)
            assertEquals(0, model.state.value.ui.step)
        }
    }

    @Test fun guestTrackWithoutVerifiedAccessReturnsToTrackChoice() = runTest(dispatcher) {
        val api = Fake(true).apply {
            track = AndroidHsk30OnboardingDto(enabled = true, allowed = false, liveLevels = listOf("nhsk1"))
        }
        val model = OnboardingViewModel(
            OnboardingRepository(api, { ApiResult.Success("verified") }), "uz",
            claimGuestDraft = {
                GuestLiDraft.from(OnboardingUiState(selectedTrack = "hsk30", selectedLevel = "nhsk1", dailyMinutes = 20))
            },
        )
        runCurrent()
        assertEquals(0, api.writes)
        assertEquals(1, model.state.value.ui.step)
        assertEquals("hsk20", model.state.value.ui.selectedTrack)
        assertEquals(20, model.state.value.ui.dailyMinutes)
    }
}
