package com.pomp.hskai.feature.voice

import android.graphics.Bitmap
import android.graphics.BitmapShader
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.Path
import android.graphics.PorterDuff
import android.graphics.PorterDuffXfermode
import android.graphics.RadialGradient
import android.graphics.Rect
import android.graphics.RectF
import android.graphics.Shader
import android.os.Build
import java.nio.ByteBuffer
import java.util.Random
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * The V8 cinnabar orb, drawn exactly as the reference canvas renderer
 * (`render()` in HSK_AI_Voice_Integrated_V8.html / iphone-pwa-voice.html):
 * a drifting linear wash, four pigment blobs, three blurred crests, a
 * travelling caustic, a glaze, grain and a thin rim.
 *
 * The crests' `ctx.filter = blur(size × 0.045)` is reproduced on every API
 * level by drawing them into a quarter-size layer and box-blurring it three
 * times (a Gaussian approximation) before it is scaled back over the orb.
 */
internal class VoiceV8OrbRenderer {
    private val noise: Bitmap = Bitmap.createBitmap(64, 64, Bitmap.Config.ARGB_8888).apply {
        val random = Random(8L)
        val pixels = IntArray(64 * 64) {
            val v = 144 + (random.nextFloat() * 105).toInt()
            Color.argb((random.nextFloat() * 22).roundToInt(), v, v, v)
        }
        setPixels(pixels, 0, 64, 0, 0, 64, 64)
    }
    private val noiseMatrix = Matrix()
    private val noisePaint = Paint().apply {
        shader = BitmapShader(noise, Shader.TileMode.REPEAT, Shader.TileMode.REPEAT)
        alpha = (0.09f * 255).roundToInt()
    }
    private val fill = Paint(Paint.ANTI_ALIAS_FLAG)
    private val crestFill = Paint(Paint.ANTI_ALIAS_FLAG)
    private val layerPaint = Paint(Paint.FILTER_BITMAP_FLAG or Paint.ANTI_ALIAS_FLAG)
    private val caustic = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        color = rgba(255, 242, 228, 0.12f)
        xfermode = PorterDuffXfermode(PorterDuff.Mode.SCREEN)
    }
    private val rim = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        color = rgba(255, 234, 220, 0.27f)
    }
    private val path = Path()
    private val clip = Path()
    private val target = RectF()
    private val source = Rect()

    private var layer: Bitmap? = null
    private var layerCanvas: Canvas? = null
    private var bytes = ByteArray(0)
    private var channels = IntArray(0)
    private var scratch = IntArray(0)

    /**
     * @param size orb diameter in pixels
     * @param dp one density-independent pixel in pixels (the demo's CSS pixel)
     * @param t the demo's `t` (`ms × 0.00083`, or 1.2 with reduced motion)
     * @param active 1.16 while listening or speaking, otherwise 1
     */
    fun draw(canvas: Canvas, size: Float, dp: Float, t: Float, active: Float) {
        if (size < 2f) return
        val c = size / 2f
        val r = c - 0.75f * dp
        canvas.save()
        clip.reset()
        clip.addCircle(c, c, r, Path.Direction.CW)
        canvas.clipPath(clip)

        fill.shader = LinearGradient(
            size * (0.15f + 0.12f * sin(t * 0.42f)), 0f,
            size * (0.78f + 0.1f * cos(t * 0.38f)), size,
            intArrayOf(0xFFB63738.toInt(), 0xFFDB554C.toInt(), 0xFFF18E72.toInt(), 0xFFFFF5DF.toInt()),
            floatArrayOf(0f, 0.29f, 0.62f, 1f),
            Shader.TileMode.CLAMP,
        )
        canvas.drawRect(0f, 0f, size, size, fill)

        blob(canvas, size * (0.25f + 0.12f * sin(t * 0.91f)), size * (0.17f + 0.10f * cos(t * 0.51f)), size * 0.74f, rgba(121, 13, 28, 0.58f))
        blob(canvas, size * (0.82f + 0.1f * cos(t * 0.78f)), size * (0.40f + 0.10f * sin(t * 0.83f)), size * 0.73f, rgba(205, 43, 46, 0.58f))
        blob(canvas, size * (0.30f + 0.18f * sin(t * 0.63f + 1f)), size * (0.78f + 0.10f * sin(t * 0.51f)), size * 0.66f, rgba(255, 251, 234, 0.76f))
        blob(canvas, size * (0.63f + 0.20f * sin(t * 0.48f)), size * (0.58f + 0.08f * cos(t * 0.74f)), size * 0.45f, rgba(255, 225, 189, 0.4f))

        drawCrests(canvas, size, t, active)

        // Travelling caustic highlight, screen-blended.
        path.reset()
        var i = 0f
        var first = true
        while (i <= 1f) {
            val y = 0.57f + 0.073f * sin(i * 9.8f + t * 1.35f) + 0.018f * sin(i * 18f - t * 0.62f)
            if (first) path.moveTo(0f, y * size) else path.lineTo(i * size, y * size)
            first = false
            i += 0.027f
        }
        caustic.strokeWidth = size * 0.026f
        canvas.drawPath(path, caustic)

        fill.shader = glaze(size, c)
        canvas.drawRect(0f, 0f, size, size, fill)

        // Grain: the demo's 64px tile on a 2× canvas is 32 CSS pixels wide.
        noiseMatrix.setScale(dp / 2f, dp / 2f)
        noisePaint.shader.setLocalMatrix(noiseMatrix)
        canvas.drawRect(0f, 0f, size, size, noisePaint)
        canvas.restore()

        rim.strokeWidth = 1.1f * dp
        canvas.drawCircle(c, c, r - 0.4f * dp, rim)
    }

    private fun blob(canvas: Canvas, x: Float, y: Float, radius: Float, color: Int) {
        fill.shader = RadialGradient(
            x, y, radius,
            intArrayOf(color, color, 0x00FFFFFF),
            floatArrayOf(0f, 0.04f, 1f),
            Shader.TileMode.CLAMP,
        )
        canvas.drawRect(x - radius, y - radius, x + radius, y + radius, fill)
    }

    private fun glaze(size: Float, c: Float): Shader {
        val colors = intArrayOf(rgba(255, 255, 255, 0.06f), 0x00FFFFFF, rgba(54, 6, 17, 0.27f))
        val stops = floatArrayOf(0f, 0.77f, 1f)
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            // The canvas's two-circle gradient, available natively from API 31.
            RadialGradient(
                size * 0.43f, size * 0.39f, size * 0.03f, c, c, size * 0.73f,
                LongArray(colors.size) { Color.pack(colors[it]) }, stops, Shader.TileMode.CLAMP,
            )
        } else {
            RadialGradient(size * 0.43f, size * 0.39f, size * 0.75f, colors, stops, Shader.TileMode.CLAMP)
        }
    }

    private fun drawCrests(canvas: Canvas, size: Float, t: Float, active: Float) {
        val side = max(16, (size / 4f).roundToInt())
        var bitmap = layer
        if (bitmap == null || bitmap.width != side) {
            bitmap?.recycle()
            bitmap = Bitmap.createBitmap(side, side, Bitmap.Config.ARGB_8888)
            layer = bitmap
            layerCanvas = Canvas(bitmap)
            bytes = ByteArray(side * side * 4)
            channels = IntArray(side * side * 4)
            scratch = IntArray(side * side * 4)
        }
        val crestCanvas = layerCanvas ?: return
        bitmap.eraseColor(0)
        val scale = side / size
        crestCanvas.save()
        crestCanvas.scale(scale, scale)
        crest(crestCanvas, size, t, 0.58f, 0.105f * active, 0f, 1.35f, rgba(255, 241, 216, 0.51f))
        crest(crestCanvas, size, t, 0.68f, 0.095f * active, 2.15f, -1.1f, rgba(255, 254, 244, 0.53f))
        crest(crestCanvas, size, t, 0.77f, 0.075f * active, 4.12f, 1.42f, rgba(251, 240, 230, 0.48f))
        crestCanvas.restore()

        // ctx.filter = blur(max(1, round(size × 0.045))px): σ in layer pixels.
        val sigma = max(1f, (size * 0.045f).roundToInt().toFloat()) * scale
        val radius = max(1, ((sqrt(4f * sigma * sigma + 1f) - 1f) / 2f).roundToInt())
        blurLayer(bitmap, side, radius)

        source.set(0, 0, side, side)
        target.set(0f, 0f, size, size)
        canvas.drawBitmap(bitmap, source, target, layerPaint)
    }

    private fun crest(
        canvas: Canvas, size: Float, t: Float,
        base: Float, amp: Float, phase: Float, rate: Float, color: Int,
    ) {
        path.reset()
        path.moveTo(-size * 0.17f, size * 1.14f)
        var i = -0.17f
        while (i <= 1.18f) {
            val y = base + amp * (
                sin(i * 9.8f + t * rate + phase) * 0.7f +
                    sin(i * 16.6f - t * 0.69f + phase) * 0.23f +
                    sin(i * 4.1f + t * 0.51f) * 0.2f
                )
            path.lineTo(i * size, y * size)
            i += 0.022f
        }
        path.lineTo(size * 1.19f, size * 1.17f)
        path.close()
        crestFill.color = color
        canvas.drawPath(path, crestFill)
    }

    /** Three box passes on premultiplied bytes; outside the layer is transparent. */
    private fun blurLayer(bitmap: Bitmap, side: Int, radius: Int) {
        val buffer = ByteBuffer.wrap(bytes)
        bitmap.copyPixelsToBuffer(buffer)
        for (index in bytes.indices) channels[index] = bytes[index].toInt() and 0xFF
        repeat(3) {
            boxPass(channels, scratch, side, radius, horizontal = true)
            boxPass(scratch, channels, side, radius, horizontal = false)
        }
        for (index in bytes.indices) bytes[index] = channels[index].toByte()
        buffer.rewind()
        bitmap.copyPixelsFromBuffer(buffer)
    }

    private fun boxPass(input: IntArray, output: IntArray, side: Int, radius: Int, horizontal: Boolean) {
        val window = radius * 2 + 1
        for (line in 0 until side) {
            for (channel in 0 until 4) {
                var sum = 0
                for (k in 0..radius) if (k < side) sum += input[index(line, k, side, channel, horizontal)]
                for (pos in 0 until side) {
                    output[index(line, pos, side, channel, horizontal)] = sum / window
                    val add = pos + radius + 1
                    val drop = pos - radius
                    if (add < side) sum += input[index(line, add, side, channel, horizontal)]
                    if (drop >= 0) sum -= input[index(line, drop, side, channel, horizontal)]
                }
            }
        }
    }

    private fun index(line: Int, pos: Int, side: Int, channel: Int, horizontal: Boolean): Int =
        (if (horizontal) line * side + pos else pos * side + line) * 4 + channel

    fun release() {
        layer?.recycle()
        layer = null
        layerCanvas = null
    }

    private companion object {
        fun rgba(r: Int, g: Int, b: Int, a: Float): Int = Color.argb((a * 255).roundToInt(), r, g, b)
    }
}
