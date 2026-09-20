package com.pomp.hskai.core.navigation

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.asPaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Style
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskGlassSurface
import com.pomp.hskai.feature.update.AppUpdateBanner

enum class MainTab(val labelRes: Int, val icon: ImageVector) {
    COURSE(R.string.nav_course, Icons.Filled.Map),
    PRACTICE(R.string.nav_practice, Icons.Filled.Style),
    VOICE(R.string.nav_ai, Icons.Filled.Mic),
    RATING(R.string.nav_rating, Icons.Filled.EmojiEvents),
    PROFILE(R.string.nav_profile, Icons.Filled.Person),
    ;

    val isCentre: Boolean get() = this == VOICE

    companion object {
        val visible: List<MainTab> get() = entries
    }
}

fun AppDestination.toTab(): MainTab? = when (this) {
    AppDestination.Today,
    AppDestination.Course,
    AppDestination.CurrentLesson,
    is AppDestination.Lesson,
    -> MainTab.COURSE

    AppDestination.Profile, AppDestination.WidgetSetup -> MainTab.PROFILE
    AppDestination.Rating -> MainTab.RATING
    AppDestination.Voice -> MainTab.VOICE
    is AppDestination.Practice -> MainTab.PRACTICE
}

/** The pill itself, without the margin it floats in. */
private val NAV_PILL_HEIGHT = 82.dp

/** The gap the pill keeps from the screen edge and from the content under it. */
private val NAV_PILL_MARGIN = 8.dp

/**
 * What the floating tab bar covers at the bottom of a main screen, above the
 * system gesture area.
 *
 * Exported because the assistant button floats outside the scaffold and still
 * has to stay off the bar.
 */
val MainBottomBarHeight: Dp = NAV_PILL_HEIGHT + NAV_PILL_MARGIN * 2

/**
 * How much room a main screen leaves free at its bottom edge.
 *
 * The tab bar is drawn *over* the content — that is what makes the glass read
 * as glass, since translucency needs something behind it. The price is that a
 * scrolling screen has to add this to its own bottom padding, or its last card
 * can never be scrolled clear of the bar.
 *
 * It already contains the system gesture inset, so a screen adds this instead
 * of `navigationBarsPadding()`, not on top of it.
 */
val LocalMainBottomInset = compositionLocalOf { 0.dp }

@Composable
fun MainScaffold(
    selectedTab: MainTab = MainTab.COURSE,
    onTabSelected: (MainTab) -> Unit,
    /**
     * False turns a tab into a full-screen one — the AI Voice conversation is
     * the only one today. A call is not a place to switch sections from, and
     * the Mini App shows no tabs there either.
     */
    bottomBarVisible: Boolean = true,
    content: @Composable (MainTab, Modifier) -> Unit,
) {
    val tabs = remember { MainTab.visible }
    val density = LocalDensity.current
    val gestureInset = WindowInsets.navigationBars.asPaddingValues().calculateBottomPadding()

    // The bar floats, so no layout hands out its height — it is measured. The
    // update banner sits above the pill and only exists in the direct build
    // two releases behind, so the measurement is the only honest source.
    var measuredBar by remember { mutableStateOf(0.dp) }
    val bottomInset = if (bottomBarVisible) {
        maxOf(measuredBar, MainBottomBarHeight + gestureInset)
    } else {
        gestureInset
    }

    Surface(modifier = Modifier.fillMaxSize(), color = PompColors.Paper) {
        Box(Modifier.fillMaxSize()) {
            CompositionLocalProvider(LocalMainBottomInset provides bottomInset) {
                content(selectedTab, Modifier.fillMaxSize().statusBarsPadding())
            }

            if (bottomBarVisible) {
                Column(
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .onSizeChanged { size ->
                            measuredBar = with(density) { size.height.toDp() }
                        },
                ) {
                    // An install two releases behind is told so here: above the
                    // tabs, on every main screen, and never inside a lesson. It
                    // takes the pill's own margin so the two read as one block.
                    // The direct channel draws it; the Play build draws nothing.
                    AppUpdateBanner(modifier = Modifier.padding(horizontal = 12.dp))
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .navigationBarsPadding()
                            .padding(horizontal = 12.dp, vertical = NAV_PILL_MARGIN),
                    ) {
                        HskGlassSurface(
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(28.dp),
                            shadowElevation = 14.dp,
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(NAV_PILL_HEIGHT)
                                    .padding(horizontal = 6.dp, vertical = 6.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceEvenly,
                            ) {
                                tabs.forEach { tab ->
                                    NavItem(
                                        tab = tab,
                                        selected = selectedTab == tab,
                                        onClick = { onTabSelected(tab) },
                                        modifier = Modifier.weight(1f),
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun NavItem(
    tab: MainTab,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val label = stringResource(tab.labelRes)
    val tint = if (selected) PompColors.Cinnabar else PompColors.InkDisabled
    val itemShape = RoundedCornerShape(18.dp)
    val selectedBackground = if (selected && !tab.isCentre) {
        PompColors.CinnabarSoft.copy(alpha = if (PompColors.IsDark) 0.72f else 0.78f)
    } else {
        Color.Transparent
    }

    Column(
        modifier = modifier
            .then(if (tab.isCentre) Modifier.offset(y = (-8).dp) else Modifier)
            .padding(horizontal = 2.dp)
            .clip(itemShape)
            .background(selectedBackground)
            .selectable(
                selected = selected,
                role = Role.Tab,
                onClick = onClick,
            )
            .padding(vertical = if (tab.isCentre) 0.dp else 7.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        if (tab.isCentre) {
            Box(contentAlignment = Alignment.Center) {
                Box(
                    modifier = Modifier
                        .size(62.dp)
                        .background(
                            color = PompColors.Cinnabar.copy(alpha = 0.12f),
                            shape = CircleShape,
                        ),
                )
                Surface(
                    modifier = Modifier
                        .size(52.dp)
                        .shadow(
                            elevation = 10.dp,
                            shape = CircleShape,
                            ambientColor = PompColors.Cinnabar.copy(alpha = 0.20f),
                            spotColor = PompColors.Cinnabar.copy(alpha = 0.30f),
                        ),
                    shape = CircleShape,
                    color = PompColors.Cinnabar,
                    border = BorderStroke(
                        3.dp,
                        if (PompColors.IsDark) {
                            PompColors.PaperRaised.copy(alpha = 0.92f)
                        } else {
                            Color.White.copy(alpha = 0.90f)
                        },
                    ),
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(
                            imageVector = tab.icon,
                            contentDescription = null,
                            tint = PompColors.Paper,
                            modifier = Modifier.size(23.dp),
                        )
                    }
                }
            }
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall,
                fontSize = 11.sp,
                color = PompColors.Cinnabar,
                maxLines = 1,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 1.dp),
            )
        } else {
            Icon(
                imageVector = tab.icon,
                contentDescription = null,
                tint = tint,
                modifier = Modifier.size(21.dp),
            )
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall,
                fontSize = 10.5.sp,
                color = tint,
                maxLines = 1,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 3.dp),
            )
        }
    }
}
