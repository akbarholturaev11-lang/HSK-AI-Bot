package com.pomp.hskai.data.local

import android.content.Context
import android.database.sqlite.SQLiteDatabase
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
 * Adding the lesson cache took the database from version 2 to 3. Everything in
 * it is a cache, so the upgrade is handled by dropping the lot — but a wrong
 * builder turns that into an `IllegalStateException` on first launch after an
 * update, which is a crash for every existing installation.
 *
 * A version 2 file is written by hand here and the real database is opened on
 * top of it.
 */
@RunWith(AndroidJUnit4::class)
class DatabaseUpgradeTest {

    private val context: Context = ApplicationProvider.getApplicationContext()
    private val name = "upgrade-probe.db"
    private var db: HskAiDatabase? = null

    @Before
    fun setUp() {
        context.deleteDatabase(name)
    }

    @After
    fun tearDown() {
        db?.close()
        context.deleteDatabase(name)
    }

    private fun writeVersionTwoFile() {
        val file = context.getDatabasePath(name)
        file.parentFile?.mkdirs()
        val legacy = SQLiteDatabase.openOrCreateDatabase(file, null)
        legacy.execSQL(
            "CREATE TABLE IF NOT EXISTS course_map_cache " +
                "(level TEXT NOT NULL PRIMARY KEY, payloadJson TEXT NOT NULL, fetchedAtMillis INTEGER NOT NULL)"
        )
        legacy.execSQL(
            "INSERT INTO course_map_cache VALUES ('hsk1', '{\"stale\":true}', 1)"
        )
        legacy.version = 2
        legacy.close()
    }

    @Test
    fun a_version_two_install_opens_on_the_new_schema_instead_of_crashing() = runTest {
        writeVersionTwoFile()

        val opened = Room.databaseBuilder(context, HskAiDatabase::class.java, name)
            .fallbackToDestructiveMigration(dropAllTables = true)
            .build()
        db = opened

        // The new table exists and answers, and the old cached map is gone
        // rather than carried across a schema it no longer matches.
        assertNull(opened.lessonCacheDao().find("hsk1", 1))
        opened.lessonCacheDao().upsert(
            LessonCacheEntity("hsk1", 1, "{}", fetchedAtMillis = 1L)
        )
        assertEquals("{}", opened.lessonCacheDao().find("hsk1", 1)?.envelopeJson)
        assertNull(opened.courseMapDao().find("hsk1"))
    }
}
