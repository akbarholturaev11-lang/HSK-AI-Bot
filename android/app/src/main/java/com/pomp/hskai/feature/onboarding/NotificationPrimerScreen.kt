package com.pomp.hskai.feature.onboarding

import android.animation.ValueAnimator
import android.os.Build
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.NotificationsActive
import androidx.compose.material.icons.filled.SystemUpdate
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskPrimaryButton

/**
 * The one time this app asks to be allowed to speak.
 *
 * Android grants notifications once for the whole app rather than per kind,
 * and it stops showing its own dialog after two refusals — so the ask has to
 * be made once, in a place where it makes sense, and never repeated. That
 * place is the end of onboarding: the learner has just chosen a level and a
 * goal, so "we will remind you in the evening" is about something they asked
 * for a minute ago.
 *
 * Saying no costs nothing: the update card and the banner do not depend on it,
 * and the question is not asked again either way.
 */
@Composable
fun NotificationPrimerScreen(
    language: String,
    onAllow: () -> Unit,
    onSkip: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val copy = OnboardingCopy.forLanguage(language)
    val motionEnabled = remember {
        Build.VERSION.SDK_INT < Build.VERSION_CODES.O || ValueAnimator.areAnimatorsEnabled()
    }

    Surface(color = PompColors.Paper, modifier = modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 28.dp, vertical = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Box(Modifier.size(150.dp), contentAlignment = Alignment.Center) {
                OnboardingPandaMascot(
                    motionEnabled = motionEnabled,
                    modifier = Modifier.fillMaxSize(),
                )
            }
            Spacer(Modifier.height(20.dp))
            Text(
                copy.notifyTitle,
                color = PompColors.Ink,
                fontSize = 24.sp,
                lineHeight = 30.sp,
                fontWeight = FontWeight.SemiBold,
                textAlign = TextAlign.Center,
                modifier = Modifier.widthIn(max = 330.dp),
            )
            Spacer(Modifier.height(22.dp))
            // Two lines, because there are exactly two things the app would
            // ever send: the evening reminder and a new version. Anything
            // vaguer than that is how a permission gets refused.
            PrimerLine(icon = Icons.Filled.NotificationsActive, text = copy.notifyLessons)
            Spacer(Modifier.height(12.dp))
            PrimerLine(icon = Icons.Filled.SystemUpdate, text = copy.notifyUpdates)
            Spacer(Modifier.height(30.dp))
            HskPrimaryButton(
                text = copy.notifyAllow,
                onClick = onAllow,
                modifier = Modifier.fillMaxWidth().widthIn(max = 360.dp),
            )
            Spacer(Modifier.height(10.dp))
            Surface(
                onClick = onSkip,
                color = PompColors.Paper,
                modifier = Modifier.fillMaxWidth().widthIn(max = 360.dp),
            ) {
                Text(
                    copy.notifyLater,
                    color = PompColors.InkSecondary,
                    style = MaterialTheme.typography.bodyMedium,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth().padding(vertical = 14.dp),
                )
            }
        }
    }
}

@Composable
private fun PrimerLine(icon: ImageVector, text: String) {
    Row(
        modifier = Modifier.widthIn(max = 340.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Icon(
            icon,
            contentDescription = null,
            tint = PompColors.Cinnabar,
            modifier = Modifier.size(20.dp),
        )
        Text(
            text,
            color = PompColors.InkSecondary,
            style = MaterialTheme.typography.bodyLarge,
        )
    }
}
