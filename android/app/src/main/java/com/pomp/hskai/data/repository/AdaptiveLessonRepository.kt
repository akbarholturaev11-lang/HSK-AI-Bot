package com.pomp.hskai.data.repository

import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AdaptiveAnswerRequestDto
import com.pomp.hskai.data.api.AdaptiveAnswerResponseDto
import com.pomp.hskai.data.api.AdaptivePlanDto
import com.pomp.hskai.data.api.AdaptivePlanRequestDto
import com.pomp.hskai.data.api.AndroidAdaptiveApi
import java.io.IOException
import kotlin.coroutines.cancellation.CancellationException
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withTimeoutOrNull

/** What became of one personal review answer. */
sealed interface AdaptiveAnswerOutcome {
    /** The server checked it; [response] carries its verdict. */
    data class Verified(val response: AdaptiveAnswerResponseDto) : AdaptiveAnswerOutcome

    /** No connection or a 5xx: kept on this phone and sent before the next plan. */
    data object Saved : AdaptiveAnswerOutcome

    /** The server refused it (stale plan, feature off, another account): the lesson just goes on. */
    data object Rejected : AdaptiveAnswerOutcome
}

/**
 * In-lesson personal review (UIUX-007). Nothing here touches the lesson's own
 * score, hearts, streak, XP or completion — those stay in [CourseRepository].
 *
 * Every failure is quiet: a plan that does not come is no review at all, and
 * an answer that cannot be sent waits in a small in-memory outbox (the same
 * limits as the Mini App's: ten answers, 36 hours). The server accepts a
 * repeated answer idempotently and rejects another account's plan, so a queued
 * answer can never be credited to the wrong learner.
 */
class AdaptiveLessonRepository(
    private val api: AndroidAdaptiveApi,
    private val accessToken: suspend () -> ApiResult<String>,
    private val now: () -> Long = System::currentTimeMillis,
    private val planTimeoutMillis: Long = PLAN_TIMEOUT_MILLIS,
) {
    private data class Pending(val body: AdaptiveAnswerRequestDto, val at: Long)

    private val outbox = mutableListOf<Pending>()
    private val lock = Mutex()

    /** Null when the feature is off for this learner, or on any failure. */
    suspend fun plan(level: String, lessonOrder: Int, language: String): AdaptivePlanDto? {
        val token = (accessToken() as? ApiResult.Success)?.value ?: return null
        flush(token)
        return try {
            val response = withTimeoutOrNull(planTimeoutMillis) {
                api.plan(
                    authorization = "Bearer $token",
                    body = AdaptivePlanRequestDto(level, lessonOrder, MISTAKE_REVIEW_FORMATS, language),
                )
            } ?: return null
            val body = response.body()
            if (!response.isSuccessful || body == null || !body.ok || !body.enabled) null else body.plan
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (_: Exception) {
            null
        }
    }

    suspend fun answer(
        planId: Long,
        itemId: String,
        selectedIndex: Int? = null,
        selectedTokens: List<String>? = null,
    ): AdaptiveAnswerOutcome {
        val body = AdaptiveAnswerRequestDto(planId, itemId, selectedIndex, selectedTokens)
        val token = (accessToken() as? ApiResult.Success)?.value
        if (token == null) {
            queue(body)
            return AdaptiveAnswerOutcome.Saved
        }
        return when (val sent = send(token, body)) {
            null -> {
                queue(body)
                AdaptiveAnswerOutcome.Saved
            }
            else -> sent
        }
    }

    /** Answers still waiting; for tests and diagnostics only. */
    suspend fun pendingCount(): Int = lock.withLock { outbox.size }

    /** Null means "try again later"; anything else is final. */
    private suspend fun send(token: String, body: AdaptiveAnswerRequestDto): AdaptiveAnswerOutcome? = try {
        val response = api.answer(authorization = "Bearer $token", body = body)
        val payload = response.body()
        when {
            response.code() >= 500 -> null
            response.isSuccessful && payload != null && payload.ok -> AdaptiveAnswerOutcome.Verified(payload)
            else -> AdaptiveAnswerOutcome.Rejected
        }
    } catch (cancelled: CancellationException) {
        throw cancelled
    } catch (_: IOException) {
        null
    } catch (_: Exception) {
        AdaptiveAnswerOutcome.Rejected
    }

    private suspend fun queue(body: AdaptiveAnswerRequestDto) = lock.withLock {
        outbox.removeAll { it.body.planId == body.planId && it.body.itemId == body.itemId }
        outbox += Pending(body, now())
        while (outbox.size > OUTBOX_MAX) outbox.removeAt(0)
    }

    private suspend fun flush(token: String) {
        val pending = lock.withLock {
            val fresh = outbox.filter { now() - it.at < OUTBOX_TTL_MILLIS }
            outbox.clear()
            fresh
        }
        if (pending.isEmpty()) return
        val keep = pending.filter { send(token, it.body) == null }
        lock.withLock {
            // Answers queued while this flush ran are newer; they win.
            val newer = outbox.toList()
            outbox.clear()
            outbox += keep.filter { old -> newer.none { it.body.planId == old.body.planId && it.body.itemId == old.body.itemId } }
            outbox += newer
            while (outbox.size > OUTBOX_MAX) outbox.removeAt(0)
        }
    }

    companion object {
        const val OUTBOX_MAX = 10
        const val OUTBOX_TTL_MILLIS = 36L * 60 * 60 * 1000
        const val PLAN_TIMEOUT_MILLIS = 6_000L
    }
}
