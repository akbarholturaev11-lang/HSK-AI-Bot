package com.pomp.hskai.feature.update

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AndroidUpdateThresholdTest {
    @Test fun `same rule for both Play and Direct with four allowed versions`() {
        assertFalse(AndroidUpdateThreshold.isMandatory(54, 54, 4))
        assertFalse(AndroidUpdateThreshold.isMandatory(53, 54, 4))
        assertFalse(AndroidUpdateThreshold.isMandatory(52, 54, 4))
        assertFalse(AndroidUpdateThreshold.isMandatory(51, 54, 4))
        assertTrue(AndroidUpdateThreshold.isMandatory(50, 54, 4))
    }

    @Test fun `all admin selections apply at their exact boundary`() {
        for (count in 1..4) {
            assertFalse(AndroidUpdateThreshold.isMandatory(54 - count + 1, 54, count))
            assertTrue(AndroidUpdateThreshold.isMandatory(54 - count, 54, count))
        }
    }

    @Test fun `unknown or nonnewer version never locks user`() {
        assertFalse(AndroidUpdateThreshold.isMandatory(51, 54, 0))
        assertFalse(AndroidUpdateThreshold.isMandatory(51, 54, 5))
        assertFalse(AndroidUpdateThreshold.isMandatory(54, 54, 1))
        assertFalse(AndroidUpdateThreshold.isMandatory(55, 54, 1))
    }
}
