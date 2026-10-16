package com.pomp.hskai.core.settings

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ShakeToReportPreferenceTest {
    @Test fun noSavedPreferenceDefaultsToOn() {
        assertTrue(resolveShakeToReportPreference(null))
    }

    @Test fun explicitOffRemainsOffAcrossStarts() {
        assertFalse(resolveShakeToReportPreference(false))
    }

    @Test fun explicitOnRemainsOn() {
        assertTrue(resolveShakeToReportPreference(true))
    }
}
