package com.pomp.hskai.feature.hint

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.data.api.AndroidHintDto
import com.pomp.hskai.data.repository.FeatureRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * The explanation blocks currently on screen, and closing them.
 *
 * Held apart from the course map's own ViewModel for one reason: the blocks
 * belong to every section, not to the course path, and the map is only where
 * they arrive. A closed block has to disappear from the practice tab too.
 *
 * The rules stay on the server. This decides nothing about who sees what —
 * it holds what arrived, and remembers what was closed in this session so the
 * block goes at once rather than after a round trip.
 */
class HintsViewModel(
    /**
     * Records the dismissal on the server.
     *
     * Narrower than the repository on purpose: this is the only call the
     * class makes, and taking just it keeps the rule above testable without
     * standing up the whole feature API.
     */
    private val dismissOnServer: suspend (String) -> Unit,
) : ViewModel() {

    private val _hints = MutableStateFlow<List<AndroidHintDto>>(emptyList())
    val hints: StateFlow<List<AndroidHintDto>> = _hints.asStateFlow()

    private val closedHere = mutableSetOf<String>()

    /**
     * Takes the blocks that came with the latest map.
     *
     * Anything closed in this session stays closed even if the server sends
     * it again — the write may still be in flight, and a block reappearing
     * after the X was pressed reads as the button not having worked.
     */
    fun onMapLoaded(hints: List<AndroidHintDto>) {
        _hints.value = hints.filter { it.key.isNotBlank() && it.key !in closedHere }
    }

    /**
     * Closes one block.
     *
     * It leaves the screen immediately and the write follows. A failed write
     * is not shown: the learner asked for the block to go, and it has gone —
     * the worst case is that it returns on a later launch.
     */
    fun dismiss(key: String) {
        if (key.isBlank() || !closedHere.add(key)) return
        _hints.update { current -> current.filterNot { it.key == key } }
        viewModelScope.launch { dismissOnServer(key) }
    }

    class Factory(
        private val repository: FeatureRepository,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            HintsViewModel({ key -> repository.dismissHint(key) }) as T
    }
}
