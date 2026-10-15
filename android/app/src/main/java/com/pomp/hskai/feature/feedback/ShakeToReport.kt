package com.pomp.hskai.feature.feedback

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import kotlin.math.sqrt

/**
 * Detect two deliberate movements rather than two >25 m/s² raw acceleration
 * readings. Raw data includes gravity, and that old threshold misses normal
 * shakes on many Android phones. High-pass the motion component instead.
 *
 * Keeping the detector platform-free lets unit tests cover realistic traces.
 */
internal class ShakeGestureDetector {
    private var initialized = false
    private var gravityX = 0f
    private var gravityY = 0f
    private var gravityZ = 0f
    private var aboveThreshold = false
    private var firstPeakAt: Long? = null
    private var lastTriggeredAt = -10_000L

    fun sample(x: Float, y: Float, z: Float, elapsedMs: Long): Boolean {
        if (!initialized) {
            initialized = true
            gravityX = x
            gravityY = y
            gravityZ = z
            return false
        }

        // Low-pass the gravity estimate and retain the rapid shake motion.
        val alpha = 0.82f
        gravityX = alpha * gravityX + (1 - alpha) * x
        gravityY = alpha * gravityY + (1 - alpha) * y
        gravityZ = alpha * gravityZ + (1 - alpha) * z
        val dx = x - gravityX
        val dy = y - gravityY
        val dz = z - gravityZ
        val force = sqrt(dx * dx + dy * dy + dz * dz)

        if (force < 5.5f) {
            aboveThreshold = false
            return false
        }
        if (force < 9.0f || aboveThreshold) return false
        aboveThreshold = true

        if (elapsedMs - lastTriggeredAt < 4_500L) return false
        val previousPeak = firstPeakAt
        val interval = previousPeak?.let { elapsedMs - it }
        if (interval != null && interval in 140L..1_500L) {
            lastTriggeredAt = elapsedMs
            firstPeakAt = null
            return true
        }
        // A single jolt or very rapid duplicate sensor samples are not shakes.
        if (interval == null || interval > 1_500L || interval < 0L) {
            firstPeakAt = elapsedMs
        }
        return false
    }
}

/** Register only when the learner's setting is ON and the screen is resumed. */
@Composable
fun ShakeToReport(enabled: Boolean, onShake: () -> Unit) {
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    val callback by rememberUpdatedState(onShake)
    DisposableEffect(context, lifecycle, enabled) {
        val manager = context.getSystemService(Context.SENSOR_SERVICE) as? SensorManager
        val sensor = manager?.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        val detector = ShakeGestureDetector()
        val listener = object : SensorEventListener {
            override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit

            override fun onSensorChanged(event: SensorEvent) {
                if (event.values.size < 3) return
                if (detector.sample(
                        x = event.values[0],
                        y = event.values[1],
                        z = event.values[2],
                        elapsedMs = event.timestamp / 1_000_000L,
                    )
                ) callback()
            }
        }
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_RESUME -> if (enabled && sensor != null) {
                    manager?.registerListener(listener, sensor, SensorManager.SENSOR_DELAY_UI)
                }
                Lifecycle.Event.ON_PAUSE, Lifecycle.Event.ON_STOP ->
                    manager?.unregisterListener(listener)
                else -> Unit
            }
        }
        lifecycle.addObserver(observer)
        if (enabled && sensor != null && lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) {
            manager?.registerListener(listener, sensor, SensorManager.SENSOR_DELAY_UI)
        }
        onDispose {
            manager?.unregisterListener(listener)
            lifecycle.removeObserver(observer)
        }
    }
}
