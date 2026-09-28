package com.pomp.hskai.core.hanzi

import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Matrix

/**
 * Where a character's stroke data sits on a square canvas, and back.
 *
 * hanzi-writer data is drawn in a 1024-unit box whose y axis points up and
 * whose top edge is y = 900, not 1024: the glyphs run from y = -124 at the
 * bottom to 900 at the top. Flipping around 1024 instead — what the writing
 * animation used to do — pushed every character 124 units (12%) down the
 * box, so its foot ran over the card's edge and an empty band sat on top.
 *
 * Drawing and handwriting both go through here. A learner's finger is only
 * compared with a stroke correctly if the two agree on where the stroke is.
 */
internal object HanziGrid {
    const val SIZE = 1024f

    /** hanzi-writer's top edge; the bottom one is `TOP - SIZE`. */
    private const val TOP = 900f

    /** Grid -> canvas, for a square canvas [side] pixels wide. */
    fun matrix(side: Float): Matrix {
        val scale = side / SIZE
        return Matrix().apply {
            translate(0f, TOP * scale)
            scale(scale, -scale)
        }
    }

    fun toCanvas(point: Offset, side: Float): Offset {
        val scale = side / SIZE
        return Offset(point.x * scale, (TOP - point.y) * scale)
    }

    fun toGrid(point: Offset, side: Float): Offset {
        val scale = side / SIZE
        return Offset(point.x / scale, TOP - point.y / scale)
    }
}
