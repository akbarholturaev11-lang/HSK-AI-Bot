package androidx.compose.material.icons.filled

import androidx.compose.material.icons.Icons
import androidx.compose.ui.graphics.vector.ImageVector

/**
 * Compose Material does not expose a Filled.Trophy symbol in the icon set used
 * by this project. The Mini App's result state is trophy-shaped conceptually,
 * so Android keeps the same API at the call site and renders the available
 * success glyph instead of failing compilation on icon-pack drift.
 */
val Icons.Filled.Trophy: ImageVector
    get() = Icons.Filled.CheckCircle
