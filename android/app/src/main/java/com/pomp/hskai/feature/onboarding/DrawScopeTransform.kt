package com.pomp.hskai.feature.onboarding

import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.DrawTransform

/** Local equivalent of DrawScope.withTransform; kept here so the panda renderer stays self-contained. */
internal inline fun DrawScope.withTransform(
    transformBlock: DrawTransform.() -> Unit,
    drawBlock: DrawScope.() -> Unit,
) {
    drawContext.canvas.save()
    try {
        drawContext.transform.transformBlock()
        drawBlock()
    } finally {
        drawContext.canvas.restore()
    }
}
