package com.pomp.hskai.feature.assistant

import android.content.Context
import com.pomp.hskai.BuildConfig
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.storage.KeystoreCipher
import java.io.File
import java.util.UUID
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import retrofit2.Response

class AssistantFailure(val code: String) : Exception(code)

class AssistantRepository(
    private val api: AssistantApi,
    private val token: suspend () -> ApiResult<String>,
    private val expired: suspend () -> Unit,
    private val json: Json,
) {
    private suspend fun <T> call(block: suspend (String) -> Response<T>): T {
        val auth = (token() as? ApiResult.Success)?.value ?: throw AssistantFailure("session_expired")
        val response = block("Bearer $auth")
        if (response.code() == 401) expired()
        if (!response.isSuccessful) {
            val code = runCatching {
                json.decodeFromString<AssistantEnvelope>(response.errorBody()?.string().orEmpty()).error
            }.getOrNull().orEmpty()
            throw AssistantFailure(code.ifBlank { "assistant_unavailable" })
        }
        return response.body() ?: throw AssistantFailure("assistant_unavailable")
    }
    suspend fun status() = call { api.status(it, BuildConfig.FLAVOR) }
    suspend fun conversations() = call { api.conversations(it) }
    suspend fun create() = call { api.create(it) }.conversation ?: throw AssistantFailure("assistant_unavailable")
    suspend fun history(id: String, before: String = "") = call { api.history(it, id, before) }
    suspend fun send(id: String, data: AssistantInput) = call { api.send(it, id, data) }
    suspend fun lookup(id: String) = call { api.lookup(it, id) }
    suspend fun abandon(id: String) { if (id.isNotBlank()) call { api.abandon(it, AbandonAssessment(id)) } }
}

data class AssistantState(
    val enabled: Boolean = false,
    val loading: Boolean = false,
    val busy: Boolean = false,
    val conversationId: String = "",
    val conversations: List<AssistantConversation> = emptyList(),
    val turns: List<AssistantTurn> = emptyList(),
    val draft: String = "",
    val media: String = "",
    val mediaKind: String = "text",
    val error: String = "",
    val nextCursor: String = "",
    val limits: String = "",
    /** A question the server never confirmed. It blocks a new send until it resolves. */
    val queued: Boolean = false,
)

/** Chats live on the phone. The network is only used to ask a new question. */
@Serializable private data class AssistantStore(
    val epoch: String,
    val conversationId: String = "",
    val draft: String = "",
    val pending: AssistantInput? = null,
    val conversations: List<AssistantConversation> = emptyList(),
    val history: Map<String, List<AssistantTurn>> = emptyMap(),
)

private const val CACHED_CONVERSATIONS = 12
private const val CACHED_TURNS = 40
private const val REFRESH_AFTER_MS = 5 * 60_000L
private const val POLL_BUDGET_MS = 130_000L

/** Application-owned: Foundation and Main share history, never a lesson ViewModel.
 * Every account reset cancels work and invalidates late results. The store is encrypted,
 * excluded from backup, and cleared when the account changes; raw media never enters history.
 *
 * Local-first: the cached chat renders immediately and the server is contacted only when it
 * can add something — a new question, a stale conversation, or an answer still being written.
 * A failed background refresh keeps the cached chat on screen instead of raising an error.
 */
class AssistantController(
    context: Context,
    val repository: AssistantRepository,
    private val json: Json,
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private val mutable = MutableStateFlow(AssistantState())
    val state = mutable.asStateFlow()
    private val cipher = KeystoreCipher("hsk-assistant-outbox-v1")
    private val file = android.util.AtomicFile(File(context.noBackupFilesDir, "assistant-outbox"))
    private var epoch = ""
    private var pending: AssistantInput? = null
    private var job: Job? = null
    private var refreshJob: Job? = null
    private var initialized = false
    private val persistMutex = Mutex()
    private val history = mutableMapOf<String, List<AssistantTurn>>()
    private var refreshedAt = 0L

    fun reset() {
        scope.coroutineContext.cancelChildren()
        epoch = ""
        initialized = false
        pending = null
        job = null
        refreshJob = null
        history.clear()
        refreshedAt = 0L
        mutable.value = AssistantState()
        file.delete()
        cipher.deleteKey()
    }

    fun attach(accountEpoch: String) {
        if (epoch == accountEpoch && initialized) return
        if (epoch.isNotBlank() && epoch != accountEpoch) reset()
        epoch = accountEpoch
        initialized = true
        scope.launch {
            val saved = runCatching {
                cipher.decrypt(file.readFully().toString(Charsets.UTF_8))?.let { json.decodeFromString<AssistantStore>(it) }
            }.getOrNull()?.takeIf { it.epoch == epoch }
            if (saved != null) {
                setPending(saved.pending)
                history.putAll(saved.history)
                // Never clobber anything the chat already fetched while this was decrypting.
                mutable.update { current ->
                    if (current.turns.isNotEmpty() || current.conversations.isNotEmpty()) current
                    else current.copy(
                        conversationId = saved.conversationId,
                        draft = saved.draft,
                        conversations = saved.conversations,
                        turns = saved.history[saved.conversationId].orEmpty(),
                    )
                }
            }
            try {
                val status = repository.status()
                mutable.update { it.copy(enabled = status.enabled, limits = status.entitlements?.toString().orEmpty()) }
            } catch (cancel: CancellationException) { throw cancel }
            catch (_: Exception) { initialized = false }
        }
    }

    fun edit(text: String) { mutable.update { it.copy(draft = text.take(4000)) }; persist() }
    fun media(data: String, kind: String) { mutable.update { it.copy(media = data, mediaKind = kind, error = "") } }
    fun error(code: String) { mutable.update { it.copy(error = code) } }

    private fun setPending(value: AssistantInput?) {
        pending = value
        mutable.update { it.copy(queued = value != null) }
    }

    /** Drops a question the server never confirmed, so a stuck queue cannot lock the chat. */
    fun discard() {
        if (mutable.value.busy) return
        setPending(null)
        mutable.update { it.copy(draft = "", media = "", mediaKind = "text", error = "") }
        persist()
    }

    private fun persist() {
        val snapshot = AssistantStore(
            epoch,
            mutable.value.conversationId,
            mutable.value.draft,
            pending,
            mutable.value.conversations.take(CACHED_CONVERSATIONS),
            history.entries.sortedByDescending { it.key == mutable.value.conversationId }
                .take(CACHED_CONVERSATIONS)
                .associate { it.key to it.value.takeLast(CACHED_TURNS) },
        )
        scope.launch(Dispatchers.IO) {
            persistMutex.withLock {
                if (snapshot.epoch.isBlank() || snapshot.epoch != epoch) return@withLock
                val value = cipher.encrypt(json.encodeToString(snapshot)) ?: return@withLock
                runCatching {
                    val output = file.startWrite()
                    try { output.write(value.toByteArray()); file.finishWrite(output) }
                    catch (error: Exception) { file.failWrite(output); throw error }
                }
            }
        }
    }

    fun open() {
        if (job?.isActive == true) return
        job = scope.launch {
            val cachedId = mutable.value.conversationId
            val warm = cachedId.isNotBlank() && mutable.value.turns.isNotEmpty()
            mutable.update { it.copy(loading = !warm, error = "") }
            try {
                var id = cachedId
                if (id.isBlank() && mutable.value.conversations.isEmpty()) {
                    val conversations = repository.conversations().conversations
                    id = conversations.firstOrNull()?.id.orEmpty()
                    mutable.update { it.copy(conversations = conversations, conversationId = id) }
                }
                val unfinished = mutable.value.turns.lastOrNull { it.status == "processing" }
                val stale = System.currentTimeMillis() - refreshedAt > REFRESH_AFTER_MS
                if (id.isNotBlank() && (!warm || stale || unfinished != null)) loadHistory(id)
            } catch (cancel: CancellationException) { throw cancel }
            // A warm cache is still worth showing; only a cold open reports a refresh failure.
            catch (error: Exception) { if (!warm) report(error) }
            try {
                // Resolving a queued question is the learner's own action: always report it.
                if (pending != null) deliver(recoverFirst = true)
                else mutable.value.turns.lastOrNull { it.status == "processing" }?.let { poll(it) }
                persist()
            } catch (cancel: CancellationException) { throw cancel }
            catch (error: Exception) { report(error) }
            finally { mutable.update { it.copy(loading = false, busy = false) } }
        }
    }

    /** Refreshes the saved-chats list; the cached list stays on screen if the network is down.
     * Runs off the main job so a background top-up never swallows a send. */
    fun conversations() {
        if (refreshJob?.isActive == true) return
        refreshJob = scope.launch {
            try {
                mutable.update { it.copy(conversations = repository.conversations().conversations) }
                persist()
            } catch (cancel: CancellationException) { throw cancel }
            catch (_: Exception) { }
        }
    }

    fun selectConversation(id: String = "") {
        if (mutable.value.busy || pending != null || job?.isActive == true) return
        if (id.isBlank()) {
            // An empty chat costs nothing until the first question; the server row is
            // created by the send itself, so starting one works offline.
            mutable.update { it.copy(conversationId = "", turns = emptyList(), nextCursor = "", error = "") }
            persist()
            return
        }
        job = scope.launch {
            val cached = history[id].orEmpty()
            mutable.update { it.copy(loading = cached.isEmpty(), error = "", conversationId = id, turns = cached, nextCursor = "") }
            try {
                loadHistory(id)
                persist()
            } catch (cancel: CancellationException) { throw cancel }
            catch (error: Exception) { if (cached.isEmpty()) report(error) }
            finally { mutable.update { it.copy(loading = false) } }
        }
    }

    fun older() {
        if (job?.isActive == true || mutable.value.nextCursor.isBlank()) return
        job = scope.launch {
            try { loadHistory(mutable.value.conversationId, mutable.value.nextCursor) }
            catch (cancel: CancellationException) { throw cancel }
            catch (error: Exception) { report(error) }
        }
    }

    private suspend fun loadHistory(id: String, before: String = "") {
        val page = repository.history(id, before)
        mutable.update { it.copy(turns = if (before.isBlank()) page.messages else (page.messages + it.turns).distinctBy { turn -> turn.clientMessageId }, nextCursor = page.nextCursor) }
        history[id] = mutable.value.turns
        if (before.isBlank()) refreshedAt = System.currentTimeMillis()
    }

    fun send(context: ScreenContext) {
        val snapshot = mutable.value
        if (snapshot.draft.isBlank() && snapshot.media.isBlank()) return
        // An unresolved question still holds the draft. Finish it instead of dropping
        // the tap: silently doing nothing reads as a broken send button.
        if (pending != null) { retry(); return }
        if (job?.isActive == true || snapshot.busy) return
        setPending(AssistantInput(UUID.randomUUID().toString(), snapshot.draft, snapshot.mediaKind, snapshot.media, context))
        persist()
        launchDelivery(false)
    }

    fun retry() {
        if (job?.isActive == true) return
        if (pending == null) { open(); return }
        launchDelivery(true)
    }

    private fun launchDelivery(recoverFirst: Boolean) {
        mutable.update { it.copy(busy = true, error = "") }
        job = scope.launch {
            try { deliver(recoverFirst) }
            catch (cancel: CancellationException) { throw cancel }
            catch (error: Exception) { report(error) }
            finally { mutable.update { it.copy(busy = false) } }
        }
    }

    private suspend fun deliver(recoverFirst: Boolean) {
        val input = pending ?: return
        if (mutable.value.conversationId.isBlank()) {
            mutable.update { it.copy(conversationId = repository.create().id) }
            persist()
        }
        val recovered = if (recoverFirst) try { repository.lookup(input.clientMessageId) }
            catch (error: AssistantFailure) { if (error.code == "assistant_not_found") null else throw error } else null
        val response = try { recovered ?: repository.send(mutable.value.conversationId, input) }
        catch (error: AssistantFailure) {
            // Definitive rejection: no request was accepted. Keep the draft, allow editing.
            if (error.code !in setOf("assistant_unavailable", "assistant_busy")) { setPending(null); persist() }
            throw error
        }
        upsert(response)
        mutable.update { it.copy(draft = "", media = "", mediaKind = "text") }
        val done = if (response.status == "processing") poll(response) else response
        if (done.status == "failed") {
            // Confirmed terminal failure can be resubmitted with a new ID, not charged twice.
            setPending(null)
            mutable.update { it.copy(draft = input.text, media = input.mediaDataUrl, mediaKind = input.kind, error = done.error) }
        } else { setPending(null) }
        persist()
    }

    /** Backs off once the quick answers are past, so a slow reply costs a handful of
     * polls instead of one every 1.5s for two minutes. */
    private suspend fun poll(initial: AssistantTurn): AssistantTurn {
        var result = initial
        mutable.update { it.copy(busy = true) }
        var waited = 0L
        var attempt = 0
        while (waited < POLL_BUDGET_MS) {
            if (result.status != "processing") return result
            val gap = when {
                attempt < 4 -> 1_500L
                attempt < 12 -> 3_000L
                else -> 5_000L
            }
            delay(gap)
            waited += gap
            attempt++
            result = repository.lookup(initial.clientMessageId)
            upsert(result)
        }
        throw AssistantFailure("assistant_timeout")
    }

    private fun upsert(turn: AssistantTurn) {
        mutable.update { it.copy(turns = (it.turns.filterNot { old -> old.clientMessageId == turn.clientMessageId } + turn)) }
        val id = mutable.value.conversationId
        if (id.isNotBlank()) history[id] = mutable.value.turns
    }
    private fun report(error: Exception) {
        mutable.update { it.copy(error = (error as? AssistantFailure)?.code ?: "assistant_network") }
    }
}
