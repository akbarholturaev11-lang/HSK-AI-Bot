package com.pomp.hskai.feature.practice

import android.content.Intent
import android.net.Uri
import android.speech.tts.TextToSpeech
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Code
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Trophy
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material.icons.filled.WifiOff
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.core.navigation.AppDestination
import com.pomp.hskai.core.navigation.DeepLinkRouter
import com.pomp.hskai.data.api.MistakeItemDto
import com.pomp.hskai.data.api.MistakeReviewAnswerResponse
import com.pomp.hskai.data.api.MistakeReviewCompleteResponse
import com.pomp.hskai.data.api.MistakeReviewQuestionDto
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonPrimitive
import java.util.Locale

private const val MISTAKES_VISIBLE_PAGE = 30

@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun MistakesOverviewScreen(
    state: PracticeUiState,
    onBack: () -> Unit,
    onStartReview: () -> Unit,
    onReload: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val overview = state.mistakes
    val total = overview?.summary?.total ?: 0
    var category by rememberSaveable { mutableStateOf("all") }
    var visibleCount by rememberSaveable { mutableIntStateOf(MISTAKES_VISIBLE_PAGE) }

    val availableCategories = remember(overview?.summary?.categories) {
        buildList {
            add("all")
            listOf("word", "grammar", "character", "pronunciation").forEach { key ->
                if ((overview?.summary?.categories?.get(key) ?: 0) > 0) add(key)
            }
        }
    }
    if (category !in availableCategories) category = "all"

    val filteredItems = remember(overview?.items, category) {
        overview?.items.orEmpty().filter { category == "all" || it.category == category }
    }
    val shownItems = filteredItems.take(visibleCount)

    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 14.dp, bottom = 20.dp),
    ) {
        item {
            MistakesHeader(onBack = onBack)
            Text(
                text = stringResource(R.string.mistakes_subtitle),
                fontSize = 13.sp,
                color = PompColors.InkSecondary,
                modifier = Modifier.padding(top = 2.dp, bottom = 14.dp),
            )
        }

        when {
            state.isLoadingMistakes && overview == null -> item {
                MistakesState(icon = null, text = stringResource(R.string.mistakes_loading), loading = true)
            }
            overview == null -> item {
                MistakesState(
                    icon = Icons.Filled.WifiOff,
                    text = stringResource(R.string.mistakes_load_error),
                    action = stringResource(R.string.mistakes_retry),
                    onAction = onReload,
                    destructive = true,
                )
            }
            total <= 0 -> item {
                MistakesEmpty(
                    onCourse = {
                        val uri = Uri.parse(DeepLinkRouter.uriFor(AppDestination.Course))
                        runCatching {
                            context.startActivity(Intent(Intent.ACTION_VIEW, uri).setPackage(context.packageName))
                        }
                    },
                )
            }
            else -> {
                item {
                    MistakesReviewCta(total = total, busy = state.isStarting, onStartReview = onStartReview)
                    Spacer(Modifier.height(14.dp))
                    LazyRow(
                        horizontalArrangement = Arrangement.spacedBy(7.dp),
                        contentPadding = PaddingValues(bottom = 2.dp),
                    ) {
                        items(availableCategories, key = { it }) { key ->
                            val count = if (key == "all") total else overview.summary.categories[key] ?: 0
                            MistakeCategoryChip(
                                text = "${mistakeCategoryLabel(key)} · $count",
                                selected = category == key,
                                onClick = {
                                    category = key
                                    visibleCount = MISTAKES_VISIBLE_PAGE
                                },
                            )
                        }
                    }
                    Spacer(Modifier.height(12.dp))
                }

                if (shownItems.isEmpty()) {
                    item {
                        MistakesState(
                            icon = Icons.Filled.WarningAmber,
                            text = stringResource(R.string.mistakes_empty_title),
                        )
                    }
                } else {
                    items(shownItems, key = { it.id }) { item ->
                        MistakeCard(item)
                        Spacer(Modifier.height(10.dp))
                    }
                }

                if (filteredItems.size > visibleCount) {
                    item {
                        Surface(
                            color = PompColors.PaperRaised,
                            shape = RoundedCornerShape(13.dp),
                            border = BorderStroke(1.dp, PompColors.Divider),
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(top = 2.dp, bottom = 12.dp)
                                .clickable {
                                    visibleCount = (visibleCount + MISTAKES_VISIBLE_PAGE).coerceAtMost(filteredItems.size)
                                },
                        ) {
                            Row(
                                horizontalArrangement = Arrangement.Center,
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier.padding(13.dp),
                            ) {
                                Icon(
                                    imageVector = Icons.Filled.KeyboardArrowDown,
                                    contentDescription = null,
                                    tint = PompColors.InkSecondary,
                                    modifier = Modifier.size(18.dp),
                                )
                                Spacer(Modifier.width(6.dp))
                                Text(
                                    text = stringResource(R.string.mistakes_more),
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = PompColors.InkSecondary,
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun MistakesHeader(onBack: () -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(11.dp),
        modifier = Modifier.padding(bottom = 6.dp),
    ) {
        Surface(
            color = PompColors.PaperRaised,
            shape = RoundedCornerShape(999.dp),
            border = BorderStroke(1.dp, PompColors.Divider),
            modifier = Modifier.size(32.dp).clickable(onClick = onBack),
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = stringResource(R.string.practice_back_to_tools),
                    tint = PompColors.InkSecondary,
                    modifier = Modifier.size(18.dp),
                )
            }
        }
        Text(
            text = stringResource(R.string.mistakes_title),
            fontSize = 23.sp,
            fontWeight = FontWeight.Bold,
            color = PompColors.Ink,
        )
    }
}

@Composable
private fun MistakesReviewCta(total: Int, busy: Boolean, onStartReview: () -> Unit) {
    val foreground = if (PompColors.IsDark) PompColors.Ink else Color.White
    val surface = if (PompColors.IsDark) PompColors.PaperRaised else PompColors.Ink
    Surface(
        color = surface,
        shape = RoundedCornerShape(18.dp),
        border = if (PompColors.IsDark) BorderStroke(1.dp, PompColors.Divider) else null,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Box {
            Text(
                text = "错",
                style = PompTextStyles.hanziMedium,
                fontSize = 84.sp,
                color = foreground.copy(alpha = 0.06f),
                modifier = Modifier.align(Alignment.TopEnd).padding(end = 2.dp),
            )
            Column(Modifier.padding(17.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Filled.Refresh, contentDescription = null, tint = foreground, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(8.dp))
                    Text(
                        text = stringResource(R.string.mistakes_review),
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Medium,
                        color = foreground,
                    )
                }
                Text(
                    text = "$total ${stringResource(R.string.mistakes_review_subtitle)}",
                    fontSize = 13.sp,
                    color = foreground.copy(alpha = 0.72f),
                    modifier = Modifier.padding(top = 5.dp, bottom = 13.dp),
                )
                Button(
                    onClick = onStartReview,
                    enabled = !busy,
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = PompColors.Cinnabar,
                        contentColor = PompColors.Paper,
                    ),
                    contentPadding = PaddingValues(horizontal = 18.dp, vertical = 12.dp),
                ) {
                    if (busy) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(16.dp),
                            strokeWidth = 2.dp,
                            color = PompColors.Paper,
                        )
                    } else {
                        Icon(Icons.Filled.PlayArrow, contentDescription = null, modifier = Modifier.size(18.dp))
                    }
                    Spacer(Modifier.width(7.dp))
                    Text(
                        text = if (busy) stringResource(R.string.mistakes_loading) else stringResource(R.string.mistakes_start),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Medium,
                    )
                }
            }
        }
    }
}

@Composable
private fun MistakeCategoryChip(text: String, selected: Boolean, onClick: () -> Unit) {
    Surface(
        color = if (selected) PompColors.Cinnabar else PompColors.PaperRaised,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, if (selected) PompColors.Cinnabar else PompColors.Divider),
        modifier = Modifier.clickable(onClick = onClick),
    ) {
        Text(
            text = text,
            fontSize = 12.sp,
            fontWeight = FontWeight.Medium,
            color = if (selected) PompColors.Paper else PompColors.InkSecondary,
            modifier = Modifier.padding(horizontal = 13.dp, vertical = 7.dp),
        )
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun MistakeCard(item: MistakeItemDto) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(15.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.padding(13.dp),
        ) {
            Surface(
                color = PompColors.FlameSoft,
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.size(44.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = mistakeCategoryIcon(item.category),
                        contentDescription = null,
                        tint = PompColors.Flame,
                        modifier = Modifier.size(20.dp),
                    )
                }
            }

            Column(Modifier.weight(1f)) {
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                    modifier = Modifier.padding(bottom = 5.dp),
                ) {
                    MistakeMetaTag(mistakeCategoryLabel(item.category))
                    val source = mistakeSourceLabel(item.source)
                    if (source.isNotBlank()) MistakeMetaTag(source)
                    item.lesson?.takeIf { it > 0 }?.let { lesson ->
                        MistakeMetaTag("${stringResource(R.string.mistakes_lesson)} $lesson")
                    }
                }

                Text(item.question, fontSize = 17.sp, fontWeight = FontWeight.Bold, color = PompColors.Ink)
                if (item.sentence.isNotBlank() && item.sentence != item.question) {
                    Text(
                        text = item.sentence,
                        style = PompTextStyles.hanziSmall,
                        fontSize = 16.sp,
                        lineHeight = 23.sp,
                        color = PompColors.Ink,
                        modifier = Modifier.padding(top = 5.dp),
                    )
                }
                if (item.pinyin.isNotBlank()) {
                    Text(
                        text = item.pinyin,
                        fontSize = 12.sp,
                        color = PompColors.Cinnabar,
                        modifier = Modifier.padding(top = 2.dp),
                    )
                }
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.padding(top = 3.dp)) {
                    item.userAnswer?.takeIf { it.isNotBlank() }?.let { wrong ->
                        Text(text = "✗ $wrong", fontSize = 12.sp, color = PompColors.Flame)
                    }
                    Text(text = "✓ ${item.correctAnswer}", fontSize = 12.sp, color = PompColors.Jade)
                }
            }

            Surface(color = PompColors.FlameSoft, shape = RoundedCornerShape(9.dp)) {
                Text(
                    text = "${maxOf(item.count, 1)}×",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = PompColors.Flame,
                    modifier = Modifier.padding(horizontal = 7.dp, vertical = 2.dp),
                )
            }
        }
    }
}

@Composable
private fun MistakeMetaTag(text: String) {
    Surface(
        color = if (PompColors.IsDark) PompColors.OptionDepth else PompColors.Paper,
        shape = RoundedCornerShape(7.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
    ) {
        Text(
            text = text,
            fontSize = 10.sp,
            color = PompColors.InkSecondary,
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
        )
    }
}

@Composable
private fun MistakesEmpty(onCourse: () -> Unit) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
        modifier = Modifier.fillMaxWidth().heightIn(min = 420.dp).padding(horizontal = 24.dp, vertical = 60.dp),
    ) {
        Surface(color = PompColors.JadeSoft, shape = RoundedCornerShape(22.dp), modifier = Modifier.size(84.dp)) {
            Box(contentAlignment = Alignment.Center) {
                Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = PompColors.Jade, modifier = Modifier.size(38.dp))
            }
        }
        Text(
            text = stringResource(R.string.mistakes_empty_title),
            fontSize = 19.sp,
            fontWeight = FontWeight.Medium,
            color = PompColors.Ink,
            modifier = Modifier.padding(top = 16.dp),
        )
        Text(
            text = stringResource(R.string.mistakes_empty_subtitle),
            fontSize = 14.sp,
            lineHeight = 21.sp,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 6.dp, bottom = 22.dp),
        )
        Button(
            onClick = onCourse,
            shape = RoundedCornerShape(13.dp),
            colors = ButtonDefaults.buttonColors(containerColor = PompColors.Cinnabar, contentColor = PompColors.Paper),
            contentPadding = PaddingValues(horizontal = 22.dp, vertical = 13.dp),
        ) {
            Text(text = stringResource(R.string.mistakes_to_course), fontSize = 14.sp, fontWeight = FontWeight.Medium)
        }
    }
}

@Composable
private fun MistakesState(
    icon: ImageVector?,
    text: String,
    loading: Boolean = false,
    action: String? = null,
    onAction: () -> Unit = {},
    destructive: Boolean = false,
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
        modifier = Modifier.fillMaxWidth().heightIn(min = 320.dp),
    ) {
        val stateColor = if (destructive) PompColors.Flame else PompColors.Cinnabar
        when {
            loading -> CircularProgressIndicator(color = PompColors.Cinnabar, modifier = Modifier.size(30.dp), strokeWidth = 2.5.dp)
            icon != null -> Icon(imageVector = icon, contentDescription = null, tint = stateColor, modifier = Modifier.size(30.dp))
        }
        Spacer(Modifier.height(9.dp))
        Text(text = text, fontSize = 14.sp, color = PompColors.InkSecondary, textAlign = TextAlign.Center)
        if (action != null) {
            Spacer(Modifier.height(14.dp))
            Button(
                onClick = onAction,
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = PompColors.Cinnabar, contentColor = PompColors.Paper),
                contentPadding = PaddingValues(horizontal = 20.dp, vertical = 12.dp),
            ) {
                Text(action, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
            }
        }
    }
}

@Composable
internal fun MistakesReviewRun(
    state: PracticeUiState,
    onSelect: (Int) -> Unit,
    onAdvance: () -> Unit,
    onCancel: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val session = state.reviewSession ?: return
    val question = session.questions.getOrNull(state.reviewIndex) ?: return
    val speaker = rememberMistakeSpeaker()
    val progress = if (session.questions.isEmpty()) 0f else state.reviewIndex.toFloat() / session.questions.size.toFloat()

    Column(modifier = modifier.fillMaxSize().background(PompColors.Paper)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, top = 12.dp, bottom = 8.dp),
        ) {
            Surface(
                color = PompColors.PaperRaised,
                shape = RoundedCornerShape(999.dp),
                border = BorderStroke(1.dp, PompColors.Divider),
                modifier = Modifier.size(32.dp).clickable(onClick = onCancel),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(Icons.Filled.Close, contentDescription = stringResource(R.string.action_close), tint = PompColors.InkSecondary, modifier = Modifier.size(18.dp))
                }
            }
            Box(
                modifier = Modifier.weight(1f).height(7.dp).clip(RoundedCornerShape(4.dp)).background(PompColors.Divider),
            ) {
                Box(
                    modifier = Modifier.fillMaxHeight().fillMaxWidth(progress.coerceIn(0f, 1f)).background(PompColors.Cinnabar),
                )
            }
        }

        LazyColumn(
            modifier = Modifier.weight(1f),
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 14.dp, bottom = 8.dp),
        ) {
            item {
                Text(
                    text = "${mistakeCategoryLabel(question.category)} · ${stringResource(R.string.mistakes_question)} ${state.reviewIndex + 1} ${stringResource(R.string.mistakes_of)} ${session.questions.size}",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                    letterSpacing = 0.4.sp,
                    color = PompColors.Cinnabar,
                    modifier = Modifier.padding(bottom = 8.dp),
                )
                Text(
                    text = question.prompt,
                    fontSize = 26.sp,
                    lineHeight = 35.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = PompColors.Ink,
                    modifier = Modifier.padding(bottom = 20.dp),
                )
                if (question.audioText.isNotBlank() || question.sentence.isNotBlank() || question.pinyin.isNotBlank()) {
                    ReviewMaterial(question = question, onSpeak = { speaker(question.audioText) })
                    Spacer(Modifier.height(16.dp))
                }
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    question.options.forEachIndexed { index, option ->
                        MistakeReviewOption(
                            index = index,
                            text = option,
                            selectedIndex = state.reviewSelectedIndex,
                            feedback = state.reviewFeedback,
                            onClick = { onSelect(index) },
                        )
                    }
                }
                state.reviewFeedback?.let { MistakeFeedback(feedback = it) }
            }
        }

        if (state.reviewFeedback != null) {
            Button(
                onClick = onAdvance,
                enabled = !state.isCompleting,
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = PompColors.Cinnabar,
                    contentColor = PompColors.Paper,
                ),
                modifier = Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, top = 10.dp, bottom = 16.dp).heightIn(min = 54.dp),
            ) {
                if (state.isCompleting) {
                    CircularProgressIndicator(color = PompColors.Paper, modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                    Spacer(Modifier.width(8.dp))
                    Text(stringResource(R.string.mistakes_loading))
                } else if (state.reviewIndex >= session.questions.lastIndex) {
                    Icon(Icons.Filled.Check, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(8.dp))
                    Text(stringResource(R.string.mistakes_finish), fontSize = 16.sp, fontWeight = FontWeight.Medium)
                } else {
                    Text(stringResource(R.string.mistakes_next), fontSize = 16.sp, fontWeight = FontWeight.Medium)
                    Spacer(Modifier.width(8.dp))
                    Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = null, modifier = Modifier.size(18.dp))
                }
            }
        }
    }
}

@Composable
private fun ReviewMaterial(question: MistakeReviewQuestionDto, onSpeak: () -> Unit) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(14.dp)) {
            if (question.audioText.isNotBlank()) {
                Surface(
                    color = PompColors.CinnabarSoft,
                    shape = RoundedCornerShape(999.dp),
                    modifier = Modifier.size(42.dp).clickable(onClick = onSpeak),
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(Icons.Filled.VolumeUp, contentDescription = null, tint = PompColors.Cinnabar, modifier = Modifier.size(20.dp))
                    }
                }
                Spacer(Modifier.height(8.dp))
            }
            if (question.sentence.isNotBlank()) {
                Text(
                    text = question.sentence,
                    style = PompTextStyles.hanziMedium,
                    fontSize = 24.sp,
                    lineHeight = 34.sp,
                    color = PompColors.Ink,
                    textAlign = TextAlign.Center,
                )
            }
            if (question.pinyin.isNotBlank()) {
                Text(
                    text = question.pinyin,
                    fontSize = 13.sp,
                    color = PompColors.Cinnabar,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 3.dp),
                )
            }
        }
    }
}

@Composable
private fun MistakeReviewOption(
    index: Int,
    text: String,
    selectedIndex: Int?,
    feedback: MistakeReviewAnswerResponse?,
    onClick: () -> Unit,
) {
    val picked = selectedIndex == index
    val correct = feedback != null && feedback.correctIndex == index
    val wrong = feedback != null && picked && !correct
    val border = when {
        correct -> PompColors.Jade
        wrong -> PompColors.Flame
        else -> PompColors.Divider
    }
    val background = when {
        correct -> PompColors.JadeSoft
        wrong -> PompColors.FlameSoft
        else -> PompColors.PaperRaised
    }
    val rankBackground = when {
        correct -> PompColors.Jade
        wrong -> PompColors.Flame
        else -> if (PompColors.IsDark) PompColors.OptionDepth else PompColors.Paper
    }
    val rankColor = if (correct || wrong) PompColors.Paper else PompColors.InkSecondary

    Surface(
        color = background,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.5.dp, border),
        modifier = Modifier.fillMaxWidth().clickable(enabled = feedback == null && selectedIndex == null, onClick = onClick),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(11.dp),
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 15.dp),
        ) {
            Surface(
                color = rankBackground,
                shape = RoundedCornerShape(8.dp),
                border = BorderStroke(1.dp, if (correct || wrong) rankBackground else PompColors.Divider),
                modifier = Modifier.size(26.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(text = optionRank(index), fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = rankColor)
                }
            }
            Text(text = text, fontSize = 16.sp, color = PompColors.Ink, modifier = Modifier.weight(1f))
        }
    }
}

@Composable
private fun MistakeFeedback(feedback: MistakeReviewAnswerResponse) {
    val correct = feedback.correct
    Surface(
        color = if (correct) PompColors.JadeSoft else PompColors.FlameSoft,
        shape = RoundedCornerShape(14.dp),
        modifier = Modifier.fillMaxWidth().padding(top = 18.dp),
    ) {
        Column(Modifier.padding(horizontal = 16.dp, vertical = 14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = if (correct) Icons.Filled.CheckCircle else Icons.Filled.WarningAmber,
                    contentDescription = null,
                    tint = if (correct) PompColors.Jade else PompColors.Flame,
                    modifier = Modifier.size(18.dp),
                )
                Spacer(Modifier.width(7.dp))
                Text(
                    text = stringResource(if (correct) R.string.mistakes_correct else R.string.mistakes_wrong),
                    fontSize = 15.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = if (correct) PompColors.Jade else PompColors.Flame,
                )
            }
            if (!correct) {
                Text(
                    text = "${stringResource(R.string.mistakes_explanation)}: ${feedback.correctAnswer}",
                    fontSize = 14.sp,
                    lineHeight = 21.sp,
                    color = PompColors.Flame,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
            if (feedback.explanation.isNotBlank() && feedback.explanation != feedback.correctAnswer) {
                Text(
                    text = feedback.explanation,
                    fontSize = 14.sp,
                    lineHeight = 21.sp,
                    color = PompColors.InkSecondary,
                    modifier = Modifier.padding(top = 6.dp),
                )
            }
        }
    }
}

@Composable
internal fun MistakesReviewResult(
    result: MistakeReviewCompleteResponse,
    onDone: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val awardedXp = result.reward?.get("awarded_xp")?.jsonPrimitive?.intOrNull ?: 0

    Column(modifier = modifier.fillMaxSize().background(PompColors.Paper)) {
        Box(Modifier.weight(1f)) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.fillMaxWidth().padding(horizontal = 24.dp, vertical = 40.dp),
            ) {
                Surface(color = PompColors.JadeSoft, shape = RoundedCornerShape(24.dp), modifier = Modifier.size(88.dp)) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(Icons.Filled.Trophy, contentDescription = null, tint = PompColors.Jade, modifier = Modifier.size(42.dp))
                    }
                }
                Text(
                    text = stringResource(R.string.mistakes_result_title),
                    fontSize = 22.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = PompColors.Ink,
                    modifier = Modifier.padding(top = 18.dp, bottom = 8.dp),
                )
                Text(
                    text = "${result.score} / ${result.total}",
                    fontSize = 40.sp,
                    fontWeight = FontWeight.Bold,
                    color = PompColors.Cinnabar,
                    modifier = Modifier.padding(vertical = 4.dp),
                )
                Text(text = stringResource(R.string.mistakes_result_score_label), fontSize = 13.sp, color = PompColors.InkSecondary)
                if (awardedXp > 0) {
                    Surface(color = PompColors.GoldSoft, shape = RoundedCornerShape(10.dp), modifier = Modifier.padding(vertical = 8.dp)) {
                        Text(
                            text = "+$awardedXp XP",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = PompColors.Gold,
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 5.dp),
                        )
                    }
                }
                Text(
                    text = if (result.remaining > 0) {
                        "${stringResource(R.string.mistakes_result_remaining)}: ${result.remaining}"
                    } else {
                        stringResource(R.string.mistakes_result_all)
                    },
                    fontSize = 14.sp,
                    color = PompColors.InkSecondary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 6.dp),
                )
            }
        }

        Button(
            onClick = onDone,
            shape = RoundedCornerShape(14.dp),
            colors = ButtonDefaults.buttonColors(containerColor = PompColors.Cinnabar, contentColor = PompColors.Paper),
            modifier = Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, top = 10.dp, bottom = 16.dp).heightIn(min = 54.dp),
        ) {
            Icon(Icons.Filled.Check, contentDescription = null, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text(text = stringResource(R.string.mistakes_done), fontSize = 16.sp, fontWeight = FontWeight.Medium)
        }
    }
}

@Composable
private fun rememberMistakeSpeaker(): (String) -> Unit {
    val context = LocalContext.current.applicationContext
    var ready by remember { mutableStateOf(false) }
    val tts = remember(context) {
        TextToSpeech(context) { status -> ready = status == TextToSpeech.SUCCESS }
    }
    DisposableEffect(tts) {
        onDispose {
            tts.stop()
            tts.shutdown()
        }
    }
    LaunchedEffect(ready) {
        if (ready) {
            tts.language = Locale.SIMPLIFIED_CHINESE
            tts.setSpeechRate(0.9f)
        }
    }
    return remember(tts, ready) {
        { text: String ->
            if (ready && text.isNotBlank()) {
                tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "mistake-review")
            }
        }
    }
}

@Composable
private fun mistakeCategoryLabel(category: String): String = stringResource(
    when (category) {
        "all" -> R.string.mistakes_all
        "word" -> R.string.mistakes_cat_word
        "grammar" -> R.string.mistakes_cat_grammar
        "character" -> R.string.mistakes_cat_character
        "pronunciation" -> R.string.mistakes_cat_pronunciation
        else -> R.string.mistakes_question
    },
)

@Composable
private fun mistakeSourceLabel(source: String): String = when (source) {
    "lesson" -> stringResource(R.string.mistakes_source_lesson)
    "test" -> stringResource(R.string.mistakes_source_test)
    "training" -> stringResource(R.string.mistakes_source_training)
    "challenge" -> stringResource(R.string.mistakes_source_challenge)
    "voice" -> stringResource(R.string.mistakes_source_voice)
    else -> source
}

private fun mistakeCategoryIcon(category: String): ImageVector = when (category) {
    "word" -> Icons.Filled.Language
    "grammar" -> Icons.Filled.Code
    "character" -> Icons.Filled.Edit
    "pronunciation" -> Icons.Filled.Mic
    else -> Icons.Filled.WarningAmber
}

private fun optionRank(index: Int): String = when (index) {
    0 -> "A"
    1 -> "B"
    2 -> "C"
    3 -> "D"
    else -> (index + 1).toString()
}
