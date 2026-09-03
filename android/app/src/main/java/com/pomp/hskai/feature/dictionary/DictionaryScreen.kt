package com.pomp.hskai.feature.dictionary

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Search
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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.data.repository.DictionaryWord

/**
 * The character dictionary: search, character, reading, meaning, HSK level.
 *
 * The word list is the Mini App's own, downloaded once and read from the
 * device afterwards, so it opens instantly and keeps working offline.
 */
@Composable
fun DictionaryScreen(
    state: DictionaryUiState,
    onQueryChange: (String) -> Unit,
    onRetry: () -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        Column(Modifier.fillMaxSize()) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(start = 4.dp, end = 16.dp, top = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(onClick = onBack) {
                    Icon(
                        Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = stringResource(R.string.action_back),
                        tint = PompColors.Ink,
                    )
                }
                Text(
                    text = stringResource(R.string.practice_dictionary_title),
                    style = MaterialTheme.typography.titleLarge,
                    color = PompColors.Ink,
                    modifier = Modifier.weight(1f),
                )
                if (state.total > 0) {
                    Text(
                        text = state.total.toString(),
                        style = MaterialTheme.typography.bodyMedium,
                        color = PompColors.InkSecondary,
                    )
                }
            }

            OutlinedTextField(
                value = state.query,
                onValueChange = onQueryChange,
                singleLine = true,
                placeholder = {
                    Text(
                        text = stringResource(R.string.dictionary_search_hint),
                        color = PompColors.InkDisabled,
                    )
                },
                leadingIcon = {
                    Icon(
                        Icons.Filled.Search,
                        contentDescription = null,
                        tint = PompColors.InkSecondary,
                    )
                },
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
                    .padding(horizontal = 20.dp, vertical = 10.dp),
            )

            when {
                state.isLoading && state.words.isEmpty() -> Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator(color = PompColors.Cinnabar)
                }

                state.isUnavailable -> DictionaryMessage(
                    text = stringResource(
                        state.error?.messageRes ?: R.string.dictionary_unavailable
                    ),
                    onRetry = onRetry,
                )

                state.words.isEmpty() -> DictionaryMessage(
                    text = stringResource(R.string.dictionary_no_match, state.query),
                    onRetry = null,
                )

                else -> LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(horizontal = 20.dp, vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(state.words, key = { it.hanzi }) { word -> WordRow(word) }
                }
            }
        }
    }
}

@Composable
private fun WordRow(word: DictionaryWord) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = word.hanzi,
                style = PompTextStyles.hanziSmall,
                color = PompColors.Ink,
            )
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(start = 14.dp),
            ) {
                Text(
                    text = word.pinyin,
                    style = PompTextStyles.pinyin,
                    color = PompColors.CinnabarDark,
                )
                Text(
                    text = word.meaning,
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                )
            }
            if (word.level.isNotBlank()) {
                Spacer(Modifier.width(10.dp))
                Surface(color = PompColors.GoldSoft, shape = RoundedCornerShape(999.dp)) {
                    Text(
                        text = word.level,
                        style = MaterialTheme.typography.labelSmall,
                        color = PompColors.InkSecondary,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun DictionaryMessage(text: String, onRetry: (() -> Unit)?) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
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
                Text(
                    text = stringResource(R.string.action_retry),
                    color = PompColors.CinnabarDark,
                )
            }
        }
    }
}
