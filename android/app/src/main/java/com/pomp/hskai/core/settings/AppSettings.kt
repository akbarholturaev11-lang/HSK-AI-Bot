package com.pomp.hskai.core.settings

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
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

class AppSettings(context: Context) {

    private val appContext = context.applicationContext

    val pinyinVisibility: Flow<PinyinVisibility> = appContext.settingsDataStore.data
        .map { PinyinVisibility.fromWireValue(it[PINYIN_KEY]) }

    suspend fun setPinyinVisibility(value: PinyinVisibility) {
        appContext.settingsDataStore.edit { it[PINYIN_KEY] = value.wireValue }
    }

    private companion object {
        val PINYIN_KEY = stringPreferencesKey("pinyin_visibility")
    }
}
