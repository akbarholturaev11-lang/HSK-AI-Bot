package com.pomp.hskai.widget

import java.time.Instant
import java.time.ZoneId
import java.time.ZonedDateTime
import kotlinx.serialization.json.*
import org.junit.Assert.*
import org.junit.Test

internal object PersonalFixtures {
    const val EPOCH = "00000000-0000-4000-8000-000000000001"
    const val BINDING = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    val cases = Json.parseToJsonElement(requireNotNull(javaClass.classLoader?.getResourceAsStream(
        "smart_widget_context_v1.json")).bufferedReader().readText()).jsonObject.getValue("cases").jsonArray
    fun raw(name: String = "saved_before"): JsonObject = cases.first {
        it.jsonObject.getValue("name").jsonPrimitive.content == name
    }.jsonObject.getValue("context").jsonObject
    fun now(raw: JsonObject = raw()): ZonedDateTime = Instant.parse(raw.getValue("generated_at").jsonPrimitive.content)
        .atZone(ZoneId.of(raw["timezone_name"]?.jsonPrimitive?.contentOrNull ?: "Etc/UTC"))
    fun snapshot(raw: JsonObject = raw(), now: ZonedDateTime = now(raw)) = WidgetSnapshot(
        now.toInstant().toEpochMilli(), now.toLocalDate().toString(), now.zone.id,
        raw.getValue("level").jsonPrimitive.content, 6, 500, 7, true, false,
        dailyXp = 500, goalXp = 20, personalContext = raw)
    fun session(raw: JsonObject = raw(), now: ZonedDateTime = now(raw)) = WidgetSession(
        epoch = EPOCH, linked = true, snapshot = snapshot(raw, now), contextBinding = BINDING)
}

class WidgetVisualStateTest {
    @Test fun `all 31 backend envelopes retain identical personal meaning`() {
        assertEquals(31, PersonalFixtures.cases.size)
        for (case in PersonalFixtures.cases) {
            val raw = case.jsonObject.getValue("context").jsonObject
            val name = case.jsonObject.getValue("name").jsonPrimitive.content
            assertNotNull(name, WidgetPersonalContext.parse(raw))
            val phase = raw.getValue("phase").jsonPrimitive.content
            val visual = WidgetVisualResolver.resolve(PersonalFixtures.session(raw), PersonalFixtures.now(raw))
            assertEquals(name, phase, visual.personalPhase)
            assertEquals(name, when (phase) {
                "completed" -> WidgetVisualState.COMPLETED
                "study_time_reached" -> WidgetVisualState.WAITING
                else -> WidgetVisualState.DAY
            }, visual.state)
            assertFalse(name, visual.state in setOf(WidgetVisualState.LATE, WidgetVisualState.CRITICAL))
        }
    }

    @Test fun `a raw completed flag and reward XP cannot complete personal learning`() {
        val raw = PersonalFixtures.raw("reward_only_not_complete")
        val session = PersonalFixtures.session(raw)
        assertTrue(session.snapshot!!.dayComplete)
        assertEquals(500, session.snapshot!!.dailyXp)
        val visual = WidgetVisualResolver.resolve(session, PersonalFixtures.now(raw))
        assertNotEquals(WidgetVisualState.COMPLETED, visual.state)
        assertNull(visual.special)
        val legacy = session.copy(contextBinding = null)
        assertEquals("neutral", WidgetVisualResolver.resolve(legacy, PersonalFixtures.now(raw)).personalPhase)
    }

    @Test fun `legacy and unbound caches stay neutral at every global hour`() {
        val raw = PersonalFixtures.raw()
        val now = PersonalFixtures.now(raw)
        for (hour in 0..23) {
            val visual = WidgetVisualResolver.resolve(PersonalFixtures.snapshot(raw), PersonalFixtures.EPOCH, now.withHour(hour))
            assertEquals(WidgetVisualState.DAY, visual.state)
            assertEquals("neutral", visual.personalPhase)
        }
    }

    @Test fun `expiry future day and zone changes neutralize personal state`() {
        val raw = PersonalFixtures.raw()
        val now = PersonalFixtures.now(raw)
        val session = PersonalFixtures.session(raw)
        for (changed in listOf(now.minusNanos(1), now.plusHours(2), now.plusDays(1),
            now.withZoneSameInstant(ZoneId.of("Asia/Tashkent")))) {
            assertEquals("neutral", WidgetVisualResolver.resolve(session, changed).personalPhase)
        }
    }

    @Test fun `only verified current daily completion can carry a milestone`() {
        val raw = PersonalFixtures.raw("verified_goal_complete")
        val visual = WidgetVisualResolver.resolve(PersonalFixtures.session(raw), PersonalFixtures.now(raw))
        assertEquals(WidgetVisualState.COMPLETED, visual.state)
        assertEquals(WidgetSpecialState(WidgetSpecialKind.MILESTONE, 7), visual.special)
        val course = PersonalFixtures.raw("course_complete")
        assertNull(WidgetVisualResolver.resolve(PersonalFixtures.session(course), PersonalFixtures.now(course)).special)
    }

    @Test fun `variants and the existing 28 art choices remain stable`() {
        WidgetVisualState.entries.forEach { state ->
            val variants = (1..120).map { day ->
                val date = PersonalFixtures.now().plusDays(day.toLong()).toLocalDate().toString()
                val choice = WidgetVisualResolver.variantFor(state, PersonalFixtures.EPOCH, date)
                assertTrue(choice in 0 until state.variants)
                assertEquals(choice, WidgetVisualResolver.variantFor(state, PersonalFixtures.EPOCH, date))
                choice
            }.toSet()
            assertEquals(state.variants, variants.size)
        }
    }
}
