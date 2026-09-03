package com.pomp.hskai.feature.rating

/**
 * Presentation rules for the Reyting tab, kept free of Compose so they can be
 * unit tested on the JVM.
 */

/**
 * The four server leagues and the glyph each one is drawn with, in order.
 *
 * The Mini App draws a fixed four-step ladder; here the highlighted step comes
 * from the server's own league name, so the badge cannot claim a standing the
 * learner does not have.
 */
val LEAGUE_LADDER: List<Pair<String, String>> = listOf(
    "Bronze" to "玄",
    "Silver" to "朱",
    "Gold" to "龙",
    "Sapphire" to "凤",
)

/** Top ranks that move up at the weekly reset, matching the Mini App. */
const val PROMOTION_ZONE = 5

/**
 * The league's glyph. An unknown name is shown as the server sent it rather
 * than being silently mapped onto the wrong badge.
 */
fun leagueGlyph(league: String): String =
    LEAGUE_LADDER.firstOrNull { it.first.equals(league, ignoreCase = true) }?.second
        ?: league.takeIf { it.isNotBlank() }
        ?: LEAGUE_LADDER.first().second

/** "3d 8h" style countdown for the weekly league reset chip. */
fun countdownText(seconds: Long): String {
    val total = seconds.coerceAtLeast(0)
    val days = total / 86_400
    val hours = (total % 86_400) / 3_600
    val minutes = (total % 3_600) / 60
    return when {
        days > 0 -> "${days}d ${hours}h"
        hours > 0 -> "${hours}h ${minutes}m"
        else -> "${minutes}m"
    }
}
