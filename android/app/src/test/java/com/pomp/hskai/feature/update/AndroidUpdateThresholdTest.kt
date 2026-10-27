package com.pomp.hskai.feature.update

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AndroidUpdateThresholdTest {
    @Test fun `sparse version codes use published release boundary only`() {
        // The last four releases are 7, 20, 40, 54; allow code 7.
        assertFalse(AndroidUpdateThreshold.isMandatory(7, 54, 7))
        assertTrue(AndroidUpdateThreshold.isMandatory(6, 54, 7))
        assertFalse(AndroidUpdateThreshold.isMandatory(20, 54, 7))
        assertTrue(AndroidUpdateThreshold.isMandatory(40, 54, 54))
        assertFalse(AndroidUpdateThreshold.isMandatory(54, 54, 54))
    }

    @Test fun `unknown policy or unavailable required release cannot block`() {
        assertFalse(AndroidUpdateThreshold.isMandatory(1, 54, null))
        assertFalse(AndroidUpdateThreshold.isMandatory(1, 54, 0))
        assertFalse(AndroidUpdateThreshold.isMandatory(1, 20, 40))
        assertFalse(AndroidUpdateThreshold.isMandatory(60, 54, 40))
    }
}
