package com.pomp.hskai.feature.course

import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.api.CourseHsk30AccessDto
import com.pomp.hskai.data.api.CourseHsk30Dto
import com.pomp.hskai.data.api.CourseLessonDto
import com.pomp.hskai.data.api.CourseMapDto
import com.pomp.hskai.data.api.CourseTrackSwitchRequest
import com.pomp.hskai.data.api.CourseUnitDto
import com.pomp.hskai.data.api.OkResponse
import com.pomp.hskai.data.local.CourseMapCacheEntity
import com.pomp.hskai.data.local.CourseMapDao
import com.pomp.hskai.data.repository.CourseRepository
import java.io.IOException
import java.lang.reflect.Proxy
import java.net.SocketTimeoutException
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
import kotlinx.serialization.json.Json
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class CourseRefreshQueueTest {
    private val dispatcher = StandardTestDispatcher()
    @Before fun setUp() = Dispatchers.setMain(dispatcher)
    @After fun tearDown() = Dispatchers.resetMain()

    private fun map(level: String = "nhsk1", allowed: Boolean = false) = CourseMapDto(
        ok = true,
        level = level,
        units = listOf(CourseUnitDto(
            number = 1,
            lessons = listOf(CourseLessonDto(order = 1, status = "current")),
        )),
        hsk30 = CourseHsk30Dto(
            activeTrack = if (level.startsWith("nhsk")) "hsk30" else "hsk20",
            activeLevel = level,
            access = CourseHsk30AccessDto(
                featureEnabled = true, permanentlyUnlocked = allowed, allowed = allowed,
            ),
        ),
    )

    private class Fixture {
        private val maps = ArrayDeque<CompletableDeferred<Response<CourseMapDto>>>()
        private val switches = ArrayDeque<CompletableDeferred<Response<OkResponse>>>()
        var mapCalls = 0
            private set
        val switchRequests = mutableListOf<CourseTrackSwitchRequest>()

        fun nextMap() = CompletableDeferred<Response<CourseMapDto>>().also(maps::add)
        fun nextSwitch() = CompletableDeferred<Response<OkResponse>>().also(switches::add)

        @Suppress("UNCHECKED_CAST")
        private fun <T> respond(reply: CompletableDeferred<T>, args: Array<out Any>?): Any? =
            (suspend { reply.await() }).startCoroutineUninterceptedOrReturn(args!!.last() as Continuation<T>)

        val api = Proxy.newProxyInstance(
            AndroidCourseApi::class.java.classLoader, arrayOf(AndroidCourseApi::class.java),
        ) { _, method, args ->
            when (method.name) {
                "courseMap" -> {
                    mapCalls++
                    check(maps.isNotEmpty()) { "Unexpected map retry" }
                    respond(maps.removeFirst(), args)
                }
                "switchCourseTrack" -> {
                    switchRequests.add(args!![1] as CourseTrackSwitchRequest)
                    check(switches.isNotEmpty()) { "Unexpected track POST retry" }
                    respond(switches.removeFirst(), args)
                }
                else -> error("Unexpected API call: ${method.name}")
            }
        } as AndroidCourseApi

        fun model() = CourseViewModel(CourseRepository(
            api = api,
            accessToken = { ApiResult.Success("test-token") },
            dao = QueueCourseMapDao(),
            json = Json { ignoreUnknownKeys = true },
        ))
    }

    private class QueueCourseMapDao : CourseMapDao {
        private val rows = mutableMapOf<String, CourseMapCacheEntity>()
        override suspend fun find(level: String) = rows[level]
        override suspend fun findMostRecent() = rows.values.maxByOrNull { it.fetchedAtMillis }
        override suspend fun upsert(entity: CourseMapCacheEntity) { rows[entity.level] = entity }
        override suspend fun clear() { rows.clear() }
    }

    @Test fun approvalDuringAnOlderAccessReadGetsOneFreshMapAfterTheBurst() = runTest(dispatcher) {
        val f = Fixture()
        val older = f.nextMap()
        val approved = f.nextMap()
        val vm = f.model()
        runCurrent()
        repeat(20) { vm.load() }
        assertEquals(1, f.mapCalls)

        older.complete(Response.success(map(allowed = false)))
        runCurrent()
        assertEquals(2, f.mapCalls)
        assertFalse(vm.state.value.map!!.hsk30!!.access.allowed)
        assertTrue(vm.state.value.isRefreshing)
        approved.complete(Response.success(map(allowed = true)))
        runCurrent()

        assertTrue(vm.state.value.map!!.hsk30!!.access.allowed)
        assertFalse(vm.state.value.isRefreshing)
        assertEquals(2, f.mapCalls)
        assertTrue(f.switchRequests.isEmpty())
    }

    @Test fun refreshWaitsForTheOverlappingTrackPostAndItsConfirmation() = runTest(dispatcher) {
        val f = Fixture()
        val older = f.nextMap()
        val confirmation = f.nextMap()
        val approved = f.nextMap()
        val post = f.nextSwitch()
        val vm = f.model()
        runCurrent()
        vm.switchCourseTrack("hsk30", "nhsk3")
        runCurrent()
        repeat(10) { vm.load() }
        post.complete(Response.success(OkResponse(ok = true)))
        runCurrent()
        assertEquals(1, f.mapCalls)
        assertTrue(vm.state.value.isSwitchingTrack)

        older.complete(Response.success(map("hsk1")))
        runCurrent()
        assertEquals(2, f.mapCalls)
        assertNull(vm.state.value.completedTrackSwitch)
        repeat(10) { vm.load() }
        confirmation.complete(Response.success(map("nhsk3")))
        runCurrent()
        assertEquals(3, f.mapCalls)
        assertFalse(vm.state.value.isSwitchingTrack)
        assertEquals(CourseTrackSwitchCompletion("hsk30", "nhsk3"), vm.state.value.completedTrackSwitch)
        approved.complete(Response.success(map("nhsk3", allowed = true)))
        runCurrent()

        assertEquals("nhsk3", vm.state.value.map!!.level)
        assertTrue(vm.state.value.map!!.hsk30!!.access.allowed)
        assertEquals(listOf(CourseTrackSwitchRequest("hsk30", "nhsk3")), f.switchRequests)
        assertEquals(3, f.mapCalls)
        assertFalse(vm.state.value.isRefreshing)
    }

    @Test fun queuedOfflineReadsKeepTheStaleMapAndStopWithoutRetryingForever() = runTest(dispatcher) {
        val f = Fixture()
        f.nextMap().complete(Response.success(map()))
        val vm = f.model()
        runCurrent()
        val failing = f.nextMap()
        val queued = f.nextMap()
        vm.load()
        runCurrent()
        repeat(20) { vm.load() }
        failing.completeExceptionally(IOException("offline"))
        runCurrent()
        assertEquals(3, f.mapCalls)
        assertTrue(vm.state.value.isRefreshing)
        assertTrue(vm.state.value.isStale)
        queued.completeExceptionally(IOException("still offline"))
        runCurrent()

        assertEquals("nhsk1", vm.state.value.map!!.level)
        assertTrue(vm.state.value.isStale)
        assertEquals(ApiError.Offline, vm.state.value.snapshot!!.refreshError)
        assertFalse(vm.state.value.isRefreshing)
        assertFalse(vm.state.value.isSwitchingTrack)
        runCurrent()
        assertEquals(3, f.mapCalls)
    }

    @Test fun aFailedTrackPostStillDrainsTheQueuedRefreshWithoutAnotherPost() = runTest(dispatcher) {
        val f = Fixture()
        f.nextMap().complete(Response.success(map("hsk1")))
        val vm = f.model()
        runCurrent()
        val post = f.nextSwitch()
        val approved = f.nextMap()
        vm.switchCourseTrack("hsk30", "nhsk2")
        runCurrent()
        repeat(10) { vm.load() }
        post.completeExceptionally(SocketTimeoutException("timeout"))
        runCurrent()

        assertFalse(vm.state.value.isSwitchingTrack)
        assertTrue(vm.state.value.isRefreshing)
        assertEquals(ApiError.Timeout, vm.state.value.trackError)
        assertEquals("hsk1", vm.state.value.map!!.level)
        approved.complete(Response.success(map("hsk1", allowed = true)))
        runCurrent()
        assertEquals(ApiError.Timeout, vm.state.value.trackError)
        assertNull(vm.state.value.completedTrackSwitch)
        assertEquals(1, f.switchRequests.size)
        assertEquals(2, f.mapCalls)
        assertTrue(vm.state.value.map!!.hsk30!!.access.allowed)
        assertFalse(vm.state.value.isRefreshing)
    }

    @Test fun queuedConfirmationRetriesOnlyGetAndKeepsTheWrongMapHidden() = runTest(dispatcher) {
        val f = Fixture()
        f.nextMap().complete(Response.success(map("hsk1")))
        val vm = f.model()
        runCurrent()
        f.nextSwitch().complete(Response.success(OkResponse(ok = true)))
        val wrongMap = f.nextMap()
        val confirmed = f.nextMap()
        vm.switchCourseTrack("hsk30", "nhsk2")
        runCurrent()
        repeat(10) { vm.load() }
        wrongMap.complete(Response.success(map("nhsk1")))
        runCurrent()

        assertEquals(3, f.mapCalls)
        assertNull(vm.state.value.snapshot)
        assertNull(vm.state.value.completedTrackSwitch)
        assertTrue(vm.state.value.isSwitchingTrack)
        confirmed.complete(Response.success(map("nhsk2", allowed = true)))
        runCurrent()
        assertEquals(CourseTrackSwitchCompletion("hsk30", "nhsk2"), vm.state.value.completedTrackSwitch)
        assertEquals("nhsk2", vm.state.value.map!!.level)
        assertEquals(1, f.switchRequests.size)
        assertFalse(vm.state.value.isRefreshing)
    }

    @Test fun aFailedQueuedConfirmationStopsAndAnExplicitRetryRemainsGetOnly() = runTest(dispatcher) {
        val f = Fixture()
        f.nextMap().complete(Response.success(map("hsk1")))
        val vm = f.model()
        runCurrent()
        f.nextSwitch().complete(Response.success(OkResponse(ok = true)))
        val failing = f.nextMap()
        val queued = f.nextMap()
        vm.switchCourseTrack("hsk30", "nhsk3")
        runCurrent()
        repeat(10) { vm.load() }
        failing.completeExceptionally(IOException("offline"))
        runCurrent()
        queued.completeExceptionally(IOException("still offline"))
        runCurrent()

        assertNull(vm.state.value.snapshot)
        assertNull(vm.state.value.completedTrackSwitch)
        assertNotNull(vm.state.value.error)
        assertFalse(vm.state.value.isSwitchingTrack)
        assertFalse(vm.state.value.isRefreshing)
        runCurrent()
        assertEquals(3, f.mapCalls)
        assertEquals(1, f.switchRequests.size)

        f.nextMap().complete(Response.success(map("nhsk3", allowed = true)))
        vm.retryTrackSwitch()
        runCurrent()
        assertEquals(4, f.mapCalls)
        assertEquals(1, f.switchRequests.size)
        assertEquals(CourseTrackSwitchCompletion("hsk30", "nhsk3"), vm.state.value.completedTrackSwitch)
    }
}
