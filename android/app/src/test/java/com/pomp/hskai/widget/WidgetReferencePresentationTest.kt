package com.pomp.hskai.widget

import java.time.ZonedDateTime
import kotlinx.serialization.json.*
import org.junit.Assert.*
import org.junit.Test

/** Current authenticated state, not guessed inactivity or a second scheduler. */
class WidgetReferencePresentationTest {
    private val now=ZonedDateTime.parse("2026-11-03T23:30:00Z[Etc/UTC]")

    private fun session(at: ZonedDateTime=now, due: String="14:00", streak: Int=7,
                        phase: String="study_time_reached", xp: Int=0, age: Long?=null): WidgetSession {
        val data=PersonalFixtures.raw().toMutableMap().apply {
            put("version",JsonPrimitive(2));put("policy_version",JsonPrimitive("smart-widget-context-v2"))
            put("generated_at",JsonPrimitive(at.minusSeconds(1).toInstant().toString()))
            put("valid_until",JsonPrimitive(minOf(at.plusMinutes(10).toInstant(),
                at.toLocalDate().plusDays(1).atStartOfDay(at.zone).toInstant()).toString()))
            put("timezone_name",JsonPrimitive(at.zone.id));put("local_day",JsonPrimitive(at.toLocalDate().toString()))
            put("time_local",JsonPrimitive(due));put("phase",JsonPrimitive(phase))
            put("verified_today_xp",JsonPrimitive(xp));put("last_observed_study_at",
                age?.let { JsonPrimitive(at.minusDays(it).toInstant().toString()) } ?: JsonNull)
        }
        val raw=JsonObject(data)
        assertNotNull(WidgetPersonalContext.parse(raw))
        return PersonalFixtures.session(raw,at).let { it.copy(snapshot=it.snapshot!!.copy(streak=streak)) }
    }

    @Test fun `late habit stays gentle while earlier personal time reaches its day end`() {
        val late=WidgetVisualResolver.resolve(session(due="23:20"),now)
        val earlier=WidgetVisualResolver.resolve(session(),now)
        assertEquals(WidgetVisualState.WAITING,late.state)
        assertEquals(WidgetVisualState.CRITICAL,earlier.state)
        assertTrue(earlier.streakAtRisk)
        assertTrue(WidgetPandaArt.palette(false,earlier).warning)
    }

    @Test fun `daily moods progress within the actual personal window`() {
        for((hour,minute,expected) in listOf(Triple(15,0,WidgetVisualState.WAITING),
            Triple(18,0,WidgetVisualState.EVENING),Triple(21,0,WidgetVisualState.LATE),
            Triple(23,30,WidgetVisualState.CRITICAL))) {
            val at=now.withHour(hour).withMinute(minute)
            assertEquals(expected,WidgetVisualResolver.resolve(session(at=at),at).state)
        }
    }

    @Test fun `verified partial study secures flame without inventing a completed goal`() {
        val visual=WidgetVisualResolver.resolve(session(xp=1),now)
        assertTrue(visual.streakSecured)
        assertFalse(visual.streakAtRisk)
        assertEquals(WidgetVisualState.WAITING,visual.state)
        assertNull(visual.special)
        assertEquals(29,WidgetPandaArt.pose(WidgetAccess.ACTIVE,visual))
        assertTrue(WidgetPandaArt.palette(false,visual).outlined)
    }

    @Test fun `zero streak does not get a save-streak warning`() {
        val visual=WidgetVisualResolver.resolve(session(streak=0),now)
        assertEquals(WidgetVisualState.WAITING,visual.state)
        assertFalse(visual.streakAtRisk)
        assertFalse(WidgetPandaArt.palette(false,visual).warning)
        assertEquals(0,visual.returnBand)
    }

    @Test fun `canonical streak already recorded on another course cannot be shown at risk`() {
        val current=session(xp=0).let { it.copy(snapshot=it.snapshot!!.copy(streakRecordedToday=true)) }
        val visual=WidgetVisualResolver.resolve(current,now)
        assertTrue(visual.streakSecured)
        assertFalse(visual.streakAtRisk)
        assertNotEquals(WidgetVisualState.COMPLETED,visual.state)
        assertNull(visual.special)
    }

    @Test fun `beginner growth and thirty days decorate the same verified phase`() {
        val at=now.withHour(12)
        val poses=mutableMapOf<Int,Set<Int>>()
        for((streak,tier) in listOf(1 to 1,2 to 1,3 to 2,29 to 2,30 to 3,300 to 3)) {
            val visual=WidgetVisualResolver.resolve(session(at=at,phase="before_study",streak=streak),at)
            assertEquals(tier,visual.streakTier)
            assertEquals("before_study",visual.personalPhase)
            poses[tier]=(0..2).map { WidgetPandaArt.pose(WidgetAccess.ACTIVE,visual.copy(variant=it)) }.toSet()
        }
        assertTrue(poses[1]!!.intersect(poses[2]!!).isEmpty())
        assertTrue(poses[2]!!.intersect(poses[3]!!).isEmpty())
    }

    @Test fun `positive history age decorates only a fresh zero-streak return invitation`() {
        for((age,band) in listOf(6L to 0,7L to 1,29L to 1,30L to 2,89L to 2,90L to 3,360L to 3)) {
            val visual=WidgetVisualResolver.resolve(session(streak=0,age=age),now)
            assertEquals(band,visual.returnBand)
            assertNull(visual.special) // No invented broken-streak/comeback event.
            assertFalse(visual.streakAtRisk)
        }
        assertEquals(0,WidgetVisualResolver.resolve(session(streak=2,age=90),now).returnBand)
        assertEquals(0,WidgetVisualResolver.resolve(session(streak=0,age=null),now).returnBand)
    }

    @Test fun `quiet paused unknown and stale remain calm even near midnight`() {
        for(phase in listOf("quiet","paused","neutral")) {
            val visual=WidgetVisualResolver.resolve(session(streak=0,age=120,phase=phase),now)
            assertEquals(0,visual.returnBand)
            assertFalse(WidgetPandaArt.palette(false,visual).warning)
            assertEquals(0,WidgetPandaArt.pose(WidgetAccess.ACTIVE,visual))
        }
        val old=session().let { it.copy(snapshot=it.snapshot!!.copy(fetchedAtMillis=now.minusHours(3).toInstant().toEpochMilli())) }
        assertEquals("neutral",WidgetVisualResolver.resolve(old,now).personalPhase)
    }

    @Test fun `v2 original time is strict and cannot add future history to v1`() {
        val raw=session(age=90).snapshot!!.personalContext!!.jsonObject
        for(value in listOf(JsonPrimitive(now.plusSeconds(1).toInstant().toString()),JsonPrimitive(123),JsonPrimitive("bad"))) {
            assertNull(WidgetPersonalContext.parse(JsonObject(raw+("last_observed_study_at" to value))))
        }
        assertNull(WidgetPersonalContext.parse(JsonObject(PersonalFixtures.raw()+
            ("last_observed_study_at" to JsonNull))))
        assertNotNull(WidgetPersonalContext.parse(PersonalFixtures.raw()))
    }

    @Test fun `all atlas moods are reachable and operational access cannot become dramatic`() {
        val reached=mutableSetOf<Int>()
        for(state in WidgetVisualState.entries) for(variant in 0 until state.variants) for(tier in 0..3) {
            val v=WidgetVisual(state,variant,personalPhase=if(state==WidgetVisualState.DAY)"before_study" else "study_time_reached",streakTier=tier)
            reached+=WidgetPandaArt.pose(WidgetAccess.ACTIVE,v)
            for(band in 1..3) reached+=WidgetPandaArt.pose(WidgetAccess.ACTIVE,v.copy(returnBand=band))
            reached+=WidgetPandaArt.pose(WidgetAccess.ACTIVE,v.copy(streakSecured=true))
            reached+=WidgetPandaArt.pose(WidgetAccess.ACTIVE,v.copy(special=WidgetSpecialState(WidgetSpecialKind.MILESTONE,30)))
            for(access in listOf(WidgetAccess.UNLINKED,WidgetAccess.STALE,WidgetAccess.FOUNDATION))
                assertEquals(0,WidgetPandaArt.pose(access,v))
        }
        assertEquals((0..35).toSet(),reached)
    }
}
