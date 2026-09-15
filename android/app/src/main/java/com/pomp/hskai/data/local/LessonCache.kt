package com.pomp.hskai.data.local

import androidx.room.Dao
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

/**
 * The last lesson envelope the server returned, stored verbatim.
 *
 * Only a lesson the learner actually opened is ever written here, and the
 * server has already spent the daily slot for it by then — `lesson()` on the
 * backend calls `LessonAccessService.status(consume=True)`, so fetching a
 * lesson IS opening it. Nothing may prefetch into this table: reading ahead
 * would silently burn a free learner's daily allowance on lessons they never
 * asked for.
 *
 * The whole envelope is kept, not the parsed lesson, so a cached read runs the
 * exact same validation a fresh one does and can never come out more permissive
 * than the server last was — same reasoning as [CourseMapCacheEntity].
 */
@Entity(tableName = "course_lesson_cache", primaryKeys = ["level", "lessonOrder"])
data class LessonCacheEntity(
    val level: String,
    val lessonOrder: Int,
    val envelopeJson: String,
    val fetchedAtMillis: Long,
)

@Dao
interface LessonCacheDao {

    @Query(
        "SELECT * FROM course_lesson_cache WHERE level = :level AND lessonOrder = :lessonOrder LIMIT 1"
    )
    suspend fun find(level: String, lessonOrder: Int): LessonCacheEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(entity: LessonCacheEntity)

    /** Called on logout: cached lessons must not outlive the session. */
    @Query("DELETE FROM course_lesson_cache")
    suspend fun clear()
}
