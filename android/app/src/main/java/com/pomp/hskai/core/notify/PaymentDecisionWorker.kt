package com.pomp.hskai.core.notify

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.pomp.hskai.HskAiApplication

class PaymentDecisionWorker(context: Context, params: WorkerParameters) :
    CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val app = applicationContext as? HskAiApplication ?: return Result.success()
        return if (app.paymentDecisionMonitor.pollPending()) Result.retry() else Result.success()
    }
}
