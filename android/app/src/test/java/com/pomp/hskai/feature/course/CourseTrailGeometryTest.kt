package com.pomp.hskai.feature.course

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CourseTrailGeometryTest {

    @Test
    fun `offsets match Mini App sinusoid and rounded swing`() {
        assertEquals(0f, coursePathOffsetDp(unitIndex = 0, nodeIndex = 0))
        assertEquals(60f, coursePathOffsetDp(unitIndex = 0, nodeIndex = 1))
        assertEquals(74f, coursePathOffsetDp(unitIndex = 0, nodeIndex = 2))
    }

    /**
     * The one thing the trail exists to do.
     *
     * It was drawing beside the nodes instead of through them, because the
     * curve was built from its own idea of where a node sits while the node
     * was placed by the layout. Both now start from the same two numbers, and
     * this pins the point where they meet.
     */
    @Test
    fun `the curve passes exactly through the node it belongs to`() {
        val segments = courseTrailSegmentsForRow(
            previousXDp = 60f,
            currentXDp = -20f,
            nextXDp = 74f,
        )
        assertEquals(2, segments.size)

        val incoming = segments[0]
        assertEquals(-20f, incoming.endXDp)
        assertEquals(COURSE_NODE_CENTER_DP, incoming.endYDp)

        val outgoing = segments[1]
        assertEquals(-20f, outgoing.startXDp)
        assertEquals(COURSE_NODE_CENTER_DP, outgoing.startYDp)
    }

    @Test
    fun `a segment reaches exactly one row up and one row down`() {
        val segments = courseTrailSegmentsForRow(previousXDp = 10f, currentXDp = 0f, nextXDp = -10f)

        assertEquals(COURSE_NODE_CENTER_DP - COURSE_PATH_ROW_HEIGHT_DP, segments[0].startYDp)
        assertEquals(COURSE_NODE_CENTER_DP + COURSE_PATH_ROW_HEIGHT_DP, segments[1].endYDp)
    }

    @Test
    fun `neighbouring rows draw the same joint`() {
        // Qatorlar alohida chiziladi. Chegarada uzilish ko'rinmasligi uchun
        // ikkalasi AYNI bo'g'inni chizishi kerak — biri pastga chiqib
        // ketayotgan yarmini, ikkinchisi yuqoridan kirib kelayotganini.
        val upper = courseTrailSegmentsForRow(previousXDp = null, currentXDp = 0f, nextXDp = 60f)
        val lower = courseTrailSegmentsForRow(previousXDp = 0f, currentXDp = 60f, nextXDp = null)

        val outgoing = upper.single()
        val incoming = lower.single()

        // Pastdagi qator o'z tepasidan bir qator yuqoridan boshlaydi, ya'ni
        // uning koordinatalari yuqoridagi qatornikidan aynan bir qator past.
        assertEquals(outgoing.startXDp, incoming.startXDp)
        assertEquals(outgoing.startYDp, incoming.startYDp + COURSE_PATH_ROW_HEIGHT_DP)
        assertEquals(outgoing.endXDp, incoming.endXDp)
        assertEquals(outgoing.endYDp, incoming.endYDp + COURSE_PATH_ROW_HEIGHT_DP)
    }

    @Test
    fun `a lone node has nothing to connect`() {
        assertTrue(courseTrailSegmentsForRow(null, 0f, null).isEmpty())
    }

    @Test
    fun `the controls sit at the midpoint so the curve enters the node straight`() {
        val segments = courseTrailSegmentsForRow(previousXDp = 60f, currentXDp = 0f, nextXDp = null)
        val incoming = segments.single()
        val middle = (incoming.startYDp + incoming.endYDp) / 2f

        assertEquals(middle, incoming.control1YDp)
        assertEquals(middle, incoming.control2YDp)
        assertEquals(incoming.startXDp, incoming.control1XDp)
        assertEquals(incoming.endXDp, incoming.control2XDp)
    }

    @Test
    fun `the row holds the node, its label and room for the bubble`() {
        // Bu son kichrayib ketsa yozuv keyingi qatorga tushadi va tugun
        // yuqoriga suriladi — ikkalasi ham bir marta sodir bo'lgan.
        val used = COURSE_NODE_TOP_GAP_DP + COURSE_NODE_BOX_DP + COURSE_NODE_LABEL_DP
        assertTrue("qator yozuvni sig'dirmaydi", COURSE_PATH_ROW_HEIGHT_DP >= used)

        // "DAVOM ETISH" pufakchasi tugundan 43dp yuqorida, balandligi ~30dp,
        // ya'ni uning tepasi tugun markazidan 58dp yuqorida. O'sha nuqta
        // yuqoridagi qatorning yozuvidan PASTDA qolishi kerak.
        val bubbleTop = COURSE_NODE_CENTER_DP - 58f
        val spareBelowLabel = COURSE_PATH_ROW_HEIGHT_DP - used
        assertTrue(
            "pufakcha yuqoridagi yozuvni yopadi",
            bubbleTop >= -spareBelowLabel,
        )
    }
}
