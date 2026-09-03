package com.pomp.hskai.core.navigation

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
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

/**
 * Primary navigation, laid out exactly like the Mini App's bottom bar:
 * Kurs · Mashq · [AI Voice] · Reyting · Profil, with AI Voice raised into the
 * centre as the single accent action.
 *
 * Obuna is deliberately never a tab — it is a monetization flow, not a daily
 * learning destination.
 */
enum class MainTab(val labelRes: Int, val icon: ImageVector) {
    COURSE(R.string.nav_course, Icons.Filled.Map),
    PRACTICE(R.string.nav_practice, Icons.Filled.Style),
    VOICE(R.string.nav_ai, Icons.Filled.Mic),
    RATING(R.string.nav_rating, Icons.Filled.EmojiEvents),
    PROFILE(R.string.nav_profile, Icons.Filled.Person),
    ;

    /** Raised centre action, mirroring the Mini App's floating microphone. */
    val isCentre: Boolean get() = this == VOICE

    companion object {
        val visible: List<MainTab> get() = entries
    }
}

/**
 * Which tab a deep link should land on.
 *
 * A lesson destination lands on the path first; entitlement is checked by the
 * lesson request before the renderer opens. `Today` no longer has a tab of its
 * own — like the Mini App, the next action lives at the top of the path — so
 * an existing `today` reminder link still resolves and lands on Kurs.
 */
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
            Surface(color = PompColors.PaperRaised) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .navigationBarsPadding()
                        .padding(horizontal = 4.dp, vertical = 6.dp),
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
    val tint = if (selected) PompColors.Cinnabar else PompColors.InkSecondary

    Column(
        modifier = modifier
            .selectable(
                selected = selected,
                role = Role.Tab,
                onClick = onClick,
            )
            .heightIn(min = 56.dp)
            .padding(vertical = 4.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        if (tab.isCentre) {
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .background(PompColors.Cinnabar, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = tab.icon,
                    contentDescription = null,
                    tint = PompColors.Paper,
                    modifier = Modifier.size(22.dp),
                )
            }
        } else {
            Icon(
                imageVector = tab.icon,
                contentDescription = null,
                tint = tint,
                modifier = Modifier.size(22.dp),
            )
            Box(Modifier.height(2.dp))
        }
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            fontSize = 11.sp,
            color = tint,
            maxLines = 1,
            textAlign = TextAlign.Center,
        )
    }
}
