package com.pomp.hskai.feature.update

import android.content.SharedPreferences
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.work.WorkManager
import com.pomp.hskai.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Foreground-only completion handoff, even after leaving the Profile tab.
 * No background worker tries to start an Android installer activity.
 */
@Composable
fun UpdateInstallMonitor() {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val preferences = remember(context) { UpdateInstallCoordinator.requestPreferences(context) }
    var queuedVersion by remember(context) {
        mutableIntStateOf(UpdateInstallCoordinator.queuedVersion(context))
    }
    var canInstall by remember { mutableStateOf(context.canInstallApks()) }

    DisposableEffect(preferences, lifecycleOwner) {
        val listener = SharedPreferences.OnSharedPreferenceChangeListener { _, _ ->
            queuedVersion = UpdateInstallCoordinator.queuedVersion(context)
        }
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                queuedVersion = UpdateInstallCoordinator.queuedVersion(context)
                canInstall = context.canInstallApks()
            }
        }
        preferences.registerOnSharedPreferenceChangeListener(listener)
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
            preferences.unregisterOnSharedPreferenceChangeListener(listener)
        }
    }

    var release by remember(queuedVersion) { mutableStateOf<UpdateRelease?>(null) }
    LaunchedEffect(queuedVersion) {
        if (queuedVersion > BuildConfig.VERSION_CODE) {
            release = withContext(Dispatchers.IO) {
                fetchRelease(context)?.takeIf { it.versionCode == queuedVersion }
            }
        }
    }

    val available = release ?: return
    val workInfos by remember(context, available.versionCode) {
        WorkManager.getInstance(context)
            .getWorkInfosForUniqueWorkFlow(UpdateDownload.uniqueWorkName(available.versionCode))
    }.collectAsState(initial = emptyList())
    val apk = UpdateDownload.apkFileForVersion(context, available.versionCode)
    val fileIsValid = apk.isFile && AppUpdate.isExpectedSize(apk.length(), available.size)
    val phase = UpdateDownload.downloadPhase(workInfos, fileIsValid)

    AutoOpenDownloadedUpdate(available, phase, fileIsValid, canInstall)
}
