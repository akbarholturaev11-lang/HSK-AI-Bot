package com.pomp.hskai.feature.update

import android.content.Context
import android.util.Log
import androidx.annotation.Keep
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.Data
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.OutOfQuotaPolicy
import androidx.work.WorkInfo
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.IOException
import java.util.concurrent.TimeUnit

private const val TAG = "UpdateDownload"
private const val PROGRESS_PERCENT = "progress_percent"
private const val INPUT_VERSION_NAME = "version_name"
private const val INPUT_VERSION_CODE = "version_code"
private const val INPUT_URL = "url"
private const val INPUT_SIZE = "size"
private const val MAX_RETRY_COUNT = 3

/** A single persistent APK download shared by the profile card and banner. */
internal object UpdateDownload {

    fun uniqueWorkName(versionCode: Int): String = "android_update_download_$versionCode"

    fun apkFileForVersion(context: Context, versionCode: Int): File =
        File(File(context.filesDir, "updates"), "update-$versionCode.apk")

    fun currentWorkInfo(workInfos: List<WorkInfo>): WorkInfo? =
        workInfos.firstOrNull { it.isUnfinished() } ?: workInfos.lastOrNull()

    fun downloadPhase(workInfos: List<WorkInfo>, downloadedFileIsValid: Boolean): UpdatePhase {
        if (workInfos.any { it.isUnfinished() }) return UpdatePhase.Downloading
        if (downloadedFileIsValid) return UpdatePhase.Downloaded
        if (workInfos.any { it.state == WorkInfo.State.FAILED || it.state == WorkInfo.State.CANCELLED }) {
            return UpdatePhase.Failed
        }
        return UpdatePhase.Ready
    }

    private fun WorkInfo.isUnfinished(): Boolean =
        state == WorkInfo.State.ENQUEUED ||
            state == WorkInfo.State.RUNNING ||
            state == WorkInfo.State.BLOCKED

    fun downloadProgressPercent(workInfo: WorkInfo?): Int? {
        return when (workInfo?.state) {
            WorkInfo.State.ENQUEUED,
            WorkInfo.State.RUNNING,
            WorkInfo.State.BLOCKED -> workInfo.progress.getInt(PROGRESS_PERCENT, 0).coerceIn(0, 100)

            WorkInfo.State.SUCCEEDED -> 100
            else -> null
        }
    }

    fun enqueue(context: Context, release: UpdateRelease) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()
        val request = OneTimeWorkRequestBuilder<UpdateDownloadWorker>()
            .setInputData(
                workDataOf(
                    INPUT_VERSION_NAME to release.versionName,
                    INPUT_VERSION_CODE to release.versionCode,
                    INPUT_URL to release.url,
                    INPUT_SIZE to release.size,
                )
            )
            .setConstraints(constraints)
            .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.SECONDS)
            .build()

        WorkManager.getInstance(context).enqueueUniqueWork(
            uniqueWorkName(release.versionCode),
            ExistingWorkPolicy.KEEP,
            request,
        )
    }
}

/**
 * WorkManager keeps this user-started transfer alive across app process death.
 * It only downloads; Android's installer remains a separate user-confirmed step.
 */
@Keep
internal class UpdateDownloadWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val release = readRelease() ?: return Result.failure()
        val directory = File(applicationContext.filesDir, "updates")
        if (!directory.exists() && !directory.mkdirs()) {
            return Result.failure()
        }

        val target = UpdateDownload.apkFileForVersion(applicationContext, release.versionCode)
        val partial = File(directory, "${target.name}.part")
        partial.delete()

        return try {
            setProgress(progressData(0))
            download(release, partial)

            if (!AppUpdate.isExpectedSize(partial.length(), release.size)) {
                throw IOException("Downloaded APK size did not match the release")
            }

            if (target.exists() && !target.delete()) {
                throw IOException("Could not replace the previous downloaded APK")
            }
            if (!partial.renameTo(target)) {
                throw IOException("Could not finalize the downloaded APK")
            }
            directory.listFiles()
                ?.filter { file ->
                    val oldVersionCode = file.name
                        .removePrefix("update-")
                        .removeSuffix(".apk")
                        .toIntOrNull()
                    oldVersionCode != null && oldVersionCode < release.versionCode
                }
                ?.forEach { it.delete() }
            setProgress(progressData(100))
            Result.success()
        } catch (error: CancellationException) {
            partial.delete()
            throw error
        } catch (error: IOException) {
            partial.delete()
            Log.w(TAG, "APK download failed (attempt ${runAttemptCount + 1})", error)
            if (runAttemptCount < MAX_RETRY_COUNT) Result.retry() else Result.failure()
        } catch (error: Exception) {
            partial.delete()
            Log.w(TAG, "APK download failed", error)
            Result.failure()
        }
    }

    private fun readRelease(): UpdateRelease? {
        val name = inputData.getString(INPUT_VERSION_NAME).orEmpty()
        val code = inputData.getInt(INPUT_VERSION_CODE, -1)
        val url = inputData.getString(INPUT_URL).orEmpty()
        val size = inputData.getLong(INPUT_SIZE, 0L)
        if (name.isBlank() || code <= 0 || size < 0L || !AppUpdate.isInstallableUrl(url)) return null
        return UpdateRelease(versionName = name, versionCode = code, url = url, size = size)
    }

    private suspend fun download(release: UpdateRelease, partial: File) {
        withContext(Dispatchers.IO) {
            val request = Request.Builder().url(release.url).get().build()
            val call = updateDownloadClient.newCall(request)
            val cancellationHandle = currentCoroutineContext()[Job]?.invokeOnCompletion { cause ->
                if (cause is CancellationException) call.cancel()
            }
            try {
                call.execute().use { response ->
                    if (!response.isSuccessful) throw IOException("Update server returned ${response.code}")
                    val body = response.body ?: throw IOException("Update response had no file")
                    val totalBytes = release.size.takeIf { it > 0L } ?: body.contentLength()

                    body.byteStream().use { input ->
                        partial.outputStream().buffered().use { output ->
                            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                            var downloadedBytes = 0L
                            var lastPercent = 0
                            while (true) {
                                currentCoroutineContext().ensureActive()
                                val read = input.read(buffer)
                                if (read < 0) break

                                output.write(buffer, 0, read)
                                downloadedBytes += read
                                val percent = AppUpdate.downloadPercent(downloadedBytes, totalBytes)
                                if (percent != null && percent != lastPercent) {
                                    lastPercent = percent
                                    setProgress(progressData(percent))
                                }
                            }
                            output.flush()
                        }
                    }
                }
            } finally {
                cancellationHandle?.dispose()
            }
        }
    }

    private fun progressData(percent: Int): Data =
        workDataOf(PROGRESS_PERCENT to percent.coerceIn(0, 100))
}

private val updateDownloadClient: OkHttpClient by lazy {
    OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .callTimeout(5, TimeUnit.MINUTES)
        .build()
}
