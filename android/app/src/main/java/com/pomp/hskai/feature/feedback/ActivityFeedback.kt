package com.pomp.hskai.feature.feedback

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.apiCall
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.serialization.Serializable
import retrofit2.Response
import retrofit2.http.*

@Serializable data class ActivityFeedbackContext(val kind: String, val level: String, val lesson_id: Int? = null)
@Serializable data class FeedbackPrepare(val context: ActivityFeedbackContext)
@Serializable data class FeedbackOption(val code: String, val label: String)
@Serializable data class FeedbackChoices(
    val liked: List<FeedbackOption> = emptyList(), val disliked: List<FeedbackOption> = emptyList(),
    val liked_sub: Map<String, List<FeedbackOption>> = emptyMap(), val disliked_detail_required: List<String> = emptyList(),
    val paid: List<FeedbackOption> = emptyList(), val paid_sub_positive: List<FeedbackOption> = emptyList(),
    val paid_sub_negative: List<FeedbackOption> = emptyList(),
)
@Serializable data class ActivityFeedbackPrompt(val feedback_id: Int, val paid: Boolean = false,
    val liked_code: String? = null, val disliked_code: String? = null, val choices: FeedbackChoices = FeedbackChoices())
@Serializable data class FeedbackPrepareReply(val ok: Boolean = false, val ordinary: ActivityFeedbackPrompt? = null)
@Serializable data class FeedbackSubmitReply(val ok: Boolean = false, val completed: Boolean = false)
interface AndroidActivityFeedbackApi {
    @POST("api/v3/android/feedback/prepare")
    suspend fun prepareFeedback(@Header("Authorization") auth: String, @Body request: FeedbackPrepare): Response<FeedbackPrepareReply>
    @POST("api/v3/android/feedback/submit")
    suspend fun submitFeedback(@Header("Authorization") auth: String, @Body request: Map<String,String>): Response<FeedbackSubmitReply>
}
class ActivityFeedbackRepository(private val api: AndroidActivityFeedbackApi,
    private val token: suspend () -> ApiResult<String>, private val expired: suspend () -> Unit = {}) {
    private suspend fun <T:Any> call(block: suspend (String)->Response<T>): ApiResult<T> {
        val auth = when(val result = token()) { is ApiResult.Success -> "Bearer ${result.value}"; is ApiResult.Failure -> return result }
        val result = withTimeoutOrNull(12_000) { apiCall { block(auth) } } ?: ApiResult.Failure(ApiError.Timeout)
        if (result is ApiResult.Failure && result.error is ApiError.SessionExpired) expired()
        return result
    }
    suspend fun prepare(context: ActivityFeedbackContext) = call { api.prepareFeedback(it, FeedbackPrepare(context)) }
    suspend fun submit(id: Int, draft: Map<String,String>) = call { api.submitFeedback(it, draft + ("feedback_id" to id.toString())) }
}

data class FeedbackQuestion(val key: String, val options: List<FeedbackOption> = emptyList(), val heading: String = "detail")
/** Data-driven equivalent of the canonical bot/PWA one-question flow. */
fun feedbackQuestions(prompt: ActivityFeedbackPrompt, draft: Map<String,String>): List<FeedbackQuestion> = buildList {
    val choices = prompt.choices
    if (prompt.paid) {
        add(FeedbackQuestion("paid_code", choices.paid, "paid"))
        if (!draft["paid_code"].isNullOrBlank()) {
            add(FeedbackQuestion("paid_sub_code", if (draft["paid_code"] in setOf("worth", "useful")) choices.paid_sub_positive else choices.paid_sub_negative))
            if (draft["paid_sub_code"] == "other") add(FeedbackQuestion("paid_other_text"))
        }
    } else {
        add(FeedbackQuestion("liked_code", choices.liked, "liked"))
        choices.liked_sub[draft["liked_code"]]?.takeIf { it.isNotEmpty() }?.let { add(FeedbackQuestion("liked_sub_code",it)) }
        if (draft["liked_code"] == "other" || draft["liked_sub_code"] == "other") add(FeedbackQuestion("liked_other_text"))
        add(FeedbackQuestion("disliked_code", choices.disliked, "disliked"))
        if (draft["disliked_code"] in choices.disliked_detail_required) add(FeedbackQuestion("disliked_detail_text"))
    }
}
data class ActivityFeedbackState(val prompt: ActivityFeedbackPrompt? = null, val draft: Map<String,String> = emptyMap(),
    val step: Int = 0, val busy: Boolean = false, val error: Boolean = false, val completed: Boolean = false) {
    val questions get() = prompt?.let { feedbackQuestions(it,draft) }.orEmpty()
    val question get() = questions.getOrNull(step)
}
class ActivityFeedbackViewModel(private val repository: ActivityFeedbackRepository) : ViewModel() {
    private val _state = MutableStateFlow(ActivityFeedbackState())
    val state = _state.asStateFlow()
    private var generation = 0
    private val attempted = mutableSetOf<ActivityFeedbackContext>()
    private var preparing = false
    fun prepare(kind: String, level: String, lesson: Int? = null) {
        val context = ActivityFeedbackContext(kind, if (level == "beginner") "hsk1" else level, lesson)
        if (_state.value.prompt != null || preparing || context in attempted) return
        attempted += context
        preparing = true
        val current = ++generation
        viewModelScope.launch {
            val reply = repository.prepare(context)
            preparing = false
            if (current != generation) return@launch
            if (reply is ApiResult.Success && reply.value.ok && reply.value.ordinary != null) {
                val prompt = reply.value.ordinary
                val initial = if (prompt.paid) prompt.liked_code?.removePrefix("paid_")?.let { mapOf("paid_code" to it) }
                    else prompt.liked_code?.let { mapOf("liked_code" to it) }
                _state.value = ActivityFeedbackState(prompt = prompt, draft = initial.orEmpty())
            }
        }
    }
    fun answer(value: String) {
        val old = _state.value; val question = old.question ?: return
        if (old.busy || old.completed || (question.options.isNotEmpty() && question.options.none { it.code == value })) return
        val draft = old.draft.toMutableMap()
        if (question.options.isNotEmpty()) {
            val downstream = when(question.key) {
                "liked_code" -> listOf("liked_sub_code","liked_other_text","disliked_code","disliked_detail_text")
                "liked_sub_code" -> listOf("liked_other_text","disliked_code","disliked_detail_text")
                "disliked_code" -> listOf("disliked_detail_text")
                "paid_code" -> listOf("paid_sub_code","paid_other_text")
                "paid_sub_code" -> listOf("paid_other_text")
                else -> emptyList()
            }
            downstream.forEach { draft.remove(it) }
        }
        draft[question.key] = value.take(1000)
        _state.update { it.copy(draft = draft, error = false) }
        if (question.options.isNotEmpty()) next()
    }
    fun next() {
        val old = _state.value; val prompt = old.prompt ?: return; val question = old.question ?: return
        if (old.busy || old.completed || old.draft[question.key].isNullOrBlank()) return
        if (old.step < old.questions.lastIndex) { _state.update { it.copy(step = it.step+1) }; return }
        _state.update { it.copy(busy = true, error = false) }
        viewModelScope.launch {
            val reply = repository.submit(prompt.feedback_id, old.draft)
            _state.update { it.copy(busy = false, completed = reply is ApiResult.Success && reply.value.ok && reply.value.completed,
                error = reply !is ApiResult.Success || !reply.value.ok || !reply.value.completed) }
        }
    }
    fun back() { if (!_state.value.busy) _state.update { it.copy(step = (it.step-1).coerceAtLeast(0), error = false) } }
    fun close() { if (!_state.value.busy) { generation++; _state.value = ActivityFeedbackState() } }
}
