package com.pomp.hskai.core.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Quiz
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
 * Obuna is deliberately never a tab — it is a monetization flow, not a daily
 * learning destination.
 */
enum class MainTab(val labelRes: Int, val icon: ImageVector) {
    TODAY(R.string.nav_today, Icons.Filled.Today),
    COURSE(R.string.nav_course, Icons.Filled.School),
    PRACTICE(R.string.nav_practice, Icons.Filled.Quiz),
    VOICE(R.string.nav_ai, Icons.Filled.Mic),
    PROFILE(R.string.nav_profile, Icons.Filled.Person),
    ;

    companion object {
        val visible: List<MainTab> get() = listOf(TODAY, COURSE, PRACTICE, VOICE, PROFILE)
    }
}

/**
 * Which tab a deep link should land on.
 *
 * A lesson destination lands on the path first; entitlement is checked by the
 * lesson request before the renderer opens.
 */
fun AppDestination.toTab(): MainTab? = when (this) {
    AppDestination.Today -> MainTab.TODAY
    AppDestination.Course,
    AppDestination.CurrentLesson,
    is AppDestination.Lesson,
    -> MainTab.COURSE

    AppDestination.Profile, AppDestination.WidgetSetup -> MainTab.PROFILE

    AppDestination.Voice -> MainTab.VOICE
    is AppDestination.Practice -> MainTab.PRACTICE
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
