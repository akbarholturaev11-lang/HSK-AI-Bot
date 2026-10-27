package com.pomp.hskai.feature.update

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
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
import com.google.android.play.core.appupdate.AppUpdateInfo
import com.google.android.play.core.appupdate.AppUpdateManagerFactory
import com.google.android.play.core.appupdate.AppUpdateOptions
import com.google.android.play.core.install.model.AppUpdateType
import com.google.android.play.core.install.model.UpdateAvailability
import com.pomp.hskai.BuildConfig
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskPrimaryButton
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

/**
 * The same admin-managed threshold as Direct, but the available update must
 * be confirmed by Google Play itself. A Direct-only release never locks Play.
 * No APK URL, install permission or sideload code is compiled into this flavour.
 */
@Composable
fun MandatoryUpdateGate(content: @Composable () -> Unit) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val manager = remember(context) { AppUpdateManagerFactory.create(context) }
    var allowedVersions by remember { mutableIntStateOf(AndroidUpdateThreshold.DEFAULT_ALLOWED_VERSIONS) }
    var updateInfo by remember { mutableStateOf<AppUpdateInfo?>(null) }
    var refresh by remember { mutableIntStateOf(0) }
    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartIntentSenderForResult()
    ) { refresh += 1 }

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) refresh += 1
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    LaunchedEffect(refresh) {
        allowedVersions = UpdatePolicyClient.allowedVersions(context)
        updateInfo = suspendCancellableCoroutine { continuation ->
            manager.appUpdateInfo
                .addOnSuccessListener { info ->
                    if (continuation.isActive) continuation.resume(info)
                }
                .addOnFailureListener {
                    if (continuation.isActive) continuation.resume(null)
                }
        }
    }

    val info = updateInfo
    val available = info != null && (
        info.updateAvailability() == UpdateAvailability.UPDATE_AVAILABLE ||
        info.updateAvailability() == UpdateAvailability.DEVELOPER_TRIGGERED_UPDATE_IN_PROGRESS
    )
    val mandatory = available && AndroidUpdateThreshold.isMandatory(
        installedVersionCode = BuildConfig.VERSION_CODE,
        availableVersionCode = info!!.availableVersionCode(),
        allowedVersions = allowedVersions,
    )
    if (!mandatory) {
        content()
        return
    }

    BackHandler(enabled = true) {}
    PlayMandatoryUpdateWall(onUpdate = {
        val candidate = updateInfo ?: return@PlayMandatoryUpdateWall
        if (candidate.isUpdateTypeAllowed(AppUpdateType.IMMEDIATE)) {
            val started = runCatching {
                manager.startUpdateFlowForResult(
                    candidate, launcher,
                    AppUpdateOptions.newBuilder(AppUpdateType.IMMEDIATE).build()
                )
            }.getOrDefault(false)
            if (started) return@PlayMandatoryUpdateWall
        }
        // Fallback remains Google Play, never sideloading or Telegram.
        val market = Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=${context.packageName}"))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        val web = Intent(Intent.ACTION_VIEW,
            Uri.parse("https://play.google.com/store/apps/details?id=${context.packageName}"))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        if (runCatching { context.startActivity(market) }.isFailure) {
            runCatching { context.startActivity(web) }
        }
    })
}

@Composable
private fun PlayMandatoryUpdateWall(onUpdate: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize()
            .background(PompColors.Paper)
            .windowInsetsPadding(WindowInsets.safeDrawing)
            .padding(horizontal = 24.dp, vertical = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Icon(Icons.Filled.SystemUpdate, contentDescription = null,
            tint = PompColors.Cinnabar, modifier = Modifier.size(48.dp))
        Text(stringResource(R.string.update_gate_title),
            style = MaterialTheme.typography.headlineSmall,
            color = PompColors.Ink,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 24.dp))
        Text(stringResource(R.string.update_gate_body),
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth().padding(top = 12.dp))
        HskPrimaryButton(
            text = stringResource(R.string.update_gate_button),
            onClick = onUpdate,
            modifier = Modifier.fillMaxWidth().padding(top = 28.dp),
        )
    }
}
