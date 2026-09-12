package com.pomp.hskai.feature.dictionary

import android.content.Intent
import android.net.Uri
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.VolumeUp
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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.core.hanzi.StrokeAnimation
import com.pomp.hskai.core.hanzi.StrokeSnapshot
import com.pomp.hskai.core.navigation.AppDestination
import com.pomp.hskai.core.navigation.DeepLinkRouter
import com.pomp.hskai.core.navigation.PracticeTool
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.repository.DictionaryWord
import kotlinx.coroutines.launch

/** Native equivalent of Mini App `hsk-lugat.html`: list -> word detail -> writer. */
@Composable
fun DictionaryScreen(
    state: DictionaryUiState,
    onQueryChange: (String) -> Unit,
    onRetry: () -> Unit,
    onBack: () -> Unit,
    onOpenWord: (DictionaryWord) -> Unit = {},
    onCloseWord: () -> Unit = {},
    onPreviousCharacter: () -> Unit = {},
    onNextCharacter: () -> Unit = {},
    onPreviousStroke: () -> Unit = {},
    onNextStroke: () -> Unit = {},
    onPlayStrokeOrder: () -> Unit = {},
    onPauseStrokeOrder: () -> Unit = {},
    onNextWord: () -> Unit = {},
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val app = context.applicationContext as? HskAiApplication
    val scope = rememberCoroutineScope()
    var audioBusy by remember { mutableStateOf(false) }

    fun speak(text: String) {
        if (audioBusy || text.isBlank() || app == null) return
        audioBusy = true
        scope.launch {
            val result = app.courseRepository.ttsAudio(text)
            if (result is ApiResult.Success) {
                runCatching { app.lessonAudioPlayer.play(result.value) }
            }
            audioBusy = false
        }
    }

    fun openPractice(tool: PracticeTool) {
        val uri = Uri.parse(DeepLinkRouter.uriFor(AppDestination.Practice(tool)))
        runCatching {
            context.startActivity(Intent(Intent.ACTION_VIEW, uri).setPackage(context.packageName))
        }
    }

    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        if (state.selectedWord == null) {
            DictionaryList(
                state = state,
                onQueryChange = onQueryChange,
                onRetry = onRetry,
                onBack = onBack,
                onOpenWord = onOpenWord,
            )
        } else {
            DictionaryDetail(
                state = state,
                audioBusy = audioBusy,
                onBack = onCloseWord,
                onSpeak = { speak(state.selectedWord.hanzi) },
                onPreviousCharacter = onPreviousCharacter,
                onNextCharacter = onNextCharacter,
                onPreviousStroke = onPreviousStroke,
                onNextStroke = onNextStroke,
                onPlayStrokeOrder = onPlayStrokeOrder,
                onPauseStrokeOrder = onPauseStrokeOrder,
                onNextWord = onNextWord,
                onPronunciation = { openPractice(PracticeTool.PRONUNCIATION) },
                onRecognition = { openPractice(PracticeTool.RECOGNITION) },
                onMemorize = { openPractice(PracticeTool.MEMORIZE) },
            )
        }
    }
}

@Composable
private fun DictionaryList(
    state: DictionaryUiState,
    onQueryChange: (String) -> Unit,
    onRetry: () -> Unit,
    onBack: () -> Unit,
    onOpenWord: (DictionaryWord) -> Unit,
) {
    Column(Modifier.fillMaxSize().statusBarsPadding()) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(start = 4.dp, end = 16.dp, top = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(onClick = onBack) {
                Icon(
                    Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = stringResource(R.string.action_back),
                    tint = PompColors.Ink,
                )
            }
            Column(Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.dictionary_new_words_title),
                    style = MaterialTheme.typography.titleLarge,
                    color = PompColors.Ink,
                )
                Text(
                    text = "汉字 · HSK 1–4",
                    style = MaterialTheme.typography.labelSmall,
                    color = PompColors.InkSecondary,
                )
            }
        }

        OutlinedTextField(
            value = state.query,
            onValueChange = onQueryChange,
            singleLine = true,
            placeholder = {
                Text(stringResource(R.string.dictionary_search_hint), color = PompColors.InkDisabled)
            },
            leadingIcon = { Icon(Icons.Filled.Search, null, tint = PompColors.InkSecondary) },
            trailingIcon = {
                if (state.query.isNotEmpty()) {
                    IconButton(onClick = { onQueryChange("") }) {
                        Icon(
                            Icons.Filled.Close,
                            contentDescription = stringResource(R.string.action_clear),
                            tint = PompColors.InkSecondary,
                        )
                    }
                }
            },
            shape = RoundedCornerShape(16.dp),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = PompColors.Cinnabar,
                unfocusedBorderColor = PompColors.Divider,
                focusedTextColor = PompColors.Ink,
                unfocusedTextColor = PompColors.Ink,
                cursorColor = PompColors.Cinnabar,
                focusedContainerColor = PompColors.PaperRaised,
                unfocusedContainerColor = PompColors.PaperRaised,
            ),
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp),
        )

        if (state.total > 0) {
            Text(
                text = if (state.query.isBlank()) {
                    stringResource(R.string.dictionary_words_count, state.total)
                } else {
                    stringResource(R.string.dictionary_results_count, state.words.size)
                },
                style = MaterialTheme.typography.labelMedium,
                color = PompColors.InkSecondary,
                modifier = Modifier.padding(horizontal = 18.dp, vertical = 2.dp),
            )
        }

        when {
            state.isLoading && state.words.isEmpty() -> Box(
                Modifier.fillMaxSize(), contentAlignment = Alignment.Center
            ) { CircularProgressIndicator(color = PompColors.Cinnabar) }

            state.isUnavailable -> DictionaryMessage(
                text = stringResource(state.error?.messageRes ?: R.string.dictionary_unavailable),
                onRetry = onRetry,
            )

            state.words.isEmpty() -> DictionaryMessage(
                text = stringResource(R.string.dictionary_no_match, state.query),
                onRetry = null,
            )

            else -> LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
            ) {
                items(state.words, key = { it.hanzi }) { word ->
                    WordRow(word = word, onClick = { onOpenWord(word) })
                }
            }
        }
    }
}

@Composable
private fun DictionaryDetail(
    state: DictionaryUiState,
    audioBusy: Boolean,
    onBack: () -> Unit,
    onSpeak: () -> Unit,
    onPreviousCharacter: () -> Unit,
    onNextCharacter: () -> Unit,
    onPreviousStroke: () -> Unit,
    onNextStroke: () -> Unit,
    onPlayStrokeOrder: () -> Unit,
    onPauseStrokeOrder: () -> Unit,
    onNextWord: () -> Unit,
    onPronunciation: () -> Unit,
    onRecognition: () -> Unit,
    onMemorize: () -> Unit,
) {
    val word = state.selectedWord ?: return
    LazyColumn(
        modifier = Modifier.fillMaxSize().statusBarsPadding(),
        contentPadding = PaddingValues(bottom = 28.dp),
    ) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth().padding(start = 4.dp, end = 16.dp, top = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(onClick = onBack) {
                    Icon(
                        Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = stringResource(R.string.action_back),
                        tint = PompColors.Ink,
                    )
                }
                Spacer(Modifier.weight(1f))
                if (word.level.isNotBlank()) LevelPill(word.level)
            }
        }

        item {
            WriterCard(
                state = state,
                onPreviousCharacter = onPreviousCharacter,
                onNextCharacter = onNextCharacter,
                onPreviousStroke = onPreviousStroke,
                onNextStroke = onNextStroke,
                onPlayStrokeOrder = onPlayStrokeOrder,
                onPauseStrokeOrder = onPauseStrokeOrder,
            )
        }

        item {
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 14.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = word.pinyin,
                    style = PompTextStyles.pinyin.copy(fontSize = 21.sp),
                    color = PompColors.Cinnabar,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1f),
                )
                IconButton(onClick = onSpeak, enabled = !audioBusy) {
                    if (audioBusy) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(22.dp),
                            strokeWidth = 2.dp,
                            color = PompColors.Cinnabar,
                        )
                    } else {
                        Icon(
                            Icons.Filled.VolumeUp,
                            contentDescription = stringResource(R.string.dictionary_listen),
                            tint = PompColors.Cinnabar,
                        )
                    }
                }
            }
            Text(
                text = word.meaning,
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.Ink,
                modifier = Modifier.padding(horizontal = 20.dp),
            )
        }

        item {
            Spacer(Modifier.height(18.dp))
            Surface(
                onClick = onNextWord,
                color = PompColors.PaperRaised,
                shape = RoundedCornerShape(16.dp),
                border = BorderStroke(1.dp, PompColors.Divider),
                modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp),
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text("字", style = PompTextStyles.hanziSmall, color = PompColors.Ink)
                    Text(
                        stringResource(R.string.dictionary_next_word),
                        style = MaterialTheme.typography.titleSmall,
                        color = PompColors.Ink,
                        modifier = Modifier.weight(1f).padding(start = 12.dp),
                    )
                    Text("›", fontSize = 28.sp, color = PompColors.InkDisabled)
                }
            }
        }

        item {
            PracticeBlock(
                onPronunciation = onPronunciation,
                onRecognition = onRecognition,
                onMemorize = onMemorize,
            )
        }
    }
}

@Composable
private fun WriterCard(
    state: DictionaryUiState,
    onPreviousCharacter: () -> Unit,
    onNextCharacter: () -> Unit,
    onPreviousStroke: () -> Unit,
    onNextStroke: () -> Unit,
    onPlayStrokeOrder: () -> Unit,
    onPauseStrokeOrder: () -> Unit,
) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 8.dp),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                WriterNavButton(
                    text = "‹",
                    enabled = state.hasPreviousCharacter,
                    description = stringResource(R.string.dictionary_previous_character),
                    onClick = onPreviousCharacter,
                )
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    if (state.characters.size > 1) {
                        Text(
                            stringResource(
                                R.string.dictionary_character_position,
                                state.characterIndex + 1,
                                state.characters.size,
                            ),
                            style = MaterialTheme.typography.labelSmall,
                            color = PompColors.InkSecondary,
                        )
                    }
                    if (state.strokeCount > 0) {
                        Text(
                            stringResource(R.string.dictionary_strokes_count, state.strokeCount),
                            style = MaterialTheme.typography.labelMedium,
                            color = PompColors.Ink,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }
                WriterNavButton(
                    text = "›",
                    enabled = state.hasNextCharacter,
                    description = stringResource(R.string.dictionary_next_character),
                    onClick = onNextCharacter,
                )
            }

            Surface(
                color = PompColors.Paper,
                shape = RoundedCornerShape(18.dp),
                border = BorderStroke(1.dp, PompColors.Divider),
                modifier = Modifier.fillMaxWidth().aspectRatio(1f).padding(top = 8.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    WriterGrid()
                    when {
                        state.isStrokeLoading -> CircularProgressIndicator(color = PompColors.Cinnabar)
                        state.strokes.isNotEmpty() && state.isStrokePlaying -> StrokeAnimation(
                            strokes = state.strokes,
                            replayKey = state.strokeReplayKey,
                            modifier = Modifier.fillMaxSize(),
                        )
                        state.strokes.isNotEmpty() -> StrokeSnapshot(
                            strokes = state.strokes,
                            visibleStrokeCount = state.visibleStrokeCount,
                            modifier = Modifier.fillMaxSize(),
                        )
                        else -> Text(
                            text = state.currentCharacter.orEmpty(),
                            style = PompTextStyles.hanziLarge.copy(fontSize = 112.sp),
                            color = PompColors.Ink,
                        )
                    }
                }
            }

            if (!state.isStrokeLoading && state.strokes.isEmpty()) {
                Text(
                    text = stringResource(R.string.dictionary_writer_unavailable),
                    style = MaterialTheme.typography.labelSmall,
                    color = PompColors.InkSecondary,
                    modifier = Modifier.padding(top = 8.dp),
                )
            }

            Row(
                modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                WriterControl(
                    text = "«",
                    enabled = state.strokes.isNotEmpty() && !state.isStrokePlaying && state.visibleStrokeCount > 0,
                    description = stringResource(R.string.dictionary_previous_stroke),
                    onClick = onPreviousStroke,
                    modifier = Modifier.weight(1f),
                )
                WriterControl(
                    text = if (state.isStrokePlaying) "⏸" else "▶",
                    enabled = state.strokes.isNotEmpty(),
                    description = stringResource(
                        if (state.isStrokePlaying) R.string.dictionary_pause_strokes
                        else R.string.dictionary_play_strokes
                    ),
                    onClick = if (state.isStrokePlaying) onPauseStrokeOrder else onPlayStrokeOrder,
                    primary = true,
                    modifier = Modifier.weight(1f),
                )
                WriterControl(
                    text = "»",
                    enabled = state.strokes.isNotEmpty() && !state.isStrokePlaying && state.visibleStrokeCount < state.strokeCount,
                    description = stringResource(R.string.dictionary_next_stroke),
                    onClick = onNextStroke,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun WriterGrid() {
    val line = PompColors.Divider.copy(alpha = 0.55f)
    Canvas(Modifier.fillMaxSize().padding(10.dp)) {
        val w = size.width
        val h = size.height
        val stroke = 1.dp.toPx()
        drawLine(line, Offset(w / 2, 0f), Offset(w / 2, h), strokeWidth = stroke)
        drawLine(line, Offset(0f, h / 2), Offset(w, h / 2), strokeWidth = stroke)
        drawLine(line, Offset.Zero, Offset(w, h), strokeWidth = stroke)
        drawLine(line, Offset(w, 0f), Offset(0f, h), strokeWidth = stroke)
    }
}

@Composable
private fun WriterNavButton(text: String, enabled: Boolean, description: String, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        enabled = enabled,
        color = PompColors.OptionDepth,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.size(42.dp),
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text(text, fontSize = 28.sp, color = if (enabled) PompColors.Ink else PompColors.InkDisabled)
        }
    }
}

@Composable
private fun WriterControl(
    text: String,
    enabled: Boolean,
    description: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    primary: Boolean = false,
) {
    Surface(
        onClick = onClick,
        enabled = enabled,
        color = if (primary) PompColors.Cinnabar else PompColors.OptionDepth,
        shape = RoundedCornerShape(13.dp),
        modifier = modifier.heightIn(min = 48.dp),
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text(
                text = text,
                fontSize = 21.sp,
                color = if (primary) PompColors.Paper else if (enabled) PompColors.Ink else PompColors.InkDisabled,
            )
        }
    }
}

@Composable
private fun PracticeBlock(
    onPronunciation: () -> Unit,
    onRecognition: () -> Unit,
    onMemorize: () -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(
            stringResource(R.string.dictionary_practice_title),
            style = MaterialTheme.typography.titleMedium,
            color = PompColors.Ink,
            fontWeight = FontWeight.Bold,
        )
        PracticeRow(
            icon = "🎙️",
            title = stringResource(R.string.dictionary_pronunciation_title),
            subtitle = stringResource(R.string.dictionary_pronunciation_subtitle),
            onClick = onPronunciation,
        )
        PracticeRow(
            icon = "🔍",
            title = stringResource(R.string.dictionary_recognition_title),
            subtitle = stringResource(R.string.dictionary_recognition_subtitle),
            onClick = onRecognition,
        )
        PracticeRow(
            icon = "⚡",
            title = stringResource(R.string.practice_memorize_title),
            subtitle = stringResource(R.string.practice_memorize_subtitle),
            onClick = onMemorize,
        )
    }
}

@Composable
private fun PracticeRow(icon: String, title: String, subtitle: String, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(15.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(icon, fontSize = 22.sp)
            Column(Modifier.weight(1f).padding(start = 12.dp)) {
                Text(title, style = MaterialTheme.typography.titleSmall, color = PompColors.Ink)
                Text(subtitle, style = MaterialTheme.typography.bodySmall, color = PompColors.InkSecondary)
            }
            Text("›", fontSize = 24.sp, color = PompColors.InkDisabled)
        }
    }
}

@Composable
private fun WordRow(word: DictionaryWord, onClick: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick).padding(vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(word.hanzi, style = PompTextStyles.hanziSmall, color = PompColors.Ink)
        Column(Modifier.weight(1f).padding(start = 14.dp)) {
            Text(word.pinyin, style = PompTextStyles.pinyin, color = PompColors.Cinnabar)
            Text(word.meaning, style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
        }
        if (word.level.isNotBlank()) {
            Spacer(Modifier.width(10.dp))
            LevelPill(word.level)
        }
    }
}

@Composable
private fun LevelPill(level: String) {
    Surface(color = PompColors.OptionDepth, shape = RoundedCornerShape(8.dp)) {
        Text(
            text = level,
            style = MaterialTheme.typography.labelSmall,
            color = PompColors.InkSecondary,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
        )
    }
}

@Composable
private fun DictionaryMessage(text: String, onRetry: (() -> Unit)?) {
    Column(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
        if (onRetry != null) {
            Spacer(Modifier.height(16.dp))
            OutlinedButton(
                onClick = onRetry,
                modifier = Modifier.heightIn(min = 48.dp),
                shape = RoundedCornerShape(14.dp),
            ) {
                Text(stringResource(R.string.action_retry), color = PompColors.Cinnabar)
            }
        }
    }
}
