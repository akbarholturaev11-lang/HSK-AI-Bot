package com.pomp.hskai.feature.dictionary

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.VolumeUp
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.core.hanzi.StrokeAnimation
import com.pomp.hskai.data.repository.DictionaryWord

/** Native dictionary backed by the same HSK 1–4 list and writer API as Mini App. */
@Composable
fun DictionaryScreen(
    state: DictionaryUiState,
    onQueryChange: (String) -> Unit,
    onRetry: () -> Unit,
    onOpenWord: (DictionaryWord) -> Unit,
    onCloseWord: () -> Unit,
    onPreviousCharacter: () -> Unit,
    onNextCharacter: () -> Unit,
    onPreviousStroke: () -> Unit,
    onReplayStrokes: () -> Unit,
    onNextStroke: () -> Unit,
    onPlayAudio: () -> Unit,
    onPreviousWord: () -> Unit,
    onNextWord: () -> Unit,
    onOpenRecognition: () -> Unit,
    onOpenPronunciation: () -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    BackHandler(enabled = state.selectedWord != null, onBack = onCloseWord)
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        if (state.selectedWord == null) {
            DictionaryList(state, onQueryChange, onRetry, onOpenWord, onBack)
        } else {
            DictionaryDetail(
                state,
                onCloseWord,
                onPreviousCharacter,
                onNextCharacter,
                onPreviousStroke,
                onReplayStrokes,
                onNextStroke,
                onPlayAudio,
                onPreviousWord,
                onNextWord,
                onOpenRecognition,
                onOpenPronunciation,
            )
        }
    }
}

@Composable
private fun DictionaryList(
    state: DictionaryUiState,
    onQueryChange: (String) -> Unit,
    onRetry: () -> Unit,
    onOpenWord: (DictionaryWord) -> Unit,
    onBack: () -> Unit,
) {
    Column(Modifier.fillMaxSize().statusBarsPadding()) {
        DictionaryHeader(onBack, stringResource(R.string.practice_dictionary_title), state.total)
        OutlinedTextField(
            value = state.query,
            onValueChange = onQueryChange,
            singleLine = true,
            placeholder = { Text(stringResource(R.string.dictionary_search_hint), color = PompColors.InkDisabled) },
            leadingIcon = { Icon(Icons.Filled.Search, null, tint = PompColors.InkSecondary) },
            trailingIcon = {
                if (state.query.isNotEmpty()) {
                    IconButton(onClick = { onQueryChange("") }) {
                        Icon(Icons.Filled.Close, stringResource(R.string.action_clear), tint = PompColors.InkSecondary)
                    }
                }
            },
            shape = RoundedCornerShape(14.dp),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = PompColors.Cinnabar,
                unfocusedBorderColor = PompColors.Divider,
                focusedTextColor = PompColors.Ink,
                unfocusedTextColor = PompColors.Ink,
                cursorColor = PompColors.Cinnabar,
            ),
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 10.dp),
        )
        when {
            state.isLoading && state.words.isEmpty() -> LoadingBox()
            state.isUnavailable -> DictionaryMessage(
                stringResource(state.error?.messageRes ?: R.string.dictionary_unavailable),
                onRetry,
            )
            state.words.isEmpty() -> DictionaryMessage(
                stringResource(R.string.dictionary_no_match, state.query),
                null,
            )
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 20.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(state.words, key = { it.hanzi }) { word -> WordRow(word) { onOpenWord(word) } }
            }
        }
    }
}

@Composable
private fun DictionaryDetail(
    state: DictionaryUiState,
    onBack: () -> Unit,
    onPreviousCharacter: () -> Unit,
    onNextCharacter: () -> Unit,
    onPreviousStroke: () -> Unit,
    onReplayStrokes: () -> Unit,
    onNextStroke: () -> Unit,
    onPlayAudio: () -> Unit,
    onPreviousWord: () -> Unit,
    onNextWord: () -> Unit,
    onOpenRecognition: () -> Unit,
    onOpenPronunciation: () -> Unit,
) {
    val word = requireNotNull(state.selectedWord)
    LazyColumn(
        modifier = Modifier.fillMaxSize().statusBarsPadding(),
        contentPadding = PaddingValues(bottom = 28.dp),
    ) {
        item { DictionaryHeader(onBack, stringResource(R.string.dictionary_detail_title), 0) }
        item {
            Column(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Surface(
                    color = PompColors.PaperRaised,
                    shape = RoundedCornerShape(20.dp),
                    border = BorderStroke(1.dp, PompColors.Divider),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Box(Modifier.fillMaxWidth().aspectRatio(1f)) {
                        WriterGrid(Modifier.fillMaxSize())
                        when {
                            state.isStrokeLoading -> CircularProgressIndicator(
                                color = PompColors.Cinnabar,
                                modifier = Modifier.align(Alignment.Center),
                            )
                            state.strokes.isNotEmpty() -> StrokeAnimation(
                                strokes = state.strokes,
                                replayKey = state.replayKey,
                                visibleStrokeCount = state.visibleStrokeCount,
                                modifier = Modifier.fillMaxSize(),
                            )
                            else -> Text(
                                text = state.currentCharacter.orEmpty(),
                                style = PompTextStyles.hanziLarge,
                                color = PompColors.Ink,
                                modifier = Modifier.align(Alignment.Center),
                            )
                        }
                    }
                }
                if (state.characters.size > 1) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(top = 10.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        OutlinedButton(onClick = onPreviousCharacter, enabled = state.characterIndex > 0) { Text("‹") }
                        Text(
                            stringResource(
                                R.string.dictionary_character_position,
                                state.characterIndex + 1,
                                state.characters.size,
                            ),
                            color = PompColors.InkSecondary,
                        )
                        OutlinedButton(
                            onClick = onNextCharacter,
                            enabled = state.characterIndex < state.characters.lastIndex,
                        ) { Text("›") }
                    }
                }
                Row(
                    modifier = Modifier.fillMaxWidth().padding(top = 10.dp),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    IconButton(onClick = onPreviousStroke, enabled = state.strokes.isNotEmpty()) {
                        Text("‹", style = MaterialTheme.typography.headlineMedium)
                    }
                    Surface(color = PompColors.CinnabarSoft, shape = CircleShape) {
                        IconButton(onClick = onReplayStrokes, enabled = state.strokes.isNotEmpty()) {
                            Icon(Icons.Filled.Refresh, stringResource(R.string.dictionary_replay), tint = PompColors.CinnabarDark)
                        }
                    }
                    IconButton(onClick = onNextStroke, enabled = state.strokes.isNotEmpty()) {
                        Text("›", style = MaterialTheme.typography.headlineMedium)
                    }
                    Spacer(Modifier.width(12.dp))
                    Text(
                        stringResource(R.string.dictionary_stroke_count, state.strokes.size),
                        style = MaterialTheme.typography.labelLarge,
                        color = PompColors.InkSecondary,
                    )
                }
                Spacer(Modifier.height(18.dp))
                Text(word.hanzi, style = PompTextStyles.hanziMedium, color = PompColors.Ink, textAlign = TextAlign.Center)
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(word.pinyin, style = PompTextStyles.pinyin, color = PompColors.CinnabarDark)
                        Text(word.meaning, style = MaterialTheme.typography.bodyLarge, color = PompColors.InkSecondary, textAlign = TextAlign.Center)
                    }
                    Spacer(Modifier.width(8.dp))
                    Surface(color = PompColors.CinnabarSoft, shape = CircleShape) {
                        IconButton(onClick = onPlayAudio, enabled = !state.isAudioLoading) {
                            if (state.isAudioLoading) {
                                CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp, color = PompColors.CinnabarDark)
                            } else {
                                Icon(Icons.AutoMirrored.Filled.VolumeUp, stringResource(R.string.dictionary_listen), tint = PompColors.CinnabarDark)
                            }
                        }
                    }
                }
                if (word.level.isNotBlank()) {
                    Text(word.level, style = MaterialTheme.typography.labelMedium, color = PompColors.InkSecondary, modifier = Modifier.padding(top = 8.dp))
                }
                Spacer(Modifier.height(24.dp))
                Text(
                    stringResource(R.string.dictionary_practice_title),
                    style = MaterialTheme.typography.titleMedium,
                    color = PompColors.Ink,
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(10.dp))
                PracticeRow(Icons.Filled.Visibility, stringResource(R.string.practice_characters_title), onOpenRecognition)
                Spacer(Modifier.height(8.dp))
                PracticeRow(Icons.Filled.Mic, stringResource(R.string.practice_pronunciation_row_title), onOpenPronunciation)
                Spacer(Modifier.height(18.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedButton(
                        onClick = onPreviousWord,
                        enabled = state.words.indexOfFirst { it.hanzi == word.hanzi } > 0,
                        modifier = Modifier.weight(1f).heightIn(min = 48.dp),
                    ) { Text(stringResource(R.string.dictionary_previous_word)) }
                    OutlinedButton(
                        onClick = onNextWord,
                        enabled = state.words.indexOfFirst { it.hanzi == word.hanzi } in 0 until state.words.lastIndex,
                        modifier = Modifier.weight(1f).heightIn(min = 48.dp),
                    ) { Text(stringResource(R.string.dictionary_next_word)) }
                }
            }
        }
    }
}

@Composable
private fun WriterGrid(modifier: Modifier = Modifier) {
    Canvas(modifier) {
        val line = PompColors.Divider.copy(alpha = .8f)
        drawLine(line, Offset(size.width / 2, 0f), Offset(size.width / 2, size.height), 1.dp.toPx())
        drawLine(line, Offset(0f, size.height / 2), Offset(size.width, size.height / 2), 1.dp.toPx())
        drawLine(line.copy(alpha = .45f), Offset.Zero, Offset(size.width, size.height), 1.dp.toPx())
        drawLine(line.copy(alpha = .45f), Offset(size.width, 0f), Offset(0f, size.height), 1.dp.toPx())
    }
}

@Composable
private fun PracticeRow(icon: ImageVector, title: String, onClick: () -> Unit) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
    ) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, null, tint = PompColors.CinnabarDark)
            Text(title, style = MaterialTheme.typography.titleSmall, color = PompColors.Ink, modifier = Modifier.padding(start = 12.dp).weight(1f))
            Text("›", style = MaterialTheme.typography.titleLarge, color = PompColors.InkSecondary)
        }
    }
}

@Composable
private fun DictionaryHeader(onBack: () -> Unit, title: String, total: Int) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(start = 4.dp, end = 16.dp, top = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconButton(onClick = onBack) {
            Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.action_back), tint = PompColors.Ink)
        }
        Text(title, style = MaterialTheme.typography.titleLarge, color = PompColors.Ink, modifier = Modifier.weight(1f))
        if (total > 0) Text(total.toString(), style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
    }
}

@Composable
private fun WordRow(word: DictionaryWord, onClick: () -> Unit) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
    ) {
        Row(Modifier.padding(horizontal = 14.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(word.hanzi, style = PompTextStyles.hanziSmall, color = PompColors.Ink)
            Column(Modifier.weight(1f).padding(start = 14.dp)) {
                Text(word.pinyin, style = PompTextStyles.pinyin, color = PompColors.CinnabarDark)
                Text(word.meaning, style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
            }
            if (word.level.isNotBlank()) {
                Spacer(Modifier.width(10.dp))
                Surface(color = PompColors.GoldSoft, shape = RoundedCornerShape(999.dp)) {
                    Text(word.level, style = MaterialTheme.typography.labelSmall, color = PompColors.InkSecondary, modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp))
                }
            }
        }
    }
}

@Composable
private fun LoadingBox() = Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
    CircularProgressIndicator(color = PompColors.Cinnabar)
}

@Composable
private fun DictionaryMessage(text: String, onRetry: (() -> Unit)?) {
    Column(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(text, style = MaterialTheme.typography.bodyLarge, color = PompColors.InkSecondary, textAlign = TextAlign.Center)
        if (onRetry != null) {
            Spacer(Modifier.height(16.dp))
            OutlinedButton(onClick = onRetry, modifier = Modifier.heightIn(min = 48.dp), shape = RoundedCornerShape(14.dp)) {
                Text(stringResource(R.string.action_retry), color = PompColors.CinnabarDark)
            }
        }
    }
}
