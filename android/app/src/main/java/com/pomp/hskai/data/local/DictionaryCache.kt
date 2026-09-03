package com.pomp.hskai.data.local

import androidx.room.Dao
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.Transaction

/**
 * One dictionary entry, in the language it was downloaded for.
 *
 * [pinyinPlain] is the tone-stripped reading the search runs against; the
 * displayed [pinyin] keeps its marks.
 */
@Entity(tableName = "dictionary_word")
data class DictionaryWordEntity(
    @PrimaryKey val hanzi: String,
    val pinyin: String,
    val pinyinPlain: String,
    val meaning: String,
    val level: String,
    /** Preserves the server's order, which groups the list by HSK level. */
    val position: Int,
)

/**
 * What the stored copy is, so an unchanged dictionary is never re-downloaded
 * and a language change is never served from the previous language's rows.
 */
@Entity(tableName = "dictionary_meta")
data class DictionaryMetaEntity(
    @PrimaryKey val id: Int = 1,
    val version: String,
    val language: String,
)

@Dao
interface DictionaryDao {

    @Query("SELECT * FROM dictionary_meta WHERE id = 1 LIMIT 1")
    suspend fun meta(): DictionaryMetaEntity?

    @Query("SELECT COUNT(*) FROM dictionary_word")
    suspend fun count(): Int

    @Query(
        """
        SELECT * FROM dictionary_word
        ORDER BY position ASC
        LIMIT :limit
        """
    )
    suspend fun all(limit: Int): List<DictionaryWordEntity>

    /**
     * Hanzi, toned or untoned pinyin, and meaning all match the same box, so
     * the learner does not have to know which field their guess belongs to.
     */
    @Query(
        """
        SELECT * FROM dictionary_word
        WHERE hanzi LIKE '%' || :query || '%'
           OR pinyinPlain LIKE '%' || :plain || '%'
           OR meaning LIKE '%' || :query || '%'
        ORDER BY
            CASE
                WHEN hanzi = :query THEN 0
                WHEN pinyinPlain = :plain THEN 1
                WHEN hanzi LIKE :query || '%' THEN 2
                WHEN pinyinPlain LIKE :plain || '%' THEN 3
                ELSE 4
            END,
            position ASC
        LIMIT :limit
        """
    )
    suspend fun search(query: String, plain: String, limit: Int): List<DictionaryWordEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(words: List<DictionaryWordEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun setMeta(meta: DictionaryMetaEntity)

    @Query("DELETE FROM dictionary_word")
    suspend fun clearWords()

    @Query("DELETE FROM dictionary_meta")
    suspend fun clearMeta()

    /** Replaces the whole dictionary, so a half-written list is never shown. */
    @Transaction
    suspend fun replace(words: List<DictionaryWordEntity>, meta: DictionaryMetaEntity) {
        clearWords()
        insertAll(words)
        setMeta(meta)
    }

    @Transaction
    suspend fun clear() {
        clearWords()
        clearMeta()
    }
}
