package com.pomp.hskai.core.settings

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.settingsDataStore: DataStore<Preferences> by preferencesDataStore(
    name = "pomp_settings",
)

/**
 * How much pinyin the learner wants to see, mirroring the Course v3 setting
 * stored as `hsk_v3_pinyin` in the Mini App.
 *
 * The wire values are kept identical so the preference means the same thing on
 * every client.
 */
enum class PinyinVisibility(val wireValue: String) {
    /** Everywhere. */
    ALL("all"),

    /** Only on new-word cards; hidden in questions, grammar and dialogue. */
    NEW_WORDS_ONLY("new"),

    /** Nowhere. */
    OFF("off"),
    ;

    companion object {
        val DEFAULT = ALL

        fun fromWireValue(value: String?): PinyinVisibility =
            entries.firstOrNull { it.wireValue == value?.trim()?.lowercase() } ?: DEFAULT
    }
}

/**
 * The learner's daily XP target, mirroring the Mini App's `dailyGoal`.
 *
 * It is a personal display preference, not an entitlement: the server neither
 * stores nor enforces it, exactly as in the Mini App, so it lives on the
 * device and is clamped to the same four choices the Mini App offers.
 */
object DailyGoal {
    const val DEFAULT = 50
    val CHOICES = listOf(10, 20, 30, 50)

    fun sanitize(value: Int?): Int = value?.takeIf { it in CHOICES } ?: DEFAULT
}

class AppSettings(context: Context) {

    private val appContext = context.applicationContext

    val pinyinVisibility: Flow<PinyinVisibility> = appContext.settingsDataStore.data
        .map { PinyinVisibility.fromWireValue(it[PINYIN_KEY]) }

    val dailyGoal: Flow<Int> = appContext.settingsDataStore.data
        .map { DailyGoal.sanitize(it[DAILY_GOAL_KEY]) }

    /**
     * The server-local date this device last posted a study reminder on.
     *
     * It is the server's date, not the device's, so the "one reminder a day"
     * rule agrees with the day the backend counts progress in.
     */
    val lastReminderDate: Flow<String?> = appContext.settingsDataStore.data
        .map { it[LAST_REMINDER_DATE_KEY] }

    suspend fun setPinyinVisibility(value: PinyinVisibility) {
        appContext.settingsDataStore.edit { it[PINYIN_KEY] = value.wireValue }
    }

    suspend fun setDailyGoal(value: Int) {
        appContext.settingsDataStore.edit { it[DAILY_GOAL_KEY] = DailyGoal.sanitize(value) }
    }

    suspend fun setLastReminderDate(value: String) {
        appContext.settingsDataStore.edit { it[LAST_REMINDER_DATE_KEY] = value }
    }

    private companion object {
        val PINYIN_KEY = stringPreferencesKey("pinyin_visibility")
        val DAILY_GOAL_KEY = intPreferencesKey("daily_goal_xp")
        val LAST_REMINDER_DATE_KEY = stringPreferencesKey("last_reminder_date")
    }
}
