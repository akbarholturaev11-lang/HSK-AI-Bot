package com.pomp.hskai.widget

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.emptyPreferences
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.runTest
import org.junit.Assert.*
import org.junit.Test

private class MemoryPreferences : DataStore<Preferences> {
    override val data = MutableStateFlow(emptyPreferences())
    override suspend fun updateData(transform: suspend (t: Preferences) -> Preferences): Preferences =
        transform(data.value).also { data.value = it }
}

class WidgetStoreTest {
    private val snapshot = WidgetSnapshot(10, "2026-09-11", "Asia/Tashkent", "hsk1", 1, 50, 2, false, false)

    @Test fun `late old account response cannot survive logout or relink`() = runTest {
        val store = WidgetStore(MemoryPreferences())
        store.linked()
        val old = store.read().epoch
        store.save(snapshot, old)
        store.clear()
        store.save(snapshot.copy(xp = 999), old)
        assertFalse(store.read().linked)
        assertNull(store.read().snapshot)
        store.linked()
        store.save(snapshot, old)
        assertNull(store.read().snapshot)
        assertNotEquals(old, store.read().epoch)
    }
    @Test fun `newer progress wins and restoring same session retains epoch`() = runTest {
        val store = WidgetStore(MemoryPreferences())
        store.linked()
        val epoch = store.read().epoch
        store.linked()
        assertEquals(epoch, store.read().epoch)
        store.save(snapshot.copy(fetchedAtMillis = 20), epoch)
        store.save(snapshot, epoch)
        assertEquals(20L, store.read().snapshot?.fetchedAtMillis)
    }
    @Test fun `reminder opt in is separate and delivery is at most one per day`() = runTest {
        val store = WidgetStore(MemoryPreferences())
        store.linked()
        val epoch = store.read().epoch
        var sent = 0
        assertFalse(store.remindOnce(epoch, "2026-09-11") { sent++; true })
        store.setReminder(true)
        assertTrue(store.remindOnce(epoch, "2026-09-11") { sent++; true })
        assertFalse(store.remindOnce(epoch, "2026-09-11") { sent++; true })
        assertTrue(store.remindOnce(epoch, "2026-09-12") { sent++; true })
        assertEquals(2, sent)
        store.clear()
        assertFalse(store.remindOnce(epoch, "2026-09-13") { sent++; true })
        assertFalse(store.read().reminderEnabled)
    }
    @Test fun `telemetry queue bounded deduped persisted and account isolated`() = runTest {
        val memory = MemoryPreferences()
        val store = WidgetStore(memory)
        store.linked()
        val event = AndroidWidgetEvent("android_widget_opened")
        store.enqueue(event); store.enqueue(event)
        assertEquals(1, store.read().events.size)
        assertEquals(event.event_id, WidgetStore(memory).read().events.single().event_id)
        repeat(40) { store.enqueue(AndroidWidgetEvent("android_widget_opened")) }
        assertEquals(WidgetPolicy.MAX_PENDING_EVENTS, store.read().events.size)
        store.clear()
        assertTrue(store.read().events.isEmpty())
    }
}
