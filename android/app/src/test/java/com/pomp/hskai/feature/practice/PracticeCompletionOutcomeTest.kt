package com.pomp.hskai.feature.practice

import com.pomp.hskai.data.api.MistakeReviewCompleteResponse
import com.pomp.hskai.data.api.PracticeCompleteResponse
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PracticeCompletionOutcomeTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `practice completion preserves backend xp and streak signals`() {
        val reward = json.parseToJsonElement(
            """
            {
              "xp": 240,
              "awarded_xp": 25,
              "duplicate": false,
              "streak": 4,
              "streak_updated": true,
              "league": "Bronze",
              "daily_xp": 25,
              "weekly_xp": 90,
              "league_points": 90,
              "energy": {"current": 4, "max": 5, "blocks_study": false}
            }
            """.trimIndent(),
        ).jsonObject

        val outcome = PracticeCompleteResponse(
            ok = true,
            score = 9,
            total = 10,
            percent = 90,
            reward = reward,
        ).toCompletionOutcome(mode = "training")

        assertEquals(PracticeCompletionKind.PRACTICE, outcome.kind)
        assertEquals(25, outcome.awardedXp)
        assertEquals(4, outcome.gamification.streak)
        assertTrue(outcome.hasStreakEvent)
        assertFalse(outcome.isDuplicate)
    }

    @Test
    fun `duplicate completion never schedules xp or streak celebration`() {
        val reward = json.parseToJsonElement(
            """
            {
              "xp": 240,
              "awarded_xp": 25,
              "duplicate": true,
              "streak": 4,
              "streak_updated": true
            }
            """.trimIndent(),
        ).jsonObject

        val outcome = MistakeReviewCompleteResponse(
            ok = true,
            score = 5,
            total = 5,
            percent = 100,
            remaining = 0,
            reward = reward,
        ).toCompletionOutcome()

        assertTrue(outcome.isDuplicate)
        assertEquals(0, outcome.awardedXp)
        assertFalse(outcome.hasStreakEvent)
    }

    @Test
    fun `placement remains distinct from ordinary practice`() {
        val outcome = PracticeCompleteResponse(
            ok = true,
            score = 7,
            total = 10,
            percent = 70,
        ).toCompletionOutcome(mode = "placement")

        assertEquals(PracticeCompletionKind.PLACEMENT, outcome.kind)
    }

    @Test
    fun `drill result is normalized without inventing gamification`() {
        val outcome = drillCompletionOutcome(
            kind = PracticeCompletionKind.RECOGNITION,
            correct = 8,
            total = 10,
        )

        assertEquals(80, outcome.percent)
        assertEquals(8, outcome.score)
        assertEquals(10, outcome.total)
        assertEquals(0, outcome.awardedXp)
        assertFalse(outcome.hasStreakEvent)
    }
}
