package com.pomp.hskai.feature.lesson

import androidx.compose.foundation.background
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.core.settings.PinyinVisibility
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.ChoiceKind
import com.pomp.hskai.domain.model.GrammarCard
import com.pomp.hskai.domain.model.MatchPairsCard
import com.pomp.hskai.domain.model.NewWordCard
import com.pomp.hskai.domain.model.PronunciationCard
import com.pomp.hskai.domain.model.ReverseBuilderCard
import com.pomp.hskai.domain.model.SentenceBuilderCard
import com.pomp.hskai.domain.model.UnsupportedCard

@Composable
internal fun CardTitle(text: String) {
    if (text.isBlank()) return
    Text(text = text, style = MaterialTheme.typography.labelLarge, color = PompColors.CinnabarDark)
    Spacer(Modifier.height(8.dp))
}

@Composable
internal fun CardPrompt(text: String) {
    if (text.isBlank()) return
    Text(text = text, style = MaterialTheme.typography.titleLarge, color = PompColors.Ink)
    Spacer(Modifier.height(16.dp))
}

@Composable
fun NewWordCardView(card: NewWordCard, pinyin: PinyinVisibility) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(text = stringResource(R.string.lesson_new_word), style = MaterialTheme.typography.labelLarge, color = PompColors.Gold)
        Spacer(Modifier.height(20.dp))
        Text(text = card.hanzi, style = PompTextStyles.hanziLarge, color = PompColors.Ink)
        if (pinyin != PinyinVisibility.OFF) {
            Text(text = card.pinyin, style = PompTextStyles.pinyin, color = PompColors.CinnabarDark)
        }
        Spacer(Modifier.height(12.dp))
        Text(text = card.meaning, style = MaterialTheme.typography.titleMedium, color = PompColors.Ink, textAlign = TextAlign.Center)
        if (card.partOfSpeech.isNotBlank()) {
            Text(text = card.partOfSpeech, style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
        }
    }
}

@Composable
fun GrammarCardView(card: GrammarCard, pinyin: PinyinVisibility) {
    Column {
        CardTitle(card.titleZh.ifBlank { stringResource(R.string.lesson_grammar) })
        Text(text = card.title, style = MaterialTheme.typography.titleLarge, color = PompColors.Ink)
        Spacer(Modifier.height(12.dp))
        Text(text = card.rule, style = MaterialTheme.typography.bodyLarge, color = PompColors.InkSecondary)
        if (card.examples.isNotEmpty()) {
            Spacer(Modifier.height(16.dp))
            card.examples.forEach { example ->
                Surface(
                    color = PompColors.PaperRaised,
                    shape = RoundedCornerShape(12.dp),
                    border = BorderStroke(1.dp, PompColors.Divider),
                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(text = example.hanzi, style = PompTextStyles.hanziMedium, color = PompColors.Ink)
                        if (pinyin == PinyinVisibility.ALL) {
                            Text(text = example.pinyin, style = PompTextStyles.pinyin, color = PompColors.InkSecondary)
                        }
                        Text(text = example.translation, style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
                    }
                }
            }
        }
    }
}

@Composable
fun PronunciationCardView(
    card: PronunciationCard,
    pinyin: PinyinVisibility,
    isAudioLoading: Boolean,
    onPlayAudio: (String) -> Unit,
    onSkip: () -> Unit,
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        CardTitle(stringResource(R.string.lesson_repeat_after_teacher))
        Text(text = card.phrase, style = PompTextStyles.hanziMedium, color = PompColors.Ink, textAlign = TextAlign.Center)
        if (pinyin == PinyinVisibility.ALL) {
            Text(text = card.pinyin, style = PompTextStyles.pinyin, color = PompColors.InkSecondary)
        }
        Spacer(Modifier.height(8.dp))
        Text(text = card.translation, style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary, textAlign = TextAlign.Center)
        Spacer(Modifier.height(18.dp))
        AudioAction(isLoading = isAudioLoading, onClick = { onPlayAudio(card.phrase) })
        Spacer(Modifier.height(24.dp))
        SecondaryAction(text = stringResource(R.string.lesson_cannot_speak_now), onClick = onSkip)
    }
}

@Composable
fun ChoiceCardView(
    card: ChoiceCard,
    pinyin: PinyinVisibility,
    selectedIndex: Int?,
    isAnswered: Boolean,
    isAudioLoading: Boolean,
    onPlayAudio: (String) -> Unit,
    onSelect: (Int) -> Unit,
) {
    Column {
        CardTitle(card.title)
        when (card.kind) {
            ChoiceKind.LISTENING -> {
                Text(text = stringResource(R.string.lesson_listen_and_choose), style = MaterialTheme.typography.titleLarge, color = PompColors.Ink)
                val audioPinyin = card.audioPinyin
                if (pinyin == PinyinVisibility.ALL && !audioPinyin.isNullOrBlank()) {
                    Spacer(Modifier.height(6.dp))
                    Text(text = audioPinyin, style = PompTextStyles.pinyin, color = PompColors.InkSecondary)
                }
                Spacer(Modifier.height(12.dp))
                AudioAction(isLoading = isAudioLoading, onClick = { onPlayAudio(card.audioText.orEmpty()) })
                Spacer(Modifier.height(16.dp))
            }
            ChoiceKind.GAP_FILL -> {
                CardPrompt(card.prompt)
                card.sentence?.takeIf { it.isNotBlank() }?.let { sentence ->
                    Text(text = sentence, style = PompTextStyles.hanziMedium, color = PompColors.Ink)
                    Spacer(Modifier.height(16.dp))
                }
            }
            ChoiceKind.DIALOG_CLOZE -> {
                CardPrompt(card.prompt.ifBlank { card.title })
                card.lines.forEach { line ->
                    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                        Text(text = "${line.speaker}: ", style = MaterialTheme.typography.bodyLarge, color = PompColors.InkSecondary)
                        Text(
                            text = if (line.isBlank) "＿＿＿" else line.text,
                            style = MaterialTheme.typography.bodyLarge,
                            color = if (line.isBlank) PompColors.CinnabarDark else PompColors.Ink,
                        )
                    }
                }
                Spacer(Modifier.height(16.dp))
            }
            else -> CardPrompt(card.prompt)
        }

        card.options.forEachIndexed { index, option ->
            OptionRow(
                text = option,
                state = optionState(index, card.correctIndex, selectedIndex, isAnswered),
                enabled = !isAnswered,
                onClick = { onSelect(index) },
                key = "ABCD".getOrNull(index)?.toString().orEmpty(),
            )
        }
    }
}

@Composable
private fun AudioAction(isLoading: Boolean, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        enabled = !isLoading,
        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
        shape = RoundedCornerShape(14.dp),
    ) {
        if (isLoading) {
            CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp, color = PompColors.Cinnabar)
            Spacer(Modifier.size(10.dp))
        }
        Text(
            text = stringResource(if (isLoading) R.string.lesson_audio_loading else R.string.lesson_play_audio),
            style = MaterialTheme.typography.labelLarge,
            color = PompColors.CinnabarDark,
        )
    }
}

internal enum class OptionState { IDLE, SELECTED_WRONG, CORRECT }

private fun optionState(index: Int, correctIndex: Int, selectedIndex: Int?, isAnswered: Boolean): OptionState = when {
    !isAnswered -> OptionState.IDLE
    index == correctIndex -> OptionState.CORRECT
    index == selectedIndex -> OptionState.SELECTED_WRONG
    else -> OptionState.IDLE
}

@Composable
private fun OptionRow(
    text: String,
    state: OptionState,
    enabled: Boolean,
    onClick: () -> Unit,
    key: String = "",
) {
    val border = when (state) {
        OptionState.IDLE -> PompColors.Divider
        OptionState.CORRECT -> PompColors.Jade
        OptionState.SELECTED_WRONG -> PompColors.Flame
    }
    val background = when (state) {
        OptionState.IDLE -> PompColors.PaperRaised
        OptionState.CORRECT -> PompColors.JadeSoft
        OptionState.SELECTED_WRONG -> PompColors.FlameSoft
    }
    val glyph = when (state) {
        OptionState.IDLE -> ""
        OptionState.CORRECT -> "\u2713"
        OptionState.SELECTED_WRONG -> "\u2715"
    }
    val description = when (state) {
        OptionState.IDLE -> text
        OptionState.CORRECT -> stringResource(R.string.cd_answer_correct, text)
        OptionState.SELECTED_WRONG -> stringResource(R.string.cd_answer_wrong, text)
    }
    val ink = when (state) {
        OptionState.IDLE -> PompColors.Ink
        OptionState.CORRECT -> PompColors.Jade
        OptionState.SELECTED_WRONG -> PompColors.Flame
    }

    Box(modifier = Modifier.fillMaxWidth().padding(top = 5.dp, bottom = 9.dp)) {
        Box(
            modifier = Modifier.matchParentSize().offset(y = 4.dp).clip(RoundedCornerShape(13.dp)).background(PompColors.OptionDepth),
        )
        Surface(
            color = background,
            shape = RoundedCornerShape(13.dp),
            border = BorderStroke(2.dp, border),
            modifier = Modifier.fillMaxWidth().heightIn(min = 54.dp).semantics { contentDescription = description },
            onClick = onClick,
            enabled = enabled,
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 15.dp, vertical = 14.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(11.dp),
            ) {
                if (key.isNotEmpty()) {
                    Surface(
                        shape = RoundedCornerShape(7.dp),
                        color = Color.Transparent,
                        border = BorderStroke(1.5.dp, PompColors.Divider),
                        modifier = Modifier.size(23.dp),
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Text(text = key, style = MaterialTheme.typography.labelSmall.copy(fontSize = 12.sp), color = PompColors.InkDisabled)
                        }
                    }
                }
                Text(text = text, style = MaterialTheme.typography.titleMedium.copy(fontSize = 15.sp), color = ink, modifier = Modifier.weight(1f))
                if (glyph.isNotEmpty()) {
                    Text(text = glyph, style = MaterialTheme.typography.titleMedium, color = border)
                }
            }
        }
    }
}

@Composable
fun SentenceBuilderCardView(card: SentenceBuilderCard, isAnswered: Boolean, onSubmit: (List<String>) -> Unit) {
    TokenBuilder(
        title = stringResource(R.string.lesson_build_sentence),
        prompt = card.promptSentence,
        tokens = card.tokens,
        isAnswered = isAnswered,
        onSubmit = onSubmit,
    )
}

@Composable
fun ReverseBuilderCardView(
    card: ReverseBuilderCard,
    pinyin: PinyinVisibility,
    isAnswered: Boolean,
    onSubmit: (List<String>) -> Unit,
) {
    Column {
        Text(text = card.hanzi, style = PompTextStyles.hanziMedium, color = PompColors.Ink)
        if (pinyin == PinyinVisibility.ALL && card.pinyin.isNotBlank()) {
            Text(text = card.pinyin, style = PompTextStyles.pinyin, color = PompColors.InkSecondary)
        }
        Spacer(Modifier.height(12.dp))
        TokenBuilder(
            title = stringResource(R.string.lesson_build_translation),
            prompt = "",
            tokens = card.tokens,
            isAnswered = isAnswered,
            onSubmit = onSubmit,
        )
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun TokenBuilder(
    title: String,
    prompt: String,
    tokens: List<String>,
    isAnswered: Boolean,
    onSubmit: (List<String>) -> Unit,
) {
    var chosen by remember(tokens) { mutableStateOf(listOf<Int>()) }
    Column {
        CardTitle(title)
        if (prompt.isNotBlank()) CardPrompt(prompt)
        Surface(
            color = PompColors.PaperRaised,
            shape = RoundedCornerShape(12.dp),
            border = BorderStroke(1.dp, PompColors.Divider),
            modifier = Modifier.fillMaxWidth().heightIn(min = 64.dp),
        ) {
            FlowRow(modifier = Modifier.padding(10.dp)) {
                chosen.forEach { index ->
                    Tile(text = tokens[index], enabled = !isAnswered, onClick = { chosen = chosen - index })
                }
            }
        }
        Spacer(Modifier.height(16.dp))
        FlowRow {
            tokens.indices.filterNot { it in chosen }.forEach { index ->
                Tile(text = tokens[index], enabled = !isAnswered, onClick = { chosen = chosen + index })
            }
        }
        Spacer(Modifier.height(20.dp))
        PrimaryAction(
            text = stringResource(R.string.lesson_check),
            enabled = !isAnswered && chosen.isNotEmpty(),
            onClick = { onSubmit(chosen.map { tokens[it] }) },
        )
    }
}

@Composable
private fun Tile(text: String, enabled: Boolean, onClick: () -> Unit) {
    Surface(
        color = if (PompColors.IsDark) PompColors.OptionDepth else PompColors.Paper,
        shape = RoundedCornerShape(10.dp),
        border = BorderStroke(1.dp, PompColors.Cinnabar),
        modifier = Modifier.padding(4.dp).heightIn(min = 48.dp),
        onClick = onClick,
        enabled = enabled,
    ) {
        Text(text = text, style = MaterialTheme.typography.titleMedium, color = PompColors.Ink, modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp))
    }
}

@Composable
fun MatchPairsCardView(card: MatchPairsCard, isAnswered: Boolean, onFinished: (List<Pair<Int, Int>>) -> Unit) {
    val rightOrder = remember(card) { card.pairs.indices.shuffled() }
    var selectedLeft by remember(card) { mutableStateOf<Int?>(null) }
    var matched by remember(card) { mutableStateOf(setOf<Int>()) }
    var wrongAttempts by remember(card) { mutableStateOf(listOf<Pair<Int, Int>>()) }

    Column {
        CardTitle(stringResource(R.string.lesson_match_pairs))
        Row(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.weight(1f)) {
                card.pairs.forEachIndexed { index, pair ->
                    Tile(text = pair.first, enabled = !isAnswered && index !in matched, onClick = { selectedLeft = index })
                }
            }
            Spacer(Modifier.padding(6.dp))
            Column(modifier = Modifier.weight(1f)) {
                rightOrder.forEach { index ->
                    Tile(
                        text = card.pairs[index].second,
                        enabled = !isAnswered && index !in matched,
                        onClick = {
                            val left = selectedLeft
                            if (left != null) {
                                if (left == index) {
                                    matched = matched + index
                                    if (matched.size == card.pairs.size) onFinished(wrongAttempts)
                                } else {
                                    wrongAttempts = wrongAttempts + (left to index)
                                }
                                selectedLeft = null
                            }
                        },
                    )
                }
            }
        }
    }
}

@Composable
fun UnsupportedCardView(card: UnsupportedCard, onSkip: () -> Unit) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(text = stringResource(R.string.lesson_card_unsupported), style = MaterialTheme.typography.titleMedium, color = PompColors.Ink, textAlign = TextAlign.Center)
        Spacer(Modifier.height(8.dp))
        Text(text = stringResource(R.string.lesson_card_unsupported_hint), style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary, textAlign = TextAlign.Center)
        Spacer(Modifier.height(20.dp))
        SecondaryAction(text = stringResource(R.string.lesson_skip_card), onClick = onSkip)
    }
}
