package com.pomp.hskai.data.local

import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.RoomDatabase

/**
 * The last course map the server returned, stored verbatim.
 *
 * Keeping the raw payload rather than a normalised copy means the cache can
 * never drift from the server's own access decisions: it is a snapshot, not a
 * second source of truth. It is only ever shown with a "stale" marker, and it
 * can never widen access beyond what the server last said.
 */
@Entity(tableName = "course_map_cache")
data class CourseMapCacheEntity(
    @PrimaryKey val level: String,
    val payloadJson: String,
    val fetchedAtMillis: Long,
)

@Dao
interface CourseMapDao {

    @Query("SELECT * FROM course_map_cache WHERE level = :level LIMIT 1")
    suspend fun find(level: String): CourseMapCacheEntity?

    @Query("SELECT * FROM course_map_cache ORDER BY fetchedAtMillis DESC LIMIT 1")
    suspend fun findMostRecent(): CourseMapCacheEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(entity: CourseMapCacheEntity)

    /** Called on logout: cached progress must not outlive the session. */
    @Query("DELETE FROM course_map_cache")
    suspend fun clear()
}

@Database(
    entities = [
        CourseMapCacheEntity::class,
        DictionaryWordEntity::class,
        DictionaryMetaEntity::class,
    ],
    version = 2,
    exportSchema = false,
)
abstract class HskAiDatabase : RoomDatabase() {
    abstract fun courseMapDao(): CourseMapDao

    abstract fun dictionaryDao(): DictionaryDao

    companion object {
        const val NAME = "pomp_hskai.db"
    }
}
