package com.pomp.hskai.feature.lesson

import com.pomp.hskai.domain.model.Lesson
import com.pomp.hskai.domain.model.LessonSection
import com.pomp.hskai.domain.model.UnsupportedCard
import org.junit.Assert.assertEquals
import org.junit.Test

/** Opt-in N1 retry selection; legacy levels keep unchanged linear navigation. */
class N1ConditionalRetryTest {
    private fun pilot(level: String = "nhsk1", part: Int = 4): Lesson {
        val sections = listOf(
            LessonSection(1, "Old material", "practice",
                listOf(UnsupportedCard("one", "placeholder"))),
            LessonSection(2, "Dialogue", "dialog",
                listOf(UnsupportedCard("two", "placeholder"))),
            LessonSection(3, "Independent checks", "learning_exit_check",
                (0..2).map { UnsupportedCard("check:$it", "placeholder") }),
            LessonSection(4, "Transfer practice", "learning_repair_bank",
                (0..2).map { UnsupportedCard("retry:$it", "placeholder") }),
        )
        return Lesson(
            level = level, order = 4, sourceLesson = 1, part = part,
            partCount = 4, isCheckpoint = true, title = "N1",
            subtitle = "N1 checkpoint", sections = sections,
        )
    }

    @Test fun successfulChecksSkipAllRemediation() {
        val l = pilot()
        assertEquals(8, nextN1PilotCardIndex(l, 5, emptySet(), true))
    }

    @Test fun aSingleFailedObjectiveShowsOnlyItsAlternateQuestion() {
        val l = pilot()
        assertEquals(6, nextN1PilotCardIndex(l, 5, setOf(1), true))
        assertEquals(8, nextN1PilotCardIndex(l, 7, setOf(1), true))
    }

    @Test fun allFailedChecksRequireAllThreeAlternates() {
        val l = pilot()
        assertEquals(5, nextN1PilotCardIndex(l, 5, setOf(0, 1, 2), true))
        assertEquals(6, nextN1PilotCardIndex(l, 6, setOf(0, 1, 2), true))
        assertEquals(7, nextN1PilotCardIndex(l, 7, setOf(0, 1, 2), true))
    }

    @Test fun lostResumeHistoryNeverSilentlyDropsPractice() {
        assertEquals(5, nextN1PilotCardIndex(pilot(), 5, emptySet(), false))
    }

    @Test fun otherCourseTracksKeepOriginalProgression() {
        assertEquals(5, nextN1PilotCardIndex(pilot(level = "hsk1"), 5, emptySet(), true))
        assertEquals(5, nextN1PilotCardIndex(pilot(part = 3), 5, emptySet(), true))
    }
}
