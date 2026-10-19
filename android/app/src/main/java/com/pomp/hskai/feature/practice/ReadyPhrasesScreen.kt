package com.pomp.hskai.feature.practice

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.outlined.StarOutline
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.settings.AppSettings
import com.pomp.hskai.core.text.PinyinSearch
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

@Serializable
private data class ReadyPhraseCatalog(
    val version: Int = 1,
    val categories: List<ReadyPhraseCategory> = emptyList(),
    val phrases: List<ReadyPhrase> = emptyList(),
)

@Serializable
private data class ReadyPhraseCategory(
    val id: String,
    val sort_order: Int = 0,
    val labels: Map<String, String> = emptyMap(),
)

@Serializable
private data class ReadyPhrase(
    val id: String,
    val category_id: String,
    val sort_order: Int = 0,
    val zh: String,
    val pinyin: String,
    val translations: Map<String, String> = emptyMap(),
)

private data class ReadyPhraseFilter(val id: String, val label: String)

@Composable
fun ReadyPhrasesScreen(
    language: String,
    settings: AppSettings,
    json: Json,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val clipboard = LocalClipboardManager.current
    val favorites by settings.readyPhraseFavorites.collectAsStateWithLifecycle(initialValue = emptySet())
    var catalog by remember { mutableStateOf<ReadyPhraseCatalog?>(null) }
    var loading by remember { mutableStateOf(true) }
    var loadError by remember { mutableStateOf(false) }
    var query by rememberSaveable { mutableStateOf("") }
    var selectedFilter by rememberSaveable { mutableStateOf("all") }

    fun load() {
        loading = true
        loadError = false
        scope.launch {
            val result = runCatching {
                withContext(Dispatchers.IO) {
                    context.assets.open("ready-phrases-v1.json").bufferedReader().use {
                        json.decodeFromString<ReadyPhraseCatalog>(it.readText())
                    }
                }
            }
            catalog = result.getOrNull()?.takeIf { it.phrases.isNotEmpty() && it.categories.isNotEmpty() }
            loadError = catalog == null
            loading = false
        }
    }

    LaunchedEffect(context, json) { load() }
    BackHandler(onBack = onBack)

    val currentCatalog = catalog
    val languageKey = language.takeIf { it in setOf("uz", "ru", "tj") } ?: "uz"
    val filters = remember(currentCatalog, languageKey) {
        buildList {
            add(ReadyPhraseFilter("all", ""))
            add(ReadyPhraseFilter("saved", ""))
            currentCatalog?.categories.orEmpty().sortedBy { it.sort_order }.forEach { category ->
                add(ReadyPhraseFilter(category.id, category.labels[languageKey].orEmpty()))
            }
        }
    }
    val visible = remember(currentCatalog, query, selectedFilter, favorites, languageKey) {
        val terms = query.trim().split(Regex("\\s+")).map(::normalizePhraseQuery).filter(String::isNotBlank)
        currentCatalog?.phrases.orEmpty().asSequence().filter { phrase ->
            val belongs = when (selectedFilter) {
                "all" -> true
                "saved" -> phrase.id in favorites
                else -> phrase.category_id == selectedFilter
            }
            belongs && terms.all { term -> searchablePhraseFields(phrase).any { it.contains(term) } }
        }.toList()
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(PompColors.Paper)
            .statusBarsPadding()
            .navigationBarsPadding()
            .padding(horizontal = 16.dp),
    ) {
        // A compact back control is enough here; search is the primary content.
        IconButton(
            onClick = onBack,
            modifier = Modifier.padding(top = 4.dp, bottom = 6.dp).size(44.dp),
        ) {
            Icon(
                Icons.AutoMirrored.Filled.ArrowBack,
                contentDescription = stringResource(R.string.ready_phrases_back),
            )
        }
        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            leadingIcon = { Icon(Icons.Filled.Search, contentDescription = null) },
            placeholder = { Text(stringResource(R.string.hsk_course_ready_phrases_search)) },
            shape = RoundedCornerShape(15.dp),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = PompColors.Cinnabar,
                unfocusedBorderColor = PompColors.Divider,
                focusedTextColor = PompColors.Ink,
                unfocusedTextColor = PompColors.Ink,
                focusedContainerColor = PompColors.PaperRaised,
                unfocusedContainerColor = PompColors.PaperRaised,
                focusedLeadingIconColor = PompColors.Cinnabar,
                unfocusedLeadingIconColor = PompColors.InkSecondary,
                focusedPlaceholderColor = PompColors.InkDisabled,
                unfocusedPlaceholderColor = PompColors.InkDisabled,
                cursorColor = PompColors.Cinnabar,
            ),
        )
        LazyRow(
            contentPadding = PaddingValues(vertical = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(7.dp),
        ) {
            items(filters, key = ReadyPhraseFilter::id) { filter ->
                val label = when (filter.id) {
                    "all" -> stringResource(R.string.hsk_course_ready_phrases_all)
                    "saved" -> stringResource(R.string.hsk_course_ready_phrases_saved)
                    else -> filter.label
                }
                FilterChip(
                    selected = selectedFilter == filter.id,
                    onClick = { selectedFilter = filter.id },
                    label = { Text(label, maxLines = 1) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = PompColors.CinnabarSoft,
                        selectedLabelColor = PompColors.CinnabarInk,
                        containerColor = PompColors.PaperRaised,
                        labelColor = PompColors.InkSecondary,
                    ),
                )
            }
        }
        val total = if (selectedFilter == "saved") favorites.size else currentCatalog?.phrases?.size ?: 0
        Text(
            stringResource(R.string.ready_phrases_count, visible.size, total),
            modifier = Modifier.padding(start = 2.dp, bottom = 8.dp),
            style = MaterialTheme.typography.labelMedium,
            color = PompColors.InkSecondary,
        )

        when {
            loading -> Column(
                modifier = Modifier.fillMaxSize(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) { CircularProgressIndicator(color = PompColors.Cinnabar) }
            loadError -> Column(
                modifier = Modifier.fillMaxSize(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                Text(stringResource(R.string.ready_phrases_load_failed), color = PompColors.InkSecondary)
                TextButton(onClick = ::load) { Text(stringResource(R.string.hsk_course_ready_phrases_retry)) }
            }
            visible.isEmpty() -> Column(
                modifier = Modifier.fillMaxSize(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                Text(
                    if (selectedFilter == "saved" && query.isBlank()) {
                        stringResource(R.string.hsk_course_ready_phrases_no_saved)
                    } else {
                        stringResource(R.string.ready_phrases_no_results)
                    },
                    color = PompColors.InkSecondary,
                )
            }
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(bottom = 24.dp),
                verticalArrangement = Arrangement.spacedBy(9.dp),
            ) {
                items(visible, key = ReadyPhrase::id) { phrase ->
                    val category = currentCatalog?.categories?.firstOrNull { it.id == phrase.category_id }
                    ReadyPhraseCard(
                        phrase = phrase,
                        category = category?.labels?.get(languageKey).orEmpty(),
                        translation = phrase.translations[languageKey].orEmpty(),
                        isSaved = phrase.id in favorites,
                        onSave = { scope.launch { settings.toggleReadyPhraseFavorite(phrase.id) } },
                        onCopy = { copyPhrase(context, clipboard, phrase.zh) },
                    )
                }
            }
        }
    }
}

@Composable
private fun ReadyPhraseCard(
    phrase: ReadyPhrase,
    category: String,
    translation: String,
    isSaved: Boolean,
    onSave: () -> Unit,
    onCopy: () -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(17.dp),
        color = PompColors.PaperRaised,
        shadowElevation = 2.dp,
    ) {
        Column(Modifier.padding(horizontal = 15.dp, vertical = 13.dp)) {
            Row(verticalAlignment = Alignment.Top) {
                Column(Modifier.weight(1f)) {
                    Text(phrase.zh, fontSize = 25.sp, lineHeight = 34.sp, color = PompColors.Ink, fontWeight = FontWeight.Medium)
                    Text(phrase.pinyin, style = MaterialTheme.typography.bodyMedium, color = PompColors.CinnabarInk, fontWeight = FontWeight.SemiBold)
                }
                IconButton(onClick = onSave, modifier = Modifier.size(38.dp)) {
                    Icon(
                        if (isSaved) Icons.Filled.Star else Icons.Outlined.StarOutline,
                        contentDescription = stringResource(if (isSaved) R.string.hsk_course_ready_phrases_saved else R.string.hsk_course_ready_phrases_save),
                        tint = if (isSaved) PompColors.Gold else PompColors.InkSecondary,
                    )
                }
            }
            Spacer(Modifier.height(5.dp))
            Text(translation, style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
            Row(
                modifier = Modifier.fillMaxWidth().padding(top = 9.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(category, modifier = Modifier.weight(1f), style = MaterialTheme.typography.labelSmall, color = PompColors.InkSecondary, maxLines = 1, overflow = TextOverflow.Ellipsis)
                TextButton(onClick = onCopy, contentPadding = PaddingValues(horizontal = 8.dp)) {
                    Icon(Icons.Filled.ContentCopy, contentDescription = null, modifier = Modifier.size(15.dp))
                    Text(stringResource(R.string.ready_phrases_copy), modifier = Modifier.padding(start = 5.dp), style = MaterialTheme.typography.labelMedium)
                }
            }
        }
    }
}

private fun searchablePhraseFields(phrase: ReadyPhrase): List<String> =
    listOf(phrase.zh, PinyinSearch.plain(phrase.pinyin)) + phrase.translations.values.map(::normalizePhraseQuery)

private fun normalizePhraseQuery(value: String): String =
    PinyinSearch.plain(value).ifBlank { value.lowercase() }

private fun copyPhrase(context: Context, clipboard: androidx.compose.ui.platform.ClipboardManager, value: String) {
    runCatching {
        clipboard.setText(AnnotatedString(value))
        Toast.makeText(context, R.string.ready_phrases_copied, Toast.LENGTH_SHORT).show()
    }.onFailure {
        runCatching {
            val service = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            service.setPrimaryClip(ClipData.newPlainText("Chinese phrase", value))
        }
    }
}
