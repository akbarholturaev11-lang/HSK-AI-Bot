package com.pomp.hskai.feature.update

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.SystemUpdate
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.pomp.hskai.BuildConfig
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * The line that stops being polite.
 *
 * The card in the profile is the ordinary way an update is offered, and for a
 * single missed release it stays the only one. Someone two releases behind has
 * already walked past that card, so this bar sits above the tab bar on every
 * main screen until the install actually happens — it cannot be dismissed,
 * because a dismissed nudge is how a build from three weeks ago keeps running.
 *
 * It is still not a wall: the lesson, practice and voice screens never show it,
 * and tapping is the only thing it asks for.
 */
@Composable
fun AppUpdateBanner(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val scope = rememberCoroutineScope()
    var release by remember { mutableStateOf<UpdateRelease?>(null) }
    var phase by remember { mutableStateOf(UpdatePhase.Ready) }
    var canInstall by remember { mutableStateOf(context.canInstallApks()) }

    LaunchedEffect(Unit) {
        release = withContext(Dispatchers.IO) { fetchRelease() }
    }

    // The install permission is granted in Android's own settings, in another
    // task; without re-reading it on the way back the bar would still be
    // asking for something the learner has just given.
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                canInstall = context.canInstallApks()
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    val available = release ?: return
    if (!AppUpdate.isFarBehind(
            release = available,
            installedVersionCode = BuildConfig.VERSION_CODE,
        )
    ) {
        // One release behind is the profile card's business, not the whole
        // app's.
        return
    }

    UpdateBannerContent(
        release = available,
        phase = phase,
        canInstall = canInstall,
        modifier = modifier,
        onClick = {
            if (phase == UpdatePhase.Downloading) return@UpdateBannerContent
            if (!canInstall) {
                context.openInstallPermissionSettings()
                return@UpdateBannerContent
            }
            phase = UpdatePhase.Downloading
            scope.launch {
                val file = withContext(Dispatchers.IO) { download(context, available) }
                if (file == null) {
                    phase = UpdatePhase.Failed
                } else {
                    // Back to Ready rather than "installed": the system dialog
                    // can be dismissed, and the bar has to survive that.
                    phase = UpdatePhase.Ready
                    context.launchInstaller(file)
                }
            }
        },
    )
}

/**
 * The bar itself, with nothing behind it, so each state can be read back off a
 * real screen in a test.
 */
@Composable
internal fun UpdateBannerContent(
    release: UpdateRelease,
    phase: UpdatePhase,
    canInstall: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val text = when {
        phase == UpdatePhase.Downloading -> stringResource(R.string.update_banner_downloading)
        phase == UpdatePhase.Failed -> stringResource(R.string.update_banner_failed)
        !canInstall -> stringResource(R.string.update_banner_permission)
        else -> stringResource(R.string.update_banner_text, release.versionName)
    }

    Surface(
        onClick = onClick,
        color = PompColors.CinnabarSoft,
        // Rounded like the tab pill it sits above, and inset by the same
        // margin, so the two read as one block rather than a strip glued to
        // a floating bar.
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Icon(
                Icons.Filled.SystemUpdate,
                contentDescription = null,
                tint = PompColors.CinnabarDark,
                modifier = Modifier.size(18.dp),
            )
            Text(
                text,
                color = PompColors.CinnabarDark,
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium,
            )
        }
    }
}
