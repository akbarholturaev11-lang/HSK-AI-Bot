package com.pomp.hskai.widget

import com.pomp.hskai.R
import org.junit.Assert.*
import org.junit.Test

/** The 28 drawings: all present, all reachable, none drawn twice. */
class WidgetArtTest {
    @Test fun `the catalog holds twenty eight assets`() {
        assertEquals(28, WidgetArt.catalog().size)
        assertEquals(28, WidgetVisualState.entries.sumOf { it.variants })
    }

    @Test fun `every state owns exactly as many variants as it declares`() {
        WidgetVisualState.entries.forEach { state ->
            val variants = WidgetArt.variants(state)
            assertEquals(state.name, state.variants, variants.size)
            assertEquals(state.name, (0 until state.variants).toList(), variants.map { it.variant })
            variants.forEach { assertEquals(state, it.state) }
        }
        assertEquals(3, WidgetVisualState.MORNING.variants)
        assertEquals(3, WidgetVisualState.DAY.variants)
        assertEquals(4, WidgetVisualState.WAITING.variants)
        assertEquals(4, WidgetVisualState.EVENING.variants)
        assertEquals(4, WidgetVisualState.LATE.variants)
        assertEquals(5, WidgetVisualState.CRITICAL.variants)
        assertEquals(5, WidgetVisualState.COMPLETED.variants)
    }

    @Test fun `no drawing and no line is used twice`() {
        val catalog = WidgetArt.catalog()
        assertEquals(28, catalog.map { it.image }.toSet().size)
        assertEquals(28, catalog.map { it.text }.toSet().size)
        catalog.forEach {
            assertNotEquals(0, it.image)
            assertNotEquals(0, it.text)
        }
    }

    @Test fun `the drawing is the static art until an animation exists`() {
        WidgetArt.catalog().forEach {
            assertNull(it.animation)
            assertEquals(it.image, it.drawable())
        }
    }

    @Test fun `each state maps onto its own artwork family`() {
        assertEquals(
            listOf(R.drawable.widget_panda_m01, R.drawable.widget_panda_m02, R.drawable.widget_panda_m03),
            WidgetArt.variants(WidgetVisualState.MORNING).map { it.image },
        )
        assertEquals(
            listOf(R.drawable.widget_panda_d01, R.drawable.widget_panda_d02, R.drawable.widget_panda_d03),
            WidgetArt.variants(WidgetVisualState.DAY).map { it.image },
        )
        assertEquals(
            listOf(R.drawable.widget_panda_w01, R.drawable.widget_panda_w02, R.drawable.widget_panda_w03, R.drawable.widget_panda_w04),
            WidgetArt.variants(WidgetVisualState.WAITING).map { it.image },
        )
        assertEquals(
            listOf(R.drawable.widget_panda_e01, R.drawable.widget_panda_e02, R.drawable.widget_panda_e03, R.drawable.widget_panda_e04),
            WidgetArt.variants(WidgetVisualState.EVENING).map { it.image },
        )
        assertEquals(
            listOf(R.drawable.widget_panda_l01, R.drawable.widget_panda_l02, R.drawable.widget_panda_l03, R.drawable.widget_panda_l04),
            WidgetArt.variants(WidgetVisualState.LATE).map { it.image },
        )
        assertEquals(
            listOf(R.drawable.widget_panda_c01, R.drawable.widget_panda_c02, R.drawable.widget_panda_c03, R.drawable.widget_panda_c04, R.drawable.widget_panda_c05),
            WidgetArt.variants(WidgetVisualState.CRITICAL).map { it.image },
        )
        assertEquals(
            listOf(R.drawable.widget_panda_ok01, R.drawable.widget_panda_ok02, R.drawable.widget_panda_ok03, R.drawable.widget_panda_ok04, R.drawable.widget_panda_ok05),
            WidgetArt.variants(WidgetVisualState.COMPLETED).map { it.image },
        )
    }

    @Test fun `each state maps onto its own lines`() {
        assertEquals(
            listOf(R.string.widget_morning_01, R.string.widget_morning_02, R.string.widget_morning_03),
            WidgetArt.variants(WidgetVisualState.MORNING).map { it.text },
        )
        assertEquals(
            listOf(R.string.widget_critical_01, R.string.widget_critical_02, R.string.widget_critical_03, R.string.widget_critical_04, R.string.widget_critical_05),
            WidgetArt.variants(WidgetVisualState.CRITICAL).map { it.text },
        )
        assertEquals(
            listOf(R.string.widget_completed_01, R.string.widget_completed_02, R.string.widget_completed_03, R.string.widget_completed_04, R.string.widget_completed_05),
            WidgetArt.variants(WidgetVisualState.COMPLETED).map { it.text },
        )
    }

    @Test fun `operational states keep their own wording and borrow a calm face`() {
        val visual = WidgetVisual(WidgetVisualState.CRITICAL, 4)
        assertEquals(R.string.widget_unlinked, WidgetArt.assetFor(WidgetAccess.UNLINKED, visual).text)
        assertEquals(R.string.widget_stale, WidgetArt.assetFor(WidgetAccess.STALE, visual).text)
        assertEquals(R.string.widget_foundation, WidgetArt.assetFor(WidgetAccess.FOUNDATION, visual).text)
        // An access state never borrows the dramatic face the clock asked for.
        listOf(WidgetAccess.UNLINKED, WidgetAccess.STALE, WidgetAccess.FOUNDATION).forEach {
            val borrowed = WidgetArt.assetFor(it, visual)
            assertTrue(borrowed.state.urgency <= WidgetVisualState.DAY.urgency)
            assertTrue(borrowed.image in WidgetArt.catalog().map { asset -> asset.image })
        }
    }

    @Test fun `an active widget draws what the resolver chose`() {
        val visual = WidgetVisual(WidgetVisualState.WAITING, 2)
        val asset = WidgetArt.assetFor(WidgetAccess.ACTIVE, visual)
        assertEquals(R.drawable.widget_panda_w03, asset.image)
        assertEquals(R.string.widget_waiting_03, asset.text)
    }

    @Test fun `a milestone keeps the celebrating face and says what was reached`() {
        val visual = WidgetVisual(WidgetVisualState.COMPLETED, 1, WidgetSpecialState(WidgetSpecialKind.MILESTONE, 30))
        val asset = WidgetArt.assetFor(WidgetAccess.ACTIVE, visual)
        assertEquals(R.drawable.widget_panda_ok02, asset.image)
        assertEquals(R.string.widget_milestone, asset.text)
    }

    @Test fun `an out of range variant cannot crash a home screen`() {
        assertEquals(
            R.drawable.widget_panda_m01,
            WidgetArt.assetFor(WidgetAccess.ACTIVE, WidgetVisual(WidgetVisualState.MORNING, -1)).image,
        )
        assertEquals(
            R.drawable.widget_panda_m03,
            WidgetArt.assetFor(WidgetAccess.ACTIVE, WidgetVisual(WidgetVisualState.MORNING, 9)).image,
        )
    }

    @Test fun `every drawing in the catalog is reachable from the resolver`() {
        val reached = mutableSetOf<Int>()
        WidgetVisualState.entries.forEach { state ->
            (1..400).forEach { offset ->
                val date = java.time.LocalDate.of(2026, 1, 1).plusDays(offset.toLong()).toString()
                listOf("a", "b", "c", "uninitialized").forEach { candidate ->
                    val variant = WidgetVisualResolver.variantFor(state, candidate, date)
                    reached += WidgetArt.variants(state)[variant].image
                }
            }
        }
        assertEquals(WidgetArt.catalog().map { it.image }.toSet(), reached)
    }
}
