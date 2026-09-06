package com.pomp.hskai.feature.foundation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.audio.LessonAudioPlayer
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.repository.CourseRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

internal data class FoundationExample(
    val zh: String,
    val pinyin: String,
    val translation: String,
)

internal data class FoundationObjective(
    val id: String,
    val label: String,
)

internal data class FoundationCard(
    val type: String,
    val id: String,
    val title: String,
    val text: String,
    val prompt: String,
    val audioText: String,
    val example: FoundationExample?,
    val examples: List<FoundationExample>,
    val options: List<String>,
    val correctIndex: Int?,
    val tokens: List<String>,
    val answerTokens: List<String>,
    val explanation: String,
    val objectiveId: String?,
    val optional: Boolean,
    val objectives: List<FoundationObjective>,
)

internal data class FoundationUiState(
    val loading: Boolean = true,
    val required: Boolean = false,
    val cards: List<FoundationCard> = emptyList(),
    val requiredObjectives: Set<String> = emptySet(),
    val masteredObjectives: Set<String> = emptySet(),
    val cardIndex: Int = 0,
    val selectedChoice: Int? = null,
    val builderTokens: List<String> = emptyList(),
    val answerCorrect: Boolean? = null,
    val speakingBonus: Boolean = false,
    val saving: Boolean = false,
    val completed: Boolean = false,
    val error: ApiError? = null,
) {
    val currentCard: FoundationCard? get() = cards.getOrNull(cardIndex)
    val progress: Float get() = if (cards.isEmpty()) 0f else ((cardIndex + 1f) / cards.size).coerceIn(0f, 1f)
    val canFinish: Boolean get() = requiredObjectives.all(masteredObjectives::contains)
}

class FoundationViewModel(
    private val repository: CourseRepository,
    private val audioPlayer: LessonAudioPlayer,
    private val language: AppLanguage,
) : ViewModel() {

    private val _state = MutableStateFlow(FoundationUiState())
    internal val state: StateFlow<FoundationUiState> = _state.asStateFlow()
    private var completionEventId = CourseRepository.newFoundationEventId()

    init {
        load()
    }

    fun load() {
        _state.value = FoundationUiState(loading = true)
        viewModelScope.launch {
            when (val result = repository.foundation()) {
                is ApiResult.Failure -> _state.update { it.copy(loading = false, error = result.error) }
                is ApiResult.Success -> {
                    val projected = runCatching {
                        result.value.foundation.cards.map { projectCard(it, language.backendCode) }
                    }.getOrNull()
                    if (projected.isNullOrEmpty()) {
                        _state.update { it.copy(loading = false, error = ApiError.Unknown) }
                    } else {
                        completionEventId = CourseRepository.newFoundationEventId()
                        _state.value = FoundationUiState(
                            loading = false,
                            required = result.value.status.required && !result.value.status.completed,
                            cards = projected,
                            requiredObjectives = result.value.foundation.requiredObjectives.toSet(),
                        )
                    }
                }
            }
        }
    }

    fun choose(index: Int) {
        val card = _state.value.currentCard ?: return
        if (card.type !in setOf("choice", "listen_choice") || index !in card.options.indices) return
        val correct = card.correctIndex == index
        _state.update { state ->
            state.copy(
                selectedChoice = index,
                answerCorrect = correct,
                masteredObjectives = if (correct && !card.objectiveId.isNullOrBlank()) {
                    state.masteredObjectives + card.objectiveId
                } else state.masteredObjectives,
            )
        }
    }

    fun addBuilderToken(token: String) {
        val card = _state.value.currentCard ?: return
        if (card.type != "builder" || token !in card.tokens) return
        val selected = _state.value.builderTokens
        if (selected.size >= card.answerTokens.size) return
        _state.update { it.copy(builderTokens = selected + token, answerCorrect = null) }
    }

    fun undoBuilderToken() {
        _state.update { state ->
            state.copy(builderTokens = state.builderTokens.dropLast(1), answerCorrect = null)
        }
    }

    fun submitBuilder() {
        val state = _state.value
        val card = state.currentCard ?: return
        if (card.type != "builder" || state.builderTokens.size != card.answerTokens.size) return
        val correct = state.builderTokens == card.answerTokens
        _state.update {
            it.copy(
                answerCorrect = correct,
                masteredObjectives = if (correct && !card.objectiveId.isNullOrBlank()) {
                    it.masteredObjectives + card.objectiveId
                } else it.masteredObjectives,
            )
        }
    }

    fun markSpoken() {
        val card = _state.value.currentCard ?: return
        if (card.type != "speak") return
        _state.update { it.copy(speakingBonus = true, answerCorrect = true) }
    }

    fun playAudio() {
        val text = _state.value.currentCard?.audioText?.trim().orEmpty()
        if (text.isEmpty()) return
        viewModelScope.launch {
            when (val audio = repository.ttsAudio(text)) {
                is ApiResult.Success -> runCatching { audioPlayer.play(audio.value) }
                is ApiResult.Failure -> Unit
            }
        }
    }

    fun advance() {
        val state = _state.value
        val card = state.currentCard ?: return
        if (card.type in setOf("choice", "listen_choice", "builder") && state.answerCorrect != true) return
        if (card.type == "result") {
            if (state.canFinish) finish()
            return
        }
        val next = (state.cardIndex + 1).coerceAtMost(state.cards.lastIndex)
        _state.update {
            it.copy(
                cardIndex = next,
                selectedChoice = null,
                builderTokens = emptyList(),
                answerCorrect = null,
                error = null,
            )
        }
    }

    fun retrySave() = finish()

    private fun finish() {
        val state = _state.value
        if (!state.canFinish || state.saving) return
        _state.update { it.copy(saving = true, error = null) }
        viewModelScope.launch {
            when (
                val result = repository.completeFoundation(
                    speakingBonus = _state.value.speakingBonus,
                    eventId = completionEventId,
                )
            ) {
                is ApiResult.Failure -> _state.update {
                    it.copy(saving = false, error = result.error)
                }
                is ApiResult.Success -> _state.update {
                    it.copy(
                        saving = false,
                        completed = result.value.ok && result.value.foundation.completed,
                        required = if (result.value.foundation.completed) false else it.required,
                        error = if (result.value.ok) null else ApiError.Unknown,
                    )
                }
            }
        }
    }

    override fun onCleared() {
        audioPlayer.release()
        super.onCleared()
    }

    class Factory(
        private val repository: CourseRepository,
        private val audioPlayer: LessonAudioPlayer,
        private val language: AppLanguage,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            FoundationViewModel(repository, audioPlayer, language) as T
    }
}

private fun projectCard(raw: JsonObject, language: String): FoundationCard = FoundationCard(
    type = raw.string("type"),
    id = raw.string("card_id"),
    title = raw.localized("title", language),
    text = raw.localized("text", language),
    prompt = raw.localized("prompt", language),
    audioText = raw.string("audio_text"),
    example = raw["example"]?.asExample(language),
    examples = raw["examples"]?.jsonArrayOrEmpty()?.mapNotNull { it.asExample(language) }.orEmpty(),
    options = raw["options"]?.jsonArrayOrEmpty()?.map { it.localizedValue(language) }.orEmpty(),
    correctIndex = raw["correct_index"]?.jsonPrimitive?.intOrNull,
    tokens = raw["tokens"]?.jsonArrayOrEmpty()?.map { it.jsonPrimitive.content }.orEmpty(),
    answerTokens = raw["answer_tokens"]?.jsonArrayOrEmpty()?.map { it.jsonPrimitive.content }.orEmpty(),
    explanation = raw.localized("explanation", language),
    objectiveId = raw["objective_id"]?.jsonPrimitive?.contentOrNull,
    optional = raw["optional"]?.jsonPrimitive?.booleanOrNull == true,
    objectives = raw["objectives"]?.jsonArrayOrEmpty()?.mapNotNull { element ->
        val obj = element as? JsonObject ?: return@mapNotNull null
        FoundationObjective(
            id = obj.string("objective_id"),
            label = obj.localized("label", language),
        )
    }.orEmpty(),
)

private fun JsonObject.string(key: String): String =
    (this[key] as? JsonPrimitive)?.contentOrNull.orEmpty()

private fun JsonObject.localized(key: String, language: String): String =
    this[key]?.localizedValue(language).orEmpty()

private fun JsonElement.localizedValue(language: String): String = when (this) {
    is JsonPrimitive -> contentOrNull.orEmpty()
    is JsonObject -> {
        val fallback = if (language == "ru") "uz" else "ru"
        string(language).ifBlank { string(fallback) }.ifBlank { string("uz") }
    }
    else -> ""
}

private fun JsonElement.asExample(language: String): FoundationExample? {
    val obj = this as? JsonObject ?: return null
    val zh = obj.string("zh")
    val pinyin = obj.string("pinyin")
    val translation = obj.localized("translation", language)
    if (zh.isBlank() && pinyin.isBlank() && translation.isBlank()) return null
    return FoundationExample(zh, pinyin, translation)
}

private fun JsonElement.jsonArrayOrEmpty(): JsonArray = this as? JsonArray ?: JsonArray(emptyList())
