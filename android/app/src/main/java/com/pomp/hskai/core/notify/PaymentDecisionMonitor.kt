package com.pomp.hskai.core.notify

import android.content.Context
import android.util.Log
import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import com.google.firebase.messaging.FirebaseMessaging
import com.pomp.hskai.BuildConfig
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import com.pomp.hskai.data.api.AndroidPushApi
import com.pomp.hskai.data.api.PushPreferencesRequest
import com.pomp.hskai.data.api.PushTokenRequest
import java.time.ZoneId
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resume
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.suspendCancellableCoroutine

data class InAppPaymentDecision(
    val deviceId: String,
    val paymentId: Int,
    val status: String,
    val planType: String,
)

/**
 * FCM is optional; the pending Android payment is also checked every 15 minutes.
 * Both transports use the same device and payment decision dedupe key.
 */
class PaymentDecisionMonitor(
    private val app: HskAiApplication,
    private val api: AndroidPushApi,
) {
    private val prefs = app.getSharedPreferences("payment_decisions", Context.MODE_PRIVATE)
    private val lock = Any()
    private val inAppPaymentDecisionChannel = Channel<InAppPaymentDecision>(Channel.UNLIMITED)
    val inAppPaymentDecisions: Flow<InAppPaymentDecision> = inAppPaymentDecisionChannel.receiveAsFlow()

    fun initializeFirebase(): Boolean {
        if (!firebaseConfigured()) return false
        return runCatching {
            if (FirebaseApp.getApps(app).isEmpty()) {
                FirebaseApp.initializeApp(
                    app,
                    FirebaseOptions.Builder()
                        .setApplicationId(BuildConfig.FIREBASE_APP_ID)
                        .setProjectId(BuildConfig.FIREBASE_PROJECT_ID)
                        .setGcmSenderId(BuildConfig.FIREBASE_SENDER_ID)
                        .setApiKey(BuildConfig.FIREBASE_API_KEY)
                        .build(),
                )
            }
            FirebaseApp.getApps(app).isNotEmpty()
        }.getOrElse {
            Log.w("PaymentDecisionMonitor", "Firebase unavailable; payment polling stays active")
            false
        }
    }

    /** Called only after a successful authenticated bootstrap. */
    fun bindDevice(deviceId: String) {
        if (deviceId.isBlank()) return
        synchronized(lock) {
            val previous = prefs.getString(DEVICE_ID, null)
            prefs.edit().putString(DEVICE_ID, deviceId).apply()
            if (previous != null && previous != deviceId) {
                prefs.edit().remove(PENDING_PAYMENT_ID).apply()
                cancelWorker()
            }
        }
        PaymentNotifications.ensureChannel(app)
        if (pendingPaymentId() > 0) scheduleWorker()
    }

    /** Called after receipt submit, including an already-pending response. */
    fun watch(paymentId: Int) {
        if (paymentId <= 0) return
        synchronized(lock) {
            prefs.edit().putInt(PENDING_PAYMENT_ID, paymentId).apply()
            scheduleWorker()
        }
    }

    /** The device this login is bound to; account notices must name it. */
    fun currentDeviceId(): String? = prefs.getString(DEVICE_ID, null)

    suspend fun syncRegistration() {
        if (!initializeFirebase() ||
            prefs.getString(DEVICE_ID, null).isNullOrBlank() ||
            app.credentialStore.refreshToken() == null
        ) return
        if (!canRegisterPush()) {
            // Notifications were switched off: the server should stop routing
            // account notices here and keep them on Telegram.
            syncPreferences()
            return
        }
        val token = suspendCancellableCoroutine<String?> { continuation ->
            FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
                if (continuation.isActive) {
                    continuation.resume(if (task.isSuccessful) task.result else null)
                }
            }
        } ?: return
        registerToken(token)
    }

    suspend fun registerToken(token: String) {
        if (!firebaseConfigured() || token.isBlank() || !canRegisterPush() ||
            prefs.getString(DEVICE_ID, null).isNullOrBlank() ||
            app.credentialStore.refreshToken() == null
        ) return
        val access = app.authRepository.accessToken() as? ApiResult.Success ?: return
        val registered = apiCall { api.register("Bearer ${access.value}", PushTokenRequest(token)) }
        if (registered is ApiResult.Success && registered.value.ok) {
            syncPreferences(access.value)
        }
    }

    suspend fun syncPreferences() {
        if (!firebaseConfigured() || app.credentialStore.refreshToken() == null) return
        val access = app.authRepository.accessToken() as? ApiResult.Success ?: return
        syncPreferences(access.value)
    }

    private suspend fun syncPreferences(accessToken: String) {
        val session = app.widgetStore.read()
        apiCall {
            api.preferences(
                "Bearer $accessToken",
                PushPreferencesRequest(
                    studyRemindersEnabled = session.reminderEnabled,
                    timezoneName = ZoneId.systemDefault().id,
                    notificationsAllowed = AccountNotifications.canPost(app),
                ),
            )
        }
    }

    private fun canRegisterPush(): Boolean {
        if (!NotificationManagerCompat.from(app).areNotificationsEnabled()) return false
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ContextCompat.checkSelfPermission(
                app,
                Manifest.permission.POST_NOTIFICATIONS,
            ) == PackageManager.PERMISSION_GRANTED
    }

    /** Called on every local logout, including an offline logout. */
    fun clear() {
        synchronized(lock) {
            prefs.edit()
                .remove(DEVICE_ID)
                .remove(PENDING_PAYMENT_ID)
                .putLong(SESSION_EPOCH, prefs.getLong(SESSION_EPOCH, 0L) + 1L)
                .apply()
            cancelWorker()
            PaymentNotifications.cancel(app)
        }
    }

    /** FCM data is a hint, not proof: verify this payment under today's login. */
    suspend fun receive(deviceId: String, paymentId: Int, status: String): Boolean {
        if (paymentId <= 0 || status !in setOf("approved", "rejected") ||
            deviceId.isBlank() || app.credentialStore.refreshToken() == null
        ) return false
        val epoch = prefs.getLong(SESSION_EPOCH, 0L)
        if (prefs.getString(DEVICE_ID, null) != deviceId) return false
        val access = app.authRepository.accessToken() as? ApiResult.Success ?: return false
        val verified = apiCall { api.paymentStatus("Bearer ${access.value}", paymentId) }
        val body = (verified as? ApiResult.Success)?.value ?: return false
        if (!body.ok || body.paymentId != paymentId || body.status != status) return false
        return postVerified(deviceId, paymentId, status, body.planType, epoch)
    }

    private fun postVerified(
        deviceId: String,
        paymentId: Int,
        status: String,
        planType: String,
        epoch: Long,
    ): Boolean {
        synchronized(lock) {
            if (prefs.getString(DEVICE_ID, null) != deviceId ||
                prefs.getLong(SESSION_EPOCH, 0L) != epoch
            ) return false
            if (planType == "hsk30_unlock" && status == "rejected") {
                val inAppSeenKey = "in-app:$deviceId:$paymentId:$status"
                if (!prefs.getBoolean(inAppSeenKey, false)) {
                    prefs.edit().putBoolean(inAppSeenKey, true).apply()
                    inAppPaymentDecisionChannel.trySend(
                        InAppPaymentDecision(
                            deviceId = deviceId,
                            paymentId = paymentId,
                            status = status,
                            planType = planType,
                        )
                    )
                }
            }
            val seenKey = "seen:$deviceId:$paymentId:$status"
            if (prefs.getBoolean(seenKey, false)) return false
            if (!PaymentNotifications.post(app, status, planType)) return false
            prefs.edit().putBoolean(seenKey, true).apply()
            if (prefs.getInt(PENDING_PAYMENT_ID, 0) == paymentId) {
                prefs.edit().remove(PENDING_PAYMENT_ID).apply()
                cancelWorker()
            }
        }
        return true
    }

    /** True means a transient failure; WorkManager may retry. */
    suspend fun pollPending(): Boolean {
        val paymentId = pendingPaymentId()
        if (paymentId <= 0) return false
        if (app.credentialStore.refreshToken() == null) {
            clear()
            return false
        }
        val epoch = prefs.getLong(SESSION_EPOCH, 0L)
        val access = app.authRepository.accessToken() as? ApiResult.Success ?: return true
        return when (val result = apiCall {
            api.paymentStatus("Bearer ${access.value}", paymentId)
        }) {
            is ApiResult.Failure -> true
            is ApiResult.Success -> {
                val status = result.value
                if (status.ok && status.paymentId == paymentId &&
                    status.status in setOf("approved", "rejected")
                ) {
                    postVerified(
                        prefs.getString(DEVICE_ID, null).orEmpty(),
                        paymentId,
                        status.status,
                        status.planType,
                        epoch,
                    )
                }
                false
            }
        }
    }

    private fun pendingPaymentId(): Int = prefs.getInt(PENDING_PAYMENT_ID, 0)

    private fun scheduleWorker() {
        WorkManager.getInstance(app).enqueueUniquePeriodicWork(
            WORK_NAME,
            ExistingPeriodicWorkPolicy.UPDATE,
            PeriodicWorkRequestBuilder<PaymentDecisionWorker>(15, TimeUnit.MINUTES).build(),
        )
    }

    private fun cancelWorker() {
        WorkManager.getInstance(app).cancelUniqueWork(WORK_NAME)
    }

    private fun firebaseConfigured(): Boolean =
        BuildConfig.FIREBASE_APP_ID.isNotBlank() &&
            BuildConfig.FIREBASE_SENDER_ID.isNotBlank() &&
            BuildConfig.FIREBASE_PROJECT_ID.isNotBlank() &&
            BuildConfig.FIREBASE_API_KEY.isNotBlank()

    private companion object {
        const val DEVICE_ID = "device_id"
        const val PENDING_PAYMENT_ID = "pending_payment_id"
        const val SESSION_EPOCH = "session_epoch"
        const val WORK_NAME = "android_payment_decision_check"
    }
}
