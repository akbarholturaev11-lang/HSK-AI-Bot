package com.pomp.hskai.feature.update

import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
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
private const val UPDATE_CHECK_PREFS = "app_update_check_cache"
private const val KEY_CHECKED_AT = "checked_at"
private const val KEY_CHECKED_VERSION = "checked_version"
private const val KEY_HAS_RELEASE = "has_release"
private const val KEY_RELEASE_NAME = "release_name"
private const val KEY_RELEASE_CODE = "release_code"
private const val KEY_RELEASE_URL = "release_url"
private const val KEY_RELEASE_SIZE = "release_size"
private val updateCheckLock = Any()

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
        release = withContext(Dispatchers.IO) { fetchRelease(context) }
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
 * Shared with the banner and the background check, which is why these are
 * `internal` rather than private to this file.
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

internal fun fetchRelease(
    context: Context,
    nowMillis: Long = System.currentTimeMillis(),
): UpdateRelease? = synchronized(updateCheckLock) {
    val prefs = context.applicationContext.getSharedPreferences(
        UPDATE_CHECK_PREFS,
        Context.MODE_PRIVATE,
    )
    val checkedAt = prefs.getLong(KEY_CHECKED_AT, 0L)
    val checkedVersion = prefs.getInt(KEY_CHECKED_VERSION, -1)
    val hasRelease = prefs.getBoolean(KEY_HAS_RELEASE, false)
    val cachedRelease = if (hasRelease && checkedVersion == BuildConfig.VERSION_CODE) {
        cachedRelease(prefs)
    } else {
        null
    }

    if (
        AppUpdate.isCheckCacheFresh(
            checkedAtMillis = checkedAt,
            nowMillis = nowMillis,
            checkedVersionCode = checkedVersion,
            installedVersionCode = BuildConfig.VERSION_CODE,
        )
    ) {
        if (!hasRelease) return@synchronized null
        if (cachedRelease != null) return@synchronized cachedRelease
    }

    try {
        val request = Request.Builder()
            .url(
                "${BuildConfig.API_ORIGIN}/api/v3/android-update/check" +
                    "?version_code=${BuildConfig.VERSION_CODE}"
            )
            .get()
            .build()
        downloadClient.newCall(request).execute().use { response ->
            val body = response.body?.string()
            val release = AppUpdate.parse(
                status = response.code,
                body = body,
                installedVersionCode = BuildConfig.VERSION_CODE,
            )
            if (response.code == 204 || release != null) {
                storeUpdateCheck(prefs, nowMillis, release)
            }
            release
        }
    } catch (error: Exception) {
        // Keep a previously validated release visible while offline, but do not
        // mark a failed network attempt as a fresh check.
        Log.d(TAG, "update check failed", error)
        cachedRelease
    }
}

private fun cachedRelease(prefs: SharedPreferences): UpdateRelease? {
    val name = prefs.getString(KEY_RELEASE_NAME, "").orEmpty()
    val code = prefs.getInt(KEY_RELEASE_CODE, -1)
    val url = prefs.getString(KEY_RELEASE_URL, "").orEmpty()
    val size = prefs.getLong(KEY_RELEASE_SIZE, 0L)
    if (name.isBlank() || code <= BuildConfig.VERSION_CODE || !AppUpdate.isInstallableUrl(url)) {
        return null
    }
    return UpdateRelease(
        versionName = name,
        versionCode = code,
        url = url,
        size = size,
    )
}

private fun storeUpdateCheck(
    prefs: SharedPreferences,
    checkedAtMillis: Long,
    release: UpdateRelease?,
) {
    prefs.edit()
        .putLong(KEY_CHECKED_AT, checkedAtMillis)
        .putInt(KEY_CHECKED_VERSION, BuildConfig.VERSION_CODE)
        .putBoolean(KEY_HAS_RELEASE, release != null)
        .apply {
            if (release == null) {
                remove(KEY_RELEASE_NAME)
                remove(KEY_RELEASE_CODE)
                remove(KEY_RELEASE_URL)
                remove(KEY_RELEASE_SIZE)
            } else {
                putString(KEY_RELEASE_NAME, release.versionName)
                putInt(KEY_RELEASE_CODE, release.versionCode)
                putString(KEY_RELEASE_URL, release.url)
                putLong(KEY_RELEASE_SIZE, release.size)
            }
        }
        .apply()
}

internal fun download(context: Context, release: UpdateRelease): File? = try {
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

internal fun Context.canInstallApks(): Boolean = packageManager.canRequestPackageInstalls()

internal fun Context.openInstallPermissionSettings() {
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

internal fun Context.launchInstaller(file: File) {
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
