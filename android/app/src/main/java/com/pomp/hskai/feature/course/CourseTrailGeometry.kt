package com.pomp.hskai.feature.course

import kotlin.math.roundToInt
import kotlin.math.sin

internal const val COURSE_PATH_ROW_HEIGHT_DP = 84f
internal const val COURSE_PATH_SWING_DP = 76f
internal const val COURSE_PATH_TOP_PADDING_DP = 8f
internal const val COURSE_NODE_CENTER_DP = 32f

internal data class CourseTrailPoint(
    val xOffsetDp: Float,
    val yDp: Float,
)

internal data class CourseTrailCubic(
    val start: CourseTrailPoint,
    val control1: CourseTrailPoint,
    val control2: CourseTrailPoint,
    val end: CourseTrailPoint,
)

internal fun coursePathOffsetDp(unitIndex: Int, nodeIndex: Int): Float =
    (sin((unitIndex * 3 + nodeIndex) * 0.9) * COURSE_PATH_SWING_DP).roundToInt().toFloat()

internal fun courseTrailPoints(unitIndex: Int, nodeCount: Int): List<CourseTrailPoint> =
    List(nodeCount.coerceAtLeast(0)) { nodeIndex ->
        CourseTrailPoint(
            xOffsetDp = coursePathOffsetDp(unitIndex, nodeIndex),
            yDp = COURSE_PATH_TOP_PADDING_DP + COURSE_NODE_CENTER_DP +
                COURSE_PATH_ROW_HEIGHT_DP * nodeIndex,
        )
    }

internal fun courseTrailCubics(unitIndex: Int, nodeCount: Int): List<CourseTrailCubic> {
    val points = courseTrailPoints(unitIndex, nodeCount)
    if (points.size < 2) return emptyList()
    return points.zipWithNext { a, b ->
        val middleY = (a.yDp + b.yDp) / 2f
        CourseTrailCubic(
            start = a,
            control1 = CourseTrailPoint(a.xOffsetDp, middleY),
            control2 = CourseTrailPoint(b.xOffsetDp, middleY),
            end = b,
        )
    }
}
