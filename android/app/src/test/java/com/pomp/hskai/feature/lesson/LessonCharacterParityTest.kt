package com.pomp.hskai.feature.lesson

import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.ChoiceKind
import com.pomp.hskai.domain.model.GrammarCard
import com.pomp.hskai.domain.model.MatchPairsCard
import com.pomp.hskai.domain.model.NewWordCard
import com.pomp.hskai.domain.model.PronunciationCard
import com.pomp.hskai.domain.model.ReverseBuilderCard
import com.pomp.hskai.domain.model.SentenceBuilderCard
import com.pomp.hskai.domain.model.UnsupportedCard
import org.junit.Assert.assertEquals
import org.junit.Test

class LessonCharacterParityTest {

    @Test
    fun card_roles_match_the_mini_app_cast() {
        assertEquals(
            LessonCharacter.Crane,
            lessonCharacterFor(
                GrammarCard(
                    materialRef = "grammar",
                    number = 1,
                    title = "Grammar",
                    titleZh = "语法",
                    rule = "rule",
                    examples = emptyList(),
                ),
            ),
        )
        assertEquals(
            LessonCharacter.Monkey,
            lessonCharacterFor(
                SentenceBuilderCard(
                    materialRef = "builder",
                    promptSentence = "prompt",
                    tokens = listOf("我", "好"),
                    answerTokens = listOf("我", "好"),
                    explanation = "",
                ),
            ),
        )
        assertEquals(
            LessonCharacter.Monkey,
            lessonCharacterFor(
                ReverseBuilderCard(
                    materialRef = "reverse",
                    hanzi = "你好",
                    pinyin = "nǐ hǎo",
                    translation = "salom",
                    tokens = listOf("salom"),
                    answerTokens = listOf("salom"),
                    explanation = "",
                ),
            ),
        )
        assertEquals(
            LessonCharacter.Monkey,
            lessonCharacterFor(
                MatchPairsCard(
                    materialRef = "match",
                    pairs = listOf("你" to "sen"),
                    explanation = "",
                ),
            ),
        )
        assertEquals(
            LessonCharacter.Panda,
            lessonCharacterFor(
                ChoiceCard(
                    materialRef = "choice",
                    kind = ChoiceKind.MEANING,
                    title = "Choose",
                    prompt = "你",
                    options = listOf("sen", "men"),
                    correctIndex = 0,
                    explanation = "",
                ),
            ),
        )
        assertEquals(
            LessonCharacter.Crane,
            lessonCharacterFor(
                ChoiceCard(
                    materialRef = "gap",
                    kind = ChoiceKind.GAP_FILL,
                    title = "Fill",
                    prompt = "我____学生",
                    options = listOf("是", "有"),
                    correctIndex = 0,
                    explanation = "",
                ),
            ),
        )
        assertEquals(
            LessonCharacter.Monkey,
            lessonCharacterFor(
                ChoiceCard(
                    materialRef = "dialog",
                    kind = ChoiceKind.DIALOG_CLOZE,
                    title = "Dialog",
                    prompt = "你好",
                    options = listOf("你好", "再见"),
                    correctIndex = 0,
                    explanation = "",
                ),
            ),
        )
        assertEquals(
            LessonCharacter.Rabbit,
            lessonCharacterFor(
                ChoiceCard(
                    materialRef = "review",
                    kind = ChoiceKind.MEANING,
                    title = "Review",
                    prompt = "学",
                    options = listOf("o‘rganmoq", "yemoq"),
                    correctIndex = 0,
                    explanation = "",
                    reviewOrigin = "previous",
                ),
            ),
        )
        assertEquals(
            LessonCharacter.Panda,
            lessonCharacterFor(
                NewWordCard(
                    materialRef = "word",
                    number = 1,
                    hanzi = "胖",
                    pinyin = "pàng",
                    partOfSpeech = "adj.",
                    meaning = "semiz",
                ),
            ),
        )
        assertEquals(
            LessonCharacter.Panda,
            lessonCharacterFor(
                PronunciationCard(
                    materialRef = "pronunciation",
                    phrase = "胖",
                    pinyin = "pàng",
                    translation = "semiz",
                ),
            ),
        )
        assertEquals(
            LessonCharacter.Panda,
            lessonCharacterFor(
                UnsupportedCard(
                    materialRef = "future",
                    rawType = "future_card",
                ),
            ),
        )
    }

    @Test
    fun feedback_reactions_match_the_mini_app_heart_rules() {
        assertEquals(LessonCharacterReaction.Jump, lessonReactionFor(correct = true, hearts = 5, streak = 3))
        assertEquals(LessonCharacterReaction.Celebrate, lessonReactionFor(correct = true, hearts = 5, streak = 4))
        assertEquals(LessonCharacterReaction.Wrong, lessonReactionFor(correct = false, hearts = 4, streak = 0))
        assertEquals(LessonCharacterReaction.OneHeart, lessonReactionFor(correct = false, hearts = 1, streak = 0))
        assertEquals(LessonCharacterReaction.Wrong, lessonReactionFor(correct = false, hearts = 0, streak = 0))
    }
}
