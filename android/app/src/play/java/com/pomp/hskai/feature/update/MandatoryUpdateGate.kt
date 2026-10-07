package com.pomp.hskai.feature.update

import androidx.compose.runtime.Composable

/** Google Play manages updates for this flavour; app content passes through. */
@Composable
fun MandatoryUpdateGate(content: @Composable () -> Unit) {
    content()
}
