package com.pomp.hskai.feature.feedback

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import android.graphics.Bitmap
import android.graphics.Canvas
import android.os.Handler
import android.os.Looper
import android.view.PixelCopy
import android.view.View
import android.view.Window
import android.view.WindowManager
import androidx.compose.ui.window.DialogWindowProvider
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull
import kotlin.coroutines.resume
import kotlin.math.roundToInt

private fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.findActivity()
    else -> null
}

/**
 * Capture the active Android window before the report UI is shown.
 * Compose and SurfaceView content is hardware drawn: PixelCopy is preferred.
 * A scaled root-view Canvas render is the fallback on devices with no PixelCopy frame.
 * Protected/FLAG_SECURE windows are never captured.
 */
suspend fun captureReportScreen(view: View): Bitmap? {
    val window = (view.parent as? DialogWindowProvider)?.window
        ?: view.context.findActivity()?.window
        ?: return null
    if (window.attributes.flags and WindowManager.LayoutParams.FLAG_SECURE != 0) return null
    val root = window.decorView
    val width = root.width
    val height = root.height
    if (width <= 0 || height <= 0) return null
    val ratio = (1080f / maxOf(width, height)).coerceAtMost(1f)
    val dstWidth = (width * ratio).roundToInt().coerceAtLeast(1)
    val dstHeight = (height * ratio).roundToInt().coerceAtLeast(1)
    val copy = runCatching { Bitmap.createBitmap(dstWidth, dstHeight, Bitmap.Config.ARGB_8888) }
        .getOrNull() ?: return null

    val successfulCopy = withTimeoutOrNull(900L) {
        suspendCancellableCoroutine<Boolean> { continuation ->
            try {
                PixelCopy.request(
                    window, copy, { result ->
                        if (continuation.isActive) {
                            continuation.resume(result == PixelCopy.SUCCESS)
                        }
                    }, Handler(Looper.getMainLooper())
                )
            } catch (_: Exception) {
                if (continuation.isActive) continuation.resume(false)
            }
        }
    } == true
    if (successfulCopy) return copy
    // Do not recycle the destination here: after a timeout PixelCopy can
    // still finish asynchronously and write to this bitmap.
    // UI-thread fallback. Capture decorView rather than a nested ComposeView.
    return runCatching {
        Bitmap.createBitmap(dstWidth, dstHeight, Bitmap.Config.ARGB_8888).also { bitmap ->
            val canvas = Canvas(bitmap)
            canvas.scale(ratio, ratio)
            root.draw(canvas)
        }
    }.getOrNull()
}
