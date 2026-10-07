package com.pomp.hskai.feature.dictionary

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
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
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.automirrored.filled.VolumeUp
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Draw
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.abs
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.core.design.components.HskBrandLoader
import com.pomp.hskai.core.design.components.HskContentSkeleton
import com.pomp.hskai.core.design.components.HskGlassButton
import com.pomp.hskai.core.design.components.HskGlassSurface
import com.pomp.hskai.core.design.components.HskSectionTitle
import com.pomp.hskai.core.hanzi.StrokeAnimation
import com.pomp.hskai.data.repository.CharacterBreakdown
import com.pomp.hskai.data.repository.DictionaryWord
import com.pomp.hskai.data.repository.ExampleSentence
import com.pomp.hskai.feature.assistant.AssistantScreen
import com.pomp.hskai.feature.assistant.dictionaryAssistantContext

/** Everything the dictionary screen can be asked to do. */
data class DictionaryActions(
    val onQueryChange: (String) -> Unit,
    val onVersionFilter: (String) -> Unit = {},
    val onLevelFilter: (String) -> Unit = {},
    val onRetry: () -> Unit,
    val onOpenWord: (DictionaryWord) -> Unit,
    val onOpenRecent: (DictionaryWord) -> Unit,
    val onCloseWord: () -> Unit,
    val onPreviousCharacter: () -> Unit,
    val onNextCharacter: () -> Unit,
    val onPlayStrokeOrder: () -> Unit,
    val onToggleStrokePlayback: () -> Unit,
    val onPauseStrokePlayback: () -> Unit,
    val onPreviousStroke: () -> Unit,
    val onNextStroke: () -> Unit,
    val onStrokeComplete: (Int) -> Unit,
    val onStrokeAnimationFinished: () -> Unit,
    val onPlayAudio: () -> Unit,
    val onPreviousWord: () -> Unit,
    val onNextWord: () -> Unit,
    val onStartWriting: () -> Unit,
    val onCloseWriting: () -> Unit,
    val onWritingDemoAgain: () -> Unit,
    val onBeginWriting: () -> Unit,
    val onWritingStroke: (List<Offset>) -> Unit,
    val onWritingHint: () -> Unit,
    val onRestartWritingRound: () -> Unit,
    val onWriteAgain: () -> Unit,
    val onWriteNextCharacter: () -> Unit,
    val onBack: () -> Unit,
)

/**
 * The HSK 2.0 and 3.0 dictionary. Word lists, examples and authored component
 * cues ship inside the APK. Missing stroke outlines use the repository's
 * existing server fallback when the device is online.
 */
@Composable
fun DictionaryScreen(
    state: DictionaryUiState,
    actions: DictionaryActions,
    modifier: Modifier = Modifier,
) {
    AssistantScreen(
        dictionaryAssistantContext(state),
        bottomBar = false,
        // Clear of the previous/next bar on an entry.
        bottomInset = if (state.selectedWord != null) WORD_NAVIGATION_HEIGHT else 0.dp,
        // The practice square takes every touch; a button floating over it
        // would swallow strokes.
        showButton = state.writing == null,
    )
    // Practice closes back to the entry, an entry to the list, and the list
    // to wherever the dictionary was opened from.
    BackHandler {
        when {
            state.writing != null -> actions.onCloseWriting()
            state.selectedWord != null -> actions.onCloseWord()
            else -> actions.onBack()
        }
    }
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        val writing = state.writing
        when {
            writing != null -> HanziWritingScreen(
                writing = writing,
                hasNextCharacter = state.hasNextCharacter,
                onClose = actions.onCloseWriting,
                onDemoAgain = actions.onWritingDemoAgain,
                onBegin = actions.onBeginWriting,
                onStroke = actions.onWritingStroke,
                onHint = actions.onWritingHint,
                onRestart = actions.onRestartWritingRound,
                onWriteAgain = actions.onWriteAgain,
                onNextCharacter = actions.onWriteNextCharacter,
            )
            state.selectedWord != null -> DictionaryDetail(state, actions)
            else -> DictionaryList(
                state = state,
                onQueryChange = actions.onQueryChange,
                onVersionFilter = actions.onVersionFilter,
                onLevelFilter = actions.onLevelFilter,
                onRetry = actions.onRetry,
                onOpenWord = actions.onOpenWord,
                onOpenRecent = actions.onOpenRecent,
                onBack = actions.onBack,
            )
        }
    }
}

@Composable
private fun DictionaryList(
    state: DictionaryUiState,
    onQueryChange: (String) -> Unit,
    onVersionFilter: (String) -> Unit,
    onLevelFilter: (String) -> Unit,
    onRetry: () -> Unit,
    onOpenWord: (DictionaryWord) -> Unit,
    onOpenRecent: (DictionaryWord) -> Unit,
    onBack: () -> Unit,
) {
    val focusManager = LocalFocusManager.current
    // Opening the dictionary shows the list; the history appears only once
    // the learner goes to search, and goes again when they start typing.
    var searchFocused by remember { mutableStateOf(false) }
    val showRecent = searchFocused && state.query.isBlank() && state.history.isNotEmpty()
    val listState = rememberLazyListState()
    LaunchedEffect(showRecent) { if (showRecent) listState.scrollToItem(0) }
    // With the search box focused, back leaves the search first.
    BackHandler(enabled = searchFocused) { focusManager.clearFocus() }

    Column(Modifier.fillMaxSize().statusBarsPadding()) {
        DictionaryHeader(onBack, stringResource(R.string.practice_dictionary_title), trailing = state.total.takeIf { it > 0 }?.toString())
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
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp, vertical = 10.dp)
                .onFocusChanged { searchFocused = it.isFocused },
        )
        DictionaryFilters(
            version = state.versionFilter,
            level = state.levelFilter,
            onVersion = onVersionFilter,
            onLevel = onLevelFilter,
        )
        when {
            state.isLoading && state.words.isEmpty() -> DictionarySkeleton()
            state.isUnavailable -> DictionaryMessage(
                stringResource(state.error?.messageRes ?: R.string.dictionary_unavailable),
                onRetry,
            )
            state.words.isEmpty() -> DictionaryMessage(
                stringResource(R.string.dictionary_no_match, state.query),
                null,
            )
            else -> LazyColumn(
                state = listState,
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 20.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(0.dp),
            ) {
                if (showRecent) {
                    item(key = "recent-title") { ListSectionTitle(stringResource(R.string.dictionary_recent_title)) }
                    itemsIndexed(state.history, key = { _, word -> "recent-${word.hanzi}" }) { index, word ->
                        Column {
                            WordRow(word) {
                                focusManager.clearFocus()
                                onOpenRecent(word)
                            }
                            if (index < state.history.lastIndex) {
                                HorizontalDivider(Modifier.padding(start = 70.dp), color = PompColors.Divider)
                            }
                        }
                    }
                    item(key = "all-title") { ListSectionTitle(stringResource(R.string.dictionary_all_words)) }
                }
                itemsIndexed(state.words, key = { _, word -> word.hanzi }) { index, word ->
                    Column {
                        WordRow(word) { onOpenWord(word) }
                        if (index < state.words.lastIndex) {
                            HorizontalDivider(Modifier.padding(start = 70.dp), color = PompColors.Divider)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun DictionaryFilters(
    version: String,
    level: String,
    onVersion: (String) -> Unit,
    onLevel: (String) -> Unit,
) {
    val versions = listOf("all", "hsk20", "hsk30")
    val levels = when (version) {
        "hsk20" -> listOf("all", "hsk1", "hsk2", "hsk3", "hsk4")
        "hsk30" -> listOf("all", "nhsk1", "nhsk2", "nhsk3")
        else -> listOf("all", "hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")
    }
    Column(verticalArrangement = Arrangement.spacedBy(7.dp)) {
        LazyRow(
            contentPadding = PaddingValues(horizontal = 20.dp),
            horizontalArrangement = Arrangement.spacedBy(7.dp),
        ) {
            items(versions, key = { "version-$it" }) { key ->
                DictionaryFilterPill(
                    text = when (key) {
                        "hsk20" -> "HSK 2.0"
                        "hsk30" -> "HSK 3.0"
                        else -> stringResource(R.string.dictionary_filter_all_versions)
                    },
                    selected = version == key,
                    onClick = { onVersion(key) },
                )
            }
        }
        LazyRow(
            contentPadding = PaddingValues(horizontal = 20.dp),
            horizontalArrangement = Arrangement.spacedBy(7.dp),
        ) {
            items(levels, key = { "level-$it" }) { key ->
                val label = when {
                    key == "all" -> stringResource(R.string.dictionary_filter_all_levels)
                    key.startsWith("nhsk") -> "N" + key.takeLast(1)
                    else -> "HSK " + key.takeLast(1)
                }
                DictionaryFilterPill(
                    text = label,
                    selected = level == key,
                    onClick = { onLevel(key) },
                )
            }
        }
    }
    Spacer(Modifier.height(4.dp))
}

@Composable
private fun DictionaryFilterPill(
    text: String,
    selected: Boolean,
    onClick: () -> Unit,
) {
    Surface(
        color = if (selected) PompColors.CinnabarSoft else PompColors.PaperRaised,
        shape = RoundedCornerShape(11.dp),
        border = BorderStroke(
            1.dp,
            if (selected) PompColors.Cinnabar else PompColors.Divider,
        ),
        modifier = Modifier.heightIn(min = 44.dp).selectable(
            selected = selected,
            role = Role.RadioButton,
            onClick = onClick,
        ),
    ) {
        Text(
            text = text,
            color = if (selected) PompColors.CinnabarDark else PompColors.InkSecondary,
            fontSize = 12.sp,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
        )
    }
}

@Composable
private fun ListSectionTitle(text: String) {
    Text(
        text,
        style = MaterialTheme.typography.labelLarge,
        color = PompColors.InkSecondary,
        modifier = Modifier.fillMaxWidth().padding(top = 6.dp, bottom = 2.dp),
    )
}

@Composable
private fun DictionaryDetail(state: DictionaryUiState, actions: DictionaryActions) {
    val word = requireNotNull(state.selectedWord)
    val isPhrase = state.characters.size > 1
    var strokeOrderOpen by remember(word.hanzi) { mutableStateOf(false) }
    // A new entry starts at the top, not where the previous one was left.
    val listState = remember(word.hanzi) { LazyListState() }
    Column(Modifier.fillMaxSize().statusBarsPadding()) {
        DictionaryHeader(actions.onCloseWord, stringResource(R.string.dictionary_detail_title), level = word.level)
        LazyColumn(
            state = listState,
            modifier = Modifier.weight(1f).fillMaxWidth(),
            contentPadding = PaddingValues(start = 20.dp, end = 20.dp, top = 4.dp, bottom = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            item(key = "word") { WordHeading(word) }
            item(key = "actions") {
                ActionRow(
                    isAudioLoading = state.isAudioLoading,
                    canShowOrder = state.strokes.isNotEmpty(),
                    canWrite = state.canWrite,
                    onListen = actions.onPlayAudio,
                    onOrder = {
                        actions.onPlayStrokeOrder()
                        strokeOrderOpen = true
                    },
                    onWrite = actions.onStartWriting,
                )
            }
            if (state.breakdowns.isNotEmpty()) {
                item(key = "parts") { PartsSection(state.breakdowns, showCharacter = isPhrase) }
            }
            val explained = state.breakdowns.mapTo(mutableSetOf()) { it.character }
            val missingMemoryCues = state.characters.filterNot(explained::contains)
            if (!state.isInsightsLoading && missingMemoryCues.isNotEmpty()) {
                item(key = "memory-prompt") { MemoryPromptSection(missingMemoryCues) }
            }
            if (state.examples.isNotEmpty()) {
                item(key = "examples") { ExamplesSection(state.examples, word.hanzi) }
            }
        }
        WordNavigation(
            previous = state.previousWord,
            next = state.nextWord,
            onPrevious = actions.onPreviousWord,
            onNext = actions.onNextWord,
        )
    }
    if (strokeOrderOpen) {
        StrokeOrderPlayer(
            state = state,
            onDismiss = {
                actions.onPauseStrokePlayback()
                strokeOrderOpen = false
            },
            onPreviousCharacter = actions.onPreviousCharacter,
            onNextCharacter = actions.onNextCharacter,
            onTogglePlayback = actions.onToggleStrokePlayback,
            onPreviousStroke = actions.onPreviousStroke,
            onNextStroke = actions.onNextStroke,
            onStrokeComplete = actions.onStrokeComplete,
            onAnimationFinished = actions.onStrokeAnimationFinished,
        )
    }
}

/** A useful recall action when this character has no authored component cue. */
@Composable
private fun MemoryPromptSection(characters: List<String>) {
    Column(Modifier.fillMaxWidth()) {
        SectionTitle(stringResource(R.string.dictionary_memory_hint_title))
        Text(
            stringResource(R.string.dictionary_memory_hint_body, characters.joinToString(" ")),
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.InkSecondary,
            modifier = Modifier.padding(horizontal = 4.dp),
        )
    }
}

/** The character large, on the practice grid; the stroke order plays here. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun StrokeOrderPlayer(
    state: DictionaryUiState,
    onDismiss: () -> Unit,
    onPreviousCharacter: () -> Unit,
    onNextCharacter: () -> Unit,
    onTogglePlayback: () -> Unit,
    onPreviousStroke: () -> Unit,
    onNextStroke: () -> Unit,
    onStrokeComplete: (Int) -> Unit,
    onAnimationFinished: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val swipeThreshold = with(LocalDensity.current) { 64.dp.toPx() }
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = PompColors.Paper,
        tonalElevation = 0.dp,
        shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .widthIn(max = 520.dp)
                .navigationBarsPadding()
                .padding(horizontal = 24.dp)
                .padding(bottom = 18.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Box(
                modifier = Modifier.fillMaxWidth().height(56.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    state.currentCharacter.orEmpty(),
                    style = PompTextStyles.hanziMedium.copy(fontSize = 38.sp),
                    color = PompColors.Ink,
                    modifier = Modifier.align(Alignment.CenterStart),
                )
                Text(
                    stringResource(R.string.dictionary_stroke_count, state.strokes.size),
                    style = MaterialTheme.typography.titleSmall,
                    color = PompColors.InkSecondary,
                )
                Row(
                    modifier = Modifier.align(Alignment.CenterEnd),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    if (state.characters.size > 1) {
                        Text(
                            stringResource(R.string.dictionary_character_position, state.characterIndex + 1, state.characters.size),
                            style = MaterialTheme.typography.labelLarge,
                            color = PompColors.InkSecondary,
                        )
                    }
                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Filled.Close, stringResource(R.string.action_close), tint = PompColors.InkSecondary)
                    }
                }
            }
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 14.dp)
                    .pointerInput(state.currentCharacter, state.characterIndex, swipeThreshold) {
                        var dragDistance = 0f
                        detectHorizontalDragGestures(
                            onHorizontalDrag = { _, amount -> dragDistance += amount },
                            onDragEnd = {
                                if (abs(dragDistance) >= swipeThreshold) {
                                    if (dragDistance < 0f) onNextCharacter() else onPreviousCharacter()
                                }
                                dragDistance = 0f
                            },
                            onDragCancel = { dragDistance = 0f },
                        )
                    },
                shape = RoundedCornerShape(22.dp),
                color = PompColors.PaperRaised,
                border = BorderStroke(1.dp, PompColors.Divider),
            ) {
                Box(Modifier.fillMaxWidth().aspectRatio(1f), contentAlignment = Alignment.Center) {
                    WriterGrid(Modifier.fillMaxSize())
                    when {
                        state.isStrokeLoading -> HskBrandLoader()
                        state.strokes.isNotEmpty() -> StrokeAnimation(
                            strokes = state.strokes,
                            replayKey = state.replayKey,
                            visibleStrokeCount = state.visibleStrokeCount,
                            isPlaying = state.isStrokePlaying,
                            onStrokeComplete = onStrokeComplete,
                            onAnimationFinished = onAnimationFinished,
                            modifier = Modifier.fillMaxSize(),
                        )
                        else -> Text(
                            text = state.currentCharacter.orEmpty(),
                            style = PompTextStyles.hanziLarge.copy(fontSize = 150.sp),
                            color = PompColors.Ink,
                        )
                    }
                }
            }
            Row(
                modifier = Modifier.fillMaxWidth().padding(top = 18.dp),
                horizontalArrangement = Arrangement.spacedBy(20.dp, Alignment.CenterHorizontally),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                StrokeControl(
                    icon = Icons.AutoMirrored.Filled.KeyboardArrowLeft,
                    description = stringResource(R.string.dictionary_stroke_previous),
                    enabled = state.completedStrokeCount > 0,
                    onClick = onPreviousStroke,
                )
                StrokeControl(
                    icon = if (state.isStrokePlaying) Icons.Filled.Pause else Icons.Filled.PlayArrow,
                    description = stringResource(
                        if (state.isStrokePlaying) R.string.dictionary_stroke_pause else R.string.dictionary_stroke_play,
                    ),
                    enabled = state.strokes.isNotEmpty() && !state.isStrokeLoading,
                    onClick = onTogglePlayback,
                )
                StrokeControl(
                    icon = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                    description = stringResource(R.string.dictionary_stroke_next),
                    enabled = state.completedStrokeCount < state.strokes.size,
                    onClick = onNextStroke,
                )
            }
        }
    }
}

@Composable
private fun StrokeControl(
    icon: ImageVector,
    description: String,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    Surface(
        onClick = onClick,
        enabled = enabled,
        shape = CircleShape,
        color = if (enabled) PompColors.CinnabarSoft else PompColors.PaperRaised,
        modifier = Modifier.size(68.dp),
    ) {
        Box(contentAlignment = Alignment.Center) {
            Icon(
                icon,
                contentDescription = description,
                tint = if (enabled) PompColors.CinnabarDark else PompColors.InkDisabled,
                modifier = Modifier.size(28.dp),
            )
        }
    }
}

@Composable
private fun WordHeading(word: DictionaryWord) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(top = 14.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(word.hanzi, style = PompTextStyles.hanziMedium, color = PompColors.Ink, textAlign = TextAlign.Center)
        Text(
            word.pinyin,
            style = PompTextStyles.pinyin.copy(fontSize = 22.sp),
            color = PompColors.CinnabarDark,
            textAlign = TextAlign.Center,
        )
        Text(
            word.meaning,
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 2.dp),
        )
    }
}

/** Listen · stroke order · write it yourself. */
@Composable
private fun ActionRow(
    isAudioLoading: Boolean,
    canShowOrder: Boolean,
    canWrite: Boolean,
    onListen: () -> Unit,
    onOrder: () -> Unit,
    onWrite: () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(top = 18.dp),
        horizontalArrangement = Arrangement.spacedBy(28.dp, Alignment.CenterHorizontally),
    ) {
        EntryAction(
            icon = Icons.AutoMirrored.Filled.VolumeUp,
            label = stringResource(R.string.dictionary_action_listen),
            description = stringResource(R.string.dictionary_listen),
            onClick = onListen,
            enabled = !isAudioLoading,
            loading = isAudioLoading,
        )
        EntryAction(
            icon = Icons.Filled.Edit,
            label = stringResource(R.string.dictionary_action_order),
            onClick = onOrder,
            enabled = canShowOrder,
        )
        EntryAction(
            icon = Icons.Filled.Draw,
            label = stringResource(R.string.dictionary_action_write),
            onClick = onWrite,
            enabled = canWrite,
        )
    }
}

@Composable
private fun EntryAction(
    icon: ImageVector,
    label: String,
    onClick: () -> Unit,
    enabled: Boolean,
    description: String = label,
    loading: Boolean = false,
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Surface(
            onClick = onClick,
            enabled = enabled,
            shape = CircleShape,
            color = if (enabled || loading) PompColors.CinnabarSoft else PompColors.Divider,
            modifier = Modifier.size(56.dp),
        ) {
            Box(contentAlignment = Alignment.Center) {
                if (loading) {
                    HskBrandLoader(compact = true)
                } else {
                    Icon(
                        icon,
                        contentDescription = description,
                        tint = if (enabled) PompColors.CinnabarDark else PompColors.InkDisabled,
                        modifier = Modifier.size(26.dp),
                    )
                }
            }
        }
        Text(
            label,
            style = MaterialTheme.typography.labelMedium,
            color = PompColors.InkSecondary,
            modifier = Modifier.padding(top = 6.dp),
        )
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(
        text,
        style = MaterialTheme.typography.titleSmall,
        color = PompColors.InkSecondary,
        modifier = Modifier.fillMaxWidth().padding(top = 26.dp, bottom = 10.dp),
    )
}

/** What each character is built from, and the line that makes it stick. */
@Composable
private fun PartsSection(breakdowns: List<CharacterBreakdown>, showCharacter: Boolean) {
    Column(Modifier.fillMaxWidth()) {
        SectionTitle(stringResource(R.string.dictionary_parts_title))
        breakdowns.forEachIndexed { index, breakdown ->
            if (index > 0) Spacer(Modifier.height(16.dp))
            if (showCharacter) {
                Text(
                    breakdown.character,
                    style = PompTextStyles.hanziSmall,
                    color = PompColors.Ink,
                    modifier = Modifier.padding(bottom = 6.dp),
                )
            }
            if (breakdown.parts.isNotEmpty()) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    breakdown.parts.forEachIndexed { partIndex, part ->
                        if (partIndex > 0) {
                            Text(
                                "+",
                                style = MaterialTheme.typography.titleMedium,
                                color = PompColors.InkSecondary,
                                modifier = Modifier.padding(horizontal = 6.dp),
                            )
                        }
                        Surface(
                            color = PompColors.PaperRaised,
                            shape = RoundedCornerShape(14.dp),
                            border = BorderStroke(1.dp, PompColors.Divider),
                            modifier = Modifier.weight(1f),
                        ) {
                            Column(
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 10.dp),
                                horizontalAlignment = Alignment.CenterHorizontally,
                            ) {
                                Text(part.hanzi, style = PompTextStyles.hanziMedium, color = PompColors.Ink)
                                Text(
                                    part.pinyin,
                                    style = PompTextStyles.pinyin.copy(fontSize = 13.sp),
                                    color = PompColors.CinnabarDark,
                                )
                                Text(
                                    part.meaning,
                                    style = MaterialTheme.typography.labelMedium,
                                    color = PompColors.InkSecondary,
                                    textAlign = TextAlign.Center,
                                    maxLines = 2,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                        }
                    }
                }
            }
            Text(
                breakdown.hint,
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.Ink,
                modifier = Modifier.padding(top = if (breakdown.parts.isEmpty()) 0.dp else 10.dp),
            )
        }
    }
}

/** Real sentences with the word marked, each in hanzi, pinyin and translation. */
@Composable
private fun ExamplesSection(examples: List<ExampleSentence>, word: String) {
    Column(Modifier.fillMaxWidth()) {
        SectionTitle(stringResource(R.string.dictionary_examples_title))
        examples.forEachIndexed { index, example ->
            if (index > 0) Spacer(Modifier.height(8.dp))
            Surface(
                color = PompColors.PaperRaised,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, PompColors.Divider),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(Modifier.padding(horizontal = 14.dp, vertical = 12.dp)) {
                    Text(
                        highlighted(example.hanzi, word),
                        style = PompTextStyles.hanziSmall.copy(fontSize = 19.sp, lineHeight = 28.sp),
                        color = PompColors.Ink,
                    )
                    Text(
                        example.pinyin,
                        style = PompTextStyles.pinyin.copy(fontSize = 14.sp),
                        color = PompColors.CinnabarDark,
                        modifier = Modifier.padding(top = 4.dp),
                    )
                    Text(
                        example.translation,
                        style = MaterialTheme.typography.bodyMedium,
                        color = PompColors.InkSecondary,
                        modifier = Modifier.padding(top = 2.dp),
                    )
                }
            }
        }
    }
}

/**
 * The sentence with the entry marked. An entry such as 不但……而且…… or 春(天)
 * is marked by its parts, the way the example was matched to it.
 */
internal fun highlighted(sentence: String, word: String): AnnotatedString = buildAnnotatedString {
    val terms = exampleTerms(word)
    var from = 0
    while (true) {
        val next = terms
            .mapNotNull { term -> sentence.indexOf(term, from).takeIf { it >= 0 }?.let { it to term } }
            .minByOrNull { it.first }
            ?: break
        append(sentence.substring(from, next.first))
        withStyle(SpanStyle(color = PompColors.Cinnabar)) { append(next.second) }
        from = next.first + next.second.length
    }
    append(sentence.substring(from))
}

/** 春(天) -> [春天, 春]; 不但……而且…… -> [不但, 而且]. Longest first. */
internal fun exampleTerms(word: String): List<String> =
    word.split('…')
        .filter { it.isNotBlank() }
        .flatMap { part ->
            listOf(part.replace(OPTIONAL_PART, "$1"), part.replace(OPTIONAL_PART, ""))
        }
        .filter { it.isNotBlank() }
        .distinct()
        .sortedByDescending { it.length }

private val OPTIONAL_PART = Regex("[(（]([^)）]*)[)）]")

/** The entries either side of this one in the list the learner came from. */
@Composable
private fun WordNavigation(
    previous: DictionaryWord?,
    next: DictionaryWord?,
    onPrevious: () -> Unit,
    onNext: () -> Unit,
) {
    Column(Modifier.fillMaxWidth().navigationBarsPadding()) {
        HorizontalDivider(color = PompColors.Divider)
        Row(
            modifier = Modifier.fillMaxWidth().height(WORD_NAVIGATION_HEIGHT).padding(horizontal = 20.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            NeighbourButton(
                word = previous,
                label = stringResource(R.string.dictionary_previous_word),
                forward = false,
                onClick = onPrevious,
                modifier = Modifier.weight(1f),
            )
            NeighbourButton(
                word = next,
                label = stringResource(R.string.dictionary_next_word),
                forward = true,
                onClick = onNext,
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun NeighbourButton(
    word: DictionaryWord?,
    label: String,
    forward: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val enabled = word != null
    val tint = if (enabled) PompColors.Ink else PompColors.InkDisabled
    Surface(
        onClick = onClick,
        enabled = enabled,
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = modifier.fillMaxSize(),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp),
            horizontalArrangement = if (forward) Arrangement.End else Arrangement.Start,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (!forward) Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, null, tint = tint)
            Column(
                modifier = Modifier.weight(1f, fill = false).padding(horizontal = 4.dp),
                horizontalAlignment = if (forward) Alignment.End else Alignment.Start,
            ) {
                Text(
                    word?.hanzi ?: label,
                    style = if (word != null) PompTextStyles.hanziSmall.copy(fontSize = 17.sp) else MaterialTheme.typography.labelMedium,
                    color = tint,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                if (word != null) {
                    Text(
                        label,
                        style = MaterialTheme.typography.labelSmall,
                        color = PompColors.InkSecondary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
            if (forward) Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, null, tint = tint)
        }
    }
}

/** 米字格: the practice grid a character is written on. */
@Composable
internal fun WriterGrid(modifier: Modifier = Modifier) {
    Canvas(modifier) {
        val line = PompColors.Divider.copy(alpha = .8f)
        drawLine(line, Offset(size.width / 2, 0f), Offset(size.width / 2, size.height), 1.dp.toPx())
        drawLine(line, Offset(0f, size.height / 2), Offset(size.width, size.height / 2), 1.dp.toPx())
        drawLine(line.copy(alpha = .45f), Offset.Zero, Offset(size.width, size.height), 1.dp.toPx())
        drawLine(line.copy(alpha = .45f), Offset(size.width, 0f), Offset(0f, size.height), 1.dp.toPx())
    }
}

@Composable
private fun DictionaryHeader(
    onBack: () -> Unit,
    title: String,
    trailing: String? = null,
    level: String = "",
) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(start = 4.dp, end = 16.dp, top = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconButton(onClick = onBack) {
            Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.action_back), tint = PompColors.Ink)
        }
        HskSectionTitle(title, modifier = Modifier.weight(1f))
        if (trailing != null) Text(trailing, style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
        if (level.isNotBlank()) LevelPill(level)
    }
}

@Composable
private fun LevelPill(level: String) {
    Surface(color = PompColors.GoldSoft, shape = RoundedCornerShape(999.dp)) {
        Text(
            dictionaryLevelLabel(level),
            style = MaterialTheme.typography.labelSmall,
            color = PompColors.InkSecondary,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
        )
    }
}

private fun dictionaryLevelLabel(level: String): String {
    val labels = level.split('|').map(String::trim).filter(String::isNotEmpty)
    val levelName = labels.firstOrNull().orEmpty()
    val isNewHsk = labels.drop(1).any { it.matches(Regex("N\\d+", RegexOption.IGNORE_CASE)) }
    return if (isNewHsk) "${levelName.uppercase()} · 3.0" else levelName
}

@Composable
private fun WordRow(word: DictionaryWord, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        shape = RectangleShape,
        color = PompColors.Paper,
    ) {
        Row(
            Modifier.fillMaxWidth().heightIn(min = 72.dp).padding(horizontal = 4.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(word.hanzi, style = PompTextStyles.hanziSmall, color = PompColors.Ink)
            Column(Modifier.weight(1f).padding(start = 14.dp)) {
                Text(word.pinyin, style = PompTextStyles.pinyin, color = PompColors.CinnabarDark)
                Text(word.meaning, style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
            }
            if (word.level.isNotBlank()) {
                Spacer(Modifier.width(10.dp))
                LevelPill(word.level)
            }
        }
    }
}

@Composable
private fun DictionarySkeleton() {
    HskContentSkeleton(
        rows = 6,
        compact = true,
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp, vertical = 8.dp),
    )
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
            HskGlassButton(
                text = stringResource(R.string.action_retry),
                onClick = onRetry,
            )
        }
    }
}

private val WORD_NAVIGATION_HEIGHT = 68.dp
