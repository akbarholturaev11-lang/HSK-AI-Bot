package com.pomp.hskai.data.repository

import com.pomp.hskai.data.api.CourseLessonDto
import com.pomp.hskai.data.api.CourseMapDto
import com.pomp.hskai.data.api.CourseUnitDto
import com.pomp.hskai.data.api.CourseUserDto
import com.pomp.hskai.data.api.LocalizedText
import com.pomp.hskai.domain.model.LessonAccess
import com.pomp.hskai.domain.model.LessonStatus
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CourseMapperTest {

    /**
     * The four server states a lesson can be in. The important pair is
     * NotReached vs PremiumLocked: only the second may show a paywall.
     */
    @Test
    fun `server access flags map to the four domain states`() {
        val open = lesson(order = 1, status = "current", completionAllowed = true)
        val notReached = lesson(
            order = 2,
            status = "locked",
            completionError = "course_lesson_not_unlocked",
        )
        val preview = lesson(
            order = 3,
            status = "current",
            previewHalf = true,
            completionError = "free_feature_limit_reached",
        )
        val premium = lesson(
            order = 4,
            status = "locked",
            lockedPremium = true,
            completionError = "free_feature_limit_reached",
        )

        val lessons = CourseMapper.toDomain(map(open, notReached, preview, premium)).lessons

        assertEquals(LessonAccess.Open, lessons[0].access)
        assertEquals(LessonAccess.NotReached, lessons[1].access)
        assertEquals(LessonAccess.HalfPreview, lessons[2].access)
        assertEquals(LessonAccess.PremiumLocked, lessons[3].access)
    }

    @Test
    fun `only premium states offer a paywall`() {
        assertFalse(LessonAccess.Open.showsPaywall)
        // A free lesson further down the path is not a sales opportunity.
        assertFalse(LessonAccess.NotReached.showsPaywall)
        assertTrue(LessonAccess.HalfPreview.showsPaywall)
        assertTrue(LessonAccess.PremiumLocked.showsPaywall)
    }

    @Test
    fun `completion_allowed wins over every other flag`() {
        // A paid user can have completion_allowed on a lesson the free tier
        // would call premium. The server's yes is final.
        val paid = lesson(
            order = 9,
            status = "current",
            completionAllowed = true,
            lockedPremium = false,
        )
        val lessons = CourseMapper.toDomain(map(paid)).lessons
        assertEquals(LessonAccess.Open, lessons[0].access)
        assertFalse(lessons[0].access.showsPaywall)
    }

    @Test
    fun `status strings map to the domain enum and unknown falls back to locked`() {
        val lessons = CourseMapper.toDomain(
            map(
                lesson(1, status = "done", completionAllowed = true),
                lesson(2, status = "CURRENT", completionAllowed = true),
                lesson(3, status = "something-new"),
            )
        ).lessons

        assertEquals(LessonStatus.DONE, lessons[0].status)
        assertEquals(LessonStatus.CURRENT, lessons[1].status)
        assertEquals(LessonStatus.LOCKED, lessons[2].status)
    }

    @Test
    fun `localized text follows the user language and falls back to russian`() {
        val tajik = CourseMapper.toDomain(
            map(lesson(1, status = "current", completionAllowed = true), language = "tj")
        )
        assertEquals("Дарси 1", tajik.units[0].title)

        val uzbek = CourseMapper.toDomain(
            map(lesson(1, status = "current", completionAllowed = true), language = "uz")
        )
        assertEquals("1-dars", uzbek.units[0].title)

        // An unknown backend language falls back the way the server does.
        val unknown = CourseMapper.toDomain(
            map(lesson(1, status = "current", completionAllowed = true), language = "en")
        )
        assertEquals("Урок 1", unknown.units[0].title)
    }

    @Test
    fun `total lessons come from the payload and are never assumed`() {
        val many = (1..63).map { lesson(it, status = if (it == 1) "current" else "locked") }
        val domain = CourseMapper.toDomain(map(*many.toTypedArray()))
        assertEquals(63, domain.totalLessons)
    }

    @Test
    fun `current lesson is the server's current node even when it is a preview`() {
        val domain = CourseMapper.toDomain(
            map(
                lesson(1, status = "done", completionAllowed = true),
                lesson(2, status = "done", completionAllowed = true),
                lesson(3, status = "current", previewHalf = true),
                lesson(4, status = "locked", lockedPremium = true),
            )
        )
        val current = domain.currentLesson
        assertEquals(3, current?.order)
        assertEquals(LessonAccess.HalfPreview, current?.access)
    }

    private fun lesson(
        order: Int,
        status: String = "locked",
        completionAllowed: Boolean = false,
        completionError: String? = null,
        previewHalf: Boolean = false,
        lockedPremium: Boolean = false,
    ) = CourseLessonDto(
        order = order,
        sourceLesson = 1,
        part = order,
        partCount = 3,
        checkpoint = false,
        status = status,
        hanzi = "你 · 好",
        pinyin = "nǐ · hǎo",
        subtitle = LocalizedText(uz = "1-qism", ru = "Часть 1", tj = "Қисми 1"),
        completionAllowed = completionAllowed,
        completionError = completionError,
        previewHalf = previewHalf,
        lockedPremium = lockedPremium,
    )

    private fun map(
        vararg lessons: CourseLessonDto,
        language: String = "uz",
    ) = CourseMapDto(
        ok = true,
        level = "hsk1",
        units = listOf(
            CourseUnitDto(
                number = 1,
                title = LocalizedText(uz = "1-dars", ru = "Урок 1", tj = "Дарси 1"),
                lessons = lessons.toList(),
            )
        ),
        user = CourseUserDto(name = "Akbar", language = language),
    )
}
