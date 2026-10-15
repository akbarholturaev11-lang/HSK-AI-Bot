package com.pomp.hskai.feature.feedback

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ShakeGestureDetectorTest {
    private fun idle(detector: ShakeGestureDetector, t: Long): Boolean =
        detector.sample(0f, 0f, 9.81f, t)

    private fun peak(detector: ShakeGestureDetector, t: Long): Boolean =
        detector.sample(15f, 0f, 9.81f, t)

    @Test fun normalTwoPulsesOpenReport() {
        val detector = ShakeGestureDetector()
        assertFalse(idle(detector, 0))
        assertFalse(peak(detector, 100))
        assertFalse(idle(detector, 180))
        assertTrue(peak(detector, 500))
    }

    @Test fun stationaryDeviceAndOrdinaryWalkingDoNotOpenReport() {
        val detector = ShakeGestureDetector()
        for (i in 0..70) {
            val t = i * 60L
            val x = if (i % 2 == 0) 3f else -3f
            assertFalse(detector.sample(x, 0f, 9.81f, t))
        }
    }

    @Test fun oneJoltAndContinuouslyHighAccelerationDoNotOpenReport() {
        val detector = ShakeGestureDetector()
        assertFalse(idle(detector, 0))
        assertFalse(peak(detector, 100))
        for (t in 150L..850L step 50) {
            assertFalse(peak(detector, t))
        }
    }

    @Test fun cooldownPreventsRepeatedWindows() {
        val detector = ShakeGestureDetector()
        idle(detector, 0)
        peak(detector, 100)
        idle(detector, 190)
        assertTrue(peak(detector, 450))
        idle(detector, 550)
        assertFalse(peak(detector, 900))
        idle(detector, 990)
        assertFalse(peak(detector, 1200))
        idle(detector, 1300)
        // Let the low-pass gravity baseline settle while the phone is still.
        idle(detector, 1700)
        idle(detector, 2100)
        idle(detector, 2400)
        idle(detector, 3000)
        idle(detector, 4800)
        assertFalse(peak(detector, 5000))
        idle(detector, 5100)
        assertTrue(peak(detector, 5400))
    }

    @Test fun twoPulsesTooFarApartDoNotOpenReport() {
        val detector = ShakeGestureDetector()
        idle(detector, 0)
        peak(detector, 100)
        idle(detector, 190)
        assertFalse(peak(detector, 2000))
    }
}
