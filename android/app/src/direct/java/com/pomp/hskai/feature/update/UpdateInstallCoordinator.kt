package com.pomp.hskai.feature.update

import android.content.Context
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.pomp.hskai.BuildConfig

/**
 * A single tap opts in to downloading AND opening Android's installer.
 * We may launch an installer only while our UI is resumed: workers cannot
 * reliably start activities from the background on modern Android.
 * Android always owns the final installation confirmation.
 */
internal object UpdateInstallCoordinator {
    private const val PREFS = "app_update_install_request"
    private const val PENDING_VERSION = "pending_version"

    private fun pending(context: Context): Int =
        context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getInt(PENDING_VERSION, -1)

    fun request(context: Context, release: UpdateRelease, fileIsValid: Boolean) {
        if (BuildConfig.QA_BUILD) return
        if (!context.canInstallApks()) {
            context.openInstallPermissionSettings()
            return
        }
        val file = UpdateDownload.apkFileForVersion(context, release.versionCode)
        if (fileIsValid) {
            synchronized(this) { clear(context) }
            context.launchInstaller(file)
            return
        }
        synchronized(this) {
            context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit().putInt(PENDING_VERSION, release.versionCode).commit()
        }
        UpdateDownload.enqueue(context, release)
    }

    /**
     * Consuming before launching prevents duplicate installers when both the
     * profile card and the persistent banner are visible at completion.
     */
    fun consumeIfReady(
        context: Context,
        releaseVersionCode: Int,
        phase: UpdatePhase,
        fileIsValid: Boolean,
        canInstall: Boolean,
        resumed: Boolean,
    ): Boolean = synchronized(this) {
        if (!shouldAutoInstall(
                pending(context), releaseVersionCode, phase,
                fileIsValid, canInstall, resumed,
            )
        ) return@synchronized false
        clear(context)
        true
    }

    internal fun shouldAutoInstall(
        pendingVersionCode: Int,
        releaseVersionCode: Int,
        phase: UpdatePhase,
        fileIsValid: Boolean,
        canInstall: Boolean,
        resumed: Boolean,
    ): Boolean =
        pendingVersionCode == releaseVersionCode &&
            phase == UpdatePhase.Downloaded &&
            fileIsValid && canInstall && resumed

    private fun clear(context: Context) {
        context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().remove(PENDING_VERSION).commit()
    }
}

/** Shared by the profile card, two-releases-behind banner and mandatory gate. */
@Composable
internal fun AutoOpenDownloadedUpdate(
    release: UpdateRelease,
    phase: UpdatePhase,
    fileIsValid: Boolean,
    canInstall: Boolean,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    var resumed by remember(lifecycleOwner) {
        mutableStateOf(lifecycleOwner.lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED))
    }

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) resumed = true
            if (event == Lifecycle.Event.ON_PAUSE || event == Lifecycle.Event.ON_STOP) resumed = false
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    LaunchedEffect(release.versionCode, phase, fileIsValid, canInstall, resumed) {
        if (UpdateInstallCoordinator.consumeIfReady(
                context, release.versionCode, phase, fileIsValid, canInstall, resumed,
            )
        ) {
            context.launchInstaller(UpdateDownload.apkFileForVersion(context, release.versionCode))
        }
    }
}
