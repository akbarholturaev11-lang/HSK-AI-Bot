package com.pomp.hskai.widget

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import java.time.ZonedDateTime

internal data class WidgetRefreshTicket(val epoch: String, val generation: Long)

private val Context.widgetDataStore by preferencesDataStore("pomp_smart_widget")

class WidgetStore(private val dataStore: DataStore<Preferences>) {
    constructor(context: Context) : this(context.applicationContext.widgetDataStore)

    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }
    private val key = stringPreferencesKey("session_v1")
    private val mutex = Mutex()
    val state = dataStore.data.map { prefs ->
        prefs[key]?.let { runCatching { json.decodeFromString<WidgetSession>(it) }.getOrNull() }
            ?: WidgetSession(epoch = "uninitialized")
    }

    suspend fun read() = state.first()

    private suspend fun change(transform: (WidgetSession) -> WidgetSession) {
        dataStore.edit { prefs ->
            val old = prefs[key]?.let {
                runCatching { json.decodeFromString<WidgetSession>(it) }.getOrNull()
            } ?: WidgetSession(epoch = "uninitialized")
            prefs[key] = json.encodeToString(transform(old))
        }
    }

    suspend fun linked(newSession: Boolean = false) = mutex.withLock {
        change { if (newSession || !it.linked) WidgetSession(linked = true) else it }
    }

    suspend fun clear() = mutex.withLock { change { WidgetSession() } }

    suspend fun save(snapshot: WidgetSnapshot, epoch: String) = mutex.withLock {
        change {
            if (it.linked && it.epoch == epoch && it.contextBinding == null &&
                snapshot.fetchedAtMillis >= (it.snapshot?.fetchedAtMillis ?: 0)
            ) it.copy(snapshot = snapshot.copy(personalContext = null)) else it
        }
    }

    internal suspend fun beginRefresh(epoch: String): WidgetRefreshTicket? = mutex.withLock {
        var ticket: WidgetRefreshTicket? = null
        change { old ->
            if (!old.linked || old.epoch != epoch || old.contextRequestGeneration == Long.MAX_VALUE) old
            else {
                ticket = WidgetRefreshTicket(epoch, old.contextRequestGeneration + 1)
                old.copy(contextRequestGeneration = old.contextRequestGeneration + 1)
            }
        }
        ticket
    }

    /** A known foreground change revokes pending older projections, without relinking. */
    internal suspend fun invalidateContext(epoch: String) = mutex.withLock {
        change { old ->
            if (!old.linked || old.epoch != epoch) old
            else old.copy(snapshot = null, contextRequestGeneration =
                if (old.contextRequestGeneration == Long.MAX_VALUE) Long.MAX_VALUE else old.contextRequestGeneration + 1)
        }
    }

    internal suspend fun failedRefresh(ticket: WidgetRefreshTicket) = mutex.withLock {
        change { old -> if (old.epoch == ticket.epoch && old.contextRequestGeneration == ticket.generation)
            old.copy(snapshot = null) else old }
    }

    /** Only the live, generation-checked bridge calls this; a cache cannot establish an owner. */
    internal suspend fun savePersonal(snapshot: WidgetSnapshot, raw: JsonElement?, ticket: WidgetRefreshTicket,
                                     now: ZonedDateTime, clock: () -> ZonedDateTime = { now }): Boolean = mutex.withLock {
        var saved = false
        val c = WidgetPersonalContext.parse(raw)
        change { old ->
            when {
                !old.linked || old.epoch != ticket.epoch || old.contextRequestGeneration != ticket.generation -> old
                raw == null -> { saved = true; old.copy(snapshot = snapshot.copy(personalContext = null)) }
                c == null -> old.copy(snapshot = null)
                old.contextBinding != null && old.contextBinding != c.binding -> old.copy(snapshot = null)
                c.revision < old.contextRevision || c.generatedMillis < old.contextGeneratedMillis -> old
                !c.current(snapshot, ticket.epoch, clock()) -> old.copy(snapshot = null)
                else -> {
                    saved = true
                    old.copy(snapshot = snapshot.copy(personalContext = raw), contextBinding = c.binding,
                             contextRevision = c.revision, contextGeneratedMillis = c.generatedMillis)
                }
            }
        }
        saved
    }

    suspend fun setReminder(enabled: Boolean) = mutex.withLock {
        change { it.copy(reminderEnabled = enabled && it.linked) }
    }

    suspend fun markOffered() = mutex.withLock { change { it.copy(onboardingOffered = true) } }

    suspend fun markInstallPromptShown(localDay: String) = mutex.withLock {
        change { it.copy(lastInstallPromptDay = localDay) }
    }

    suspend fun enqueue(event: AndroidWidgetEvent) = mutex.withLock {
        change {
            if (!it.linked || it.events.any { queued -> queued.event_id == event.event_id }) it
            else it.copy(events = (it.events + event).takeLast(WidgetPolicy.MAX_PENDING_EVENTS))
        }
    }

    suspend fun acknowledge(epoch: String, eventId: String) = mutex.withLock {
        change { if (it.epoch == epoch) it.copy(events = it.events.filterNot { e -> e.event_id == eventId }) else it }
    }

    /** Reserve durably before posting; logout cannot race a notification delivery. */
    suspend fun remindOnce(epoch: String, day: String, post: () -> Boolean): Boolean = mutex.withLock {
        val current = read()
        if (!current.linked || !current.reminderEnabled || current.epoch != epoch ||
            current.lastReminderDay == day
        ) return@withLock false
        change { it.copy(lastReminderDay = day) }
        val posted = post()
        if (!posted) change { it.copy(lastReminderDay = current.lastReminderDay) }
        posted
    }
}
