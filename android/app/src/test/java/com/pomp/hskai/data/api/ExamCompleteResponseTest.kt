package com.pomp.hskai.data.api

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ExamCompleteResponseTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `exam completion preserves reward and wrong items`() {
        val payload = """
            {
              "ok": true,
              "duplicate": false,
              "score": 11,
              "total": 12,
              "percent": 92,
              "pass_score": 60,
              "passed": true,
              "section_scores": {
                "listening": {"score": 4, "total": 4, "percent": 100},
                "reading": {"score": 4, "total": 4, "percent": 100},
                "writing": {"score": 3, "total": 4, "percent": 75}
              },
              "reward": {
                "xp": 320,
                "awarded_xp": 35,
                "duplicate": false,
                "streak": 5,
                "previous_streak": 4,
                "streak_updated": true,
                "league": "Bronze",
                "weekly_xp": 160,
                "daily_xp": 35,
                "league_points": 160,
                "energy": {"current": 4, "max": 5, "blocks_study": false}
              },
              "wrong_items": [
                {
                  "question": "选择正确答案",
                  "selected_answer": "A",
                  "correct_answer": "B",
                  "explanation": "B is correct",
                  "pinyin": ""
                }
              ]
            }
        """.trimIndent()

        val response = json.decodeFromString<ExamCompleteResponse>(payload)

        assertTrue(response.ok)
        assertFalse(response.duplicate)
        assertTrue(response.passed)
        assertEquals(35, response.reward.awardedXp)
        assertEquals(5, response.reward.streak)
        assertTrue(response.reward.streakUpdated)
        assertEquals(1, response.wrongItems.size)
        assertEquals("B", response.wrongItems.single().correctAnswer)
        assertEquals(3, response.sectionScores.size)
    }
}
