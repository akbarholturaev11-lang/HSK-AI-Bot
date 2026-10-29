package com.pomp.hskai.widget

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.mutablePreferencesOf
import androidx.datastore.preferences.core.stringPreferencesKey
import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.*
import java.time.ZoneId
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import org.junit.Assert.*
import org.junit.Test

private class ContextPreferences : DataStore<Preferences> {
    override val data = MutableStateFlow(emptyPreferences())
    override suspend fun updateData(transform: suspend (Preferences) -> Preferences): Preferences =
        transform(data.value).also { data.value = it }
}

class WidgetPersonalContextTest {
    private fun changed(raw: JsonObject = PersonalFixtures.raw(), vararg pairs: Pair<String, JsonElement>) =
        JsonObject(raw.toMutableMap().apply { putAll(pairs) })

    @Test fun `the real Retrofit adapter sends only passive protocol fields and bearer header`() = runTest {
        val server=MockWebServer()
        try {
            server.enqueue(MockResponse().setBody("{\"ok\":true}"))
            val api=Retrofit.Builder().baseUrl(server.url("/"))
                .addConverterFactory(Json.asConverterFactory("application/json".toMediaType()))
                .build().create(AndroidEventsApi::class.java)
            assertTrue(api.widgetMap("Bearer synthetic",0,1,PersonalFixtures.EPOCH).isSuccessful)
            val request=server.takeRequest()
            assertEquals("Bearer synthetic",request.getHeader("Authorization"))
            assertEquals("/api/v3/android/course/map",request.requestUrl!!.encodedPath)
            assertEquals(setOf("tz","widget_context_version","widget_context_epoch"),request.requestUrl!!.queryParameterNames)
            assertEquals("1",request.requestUrl!!.queryParameter("widget_context_version"))
            assertEquals(PersonalFixtures.EPOCH,request.requestUrl!!.queryParameter("widget_context_epoch"))
            assertEquals(0L,request.bodySize)
        } finally { server.shutdown() }
    }

    @Test fun `strict wire flags numbers extra fields and semantic forgeries are rejected`() {
        val invalid = listOf(
            changed(pairs = arrayOf("version" to JsonPrimitive(2))),
            changed(pairs = arrayOf("version" to JsonPrimitive("1"))),
            changed(pairs = arrayOf("dispatch_allowed" to JsonPrimitive(0))),
            changed(pairs = arrayOf("dispatch_allowed" to JsonPrimitive("false"))),
            changed(pairs = arrayOf("dispatch_allowed" to JsonPrimitive(true))),
            changed(pairs = arrayOf("plan_completed" to JsonPrimitive(1))),
            changed(pairs = arrayOf("token" to JsonPrimitive("forbidden"))),
            changed(pairs = arrayOf("track" to JsonPrimitive("hsk30"))),
            changed(pairs = arrayOf("phase" to JsonPrimitive("completed"))),
            changed(pairs = arrayOf("goal_state" to JsonPrimitive("met"))),
            changed(pairs = arrayOf("lesson_order" to JsonPrimitive(99))),
            changed(pairs = arrayOf("time_local" to JsonPrimitive("14:00:00"))),
        )
        invalid.forEach { assertNull(it.toString(), WidgetPersonalContext.parse(it)) }
        assertNull(WidgetPersonalContext.parse(JsonPrimitive("bad")))
        assertNull(WidgetPersonalContext.parse(JsonArray(emptyList())))
    }

    @Test fun `an arbitrary cached envelope cannot establish a current binding`() = runTest {
        val store = WidgetStore(ContextPreferences()); store.linked()
        val epoch = store.read().epoch
        val raw = changed(pairs = arrayOf("request_epoch" to JsonPrimitive(epoch)))
        store.save(PersonalFixtures.snapshot(raw), epoch)
        assertNull(store.read().contextBinding)
        assertNull(store.read().snapshot?.personalContext)
        assertEquals("neutral", WidgetVisualResolver.resolve(store.read(), PersonalFixtures.now(raw)).personalPhase)
    }

    @Test fun `live acceptance preserves flags while older revisions generations and ordinary maps cannot rewind`() = runTest {
        val store = WidgetStore(ContextPreferences()); store.linked(); store.setReminder(true)
        val epoch = store.read().epoch
        val raw = changed(pairs = arrayOf("request_epoch" to JsonPrimitive(epoch)))
        val now = PersonalFixtures.now(raw)
        val ticket = store.beginRefresh(epoch)!!
        assertTrue(store.savePersonal(PersonalFixtures.snapshot(raw), raw, ticket, now))
        assertTrue(store.read().reminderEnabled)
        assertTrue(store.read().events.isEmpty())
        val accepted = store.read().snapshot
        store.save(PersonalFixtures.snapshot(raw).copy(level = "hsk2", xp = 9999), epoch)
        assertEquals(accepted, store.read().snapshot)
        val newer = store.beginRefresh(epoch)!!
        assertFalse(store.savePersonal(PersonalFixtures.snapshot(raw), changed(raw,
            "revision" to JsonPrimitive(1)), newer, now))
        assertEquals(accepted, store.read().snapshot)
        assertFalse(store.savePersonal(PersonalFixtures.snapshot(raw), raw, ticket, now))
        assertEquals(accepted, store.read().snapshot)
    }

    @Test fun `generated time cannot rewind and expiry is checked at durable acceptance`() = runTest {
        val store = WidgetStore(ContextPreferences()); store.linked()
        val raw = changed(pairs = arrayOf("request_epoch" to JsonPrimitive(store.read().epoch)))
        val now = PersonalFixtures.now(raw)
        assertTrue(store.savePersonal(PersonalFixtures.snapshot(raw), raw, store.beginRefresh(store.read().epoch)!!, now))
        val accepted = store.read().snapshot
        val earlier = changed(raw,"generated_at" to JsonPrimitive(now.minusSeconds(1).toInstant().toString()))
        assertFalse(store.savePersonal(PersonalFixtures.snapshot(earlier),earlier,store.beginRefresh(store.read().epoch)!!,now))
        assertEquals(accepted,store.read().snapshot)
        assertFalse(store.savePersonal(PersonalFixtures.snapshot(raw),raw,store.beginRefresh(store.read().epoch)!!,now,
            clock = { now.plusHours(2) }))
        assertNull(store.read().snapshot)
    }

    @Test fun `known foreground changes and logout fence already pending responses`() = runTest {
        val store = WidgetStore(ContextPreferences()); store.linked()
        val epoch = store.read().epoch
        val raw = changed(pairs = arrayOf("request_epoch" to JsonPrimitive(epoch)))
        val old = store.beginRefresh(epoch)!!
        store.invalidateContext(epoch)
        assertFalse(store.savePersonal(PersonalFixtures.snapshot(raw), raw, old, PersonalFixtures.now(raw)))
        val current = store.beginRefresh(epoch)!!
        assertTrue(store.savePersonal(PersonalFixtures.snapshot(raw), raw, current, PersonalFixtures.now(raw)))
        store.clear(); store.linked()
        store.failedRefresh(current)
        assertFalse(store.savePersonal(PersonalFixtures.snapshot(raw), raw, current, PersonalFixtures.now(raw)))
        assertNull(store.read().snapshot)
        assertNotEquals(epoch, store.read().epoch)
    }

    @Test fun `wrong binding and expired future or changed zone frames cannot become personal`() = runTest {
        val store = WidgetStore(ContextPreferences()); store.linked()
        val epoch = store.read().epoch
        val raw = changed(pairs = arrayOf("request_epoch" to JsonPrimitive(epoch)))
        val now = PersonalFixtures.now(raw)
        assertTrue(store.savePersonal(PersonalFixtures.snapshot(raw), raw, store.beginRefresh(epoch)!!, now))
        for (at in listOf(now.minusNanos(1), now.plusHours(2), now.withZoneSameInstant(ZoneId.of("Asia/Tashkent")))) {
            assertFalse(store.savePersonal(PersonalFixtures.snapshot(raw), raw, store.beginRefresh(epoch)!!, at))
            assertNull(store.read().snapshot)
        }
        assertFalse(store.savePersonal(PersonalFixtures.snapshot(raw), changed(raw,"binding" to JsonPrimitive("b".repeat(64))),
            store.beginRefresh(epoch)!!, now))
        assertEquals(PersonalFixtures.BINDING, store.read().contextBinding)
    }

    @Test fun `unsupported cached personal data remains linked and neutral on a fresh process`() = runTest {
        val memory = ContextPreferences()
        val snapshot = PersonalFixtures.snapshot().copy(personalContext = JsonPrimitive("future representation"))
        val encoded = Json.encodeToString(WidgetSession.serializer(), WidgetSession(
            epoch = PersonalFixtures.EPOCH, linked = true, snapshot = snapshot))
        memory.updateData { mutablePreferencesOf(stringPreferencesKey("session_v1") to encoded) }
        val session = WidgetStore(memory).read()
        assertTrue(session.linked)
        assertNotNull(session.snapshot)
        assertEquals("neutral", WidgetVisualResolver.resolve(session, PersonalFixtures.now()).personalPhase)
    }

    private fun frame(raw: JsonObject): JsonObject {
        val dto = CourseMapDto(ok = true, level = raw.getValue("level").jsonPrimitive.content,
            progress = CourseProgressDto(xp = 500, dailyXp = 500, streak = 7,
                localDate = PersonalFixtures.now(raw).toLocalDate().toString()),
            units = listOf(CourseUnitDto(number = 1, lessons = listOf(CourseLessonDto(order = 6, status = "current")))))
        return JsonObject(Json.encodeToJsonElement(CourseMapDto.serializer(), dto).jsonObject + ("widget_context" to raw))
    }

    @Test fun `the actual refresh bridge captures epoch token and bounded offset before request`() = runTest {
        val store = WidgetStore(ContextPreferences()); store.linked(); store.setReminder(true)
        var calls = 0
        val raw = changed(pairs = arrayOf("request_epoch" to JsonPrimitive(store.read().epoch)))
        val bridge = WidgetRefreshBridge(store, { ApiResult.Success(AuthRepository.AuthenticatedSession("synthetic", 7)) },
            { generation, accept -> if (generation == 7L) { accept(); true } else false }, { error("No invalidation") }, fetch = { token, epoch, offset ->
                assertEquals("synthetic",token);assertEquals(store.read().epoch,epoch);assertEquals(0,offset)
                calls++;ApiResult.Success(frame(raw))
            }, clock = { PersonalFixtures.now(raw) })
        bridge.refresh()
        assertEquals(1,calls)
        assertEquals("before_study",WidgetVisualResolver.resolve(store.read(),PersonalFixtures.now(raw)).personalPhase)
        assertTrue(store.read().reminderEnabled);assertTrue(store.read().events.isEmpty())
    }

    @Test fun `late old session success and failure cannot affect the replacement account`() = runTest {
        for (failure in listOf(false,true)) {
            val store=WidgetStore(ContextPreferences());store.linked()
            val epoch=store.read().epoch
            val raw=changed(pairs=arrayOf("request_epoch" to JsonPrimitive(epoch)))
            val entered=CompletableDeferred<Unit>();val finish=CompletableDeferred<Unit>()
            var generation=1L;var invalidations=0
            val bridge=WidgetRefreshBridge(store,{ApiResult.Success(AuthRepository.AuthenticatedSession("old",1))},
                {g,accept->if(g==generation){accept();true}else false},{g->if(g==generation){invalidations++;store.clear()}},fetch={_,_,_->entered.complete(Unit);finish.await()
                    if(failure)ApiResult.Failure(ApiError.SessionExpired) else ApiResult.Success(frame(raw))},
                clock={PersonalFixtures.now(raw)})
            val request=async{bridge.refresh()};entered.await()
            generation=2;store.clear();store.linked();finish.complete(Unit);request.await()
            assertTrue(store.read().linked);assertNull(store.read().snapshot)
            assertNotEquals(epoch,store.read().epoch);assertEquals(0,invalidations)
        }
    }

    @Test fun `unlinked bridge has zero auth network and events and failed refresh is stale`() = runTest {
        val store=WidgetStore(ContextPreferences());var calls=0
        val bridge=WidgetRefreshBridge(store,{calls++;ApiResult.Failure(ApiError.Unknown)},
            {_,_->error("No session")},{error("No invalidation")},fetch={_,_,_->error("No transport")})
        bridge.refresh();assertEquals(0,calls)
        store.linked();bridge.refresh();assertEquals(1,calls)
        assertTrue(store.read().linked);assertNull(store.read().snapshot);assertTrue(store.read().events.isEmpty())
    }
}
