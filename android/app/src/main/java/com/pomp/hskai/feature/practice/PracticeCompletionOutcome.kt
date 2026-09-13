package com.pomp.hskai.feature.practice

import com.pomp.hskai.data.api.CourseGamificationDto
import com.pomp.hskai.data.api.ExamCompleteResponse
import com.pomp.hskai.data.api.ExamSectionScoreDto
import com.pomp.hskai.data.api.MistakeReviewCompleteResponse
import com.pomp.hskai.data.api.PracticeCompleteResponse
import com.pomp.hskai.data.api.PracticeWrongDto
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.decodeFromJsonElement

/**
 * One native completion contract for every Practice surface.
 *
 * Result facts stay specific to the activity (exam pass/fail, remaining
 * mistakes, section scores), while celebration facts are normalized here so
 * the UI never invents XP, streaks or duplicate state locally.
 */
internal data class PracticeCompletionOutcome(
    val kind: PracticeCompletionKind,
    val score: Int,
    val total: Int,
    val percent: Int,
    val passed: Boolean? = null,
    val passScore: Int? = null,
    val recommendation: String = "",
    val remainingMistakes: Int? = null,
    val sectionScores: Map<String, ExamSectionScoreDto> = emptyMap(),
    val wrongItems: List<PracticeWrongDto> = emptyList(),
    val gamification: CourseGamificationDto = CourseGamificationDto(),
) {
    val isDuplicate: Boolean get() = gamification.duplicate
    val awardedXp: Int get() = if (isDuplicate) 0 else gamification.awardedXp.coerceAtLeast(0)
    val hasStreakEvent: Boolean
        get() = !isDuplicate && gamification.streakUpdated && gamification.streak > 0
}

internal enum class PracticeCompletionKind {
    PRACTICE,
    PLACEMENT,
    HSK_EXAM,
    MISTAKE_REVIEW,
    RECOGNITION,
    PRONUNCIATION,
}

private val completionJson = Json {
    ignoreUnknownKeys = true
    coerceInputValues = true
}

/**
 * Practice and mistake-review endpoints already return the canonical
 * CourseGamificationService snapshot under `reward`. Decode it into the same
 * DTO used by lesson completion instead of reading individual JSON keys in UI.
 */
internal fun JsonObject?.toCourseGamification(): CourseGamificationDto {
    if (this == null) return CourseGamificationDto()
    return runCatching {
        completionJson.decodeFromJsonElement<CourseGamificationDto>(this)
    }.getOrElse { CourseGamificationDto() }
}

internal fun PracticeCompleteResponse.toCompletionOutcome(
    mode: String,
): PracticeCompletionOutcome = PracticeCompletionOutcome(
    kind = if (mode.equals("placement", ignoreCase = true)) {
        PracticeCompletionKind.PLACEMENT
    } else {
        PracticeCompletionKind.PRACTICE
    },
    score = score,
    total = total,
    percent = percent.coerceIn(0, 100),
    recommendation = recommendation,
    wrongItems = wrongItems,
    gamification = reward.toCourseGamification(),
)

internal fun MistakeReviewCompleteResponse.toCompletionOutcome(): PracticeCompletionOutcome =
    PracticeCompletionOutcome(
        kind = PracticeCompletionKind.MISTAKE_REVIEW,
        score = score,
        total = total,
        percent = percent.coerceIn(0, 100),
        remainingMistakes = remaining,
        gamification = reward.toCourseGamification(),
    )

/**
 * Exam result data is normalized here now; reward/wrong-items are parameters
 * until the Android exam DTO is widened to retain the fields already returned
 * by CourseHskExamService. Keeping the seam explicit prevents fake client-side
 * gamification in the meantime.
 */
internal fun ExamCompleteResponse.toCompletionOutcome(
    gamification: CourseGamificationDto = CourseGamificationDto(),
    wrongItems: List<PracticeWrongDto> = emptyList(),
): PracticeCompletionOutcome = PracticeCompletionOutcome(
    kind = PracticeCompletionKind.HSK_EXAM,
    score = score,
    total = total,
    percent = percent.coerceIn(0, 100),
    passed = passed,
    passScore = passScore,
    sectionScores = sectionScores,
    wrongItems = wrongItems,
    gamification = gamification,
)

internal fun drillCompletionOutcome(
    kind: PracticeCompletionKind,
    correct: Int,
    total: Int,
): PracticeCompletionOutcome {
    require(kind == PracticeCompletionKind.RECOGNITION || kind == PracticeCompletionKind.PRONUNCIATION)
    val safeTotal = total.coerceAtLeast(0)
    val safeScore = correct.coerceIn(0, safeTotal)
    val percent = if (safeTotal == 0) 0 else (safeScore * 100.0 / safeTotal).toInt()
    return PracticeCompletionOutcome(
        kind = kind,
        score = safeScore,
        total = safeTotal,
        percent = percent.coerceIn(0, 100),
    )
}
