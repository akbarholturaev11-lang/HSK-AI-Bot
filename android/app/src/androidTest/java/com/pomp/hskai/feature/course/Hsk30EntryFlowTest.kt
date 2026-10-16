package com.pomp.hskai.feature.course

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.runtime.MutableState
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertTextEquals
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.data.api.CourseHsk30AccessDto
import com.pomp.hskai.data.api.CourseHsk30Dto
import com.pomp.hskai.data.api.CourseLessonDto
import com.pomp.hskai.data.api.CourseMapDto
import com.pomp.hskai.data.api.CourseUnitDto
import com.pomp.hskai.data.api.CourseUserDto
import com.pomp.hskai.data.api.LocalizedText
import com.pomp.hskai.data.repository.CourseMapSnapshot
import com.pomp.hskai.data.repository.CourseMapper
import com.pomp.hskai.feature.limit.LimitGate
import com.pomp.hskai.feature.assistant.AssistantBinding
import com.pomp.hskai.feature.assistant.LocalAssistant
import com.pomp.hskai.feature.assistant.ScreenRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/** Server access and payment availability drive the real course entry dialog. */
@RunWith(AndroidJUnit4::class)
class Hsk30EntryFlowTest {
    @get:Rule val compose = createComposeRule()
    private val strings = InstrumentationRegistry.getInstrumentation().targetContext.resources
    private val assistantRegistry = ScreenRegistry()
    private val lockedAccess = CourseHsk30AccessDto(
        featureEnabled = true,
        allowed = false,
        reason = "hsk30_unlock_required",
    )

    private fun courseState(
        level: String = "nhsk1",
        access: CourseHsk30AccessDto = lockedAccess,
        paymentEnabled: Boolean = true,
        priceTjs: Int = 10,
        priceDisplay: String = "$1.08",
    ): CourseUiState {
        val dto = CourseMapDto(
            ok = true,
            level = level,
            user = CourseUserDto(language = "uz", isPaid = access.paidAccess),
            units = listOf(CourseUnitDto(
                number = 1,
                title = LocalizedText(uz = "Salomlashish"),
                lessons = listOf(CourseLessonDto(
                    order = 1,
                    sourceLesson = 1,
                    part = 1,
                    partCount = 1,
                    status = "current",
                    hanzi = "你好",
                    pinyin = "nǐ hǎo",
                    subtitle = LocalizedText(uz = "Salom"),
                    completionAllowed = access.allowed,
                    lockedPremium = !access.allowed,
                )),
            )),
            hsk30 = CourseHsk30Dto(
                activeTrack = "hsk30",
                activeLevel = level,
                access = access,
                liveLevels = listOf("nhsk1", "nhsk2", "nhsk3"),
                paymentEnabled = paymentEnabled,
                priceTjs = priceTjs,
                priceDisplay = priceDisplay,
            ),
        )
        return CourseUiState(
            isLoading = false,
            snapshot = CourseMapSnapshot(CourseMapper.toDomain(dto), isStale = false, fetchedAtMillis = 1L),
        )
    }

    private fun showCourse(
        state: MutableState<CourseUiState>,
        onUnlock: () -> Unit = {},
        onSwitch: (String, String?) -> Unit = { _, _ -> },
    ) {
        val app = InstrumentationRegistry.getInstrumentation().targetContext.applicationContext as HskAiApplication
        val binding = AssistantBinding(assistantRegistry, app.assistant, {}, { _, _ -> })
        compose.setContent {
            CompositionLocalProvider(LocalAssistant provides binding) {
                PompHskAiTheme {
                    CourseScreen(
                        state = state.value,
                        dailyGoal = 30,
                        limit = LimitGate(),
                        onLesson = {},
                        onTodayTask = {},
                        onOpenGoal = {},
                        onOpenChest = {},
                        onChestRewardConsumed = {},
                        onSwitchTrack = onSwitch,
                        onUnlockHsk30 = onUnlock,
                        onRetry = {},
                    )
                }
            }
        }
    }


    @Test fun bundledHsk30BookImageDecodesOnAndroid() {
        val bitmap = requireNotNull(
            BitmapFactory.decodeResource(strings, R.drawable.hsk30_course_books)
        ) { "Packaged HSK 3.0 JPEG failed to decode on this Android device" }
        assertTrue(bitmap.width >= 640 && bitmap.height >= 400)
        bitmap.recycle()
    }

    @Test fun lockedN1N2AndN3OpenPaymentOnceAndReturnToTheLegacyTrack() {
        val state = mutableStateOf(courseState())
        var payments = 0
        val switches = mutableListOf<Pair<String, String?>>()
        showCourse(state, onUnlock = { payments++ }, onSwitch = { track, level -> switches += track to level })

        listOf("nhsk1", "nhsk2", "nhsk3").forEachIndexed { index, level ->
            compose.runOnIdle { state.value = courseState(level) }
            compose.onNodeWithText(strings.getString(R.string.hsk30_access_required_title))
                .performScrollTo().assertIsDisplayed()
            compose.onNodeWithText("$1.08").performScrollTo().assertIsDisplayed()
            compose.onNodeWithText(strings.getString(R.string.hsk30_access_unlock_button))
                .performScrollTo().assertIsEnabled().performClick()
            compose.runOnIdle { assertEquals(index + 1, payments) }
            compose.onNodeWithText(strings.getString(R.string.hsk30_access_back_hsk20))
                .performScrollTo().performClick()
            compose.runOnIdle {
                assertEquals(List(index + 1) { "hsk20" to null }, switches)
                assertEquals(index + 1, payments)
            }
        }
    }

    @Test fun paidPermanentAndProvisionalAccessKeepTheCourseOpen() {
        val cases = listOf(
            lockedAccess.copy(allowed = true, paidAccess = true, reason = "paid_subscription"),
            lockedAccess.copy(allowed = true, permanentlyUnlocked = true, reason = "permanent_unlock"),
            lockedAccess.copy(allowed = true, paymentPending = true, provisionalAccess = true, reason = "payment_pending"),
        )
        val state = mutableStateOf(courseState(access = cases.first()))
        showCourse(state)

        cases.forEach { access ->
            compose.runOnIdle { state.value = courseState(access = access) }
            compose.onNodeWithTag("course-level-heading").assertTextEquals("HSK 1")
            compose.onNodeWithText(strings.getString(R.string.hsk30_access_required_title)).assertDoesNotExist()
            compose.onNodeWithText(strings.getString(R.string.hsk30_access_unlock_button)).assertDoesNotExist()
            compose.onNodeWithText(strings.getString(R.string.hsk30_access_back_hsk20)).assertDoesNotExist()
        }
    }

    @Test fun disabledEntryPaymentWithFreeServerAccessKeepsCourseOpen() {
        val freeAccess = lockedAccess.copy(
            allowed = true,
            reason = "hsk30_free_access",
        )
        val state = mutableStateOf(courseState(
            access = freeAccess,
            paymentEnabled = false,
            priceDisplay = "",
        ))
        var payments = 0
        showCourse(state, onUnlock = { payments++ })

        compose.onNodeWithTag("course-level-heading").assertTextEquals("HSK 1")
        compose.onNodeWithText(strings.getString(R.string.hsk30_access_required_title)).assertDoesNotExist()
        compose.onNodeWithText(strings.getString(R.string.hsk30_access_unlock_button)).assertDoesNotExist()
        compose.runOnIdle { assertEquals(0, payments) }
    }

    @Test fun pandaStaysVisibleWhileServerConfirmsFreeHsk30Course() {
        val freeAccess = lockedAccess.copy(
            allowed = true,
            reason = "hsk30_free_access",
        )
        val state = mutableStateOf(
            courseState(access = freeAccess, paymentEnabled = false, priceDisplay = "")
                .copy(isSwitchingTrack = true)
        )
        showCourse(state)
        compose.onNodeWithText(strings.getString(R.string.course_track_preparing_title))
            .assertIsDisplayed()

        compose.runOnIdle { state.value = state.value.copy(isSwitchingTrack = false) }
        compose.onNodeWithText(strings.getString(R.string.course_track_preparing_title))
            .assertDoesNotExist()
        compose.onNodeWithTag("course-level-heading").assertTextEquals("HSK 1")
    }

    @Test fun courseHeaderPickerPreselectsSavedBandAndShowsVersions() {
        val freeAccess = lockedAccess.copy(allowed = true, reason = "hsk30_free_access")
        val state = mutableStateOf(courseState(access = freeAccess, paymentEnabled = false))
        val calls = mutableListOf<Pair<String, String?>>()
        showCourse(state, onSwitch = { track, level -> calls += track to level })

        compose.onNodeWithTag("course-level-heading").assertTextEquals("HSK 1").performClick()
        compose.onNodeWithText(strings.getString(R.string.course_choice_title)).assertIsDisplayed()
        compose.onNodeWithText("HSK 2.0").assertIsDisplayed()
        compose.onNodeWithText("HSK 3.0").assertIsDisplayed()
        compose.onNodeWithContentDescription(strings.getString(R.string.assistant_open)).assertDoesNotExist()
        compose.runOnIdle { assertTrue(assistantRegistry.current!!.hidesAssistant) }
        val sheet = compose.onNodeWithTag("course-choice-sheet").fetchSemanticsNode().boundsInRoot
        val confirm = compose.onNodeWithText(strings.getString(R.string.course_choice_confirm))
            .fetchSemanticsNode().boundsInRoot
        assertTrue(
            "Course selection must not reserve an empty assistant row below Confirm",
            sheet.bottom - confirm.bottom <= 80f * strings.displayMetrics.density,
        )
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        // Wait for the native sheet window to reach the display compositor.
        instrumentation.waitForIdleSync()
        Thread.sleep(500)
        val image = requireNotNull(instrumentation.uiAutomation.takeScreenshot())
        File(instrumentation.targetContext.getExternalFilesDir(null), "ui-fix-course-choice.png")
            .outputStream().use {
                image.compress(Bitmap.CompressFormat.PNG, 100, it)
            }
        compose.onNodeWithText("HSK 2.0").performClick()
        compose.onNodeWithText("HSK 3").assertIsDisplayed()
        compose.onNodeWithText(strings.getString(R.string.course_choice_confirm)).performClick()
        compose.runOnIdle {
            assertEquals(listOf("hsk20" to null), calls)
            assertTrue(!assistantRegistry.current!!.hidesAssistant)
        }
    }

    @Test fun unavailablePaymentExplainsTheBlockAndStillAllowsReturning() {
        val cases = listOf(
            courseState(paymentEnabled = false),
            courseState(priceTjs = 0),
            courseState(priceDisplay = ""),
        )
        val state = mutableStateOf(cases.first())
        var payments = 0
        val switches = mutableListOf<Pair<String, String?>>()
        showCourse(state, onUnlock = { payments++ }, onSwitch = { track, level -> switches += track to level })

        cases.forEachIndexed { index, unavailable ->
            compose.runOnIdle { state.value = unavailable }
            compose.onNodeWithText(strings.getString(R.string.hsk30_unlock_unavailable))
                .performScrollTo().assertIsDisplayed()
            compose.onNodeWithText(strings.getString(R.string.hsk30_access_unlock_button))
                .performScrollTo().assertIsNotEnabled()
            compose.onNodeWithText(strings.getString(R.string.hsk30_access_back_hsk20))
                .performScrollTo().performClick()
            compose.runOnIdle {
                assertEquals(0, payments)
                assertEquals(List(index + 1) { "hsk20" to null }, switches)
            }
        }
    }

    @Test fun returningHidesTheLockedDialogWhileTheServerSwitchIsInFlight() {
        val state = mutableStateOf(courseState())
        val switches = mutableListOf<Pair<String, String?>>()
        showCourse(state, onSwitch = { track, level ->
            switches += track to level
            state.value = state.value.copy(isSwitchingTrack = true)
        })
        compose.onNodeWithText(strings.getString(R.string.hsk30_access_back_hsk20))
            .performScrollTo().performClick()
        compose.onNodeWithText(strings.getString(R.string.hsk30_access_required_title)).assertDoesNotExist()
        compose.onNodeWithText(strings.getString(R.string.hsk30_access_unlock_button)).assertDoesNotExist()
        compose.onNodeWithText(strings.getString(R.string.hsk30_access_back_hsk20)).assertDoesNotExist()
        compose.runOnIdle { assertEquals(listOf("hsk20" to null), switches) }
    }
}
