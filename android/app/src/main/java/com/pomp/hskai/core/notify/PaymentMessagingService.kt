package com.pomp.hskai.core.notify

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.pomp.hskai.HskAiApplication
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

/** Data-only FCM: the app checks its current local session before displaying. */
class PaymentMessagingService : FirebaseMessagingService() {
    override fun onMessageReceived(message: RemoteMessage) {
        val data = message.data
        if (data["kind"] != "payment_decision") return
        val paymentId = data["payment_id"]?.toIntOrNull() ?: return
        val deviceId = data["device_id"].orEmpty()
        val status = data["status"].orEmpty()
        val app = application as? HskAiApplication ?: return
        runBlocking { app.paymentDecisionMonitor.receive(deviceId, paymentId, status) }
    }

    override fun onNewToken(token: String) {
        val app = application as? HskAiApplication ?: return
        app.applicationScope.launch { app.paymentDecisionMonitor.registerToken(token) }
    }
}
