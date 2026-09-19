package com.pomp.hskai.data.local

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/**
 * The lesson cache is keyed by level AND number, hand-written as a composite
 * primary key and a two-column lookup. Compiling proves neither, so the query
 * is exercised against real SQLite here.
 */
@RunWith(AndroidJUnit4::class)
class LessonCacheDaoTest {

    private lateinit var db: HskAiDatabase
    private lateinit var dao: LessonCacheDao

    @Before
    fun setUp() {
        db = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext(),
            HskAiDatabase::class.java,
        ).build()
        dao = db.lessonCacheDao()
    }

    @After
    fun tearDown() {
        db.close()
    }

    private fun row(level: String, order: Int, payload: String) =
        LessonCacheEntity(level, order, payload, fetchedAtMillis = 1_700_000_000_000L)

    @Test
    fun a_stored_lesson_comes_back_under_its_own_level_and_number() = runTest {
        dao.upsert(row("hsk1", 3, "{\"a\":1}"))

        assertEquals("{\"a\":1}", dao.find("hsk1", 3)?.envelopeJson)
        assertNull(dao.find("hsk1", 4))
        assertNull(dao.find("hsk2", 3))
    }

    @Test
    fun the_same_lesson_number_at_another_level_is_a_separate_row() = runTest {
        dao.upsert(row("hsk1", 1, "one"))
        dao.upsert(row("hsk2", 1, "two"))

        assertEquals("one", dao.find("hsk1", 1)?.envelopeJson)
        assertEquals("two", dao.find("hsk2", 1)?.envelopeJson)
    }

    @Test
    fun reopening_a_lesson_replaces_its_row_instead_of_adding_one() = runTest {
        dao.upsert(row("hsk1", 1, "old"))
        dao.upsert(row("hsk1", 1, "new"))

        assertEquals("new", dao.find("hsk1", 1)?.envelopeJson)
    }

    @Test
    fun clearing_leaves_no_lesson_behind() = runTest {
        dao.upsert(row("hsk1", 1, "one"))
        dao.upsert(row("hsk2", 9, "two"))

        dao.clear()

        assertNull(dao.find("hsk1", 1))
        assertNull(dao.find("hsk2", 9))
    }
}
