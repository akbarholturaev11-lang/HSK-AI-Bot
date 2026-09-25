package com.pomp.hskai.widget

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.mutablePreferencesOf
import androidx.datastore.preferences.core.stringPreferencesKey
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
    @Test fun `a cache written before the goal fields still opens`() = runTest {
        // An unreadable cache is dropped, and a dropped cache shows "link your
        // account" to someone who is linked. New snapshot fields must default.
        val memory = MemoryPreferences()
        val legacy = "{\"epoch\":\"e1\",\"linked\":true,\"snapshot\":{" +
            "\"fetchedAtMillis\":10,\"localDay\":\"2026-09-11\",\"zoneId\":\"Asia/Tashkent\"," +
            "\"level\":\"hsk1\",\"lessonOrder\":1,\"xp\":50,\"streak\":2," +
            "\"dayComplete\":false,\"foundationRequired\":false}}"
        memory.updateData { mutablePreferencesOf(stringPreferencesKey("session_v1") to legacy) }
        val store = WidgetStore(memory)
        assertTrue(store.read().linked)
        assertEquals(50, store.read().snapshot?.xp)
        assertEquals(0, store.read().snapshot?.goalXp)
        assertEquals(0, store.read().snapshot?.dailyXp)
    }
    @Test fun `widget install prompt is durable and only auto shows once per local day`() = runTest {
        val memory = MemoryPreferences()
        val store = WidgetStore(memory)
        store.linked()

        assertTrue(
            WidgetInstallPromptPolicy.shouldAutoShow(
                installed = false,
                lastShownDay = store.read().lastInstallPromptDay,
                today = "2026-09-23",
            )
        )

        store.markInstallPromptShown("2026-09-23")
        assertEquals("2026-09-23", WidgetStore(memory).read().lastInstallPromptDay)
        assertFalse(
            WidgetInstallPromptPolicy.shouldAutoShow(
                installed = false,
                lastShownDay = store.read().lastInstallPromptDay,
                today = "2026-09-23",
            )
        )
        assertTrue(
            WidgetInstallPromptPolicy.shouldAutoShow(
                installed = false,
                lastShownDay = store.read().lastInstallPromptDay,
                today = "2026-09-24",
            )
        )
        assertFalse(
            WidgetInstallPromptPolicy.shouldAutoShow(
                installed = true,
                lastShownDay = null,
                today = "2026-09-24",
            )
        )
    }

    @Test fun `a pin is called blocked only on xiaomi when nothing covered the app and no widget arrived`() {
        assertTrue(WidgetInstallPromptPolicy.pinLooksBlocked("Xiaomi", systemUiSeen = false, placed = false))
        assertTrue(WidgetInstallPromptPolicy.pinLooksBlocked("xiaomi", systemUiSeen = false, placed = false))
        // The launcher's sheet showed up, or the widget landed: not blocked.
        assertFalse(WidgetInstallPromptPolicy.pinLooksBlocked("Xiaomi", systemUiSeen = true, placed = false))
        assertFalse(WidgetInstallPromptPolicy.pinLooksBlocked("Xiaomi", systemUiSeen = false, placed = true))
        // Other phones never get the Xiaomi permission hint.
        assertFalse(WidgetInstallPromptPolicy.pinLooksBlocked("Google", systemUiSeen = false, placed = false))
        assertFalse(WidgetInstallPromptPolicy.pinLooksBlocked("samsung", systemUiSeen = false, placed = false))
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
