package com.pomp.hskai.core.design

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.unit.dp

/** HSK AI's shared shape scale for controls and grouped content. */
object PompShapes {
    val Small: Shape = RoundedCornerShape(8.dp)
    val Medium: Shape = RoundedCornerShape(12.dp)
    val Large: Shape = RoundedCornerShape(20.dp)
    val Pill: Shape = RoundedCornerShape(50)
}
