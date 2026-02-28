package com.blindnavai.haptic

import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager

class VibrationManager(context: Context) {
    private val vibrator: Vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        val manager = context.getSystemService(VibratorManager::class.java)
        manager.defaultVibrator
    } else {
        @Suppress("DEPRECATION")
        context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
    }

    fun vibrateMinor() {
        vibratePattern(longArrayOf(0, 120), intArrayOf(0, 180))
    }

    fun vibrateMovingObject() {
        vibratePattern(longArrayOf(0, 80, 100, 80), intArrayOf(0, 200, 0, 220))
    }

    fun vibrateImmediateHazard() {
        vibratePattern(longArrayOf(0, 450), intArrayOf(0, 255))
    }

    private fun vibratePattern(timings: LongArray, amplitudes: IntArray) {
        val effect = VibrationEffect.createWaveform(timings, amplitudes, -1)
        vibrator.vibrate(effect)
    }
}
