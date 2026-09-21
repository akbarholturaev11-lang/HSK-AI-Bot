package com.pomp.hskai.widget

import androidx.annotation.DrawableRes
import androidx.annotation.StringRes
import com.pomp.hskai.R

/**
 * One drawing and one line, chosen together.
 *
 * [image] is the static V1 artwork and doubles as the fallback. [animation]
 * is the slot a moving version will take later: a renderer asks for
 * [drawable], so introducing motion is one field per row and no change to the
 * state engine. The artwork itself carries no words — [text] is a resource,
 * so Uzbek, Russian and Tajik stay complete.
 */
data class WidgetAsset(
    val state: WidgetVisualState,
    val variant: Int,
    @DrawableRes val image: Int,
    @StringRes val text: Int,
    @DrawableRes val animation: Int? = null,
) {
    @DrawableRes fun drawable(): Int = animation ?: image
}

/**
 * The 28 drawings, and the only place a state turns into one.
 *
 * Selection ([WidgetVisualResolver]), artwork (here) and layout
 * ([WidgetContent]) stay three separate concerns, so new art is a row in this
 * table and a new rule is a branch in the resolver.
 */
object WidgetArt {
    private val CATALOG: Map<WidgetVisualState, List<WidgetAsset>> = mapOf(
        WidgetVisualState.MORNING to listOf(
            asset(WidgetVisualState.MORNING, 0, R.drawable.widget_panda_m01, R.string.widget_morning_01),
            asset(WidgetVisualState.MORNING, 1, R.drawable.widget_panda_m02, R.string.widget_morning_02),
            asset(WidgetVisualState.MORNING, 2, R.drawable.widget_panda_m03, R.string.widget_morning_03),
        ),
        WidgetVisualState.DAY to listOf(
            asset(WidgetVisualState.DAY, 0, R.drawable.widget_panda_d01, R.string.widget_day_01),
            asset(WidgetVisualState.DAY, 1, R.drawable.widget_panda_d02, R.string.widget_day_02),
            asset(WidgetVisualState.DAY, 2, R.drawable.widget_panda_d03, R.string.widget_day_03),
        ),
        WidgetVisualState.WAITING to listOf(
            asset(WidgetVisualState.WAITING, 0, R.drawable.widget_panda_w01, R.string.widget_waiting_01),
            asset(WidgetVisualState.WAITING, 1, R.drawable.widget_panda_w02, R.string.widget_waiting_02),
            asset(WidgetVisualState.WAITING, 2, R.drawable.widget_panda_w03, R.string.widget_waiting_03),
            asset(WidgetVisualState.WAITING, 3, R.drawable.widget_panda_w04, R.string.widget_waiting_04),
        ),
        WidgetVisualState.EVENING to listOf(
            asset(WidgetVisualState.EVENING, 0, R.drawable.widget_panda_e01, R.string.widget_evening_01),
            asset(WidgetVisualState.EVENING, 1, R.drawable.widget_panda_e02, R.string.widget_evening_02),
            asset(WidgetVisualState.EVENING, 2, R.drawable.widget_panda_e03, R.string.widget_evening_03),
            asset(WidgetVisualState.EVENING, 3, R.drawable.widget_panda_e04, R.string.widget_evening_04),
        ),
        WidgetVisualState.LATE to listOf(
            asset(WidgetVisualState.LATE, 0, R.drawable.widget_panda_l01, R.string.widget_late_01),
            asset(WidgetVisualState.LATE, 1, R.drawable.widget_panda_l02, R.string.widget_late_02),
            asset(WidgetVisualState.LATE, 2, R.drawable.widget_panda_l03, R.string.widget_late_03),
            asset(WidgetVisualState.LATE, 3, R.drawable.widget_panda_l04, R.string.widget_late_04),
        ),
        WidgetVisualState.CRITICAL to listOf(
            asset(WidgetVisualState.CRITICAL, 0, R.drawable.widget_panda_c01, R.string.widget_critical_01),
            asset(WidgetVisualState.CRITICAL, 1, R.drawable.widget_panda_c02, R.string.widget_critical_02),
            asset(WidgetVisualState.CRITICAL, 2, R.drawable.widget_panda_c03, R.string.widget_critical_03),
            asset(WidgetVisualState.CRITICAL, 3, R.drawable.widget_panda_c04, R.string.widget_critical_04),
            asset(WidgetVisualState.CRITICAL, 4, R.drawable.widget_panda_c05, R.string.widget_critical_05),
        ),
        WidgetVisualState.COMPLETED to listOf(
            asset(WidgetVisualState.COMPLETED, 0, R.drawable.widget_panda_ok01, R.string.widget_completed_01),
            asset(WidgetVisualState.COMPLETED, 1, R.drawable.widget_panda_ok02, R.string.widget_completed_02),
            asset(WidgetVisualState.COMPLETED, 2, R.drawable.widget_panda_ok03, R.string.widget_completed_03),
            asset(WidgetVisualState.COMPLETED, 3, R.drawable.widget_panda_ok04, R.string.widget_completed_04),
            asset(WidgetVisualState.COMPLETED, 4, R.drawable.widget_panda_ok05, R.string.widget_completed_05),
        ),
    )

    private fun asset(
        state: WidgetVisualState,
        variant: Int,
        @DrawableRes image: Int,
        @StringRes text: Int,
    ) = WidgetAsset(state = state, variant = variant, image = image, text = text)

    /** Every drawing the widget owns. Nothing is drawn that is not in here. */
    fun catalog(): List<WidgetAsset> = CATALOG.values.flatten()

    fun variants(state: WidgetVisualState): List<WidgetAsset> = CATALOG.getValue(state)

    /**
     * The drawing and the line for one render.
     *
     * The three operational states borrow a calm face and keep their own
     * wording: they are about access, not about how the day is going, so they
     * must not look like an opinion on the learner's progress.
     */
    fun assetFor(access: WidgetAccess, visual: WidgetVisual): WidgetAsset = when (access) {
        WidgetAccess.UNLINKED -> borrow(WidgetVisualState.MORNING, 0, R.string.widget_unlinked)
        WidgetAccess.STALE -> borrow(WidgetVisualState.DAY, 0, R.string.widget_stale)
        WidgetAccess.FOUNDATION -> borrow(WidgetVisualState.MORNING, 1, R.string.widget_foundation)
        WidgetAccess.ACTIVE -> active(visual)
    }

    private fun active(visual: WidgetVisual): WidgetAsset {
        val drawn = variants(visual.state)[visual.variant.coerceIn(0, visual.state.variants - 1)]
        val special = visual.special ?: return drawn
        // A milestone keeps the celebrating face and says what was reached.
        // The four kinds with no producer never arrive here; they borrow the
        // nearest family so adding one later is a row, not a redesign.
        return when (special.kind) {
            WidgetSpecialKind.MILESTONE -> drawn.copy(text = R.string.widget_milestone)
            WidgetSpecialKind.STREAK_BROKEN,
            WidgetSpecialKind.COMEBACK,
            WidgetSpecialKind.NEW_USER,
            WidgetSpecialKind.SEASONAL,
            -> drawn
        }
    }

    private fun borrow(state: WidgetVisualState, variant: Int, @StringRes text: Int): WidgetAsset =
        variants(state)[variant].copy(text = text)
}
