package com.pomp.hskai.feature.practice

import com.pomp.hskai.data.api.DrillWordDto
import com.pomp.hskai.data.repository.DictionaryWord

/**
 * One recognition question: the learner reads the pinyin and the meaning and
 * picks the character out of four.
 */
data class DrillQuestion(
    val hanzi: String,
    val pinyin: String,
    val meaning: String,
    val options: List<String>,
    /** True when the server sent this word because its review came due. */
    val isReview: Boolean,
) {
    fun isCorrect(option: String): Boolean = option == hanzi
}

/**
 * Builds the Mini App's recognition drill on the device.
 *
 * The division of labour is the Mini App's: the server names the characters
 * that are due (`/practice/words`), and everything the learner reads — the
 * pinyin, the meaning, the three distractors — comes from the client's own
 * dictionary. That is why switching language never changes the answer.
 *
 * Single-character words only: the distractors have to look like plausible
 * neighbours of the target, and a mixed pool of one- and two-character words
 * gives the answer away by shape alone.
 */
object WordDrill {

    const val QUESTIONS_PER_DRILL = 10
    private const val OPTIONS_PER_QUESTION = 4

    fun pool(dictionary: List<DictionaryWord>): List<DictionaryWord> =
        dictionary.filter { it.hanzi.codePointCount(0, it.hanzi.length) == 1 }

    /**
     * @param targets what the server asked for, in its order.
     * @param pool every single-character word the client can draw on.
     * @param shuffle seam for the tests; production passes a real shuffle.
     */
    fun build(
        targets: List<DrillWordDto>,
        pool: List<DictionaryWord>,
        limit: Int = QUESTIONS_PER_DRILL,
        shuffle: (List<DictionaryWord>) -> List<DictionaryWord> = { it.shuffled() },
    ): List<DrillQuestion> {
        val byHanzi = pool.associateBy { it.hanzi }
        val picks = mutableListOf<Pair<DictionaryWord, Boolean>>()
        val used = mutableSetOf<String>()

        targets.forEach { target ->
            val word = byHanzi[target.hanzi] ?: return@forEach
            if (used.add(word.hanzi)) picks += word to (target.kind == "review")
        }
        // An empty or short server list is not a failure: the drill fills up
        // from the dictionary and still runs.
        if (picks.size < limit) {
            shuffle(pool.filter { it.hanzi !in used }).forEach { word ->
                if (picks.size >= limit) return@forEach
                if (used.add(word.hanzi)) picks += word to false
            }
        }

        return picks.take(limit).mapNotNull { (word, isReview) ->
            val distractors = shuffle(pool.filter { it.hanzi != word.hanzi })
                .take(OPTIONS_PER_QUESTION - 1)
            // Too few neighbours drops this one question, never the drill.
            if (distractors.size < OPTIONS_PER_QUESTION - 1) return@mapNotNull null
            DrillQuestion(
                hanzi = word.hanzi,
                pinyin = word.pinyin,
                meaning = word.meaning,
                options = shuffle(distractors + word).map { it.hanzi },
                isReview = isReview,
            )
        }
    }
}
