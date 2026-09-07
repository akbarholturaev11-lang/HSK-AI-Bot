package com.pomp.hskai.core.settings

/**
 * Where a half-finished lesson keeps its place.
 *
 * The Mini App stores this in `localStorage` under
 * `hsk_v3_lesson_resume:v2:<level>:<order>`; the same behaviour has to exist
 * here, because a learner who is interrupted mid-lesson and comes back to the
 * first card twice usually does not come back a third time.
 *
 * It is a seam rather than a direct dependency on [AppSettings] so the lesson
 * can be tested without an Android context.
 */
interface LessonResumeStore {

    /** The card index to resume at, or 0 when nothing is remembered. */
    suspend fun lessonResumeIndex(level: String, order: Int): Int

    suspend fun setLessonResumeIndex(level: String, order: Int, index: Int)

    suspend fun clearLessonResume(level: String, order: Int)
}
