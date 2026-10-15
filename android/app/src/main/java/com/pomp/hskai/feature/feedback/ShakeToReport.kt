package com.pomp.hskai.feature.feedback

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.SystemClock
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import kotlin.math.sqrt

/** Foreground-only accelerometer listener; no sensor is registered before opt-in. */
@Composable
fun ShakeToReport(enabled: Boolean, onShake: () -> Unit) {
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    val callback by rememberUpdatedState(onShake)
    DisposableEffect(context, lifecycle, enabled) {
        val manager = context.getSystemService(Context.SENSOR_SERVICE) as? SensorManager
        val sensor = manager?.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        var lastSpike = 0L
        var lastOpened = 0L
        val listener = object : SensorEventListener {
            override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit

            override fun onSensorChanged(event: SensorEvent) {
                val x = event.values[0]
                val y = event.values[1]
                val z = event.values[2]
                val acceleration = sqrt(x * x + y * y + z * z)
                if (acceleration < 25f) return
                val now = SystemClock.elapsedRealtime()
                if (now - lastOpened < 5000L) return
                if (lastSpike > 0 && now - lastSpike in 120L..850L) {
                    lastOpened = now
                    lastSpike = 0
                    callback()
                } else {
                    lastSpike = now
                }
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
