package com.pomp.hskai.feature.course

import kotlin.test.Test
import kotlin.test.assertEquals

class CourseTrailGeometryTest {
    @Test
    fun `offsets match Mini App sinusoid and rounded swing`() {
        assertEquals(0f, coursePathOffsetDp(unitIndex = 0, nodeIndex = 0))
        assertEquals(60f, coursePathOffsetDp(unitIndex = 0, nodeIndex = 1))
        assertEquals(74f, coursePathOffsetDp(unitIndex = 0, nodeIndex = 2))
    }

    @Test
    fun `points use path top padding plus the 64dp node center`() {
        val points = courseTrailPoints(unitIndex = 0, nodeCount = 3)
        assertEquals(listOf(40f, 124f, 208f), points.map { it.yDp })
    }

    @Test
    fun `each segment uses the midpoint y for both cubic controls`() {
        val cubics = courseTrailCubics(unitIndex = 0, nodeCount = 3)
        assertEquals(2, cubics.size)

        assertEquals(82f, cubics[0].control1.yDp)
        assertEquals(82f, cubics[0].control2.yDp)
        assertEquals(cubics[0].start.xOffsetDp, cubics[0].control1.xOffsetDp)
        assertEquals(cubics[0].end.xOffsetDp, cubics[0].control2.xOffsetDp)

        assertEquals(166f, cubics[1].control1.yDp)
        assertEquals(166f, cubics[1].control2.yDp)
    }
}
