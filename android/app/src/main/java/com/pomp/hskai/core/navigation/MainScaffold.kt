package com.pomp.hskai.core.navigation

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Person
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.style.TextAlign
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
            Column {
                // An install two releases behind is told so here: above the
                // tabs, on every main screen, and never inside a lesson. It
                // takes the pill's own margin so the two read as one block.
                // The direct channel draws it; the Play build draws nothing.
                AppUpdateBanner(modifier = Modifier.padding(horizontal = 12.dp))
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .navigationBarsPadding()
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                ) {
                    HskGlassSurface(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(28.dp),
                        shadowElevation = 14.dp,
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(82.dp)
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
