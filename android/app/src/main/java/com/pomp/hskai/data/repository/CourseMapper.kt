package com.pomp.hskai.data.repository

import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.data.api.CourseLessonDto
import com.pomp.hskai.data.api.CourseMapDto
import com.pomp.hskai.domain.model.CourseLesson
import com.pomp.hskai.domain.model.CourseMap
import com.pomp.hskai.domain.model.CourseMilestone
import com.pomp.hskai.domain.model.CourseProgress
import com.pomp.hskai.domain.model.CourseToday
import com.pomp.hskai.domain.model.CourseUnit
import com.pomp.hskai.domain.model.CourseUser
import com.pomp.hskai.domain.model.LessonAccess
import com.pomp.hskai.domain.model.LessonStatus
import com.pomp.hskai.domain.model.RewardChest
import com.pomp.hskai.domain.model.TodayTask
import com.pomp.hskai.domain.model.TodayTaskAccess

/** Translates the server payload into domain models without re-deciding access. */
object CourseMapper {

    fun toDomain(dto: CourseMapDto): CourseMap {
        val language = AppLanguage.fromBackendCode(dto.user.language)
        return CourseMap(
            level = dto.level,
            units = dto.units.map { unit ->
                CourseUnit(
                    number = unit.number,
                    title = unit.title.forLanguage(language),
                    isLocked = unit.status?.trim()?.lowercase() == "locked",
                    milestone = unit.milestone?.let { milestone ->
                        CourseMilestone(
                            title = milestone.title.forLanguage(language),
                            status = milestone.status,
                        )
                    },
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
                rewardChest = dto.progress.rewardChest?.let { chest ->
                    RewardChest(
                        ready = chest.ready,
                        progress = chest.progress.coerceIn(0, 100),
                        nextXp = chest.nextXp.coerceAtLeast(0),
                    )
                },
            ),
            user = CourseUser(
                name = dto.user.name,
                initials = dto.user.avatar,
                isPaid = dto.user.isPaid,
                referralCode = dto.user.referralCode,
            ),
            notificationsEnabled = dto.notify.enabled,
            today = dto.today?.let { today ->
                CourseToday(
                    goalXp = today.goalXp,
                    doneXp = today.doneXp,
                    streak = today.streak,
                    total = today.total,
                    done = today.done,
                    complete = today.complete,
                    tasks = today.tasks.map { task ->
                        TodayTask(
                            type = task.type,
                            ref = task.ref,
                            skill = task.skill,
                            role = task.role,
                            done = task.done,
                            access = when (task.access.trim().lowercase()) {
                                "ad" -> TodayTaskAccess.AD
                                "locked" -> TodayTaskAccess.LOCKED
                                else -> TodayTaskAccess.OPEN
                            },
                            available = task.available,
                        )
                    },
                    level = today.level,
                    localDay = today.localDay,
                )
            },
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

    private fun CourseLessonDto.access(): LessonAccess = when {
        completionAllowed -> LessonAccess.Open
        previewHalf -> LessonAccess.HalfPreview
        lockedPremium -> LessonAccess.PremiumLocked
        else -> LessonAccess.NotReached
    }
}
