package com.pomp.hskai.core.notify

import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import com.pomp.hskai.data.api.AccountNoticeAckRequest
import com.pomp.hskai.data.api.AndroidPushApi

/**
 * Shows the subscription and limit notices the server routes here first.
 *
 * The push carries only an id. The notice is read back under the current
 * login, and the server is told whether it appeared: a refusal, or no answer
 * within ten minutes, sends the learner the Telegram copy instead. A notice
 * the server has already sent to Telegram comes back with `show = false`.
 */
class AccountNoticeMonitor(
    private val app: HskAiApplication,
    private val api: AndroidPushApi,
) {
    suspend fun receive(deviceId: String, noticeId: Int): Boolean {
        if (noticeId <= 0 || deviceId.isBlank() || app.credentialStore.refreshToken() == null) {
            return false
        }
        // A push addressed to an earlier login on this phone is not ours to show.
        if (app.paymentDecisionMonitor.currentDeviceId() != deviceId) return false
        val access = app.authRepository.accessToken() as? ApiResult.Success ?: return false
        val bearer = "Bearer ${access.value}"

        if (!AccountNotifications.canPost(app)) {
            // Said at once, so Telegram does not wait the full ten minutes.
            apiCall { api.acknowledgeNotice(bearer, noticeId, AccountNoticeAckRequest(shown = false)) }
            return false
        }
        // Unreachable server: no answer is sent, so Telegram takes over in ten minutes.
        val response = (apiCall { api.notice(bearer, noticeId) } as? ApiResult.Success)?.value
            ?: return false
        val notice = response.notice ?: return false
        if (!response.ok || !notice.show || notice.id != noticeId) return false

        val shown = AccountNotifications.post(app, notice)
        apiCall { api.acknowledgeNotice(bearer, noticeId, AccountNoticeAckRequest(shown = shown)) }
        return shown
    }
}
