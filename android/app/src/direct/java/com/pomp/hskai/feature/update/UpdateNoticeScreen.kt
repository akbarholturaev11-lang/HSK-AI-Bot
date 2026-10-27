package com.pomp.hskai.feature.update

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.work.WorkManager
import com.pomp.hskai.R
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Android Direct APK-only landing for a fixed-in-new-version notice.
 * This reuses the existing verified WorkManager download and installer handoff.
 * Opening a notification never starts a download without the learner's tap.
 */
@Composable
fun UpdateNoticeScreen(onClose: () -> Unit) {
    val context = LocalContext.current
    val owner = LocalLifecycleOwner.current
    var checked by remember { mutableStateOf(false) }
    var release by remember { mutableStateOf<UpdateRelease?>(null) }
    var canInstall by remember { mutableStateOf(context.canInstallApks()) }

    BackHandler(onBack = onClose)
    LaunchedEffect(Unit) {
        release = withContext(Dispatchers.IO) { fetchRelease(context, forceRefresh = true) }
        checked = true
    }
    DisposableEffect(owner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) canInstall = context.canInstallApks()
        }
        owner.lifecycle.addObserver(observer)
        onDispose { owner.lifecycle.removeObserver(observer) }
    }

    Box(Modifier.fillMaxSize()) {
        val available = release
        when {
            available != null -> {
                val workInfos by remember(context, available.versionCode) {
                    WorkManager.getInstance(context)
                        .getWorkInfosForUniqueWorkFlow(UpdateDownload.uniqueWorkName(available.versionCode))
                }.collectAsState(initial = emptyList())
                val file = UpdateDownload.apkFileForVersion(context, available.versionCode)
                val valid = file.isFile && AppUpdate.isExpectedSize(file.length(), available.size)
                val phase = UpdateDownload.downloadPhase(workInfos, valid)
                val workInfo = UpdateDownload.currentWorkInfo(workInfos)

                AutoOpenDownloadedUpdate(available, phase, valid, canInstall)
                MandatoryUpdateContent(
                    release = available,
                    phase = phase,
                    downloadPercent = UpdateDownload.downloadProgressPercent(workInfo),
                    canInstall = canInstall,
                    onUpdate = {
                        if (phase != UpdatePhase.Downloading) {
                            UpdateInstallCoordinator.beginUpdateRequest(context, available, valid)
                        }
                    },
                )
            }
            !checked -> CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
            else -> Text(
                text = stringResource(R.string.update_gate_failed),
                modifier = Modifier.align(Alignment.Center).padding(32.dp),
            )
        }
        IconButton(
            onClick = onClose,
            modifier = Modifier.align(Alignment.TopEnd).statusBarsPadding().padding(12.dp),
        ) {
            Icon(Icons.Filled.Close, contentDescription = stringResource(android.R.string.cancel))
        }
    }
}
