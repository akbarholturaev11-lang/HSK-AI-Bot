package com.pomp.hskai.feature.dictionary

/**
 * The entries a learner opened from a search, newest first.
 *
 * Opening one again moves it back to the top rather than listing it twice,
 * and only the last [LIMIT] are kept: the list sits above the dictionary
 * while the search box is focused, and a long one would push the words out.
 */
internal object DictionaryHistory {
    const val LIMIT = 5

    fun record(history: List<String>, hanzi: String): List<String> {
        val word = hanzi.trim()
        if (word.isEmpty()) return history
        return (listOf(word) + history.filter { it != word }).take(LIMIT)
    }
}
