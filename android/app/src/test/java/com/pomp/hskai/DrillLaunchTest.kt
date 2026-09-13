package com.pomp.hskai

import com.pomp.hskai.feature.practice.DrillMode
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class DrillLaunchTest {

    @Test
    fun every_opening_gets_a_fresh_view_model_key() {
        val pronunciation = DrillLaunch(DrillMode.PRONUNCIATION)
        val recognition = DrillLaunch(DrillMode.RECOGNITION)
        val secondRecognition = DrillLaunch(DrillMode.RECOGNITION)

        assertNotEquals(pronunciation.viewModelKey, recognition.viewModelKey)
        assertNotEquals(recognition.viewModelKey, secondRecognition.viewModelKey)
        assertTrue(pronunciation.viewModelKey.startsWith("drill-"))
    }
}
