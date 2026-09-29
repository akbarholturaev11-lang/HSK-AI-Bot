package com.pomp.hskai.core.notify

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.feature.update.UpdatePushHandler
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

/** Data-only FCM router. Every kind is re-validated locally before display. */
class HskAiMessagingService : FirebaseMessagingService() {
    override fun onMessageReceived(message: RemoteMessage) {
        val app = application as? HskAiApplication ?: return
        val data = message.data
        runBlocking {
            when (data["kind"]) {
                "payment_decision" -> {
                    val paymentId = data["payment_id"]?.toIntOrNull() ?: return@runBlocking
                    app.paymentDecisionMonitor.receive(
                        deviceId = data["device_id"].orEmpty(),
                        paymentId = paymentId,
                        status = data["status"].orEmpty(),
                    )
                }

                "app_update" -> {
                    val versionCode = data["version_code"]?.toIntOrNull() ?: return@runBlocking
                    UpdatePushHandler.handle(applicationContext, versionCode)
                }

                "account_notice" -> {
                    val noticeId = data["notice_id"]?.toIntOrNull() ?: return@runBlocking
                    app.accountNoticeMonitor.receive(
                        deviceId = data["device_id"].orEmpty(),
                        noticeId = noticeId,
                    )
                }

                "study_reminder" -> {
                    val localDay = data["local_day"]?.takeIf {
                        it.matches(Regex("\\d{4}-\\d{2}-\\d{2}"))
                    } ?: return@runBlocking
                    if (app.studyReminderCoordinator.run(localDay) ==
                        StudyReminderCoordinator.Outcome.SESSION_EXPIRED
                    ) {
                        StudyReminderScheduler.cancel(applicationContext)
                    }
                }
            }
        }
    }

    override fun onNewToken(token: String) {
        val app = application as? HskAiApplication ?: return
        app.applicationScope.launch { app.paymentDecisionMonitor.registerToken(token) }
    }
}
