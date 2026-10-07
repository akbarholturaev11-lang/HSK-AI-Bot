package com.pomp.hskai.feature.update

import android.content.Context
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.SystemUpdate
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.work.WorkManager
import com.pomp.hskai.BuildConfig
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskPrimaryButton
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Stops a direct install from entering the app after it has missed three
 * published releases. The Play source set deliberately passes through.
 */
@Composable
fun MandatoryUpdateGate(content: @Composable () -> Unit) {
    val context = LocalContext.current
    var release by remember { mutableStateOf<UpdateRelease?>(null) }

    LaunchedEffect(Unit) {
        release = withContext(Dispatchers.IO) { fetchRelease(context) }
    }

    val available = release
    if (available == null || !AppUpdate.isMandatoryUpdate(available, BuildConfig.VERSION_CODE)) {
        content()
        return
    }

    BackHandler(enabled = true) {}
    MandatoryUpdateWall(release = available)
}

@Composable
private fun MandatoryUpdateWall(release: UpdateRelease) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    var canInstall by remember { mutableStateOf(context.canInstallApks()) }

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) canInstall = context.canInstallApks()
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    val workInfos by remember(context, release.versionCode) {
        WorkManager.getInstance(context)
            .getWorkInfosForUniqueWorkFlow(UpdateDownload.uniqueWorkName(release.versionCode))
    }.collectAsState(initial = emptyList())
    val file = UpdateDownload.apkFileForVersion(context, release.versionCode)
    val downloadedFileIsValid = file.isFile && AppUpdate.isExpectedSize(file.length(), release.size)
    val workInfo = UpdateDownload.currentWorkInfo(workInfos)
    val phase = UpdateDownload.downloadPhase(workInfos, downloadedFileIsValid)
    val progress = UpdateDownload.downloadProgressPercent(workInfo)

    MandatoryUpdateContent(
        release = release,
        phase = phase,
        downloadPercent = progress,
        canInstall = canInstall,
        onUpdate = {
            if (phase == UpdatePhase.Downloading) return@MandatoryUpdateContent
            if (!canInstall) {
                context.openInstallPermissionSettings()
            } else if (downloadedFileIsValid) {
                context.launchInstaller(file)
            } else {
                UpdateDownload.enqueue(context, release)
            }
        },
    )
}

@Composable
internal fun MandatoryUpdateContent(
    release: UpdateRelease,
    phase: UpdatePhase,
    downloadPercent: Int?,
    canInstall: Boolean,
    onUpdate: () -> Unit,
) {
    val status = when {
        phase == UpdatePhase.Downloading -> stringResource(
            R.string.update_gate_downloading,
            downloadPercent ?: 0,
        )
        phase == UpdatePhase.Downloaded -> stringResource(R.string.update_gate_downloaded)
        phase == UpdatePhase.Failed -> stringResource(R.string.update_gate_failed)
        !canInstall -> stringResource(R.string.update_gate_permission)
        else -> stringResource(R.string.update_gate_body)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(PompColors.Paper)
            .windowInsetsPadding(WindowInsets.safeDrawing)
            .padding(horizontal = 24.dp, vertical = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Icon(
            imageVector = Icons.Filled.SystemUpdate,
            contentDescription = null,
            tint = PompColors.Cinnabar,
            modifier = Modifier.size(48.dp),
        )
        Text(
            text = stringResource(R.string.update_gate_title),
            style = MaterialTheme.typography.headlineSmall,
            color = PompColors.Ink,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 24.dp),
        )
        Text(
            text = stringResource(R.string.update_gate_version, release.versionName),
            style = MaterialTheme.typography.titleMedium,
            color = PompColors.CinnabarDark,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 12.dp),
        )
        Text(
            text = status,
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 12.dp),
        )
        HskPrimaryButton(
            text = stringResource(R.string.update_gate_button),
            onClick = onUpdate,
            loading = phase == UpdatePhase.Downloading,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 28.dp),
        )
    }
}
