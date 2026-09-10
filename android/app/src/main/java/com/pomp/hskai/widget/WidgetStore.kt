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
            if (it.linked && it.epoch == epoch &&
                snapshot.fetchedAtMillis >= (it.snapshot?.fetchedAtMillis ?: 0)
            ) it.copy(snapshot = snapshot) else it
        }
    }

    suspend fun setReminder(enabled: Boolean) = mutex.withLock {
        change { it.copy(reminderEnabled = enabled && it.linked) }
    }

    suspend fun markOffered() = mutex.withLock { change { it.copy(onboardingOffered = true) } }

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
