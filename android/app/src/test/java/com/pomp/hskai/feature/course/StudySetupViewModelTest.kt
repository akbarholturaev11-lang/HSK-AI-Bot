package com.pomp.hskai.feature.course

import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidStudyPreferencesApi
import com.pomp.hskai.data.api.CourseStudySetupDto
import com.pomp.hskai.data.api.StudyPreferencesRequestDto
import com.pomp.hskai.data.api.StudyPreferencesResponseDto
import com.pomp.hskai.data.repository.StudyPreferencesRepository
import com.pomp.hskai.domain.model.CourseStudySetup
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class StudySetupViewModelTest {
    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setUp() {
        Dispatchers.setMain(dispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun refreshAfterTimeSaveKeepsFocusStage() = runTest(dispatcher) {
        val api = object : AndroidStudyPreferencesApi {
            override suspend fun setStudyPreferences(
                authorization: String,
                body: StudyPreferencesRequestDto,
            ): Response<StudyPreferencesResponseDto> = Response.success(
                StudyPreferencesResponseDto(
                    ok = true,
                    studySetup = CourseStudySetupDto(
                        goal = "hsk_exam",
                        goalChosen = true,
                        dailyMinutes = body.dailyMinutes ?: 10,
                        preferredFocus = null,
                        dailyGoalXp = 35,
                        dailyGoalIsCustom = false,
                        planSize = 2,
                        pendingGoal = false,
                        pending = true,
                    ),
                )
            )
        }
        val repository = StudyPreferencesRepository(
            api = api,
            accessToken = { ApiResult.Success("token") },
        )
        val viewModel = StudySetupViewModel(repository)
        val initial = CourseStudySetup(
            goal = "hsk_exam",
            goalChosen = true,
            dailyMinutes = 10,
            preferredFocus = null,
            dailyGoalXp = 30,
            dailyGoalIsCustom = false,
            planSize = 2,
            pendingGoal = false,
            pending = true,
        )

        viewModel.sync(initial)
        assertEquals(StudySetupStage.TIME, viewModel.state.value.stage)

        viewModel.chooseTime(15)
        advanceUntilIdle()
        assertEquals(StudySetupStage.FOCUS, viewModel.state.value.stage)
        assertTrue(viewModel.state.value.visible)

        viewModel.sync(initial.copy(dailyMinutes = 15, dailyGoalXp = 35))
        assertEquals(StudySetupStage.FOCUS, viewModel.state.value.stage)
        assertTrue(viewModel.state.value.visible)
    }
}
