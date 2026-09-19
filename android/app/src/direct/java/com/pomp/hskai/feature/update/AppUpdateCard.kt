package com.pomp.hskai.feature.update

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import android.util.Log
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.SystemUpdate
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.core.content.FileProvider
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.pomp.hskai.BuildConfig
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.feature.profile.ProfileActionCard
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.util.concurrent.TimeUnit

private const val TAG = "AppUpdate"

/**
 * "A newer version exists", in the one place a learner goes looking.
 *
 * Android cannot update a sideloaded app silently — the system always shows
 * its own install confirmation — so this is deliberately one tap and then the
 * system's dialog, never a background swap. The card lives in the profile and
 * nowhere else: an update is not urgent enough to stand between someone and
 * the lesson they opened the app for.
 *
 * The Play build has a no-op in place of this file. Google Play forbids an app
 * it distributes from updating itself by any other route, which is why none of
 * this is compiled into that flavour.
 */
@Composable
fun AppUpdateCard(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val scope = rememberCoroutineScope()
    var release by remember { mutableStateOf<UpdateRelease?>(null) }
    var phase by remember { mutableStateOf(UpdatePhase.Ready) }
    var canInstall by remember { mutableStateOf(context.canInstallApks()) }

    LaunchedEffect(Unit) {
        release = withContext(Dispatchers.IO) { fetchRelease() }
    }

    // Granting the permission happens in Android's own settings, in another
    // task. Without re-reading it on the way back, the card would still be
    // asking for a permission the learner has just given — and tapping it
    // would send them straight back to the same screen.
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

    UpdateCardContent(
        release = available,
        phase = phase,
        canInstall = canInstall,
        modifier = modifier,
        onClick = {
            if (phase == UpdatePhase.Downloading) return@UpdateCardContent
            if (!canInstall) {
                context.openInstallPermissionSettings()
                return@UpdateCardContent
            }
            phase = UpdatePhase.Downloading
            scope.launch {
                val file = withContext(Dispatchers.IO) { download(context, available) }
                if (file == null) {
                    phase = UpdatePhase.Failed
                } else {
                    // Back to Ready, not "installed": the system dialog can be
                    // dismissed, and the card must still be there if it was.
                    phase = UpdatePhase.Ready
                    context.launchInstaller(file)
                }
            }
        },
    )
}

/**
 * The card itself, with nothing behind it.
 *
 * Split out so the wording of each state can be read back off a real screen in
 * a test — the version people see, the size, "downloading", the failure, and
 * the one that is easy to get wrong: with no install permission the card must
 * ask for the permission rather than announce a version it cannot install.
 */
@Composable
internal fun UpdateCardContent(
    release: UpdateRelease,
    phase: UpdatePhase,
    canInstall: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val title: String
    val subtitle: String
    when {
        phase == UpdatePhase.Downloading -> {
            title = stringResource(R.string.update_card_title, release.versionName)
            subtitle = stringResource(R.string.update_card_downloading)
        }
        phase == UpdatePhase.Failed -> {
            title = stringResource(R.string.update_card_title, release.versionName)
            subtitle = stringResource(R.string.update_card_failed)
        }
        !canInstall -> {
            title = stringResource(R.string.update_card_permission)
            subtitle = stringResource(R.string.update_card_permission_hint)
        }
        else -> {
            title = stringResource(R.string.update_card_title, release.versionName)
            subtitle = stringResource(R.string.update_card_subtitle, formatSize(release.size))
        }
    }

    ProfileActionCard(
        icon = Icons.Filled.SystemUpdate,
        iconBackground = PompColors.JadeSoft,
        iconTint = PompColors.Jade,
        title = title,
        subtitle = subtitle,
        modifier = modifier,
        onClick = onClick,
    )
}

internal enum class UpdatePhase { Ready, Downloading, Failed }

/**
 * Its own client on purpose.
 *
 * The app's shared OkHttp client carries `OriginGuardInterceptor`, which
 * rejects every host but our API — correct for the API, and fatal here, since
 * the artifact is served from object storage. This one accepts only what
 * [AppUpdate.isInstallableUrl] already allowed, and follows redirects because
 * storage buckets use them.
 */
private val downloadClient: OkHttpClient by lazy {
    OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .callTimeout(5, TimeUnit.MINUTES)
        .build()
}

private fun fetchRelease(): UpdateRelease? = try {
    val request = Request.Builder()
        .url(
            "${BuildConfig.API_ORIGIN}/api/v3/android-update/check" +
                "?version_code=${BuildConfig.VERSION_CODE}"
        )
        .get()
        .build()
    downloadClient.newCall(request).execute().use { response ->
        AppUpdate.parse(
            status = response.code,
            body = response.body?.string(),
            installedVersionCode = BuildConfig.VERSION_CODE,
        )
    }
} catch (error: Exception) {
    // No network, no server, no card. An update is never worth an error
    // message in a profile someone opened to look at their streak.
    Log.d(TAG, "update check failed", error)
    null
}

private fun download(context: Context, release: UpdateRelease): File? = try {
    val directory = File(context.cacheDir, "updates").apply { mkdirs() }
    // One file, always overwritten. Keeping a version-named file per release
    // would quietly fill the cache with installers nobody will open again.
    val target = File(directory, "update.apk")
    val request = Request.Builder().url(release.url).get().build()
    downloadClient.newCall(request).execute().use { response ->
        val body = response.body
        if (!response.isSuccessful || body == null) {
            target.delete()
            null
        } else {
            target.outputStream().use { out -> body.byteStream().copyTo(out) }
            if (AppUpdate.isExpectedSize(target.length(), release.size)) {
                target
            } else {
                // Not the file we were promised. Deleting it matters more than
                // reporting it: a half-written APK left in the cache is the
                // one the next attempt would find.
                Log.w(TAG, "downloaded ${target.length()} bytes, expected ${release.size}")
                target.delete()
                null
            }
        }
    }
} catch (error: Exception) {
    Log.w(TAG, "update download failed", error)
    null
}

private fun Context.canInstallApks(): Boolean = packageManager.canRequestPackageInstalls()

private fun Context.openInstallPermissionSettings() {
    try {
        startActivity(
            Intent(
                Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                Uri.parse("package:$packageName"),
            ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        )
    } catch (error: Exception) {
        Log.w(TAG, "could not open the install permission screen", error)
    }
}

private fun Context.launchInstaller(file: File) {
    try {
        val uri = FileProvider.getUriForFile(this, "$packageName.updates", file)
        startActivity(
            Intent(Intent.ACTION_VIEW)
                .setDataAndType(uri, "application/vnd.android.package-archive")
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        )
    } catch (error: Exception) {
        Log.w(TAG, "could not open the installer", error)
    }
}

private fun formatSize(bytes: Long): String = when {
    bytes >= 1024 * 1024 -> String.format("%.1f MB", bytes / (1024.0 * 1024.0))
    bytes >= 1024 -> "${bytes / 1024} KB"
    else -> "$bytes B"
}
