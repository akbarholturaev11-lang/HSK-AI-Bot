package com.pomp.hskai.feature.onboarding

/**
 * Pure responsive contract ported from course_v3_onboarding.html media queries.
 * Keeping thresholds here makes UI parity testable without Compose screenshots.
 */
internal data class OnboardingLayoutSpec(
    val compactWidth: Boolean,
    val shortHeight: Boolean,
    val wideWidth: Boolean,
    val horizontalPadding: Int,
    val guideHorizontalPadding: Int,
    val guideVerticalPadding: Int,
    val guideGap: Int,
    val guidePandaWidth: Int,
    val guidePandaHeight: Int,
    val questionFontSize: Int,
    val footerHorizontalPadding: Int,
    val footerTopPadding: Int,
    val footerBottomPadding: Int,
    val welcomeHorizontalPadding: Int,
    val welcomeTopPadding: Int,
    val welcomeBottomPadding: Int,
    val welcomePandaWidth: Int,
    val welcomePandaHeight: Int,
    val welcomePandaBottomMargin: Int,
    val welcomeBubbleBottomMargin: Int,
    val welcomeTitleSize: Int,
    val welcomeBodySize: Int,
) {
    companion object {
        fun resolve(widthDp: Int, heightDp: Int): OnboardingLayoutSpec {
            val compact = widthDp <= 360
            val short = heightDp <= 700
            val wide = widthDp >= 700
            return OnboardingLayoutSpec(
                compactWidth = compact,
                shortHeight = short,
                wideWidth = wide,
                horizontalPadding = if (compact) 16 else 24,
                guideHorizontalPadding = if (compact) 16 else 24,
                guideVerticalPadding = if (compact) 15 else if (short) 12 else if (wide) 30 else 22,
                guideGap = if (compact) 12 else 16,
                guidePandaWidth = if (compact) 70 else 90,
                guidePandaHeight = if (compact) 80 else 100,
                questionFontSize = if (compact) 19 else 21,
                footerHorizontalPadding = if (compact) 16 else 24,
                footerTopPadding = if (short) 12 else 16,
                footerBottomPadding = if (short) 14 else 20,
                welcomeHorizontalPadding = if (compact) 24 else 30,
                welcomeTopPadding = if (short) 24 else 36,
                welcomeBottomPadding = if (short) 16 else 28,
                welcomePandaWidth = when {
                    wide -> 220
                    short -> 144
                    else -> 190
                },
                welcomePandaHeight = when {
                    wide -> 233
                    short -> 153
                    else -> 202
                },
                welcomePandaBottomMargin = if (short) 16 else 23,
                welcomeBubbleBottomMargin = if (short) 18 else 27,
                welcomeTitleSize = if (short) 34 else 38,
                welcomeBodySize = if (short) 14 else 16,
            )
        }
    }
}
