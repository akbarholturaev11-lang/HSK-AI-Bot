package com.pomp.hskai.feature.course

import com.pomp.hskai.domain.model.CourseLesson
import com.pomp.hskai.domain.model.LessonAccess
import com.pomp.hskai.domain.model.LessonStatus
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CourseUnlockTransitionTest {

    private fun lesson(order: Int, status: LessonStatus): CourseLesson = CourseLesson(
        order = order,
        sourceLesson = order,
        part = 1,
        partCount = 1,
        isCheckpoint = false,
        status = status,
        access = if (status == LessonStatus.LOCKED) LessonAccess.NotReached else LessonAccess.Open,
        hanziPreview = "学",
        pinyinPreview = "xué",
        subtitle = "",
    )

    @Test
    fun only_a_real_locked_to_unlocked_transition_is_revealed() {
        val before = listOf(
            lesson(1, LessonStatus.CURRENT),
            lesson(2, LessonStatus.LOCKED),
            lesson(3, LessonStatus.LOCKED),
        )
        val after = listOf(
            lesson(1, LessonStatus.DONE),
            lesson(2, LessonStatus.CURRENT),
            lesson(3, LessonStatus.LOCKED),
        )

        assertEquals(2, findNewlyUnlockedLesson(before, after))
    }

    @Test
    fun ordinary_progress_updates_do_not_fake_an_unlock() {
        val before = listOf(
            lesson(1, LessonStatus.CURRENT),
            lesson(2, LessonStatus.LOCKED),
        )
        val after = listOf(
            lesson(1, LessonStatus.CURRENT),
            lesson(2, LessonStatus.LOCKED),
        )

        assertNull(findNewlyUnlockedLesson(before, after))
    }

    @Test
    fun first_real_unlock_wins_when_a_server_response_opens_more_than_one() {
        val before = listOf(
            lesson(2, LessonStatus.LOCKED),
            lesson(3, LessonStatus.LOCKED),
        )
        val after = listOf(
            lesson(2, LessonStatus.CURRENT),
            lesson(3, LessonStatus.CURRENT),
        )

        assertEquals(2, findNewlyUnlockedLesson(before, after))
    }
}
