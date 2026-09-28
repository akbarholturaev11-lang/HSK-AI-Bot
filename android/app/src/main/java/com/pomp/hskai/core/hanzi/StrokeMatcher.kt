package com.pomp.hskai.core.hanzi

import androidx.compose.ui.geometry.Offset
import kotlin.math.PI
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/** How one handwritten stroke compared with the stroke it should have been. */
internal data class StrokeMatch(
    val isMatch: Boolean,
    /** Right place and shape, drawn from the wrong end. */
    val isBackwards: Boolean = false,
)

/**
 * Decides whether a learner's stroke is the one the character needs next.
 *
 * A port of hanzi-writer's `strokeMatches` — the checker behind its quiz mode
 * and behind every web app that uses it — with its thresholds unchanged. A
 * stroke passes when it lies near the expected stroke's centre line, starts
 * and ends near its ends, runs the same way, has the same shape once size and
 * position are taken out, and is not much shorter. It is then compared with
 * the strokes still to come: when one of those fits better, the learner has
 * most likely written a later stroke early, and the bar is raised.
 *
 * Every point is in the character's own 1024-unit grid ([HanziGrid.toGrid]),
 * the space the thresholds were tuned in.
 */
internal object StrokeMatcher {

    fun match(
        userPoints: List<Offset>,
        medians: List<List<Offset>>,
        strokeIndex: Int,
        outlineVisible: Boolean,
        leniency: Float = 1f,
    ): StrokeMatch {
        val points = stripDuplicates(userPoints)
        val target = medians.getOrNull(strokeIndex)
        if (points.size < 2 || target == null || target.size < 2) return StrokeMatch(false)

        val first = matchData(points, target, strokeIndex, outlineVisible, leniency, checkBackwards = true)
        if (!first.isMatch) return StrokeMatch(false, first.isBackwards)

        var closest = first.averageDistance
        for (later in strokeIndex + 1 until medians.size) {
            val other = matchData(
                points,
                medians[later],
                later,
                outlineVisible,
                leniency,
                checkBackwards = false,
            )
            if (other.isMatch && other.averageDistance < closest) closest = other.averageDistance
        }
        // A later stroke fits better: tighten, between 0.3 and 0.6 of the
        // leniency depending on how much better, rather than refuse outright.
        if (closest < first.averageDistance) {
            val adjustment = (0.6f * (closest + first.averageDistance)) / (2f * first.averageDistance)
            val strict = matchData(
                points,
                target,
                strokeIndex,
                outlineVisible,
                leniency * adjustment,
                checkBackwards = true,
            )
            return StrokeMatch(strict.isMatch, strict.isBackwards)
        }
        return StrokeMatch(true)
    }

    private class MatchData(val isMatch: Boolean, val averageDistance: Float, val isBackwards: Boolean)

    private fun matchData(
        points: List<Offset>,
        stroke: List<Offset>,
        strokeNumber: Int,
        outlineVisible: Boolean,
        leniency: Float,
        checkBackwards: Boolean,
    ): MatchData {
        val averageDistance = averageDistance(points, stroke)
        // The first stroke drawn on an empty grid has nothing to line up
        // against, so it is allowed to wander twice as far.
        val distanceModifier = if (outlineVisible || strokeNumber > 0) 0.5f else 1f
        if (averageDistance > AVERAGE_DISTANCE_THRESHOLD * distanceModifier * leniency) {
            return MatchData(false, averageDistance, false)
        }
        val isMatch = startAndEndMatch(points, stroke, leniency) &&
            directionMatches(points, stroke) &&
            shapeMatches(points, stroke, leniency) &&
            lengthMatches(points, stroke, leniency)
        if (checkBackwards && !isMatch) {
            val reversed = matchData(points.asReversed(), stroke, strokeNumber, outlineVisible, leniency, false)
            if (reversed.isMatch) return MatchData(false, averageDistance, true)
        }
        return MatchData(isMatch, averageDistance, false)
    }

    /** Mean distance from each drawn point to the nearest point of the stroke. */
    private fun averageDistance(points: List<Offset>, stroke: List<Offset>): Float =
        points.sumOf { point -> stroke.minOf { (it - point).getDistance() }.toDouble() }.toFloat() / points.size

    private fun startAndEndMatch(points: List<Offset>, stroke: List<Offset>, leniency: Float): Boolean {
        val limit = START_AND_END_DISTANCE_THRESHOLD * leniency
        return (stroke.first() - points.first()).getDistance() <= limit &&
            (stroke.last() - points.last()).getDistance() <= limit
    }

    private fun directionMatches(points: List<Offset>, stroke: List<Offset>): Boolean {
        val strokeVectors = edges(stroke).filter { it.getDistance() > 0f }
        if (strokeVectors.isEmpty()) return false
        val similarities = edges(points).map { edge ->
            strokeVectors.maxOf { cosineSimilarity(it, edge) }
        }
        return similarities.average() > COSINE_SIMILARITY_THRESHOLD
    }

    private fun lengthMatches(points: List<Offset>, stroke: List<Offset>, leniency: Float): Boolean =
        leniency * (length(points) + 25f) / (length(stroke) + 25f) >= MIN_LENGTH_THRESHOLD

    private fun shapeMatches(points: List<Offset>, stroke: List<Offset>, leniency: Float): Boolean {
        val drawn = normalizeCurve(points) ?: return false
        val expected = normalizeCurve(stroke) ?: return false
        val best = SHAPE_FIT_ROTATIONS.minOf { theta -> frechetDistance(drawn, rotated(expected, theta)) }
        return best <= FRECHET_THRESHOLD * leniency
    }

    // --- geometry, as in hanzi-writer's geometry.ts ---

    private fun stripDuplicates(points: List<Offset>): List<Offset> {
        if (points.size < 2) return points
        val result = ArrayList<Offset>(points.size)
        points.forEach { if (result.isEmpty() || result.last() != it) result.add(it) }
        return result
    }

    private fun edges(points: List<Offset>): List<Offset> =
        points.zipWithNext { a, b -> b - a }

    private fun length(points: List<Offset>): Float =
        points.zipWithNext { a, b -> (b - a).getDistance() }.sum()

    private fun cosineSimilarity(a: Offset, b: Offset): Float {
        val magnitude = a.getDistance() * b.getDistance()
        return if (magnitude == 0f) 0f else (a.x * b.x + a.y * b.y) / magnitude
    }

    /** Resampled to evenly spaced points, centred, and scaled to unit size. */
    private fun normalizeCurve(curve: List<Offset>): List<Offset>? {
        if (length(curve) <= 0f) return null
        val outlined = outlineCurve(curve)
        val mean = Offset(outlined.map { it.x }.average().toFloat(), outlined.map { it.y }.average().toFloat())
        val translated = outlined.map { it - mean }
        val first = translated.first()
        val last = translated.last()
        val scale = sqrt(((first.x * first.x + first.y * first.y) + (last.x * last.x + last.y * last.y)) / 2f)
        if (scale == 0f) return null
        return subdivideCurve(translated.map { Offset(it.x / scale, it.y / scale) })
    }

    private fun outlineCurve(curve: List<Offset>, count: Int = OUTLINE_POINTS): List<Offset> {
        val segment = length(curve) / (count - 1)
        val result = mutableListOf(curve.first())
        // The next unvisited point of [curve]; hanzi-writer shifts a queue.
        var cursor = 1
        repeat(count - 2) {
            var last = result.last()
            var distanceLeft = segment
            while (cursor < curve.size) {
                val next = curve[cursor]
                val toNext = (next - last).getDistance()
                if (toNext < distanceLeft) {
                    distanceLeft -= toNext
                    last = next
                    cursor++
                } else {
                    result.add(extendPointOnLine(last, next, distanceLeft - toNext))
                    return@repeat
                }
            }
        }
        result.add(curve.last())
        return result
    }

    private fun extendPointOnLine(from: Offset, to: Offset, distance: Float): Offset {
        val vector = to - from
        val norm = distance / vector.getDistance()
        return Offset(to.x + norm * vector.x, to.y + norm * vector.y)
    }

    private fun subdivideCurve(curve: List<Offset>, maxLength: Float = 0.05f): List<Offset> {
        val result = mutableListOf(curve.first())
        for (point in curve.drop(1)) {
            val previous = result.last()
            val segment = (point - previous).getDistance()
            if (segment > maxLength) {
                val pieces = ceil(segment / maxLength).toInt()
                val pieceLength = segment / pieces
                for (i in 0 until pieces) {
                    result.add(extendPointOnLine(point, previous, -pieceLength * (i + 1)))
                }
            } else {
                result.add(point)
            }
        }
        return result
    }

    private fun rotated(curve: List<Offset>, theta: Float): List<Offset> {
        val c = cos(theta)
        val s = sin(theta)
        return curve.map { Offset(c * it.x - s * it.y, s * it.x + c * it.y) }
    }

    /** Discrete Fréchet distance, one column at a time. */
    private fun frechetDistance(a: List<Offset>, b: List<Offset>): Float {
        val long = if (a.size >= b.size) a else b
        val short = if (a.size >= b.size) b else a
        var previous = FloatArray(short.size)
        for (i in long.indices) {
            val current = FloatArray(short.size)
            for (j in short.indices) {
                val distance = (long[i] - short[j]).getDistance()
                current[j] = when {
                    i == 0 && j == 0 -> distance
                    j == 0 -> max(previous[0], distance)
                    i == 0 -> max(current[j - 1], distance)
                    else -> max(min(min(previous[j], previous[j - 1]), current[j - 1]), distance)
                }
            }
            previous = current
        }
        return previous[short.size - 1]
    }

    // hanzi-writer's defaults (strokeMatches.ts). Bigger is more lenient,
    // except the two minimums.
    private const val AVERAGE_DISTANCE_THRESHOLD = 350f
    private const val START_AND_END_DISTANCE_THRESHOLD = 250f
    private const val FRECHET_THRESHOLD = 0.4f
    private const val MIN_LENGTH_THRESHOLD = 0.35f
    private const val COSINE_SIMILARITY_THRESHOLD = 0f
    private const val OUTLINE_POINTS = 30
    private val SHAPE_FIT_ROTATIONS = listOf(
        (PI / 16).toFloat(),
        (PI / 32).toFloat(),
        0f,
        (-PI / 32).toFloat(),
        (-PI / 16).toFloat(),
    )
}
