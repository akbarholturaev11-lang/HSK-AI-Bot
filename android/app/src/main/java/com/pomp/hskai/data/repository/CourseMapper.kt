package com.pomp.hskai.data.repository

import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.data.api.CourseLessonDto
import com.pomp.hskai.data.api.CourseMapDto
import com.pomp.hskai.domain.model.CourseLesson
import com.pomp.hskai.domain.model.CourseMap
import com.pomp.hskai.domain.model.CourseProgress
import com.pomp.hskai.domain.model.CourseUnit
import com.pomp.hskai.domain.model.CourseUser
import com.pomp.hskai.domain.model.LessonAccess
import com.pomp.hskai.domain.model.LessonStatus

/**
 * Translates the server payload into domain models.
 *
 * The access decision is *read*, never recomputed: the client has no rule of
 * its own about who may open what.
 */
object CourseMapper {

    fun toDomain(dto: CourseMapDto): CourseMap {
        val language = AppLanguage.fromBackendCode(dto.user.language)
        return CourseMap(
            level = dto.level,
            units = dto.units.map { unit ->
                CourseUnit(
                    number = unit.number,
                    title = unit.title.forLanguage(language),
                    lessons = unit.lessons.map { it.toDomain(language) },
                )
            },
            progress = CourseProgress(
                completedLessons = dto.progress.completed,
                xp = dto.progress.xp,
                dailyXp = dto.progress.dailyXp,
                weeklyXp = dto.progress.weeklyXp,
                streak = dto.progress.streak,
                longestStreak = dto.progress.longestStreak,
                league = dto.progress.league,
                weekActivityDates = dto.progress.weekActivityDates,
                localDate = dto.progress.localDate,
                weekStart = dto.progress.weekStart,
                hasRewardChest = dto.progress.rewardChest?.available == true,
            ),
            user = CourseUser(
                name = dto.user.name,
                initials = dto.user.avatar,
                isPaid = dto.user.isPaid,
                referralCode = dto.user.referralCode,
            ),
            notificationsEnabled = dto.notify.enabled,
        )
    }

    private fun CourseLessonDto.toDomain(language: AppLanguage) = CourseLesson(
        order = order,
        sourceLesson = sourceLesson,
        part = part,
        partCount = partCount,
        isCheckpoint = checkpoint,
        status = when (status.trim().lowercase()) {
            "done" -> LessonStatus.DONE
            "current" -> LessonStatus.CURRENT
            else -> LessonStatus.LOCKED
        },
        access = access(),
        hanziPreview = hanzi,
        pinyinPreview = pinyin,
        subtitle = subtitle.forLanguage(language),
    )

    /**
     * Order matters. `completion_allowed` is the server's yes; everything else
     * is a specific kind of no, and only two of those justify a paywall.
     */
    private fun CourseLessonDto.access(): LessonAccess = when {
        completionAllowed -> LessonAccess.Open
        previewHalf -> LessonAccess.HalfPreview
        lockedPremium -> LessonAccess.PremiumLocked
        else -> LessonAccess.NotReached
    }
}
