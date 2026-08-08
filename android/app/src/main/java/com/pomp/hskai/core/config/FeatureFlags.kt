package com.pomp.hskai.core.config

/**
 * Unfinished features fail closed.
 *
 * A tab or button must never open a screen that cannot do its job yet, so the
 * navigation bar only shows what is actually implemented. Each flag flips on
 * in the phase that builds the feature, not before.
 */
object FeatureFlags {
    /** Phase F. */
    const val PRACTICE_ENABLED = false

    /** Phase G. */
    const val VOICE_ENABLED = false

    /** Phase J. Until then no screen may offer a subscription CTA. */
    const val SUBSCRIPTION_ENABLED = false
}
