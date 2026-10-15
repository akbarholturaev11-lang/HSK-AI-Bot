package com.pomp.hskai.core.design.components

import android.content.Context
import android.media.AudioManager
import android.media.MediaPlayer
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.provider.Settings
import com.pomp.hskai.R

/** Short, local launch-only chime. Never holds up app loading or requests permissions. */
internal class HskLaunchFeedback(private val context: Context) {
    private var player: MediaPlayer? = null

    fun play() {
        try {
            val manager = context.getSystemService(AudioManager::class.java) ?: return
            if (manager.ringerMode != AudioManager.RINGER_MODE_NORMAL) return
            if (manager.getStreamVolume(AudioManager.STREAM_MUSIC) == 0) return
            player = MediaPlayer.create(context, R.raw.hsk_launch_gold)?.apply {
                setVolume(0.4f, 0.4f)
                start()
            }
        } catch (_: Exception) {
            release()
        }
    }

    fun pulse(strong: Boolean) {
        try {
            if (Settings.System.getInt(
                    context.contentResolver, Settings.System.HAPTIC_FEEDBACK_ENABLED, 1
                ) == 0
            ) return
            // API 31+ exposes the real device vibrator through VibratorManager.
            // Older devices retain the legacy fallback; no activity context needed.
            val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                context.getSystemService(VibratorManager::class.java)?.defaultVibrator
            } else {
                context.getSystemService(Vibrator::class.java)
            } ?: return
            if (!vibrator.hasVibrator()) return
            val duration = if (strong) 22L else 12L
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator.vibrate(VibrationEffect.createOneShot(duration, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                vibrator.vibrate(duration)
            }
        } catch (_: Exception) {
            // Devices without vibration support must still launch normally.
        }
    }

    fun release() {
        try {
            player?.stop()
        } catch (_: Exception) {
            // Playback may have been rejected or already completed.
        }
        try {
            player?.release()
        } catch (_: Exception) {}
        player = null
    }
}
