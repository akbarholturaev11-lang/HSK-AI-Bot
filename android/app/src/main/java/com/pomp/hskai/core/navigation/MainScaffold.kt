package com.pomp.hskai.core.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.Today
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors

/**
 * Primary navigation.
 *
 * Only tabs whose feature actually works are shown. Mashq and AI arrive with
 * Phases F and G; until then they are absent rather than present-but-dead.
 * Obuna is deliberately never a tab — it is a monetization flow, not a daily
 * learning destination.
 */
enum class MainTab(val labelRes: Int, val icon: ImageVector) {
    TODAY(R.string.nav_today, Icons.Filled.Today),
    COURSE(R.string.nav_course, Icons.Filled.School),
    PROFILE(R.string.nav_profile, Icons.Filled.Person),
    ;

    companion object {
        /**
         * Mashq and AI are absent rather than disabled: Phases F and G add
         * their entries here together with the screens behind them.
         */
        val visible: List<MainTab> get() = listOf(TODAY, COURSE, PROFILE)
    }
}

/**
 * Which tab a deep link should land on.
 *
 * A lesson destination lands on the path rather than opening the lesson: the
 * renderer arrives in Phase E, and entitlement is checked there, not here.
 * Destinations whose feature is not built yet return null so the app opens
 * normally instead of on a dead screen.
 */
fun AppDestination.toTab(): MainTab? = when (this) {
    AppDestination.Today -> MainTab.TODAY
    AppDestination.Course,
    AppDestination.CurrentLesson,
    is AppDestination.Lesson,
    -> MainTab.COURSE

    AppDestination.Profile, AppDestination.WidgetSetup -> MainTab.PROFILE

    // Phases G and F. Until their tabs exist there is nowhere to land, so the
    // app opens normally rather than on an empty screen.
    AppDestination.Voice -> null
    is AppDestination.Practice -> null
}

@Composable
fun MainScaffold(
    selectedTab: MainTab = MainTab.TODAY,
    onTabSelected: (MainTab) -> Unit,
    content: @Composable (MainTab, Modifier) -> Unit,
) {
    val tabs = remember { MainTab.visible }

    Scaffold(
        containerColor = PompColors.Paper,
        bottomBar = {
            NavigationBar(containerColor = PompColors.PaperRaised) {
                tabs.forEach { tab ->
                    val label = stringResource(tab.labelRes)
                    NavigationBarItem(
                        selected = selectedTab == tab,
                        onClick = { onTabSelected(tab) },
                        icon = { Icon(tab.icon, contentDescription = label) },
                        label = { Text(label) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = PompColors.Paper,
                            selectedTextColor = PompColors.CinnabarDark,
                            indicatorColor = PompColors.Cinnabar,
                            unselectedIconColor = PompColors.InkSecondary,
                            unselectedTextColor = PompColors.InkSecondary,
                        ),
                    )
                }
            }
        },
    ) { insets ->
        content(selectedTab, Modifier.padding(insets))
    }
}
