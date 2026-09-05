package com.pomp.hskai.core.navigation

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.Style
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors

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

@Composable
fun MainScaffold(
    selectedTab: MainTab = MainTab.COURSE,
    onTabSelected: (MainTab) -> Unit,
    content: @Composable (MainTab, Modifier) -> Unit,
) {
    val tabs = remember { MainTab.visible }

    Scaffold(
        containerColor = PompColors.Paper,
        bottomBar = {
            Surface(
                color = PompColors.PaperRaised,
                border = BorderStroke(1.dp, PompColors.Divider),
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .navigationBarsPadding()
                        .height(70.dp)
                        .padding(horizontal = 4.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.Top,
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
        },
    ) { insets ->
        content(selectedTab, Modifier.padding(insets))
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

    Column(
        modifier = modifier
            .selectable(
                selected = selected,
                role = Role.Tab,
                onClick = onClick,
            )
            .then(if (tab.isCentre) Modifier.offset(y = (-20).dp) else Modifier),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Top,
    ) {
        if (tab.isCentre) {
            Surface(
                modifier = Modifier.size(58.dp),
                shape = CircleShape,
                color = PompColors.Cinnabar,
                border = BorderStroke(4.dp, PompColors.PaperRaised),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = tab.icon,
                        contentDescription = null,
                        tint = PompColors.Paper,
                        modifier = Modifier.size(24.dp),
                    )
                }
            }
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall,
                fontSize = 11.sp,
                color = PompColors.Cinnabar,
                maxLines = 1,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 4.dp),
            )
        } else {
            Icon(
                imageVector = tab.icon,
                contentDescription = null,
                tint = tint,
                modifier = Modifier.size(22.dp),
            )
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall,
                fontSize = 11.sp,
                color = tint,
                maxLines = 1,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 3.dp),
            )
        }
    }
}
