package com.pomp.hskai.feature.onboarding

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.io.IOException

private val Context.guestLiDataStore by preferencesDataStore(name = "pomp_guest_li")
private val draftKey = stringPreferencesKey("choices")
private const val DRAFT_TTL_MS = 30 * 60_000L

@Serializable
internal data class GuestLiDraft(
    val track: String,
    val level: String,
    val goals: List<String>,
    val minutes: Int,
    val focus: String,
    val streak: Int,
    val savedAt: Long,
    val armed: Boolean = false,
) {
    fun validAt(now: Long): Boolean =
        savedAt > 0 && now - savedAt in 0..DRAFT_TTL_MS &&
            ((track == "hsk20" && level in setOf("beginner", "hsk1", "hsk2", "hsk3", "hsk4")) ||
                (track == "hsk30" && level in setOf("nhsk1", "nhsk2", "nhsk3"))) &&
            goals.isNotEmpty() && goals.distinct().size == goals.size &&
            goals.all { it in setOf("hsk_exam", "study_china", "work_china", "daily_communication", "travel") } &&
            minutes in setOf(5, 10, 15, 20, 30) && streak in setOf(7, 14, 30, 50) &&
            focus in setOf("speaking", "listening", "vocabulary", "grammar", "none")

    fun applyTo(state: OnboardingUiState): OnboardingUiState = state.copy(
        selectedTrack = track, selectedLevel = level, selectedGoal = goals.first(),
        selectedGoals = goals, dailyMinutes = minutes, preferredFocus = focus, streakTargetDays = streak,
    )

    companion object {
        fun from(state: OnboardingUiState, now: Long = System.currentTimeMillis()) = GuestLiDraft(
            state.selectedTrack, state.selectedLevel, state.selectedGoals, state.dailyMinutes,
            state.preferredFocus, state.streakTargetDays, now,
        )
    }
}

/** Anonymous choices only; no provider, account identifier, token or entitlement is persisted. */
internal class GuestLiDraftStore(context: Context) {
    private val store = context.applicationContext.guestLiDataStore
    private fun decode(value: String?): GuestLiDraft? = value?.let {
        runCatching { Json.decodeFromString<GuestLiDraft>(it) }.getOrNull()
            ?.takeIf { draft -> draft.validAt(System.currentTimeMillis()) }
    }

    suspend fun read(): GuestLiDraft? = try {
        decode(store.data.first()[draftKey])
    } catch (_: IOException) { null }

    suspend fun save(draft: GuestLiDraft) {
        store.edit { it[draftKey] = Json.encodeToString(draft.copy(armed = false)) }
    }

    suspend fun arm(): Boolean {
        var armed = false
        store.edit {
            val draft = decode(it[draftKey]) ?: return@edit
            it[draftKey] = Json.encodeToString(draft.copy(armed = true))
            armed = true
        }
        return armed
    }

    suspend fun clear() { store.edit { it.remove(draftKey) } }

    /** Transfer only once, after bearer status; it cannot leak to another session. */
    suspend fun takeArmed(): GuestLiDraft? {
        var claimed: GuestLiDraft? = null
        store.edit {
            claimed = decode(it[draftKey])?.takeIf { draft -> draft.armed }
            it.remove(draftKey)
        }
        return claimed
    }
}
