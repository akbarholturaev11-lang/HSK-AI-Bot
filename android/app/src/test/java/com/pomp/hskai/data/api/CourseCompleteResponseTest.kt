package com.pomp.hskai.data.api

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CourseCompleteResponseTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `completion preserves mini app gamification celebration signals`() {
        val payload = """
            {
              "ok": true,
              "completed_lesson": 7,
              "next_lesson": 8,
              "completed_lessons_count": 7,
              "rank_before": 12,
              "rank_after": 9,
              "gamification": {
                "xp": 245,
                "awarded_xp": 25,
                "duplicate": false,
                "streak": 4,
                "longest_streak": 6,
                "previous_streak": 3,
                "streak_updated": true,
                "streak_reset": false,
                "activity_date": "2026-09-13",
                "last_activity_date": "2026-09-13",
                "local_date": "2026-09-13",
                "week_start": "2026-09-07",
                "week_activity_dates": ["2026-09-10", "2026-09-13"],
                "league": "Bronze",
                "weekly_xp": 125,
                "daily_xp": 25,
                "league_points": 125,
                "weekly_reset_day": "monday",
                "weekly_reset_at": "2026-09-13T16:00:00+00:00",
                "weekly_reset_seconds": 1234,
                "energy": {"current": 4, "max": 5, "blocks_study": false},
                "reward_chest": {"ready": true, "progress": 80, "next_xp": 0}
              }
            }
        """.trimIndent()

        val response = json.decodeFromString<CourseCompleteResponse>(payload)

        assertTrue(response.ok)
        assertEquals(25, response.gamification.awardedXp)
        assertEquals(4, response.gamification.streak)
        assertEquals(3, response.gamification.previousStreak)
        assertTrue(response.gamification.streakUpdated)
        assertFalse(response.gamification.streakReset)
        assertEquals("Bronze", response.gamification.league)
        assertEquals(125, response.gamification.weeklyXp)
        assertEquals(4, response.gamification.energy.current)
        assertTrue(response.gamification.rewardChest?.ready == true)
        assertEquals(12, response.rankBefore)
        assertEquals(9, response.rankAfter)
    }
}