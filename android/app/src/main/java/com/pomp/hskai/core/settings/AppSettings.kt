package com.pomp.hskai.core.settings

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
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

/** Android-only appearance preference: the current white theme, Cosmos Blue dark, or system. */
enum class AppThemeMode(val wireValue: String) {
    LIGHT("light"),
    DARK("dark"),
    SYSTEM("system"),
    ;

    companion object {
        val DEFAULT = LIGHT

        fun fromWireValue(value: String?): AppThemeMode =
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

    /**
     * What the picker offers, copied from the Mini App's own list
     * (`course-v3.html`: `opts=[20,30,40,50,80]`). They have to match: a goal
     * chosen in one product must be selectable in the other, and 40 used not
     * to be offered here at all.
     */
    val CHOICES = listOf(20, 30, 40, 50, 80)

    /** The server's bounds (`miniapp_preferences.py`: ge=10, le=500). */
    private val RANGE = 10..500

    /**
     * Accepts anything the server would, not only what the picker offers.
     *
     * This used to be an allowlist, which silently rewrote a stored goal the
     * list did not contain — a learner who chose 40 in the Mini App had it
     * turned into 50 on the way in, which is precisely how one account showed
     * two different goals.
     */
    fun sanitize(value: Int?): Int = value?.takeIf { it in RANGE } ?: DEFAULT
}

class AppSettings(context: Context) : LessonResumeStore {

    private val appContext = context.applicationContext

    val pinyinVisibility: Flow<PinyinVisibility> = appContext.settingsDataStore.data
        .map { PinyinVisibility.fromWireValue(it[PINYIN_KEY]) }

    val themeMode: Flow<AppThemeMode> = appContext.settingsDataStore.data
        .map { AppThemeMode.fromWireValue(it[THEME_MODE_KEY]) }

    val dailyGoal: Flow<Int> = appContext.settingsDataStore.data
        .map { DailyGoal.sanitize(it[DAILY_GOAL_KEY]) }

    /**
     * Mini App parity for `hsk_v3_setup_asked`.
     *
     * Once the post-lesson personalization sheet is shown, the same pending
     * setup must not interrupt the learner again for 24 hours if they dismiss
     * it or leave the app before answering.
     */
    val lastStudySetupAskedAtMillis: Flow<Long?> = appContext.settingsDataStore.data
        .map { it[LAST_STUDY_SETUP_ASKED_AT_KEY] }

    /**
     * The server-local date this device last posted a study reminder on.
     *
     * It is the server's date, not the device's, so the "one reminder a day"
     * rule agrees with the day the backend counts progress in.
     */
    val lastReminderDate: Flow<String?> = appContext.settingsDataStore.data
        .map { it[LAST_REMINDER_DATE_KEY] }

    /**
     * AI Voice call settings, mirroring the Mini App's `hsk_voice_sub` and
     * `hsk_voice_rate`: whether the pinyin and translation are shown under a
     * reply, and whether the partner speaks slowly.
     */
    val voiceSubtitles: Flow<Boolean> = appContext.settingsDataStore.data
        .map { it[VOICE_SUBTITLES_KEY] ?: true }

    val voiceSlowSpeech: Flow<Boolean> = appContext.settingsDataStore.data
        .map { it[VOICE_SLOW_SPEECH_KEY] ?: false }

    /**
     * Whether the one-time notification primer has been answered.
     *
     * Android grants notifications once for the whole app, not per kind, and
     * it only ever shows its dialog twice. So this is asked once, at the end
     * of onboarding, and never again — whatever the answer was. A learner who
     * said no keeps the update card and the banner; nothing else changes.
     */
    val notificationPrimerSeen: Flow<Boolean> = appContext.settingsDataStore.data
        .map { it[NOTIFICATION_PRIMER_SEEN_KEY] ?: false }

    suspend fun setNotificationPrimerSeen() {
        appContext.settingsDataStore.edit { it[NOTIFICATION_PRIMER_SEEN_KEY] = true }
    }

    suspend fun setVoiceSubtitles(value: Boolean) {
        appContext.settingsDataStore.edit { it[VOICE_SUBTITLES_KEY] = value }
    }

    suspend fun setVoiceSlowSpeech(value: Boolean) {
        appContext.settingsDataStore.edit { it[VOICE_SLOW_SPEECH_KEY] = value }
    }

    suspend fun setPinyinVisibility(value: PinyinVisibility) {
        appContext.settingsDataStore.edit { it[PINYIN_KEY] = value.wireValue }
    }

    suspend fun setThemeMode(value: AppThemeMode) {
        appContext.settingsDataStore.edit { it[THEME_MODE_KEY] = value.wireValue }
    }

    suspend fun setDailyGoal(value: Int) {
        appContext.settingsDataStore.edit { it[DAILY_GOAL_KEY] = DailyGoal.sanitize(value) }
    }

    suspend fun setLastStudySetupAskedAtMillis(value: Long) {
        appContext.settingsDataStore.edit { it[LAST_STUDY_SETUP_ASKED_AT_KEY] = value }
    }

    suspend fun setLastReminderDate(value: String) {
        appContext.settingsDataStore.edit { it[LAST_REMINDER_DATE_KEY] = value }
    }

    suspend fun dictionaryLastCheckedAtMillis(language: String): Long? =
        appContext.settingsDataStore.data.first()[dictionaryCheckedAtKey(language)]

    suspend fun dictionaryLastCheckedClientVersion(language: String): Int? =
        appContext.settingsDataStore.data.first()[dictionaryCheckedVersionKey(language)]

    suspend fun setDictionaryLastChecked(
        language: String,
        checkedAtMillis: Long,
        clientVersionCode: Int,
    ) {
        appContext.settingsDataStore.edit {
            it[dictionaryCheckedAtKey(language)] = checkedAtMillis
            it[dictionaryCheckedVersionKey(language)] = clientVersionCode
        }
    }

    /**
     * Mini App `hsk_v3_lesson_resume:v2:<level>:<order>` — the card the learner
     * stopped on. Leaving a lesson halfway and starting it again from the top
     * is the fastest way to lose someone, so the position is kept for a week
     * and then forgotten, exactly as the Mini App forgets it.
     */
    override suspend fun lessonResumeIndex(level: String, order: Int): Int {
        val prefs = appContext.settingsDataStore.data.first()
        val savedAt = prefs[resumeAtKey(level, order)] ?: return 0
        if (System.currentTimeMillis() - savedAt > LESSON_RESUME_TTL_MILLIS) return 0
        return (prefs[resumeIndexKey(level, order)] ?: 0).coerceAtLeast(0)
    }

    override suspend fun setLessonResumeIndex(level: String, order: Int, index: Int) {
        appContext.settingsDataStore.edit {
            it[resumeIndexKey(level, order)] = index.coerceAtLeast(0)
            it[resumeAtKey(level, order)] = System.currentTimeMillis()
        }
    }

    override suspend fun clearLessonResume(level: String, order: Int) {
        appContext.settingsDataStore.edit {
            it.remove(resumeIndexKey(level, order))
            it.remove(resumeAtKey(level, order))
        }
    }

    private fun dictionaryCheckedAtKey(language: String) =
        longPreferencesKey("dictionary_checked_at:v1:${language.lowercase()}")

    private fun dictionaryCheckedVersionKey(language: String) =
        intPreferencesKey("dictionary_checked_version:v1:${language.lowercase()}")

    private fun resumeIndexKey(level: String, order: Int) =
        intPreferencesKey("lesson_resume_index:v2:${level.lowercase()}:$order")

    private fun resumeAtKey(level: String, order: Int) =
        longPreferencesKey("lesson_resume_at:v2:${level.lowercase()}:$order")

    private companion object {
        /** The Mini App's `LESSON_RESUME_TTL_MS`. */
        const val LESSON_RESUME_TTL_MILLIS = 7L * 24 * 60 * 60 * 1000

        val PINYIN_KEY = stringPreferencesKey("pinyin_visibility")
        val THEME_MODE_KEY = stringPreferencesKey("theme_mode")
        val DAILY_GOAL_KEY = intPreferencesKey("daily_goal_xp")
        val LAST_STUDY_SETUP_ASKED_AT_KEY = longPreferencesKey("hsk_v3_setup_asked")
        val LAST_REMINDER_DATE_KEY = stringPreferencesKey("last_reminder_date")
        val VOICE_SUBTITLES_KEY = booleanPreferencesKey("hsk_voice_sub")
        val VOICE_SLOW_SPEECH_KEY = booleanPreferencesKey("hsk_voice_rate_slow")
        val NOTIFICATION_PRIMER_SEEN_KEY = booleanPreferencesKey("notification_primer_seen")
    }
}
