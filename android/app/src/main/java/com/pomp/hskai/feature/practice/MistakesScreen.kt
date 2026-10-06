package com.pomp.hskai.feature.practice

import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import com.pomp.hskai.core.design.components.HskAnswerOption
import com.pomp.hskai.core.design.components.HskSceneBackground
import com.pomp.hskai.core.design.components.HskStageCoach
import com.pomp.hskai.core.design.components.HskStageHeading
import com.pomp.hskai.core.design.components.hskOptionState
import com.pomp.hskai.core.navigation.LocalMainBottomInset
import android.content.Intent
import android.net.Uri
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
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Code
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Trophy
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material.icons.filled.WifiOff
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskBrandLoader
import com.pomp.hskai.core.design.components.HskGlassIconButton
import com.pomp.hskai.core.design.components.HskGlassSurface
import com.pomp.hskai.core.design.components.HskCoachBeside
import com.pomp.hskai.core.design.components.HskPrimaryButton
import com.pomp.hskai.core.design.components.hskReactionFor
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.core.navigation.AppDestination
import com.pomp.hskai.core.navigation.DeepLinkRouter
import com.pomp.hskai.data.api.MistakeTargetDto
import com.pomp.hskai.data.api.MistakeReviewAnswerResponse
import com.pomp.hskai.data.api.MistakeReviewCompleteResponse
import com.pomp.hskai.data.api.MistakeReviewQuestionDto
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonPrimitive

private const val MISTAKES_VISIBLE_PAGE = 30

@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun MistakesOverviewScreen(
    state: PracticeUiState,
    onBack: () -> Unit,
    onStartReview: () -> Unit,
    onReload: () -> Unit,
    onSelectCategory: (String) -> Unit = {},
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val overview = state.mistakes
    val total = overview?.summary?.total ?: 0
    // The chip lives in the view model: it also scopes the review that Start
    // opens, so the list and the review never disagree about the category.
    val category = state.mistakeCategory
    var visibleCount by rememberSaveable { mutableIntStateOf(MISTAKES_VISIBLE_PAGE) }

    val availableCategories = remember(overview?.summary?.categories) {
        buildList {
            add("all")
            listOf("word", "grammar", "character", "pronunciation").forEach { key ->
                if ((overview?.summary?.categories?.get(key) ?: 0) > 0) add(key)
            }
        }
    }
    if (category !in availableCategories && overview != null) onSelectCategory("all")

    val filteredItems = remember(overview?.targets, category) {
        overview?.targets.orEmpty().filter { category == "all" || it.category == category }
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
                    val scopeCount = if (category == "all") total else overview.summary.categories[category] ?: 0
                    MistakesReviewCta(
                        title = if (category == "all") {
                            stringResource(R.string.mistakes_review)
                        } else {
                            stringResource(R.string.mistakes_review_category, mistakeCategoryLabel(category))
                        },
                        count = scopeCount,
                        busy = state.isStarting,
                        onStartReview = onStartReview,
                    )
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
                                    onSelectCategory(key)
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
                        MistakeTargetCard(item)
                        Spacer(Modifier.height(10.dp))
                    }
                }

                if (filteredItems.size > visibleCount) {
                    item {
                        HskGlassSurface(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(top = 2.dp, bottom = 12.dp),
                            shape = RoundedCornerShape(13.dp),
                            shadowElevation = 4.dp,
                            onClick = {
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
        HskGlassIconButton(
            icon = Icons.AutoMirrored.Filled.ArrowBack,
            contentDescription = stringResource(R.string.practice_back_to_tools),
            onClick = onBack,
            size = 32.dp,
            iconSize = 18.dp,
            tint = PompColors.InkSecondary,
        )
        Text(
            text = stringResource(R.string.mistakes_title),
            fontSize = 23.sp,
            fontWeight = FontWeight.Bold,
            color = PompColors.Ink,
        )
    }
}

@Composable
private fun MistakesReviewCta(title: String, count: Int, busy: Boolean, onStartReview: () -> Unit) {
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
                        text = title,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Medium,
                        color = foreground,
                    )
                }
                Text(
                    text = stringResource(R.string.mistakes_review_count, count),
                    fontSize = 13.sp,
                    color = foreground.copy(alpha = 0.72f),
                    modifier = Modifier.padding(top = 5.dp, bottom = 13.dp),
                )
                HskPrimaryButton(
                    text = stringResource(R.string.mistakes_start),
                    onClick = onStartReview,
                    enabled = !busy,
                    loading = busy,
                )
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

/**
 * One thing the learner got wrong: the word or sentence with its pinyin and
 * meaning, what they answered instead, and how many of its three exercises
 * are already passed.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun MistakeTargetCard(item: MistakeTargetDto) {
    HskGlassSurface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(15.dp),
        shadowElevation = 5.dp,
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
                    val categoryLabel = mistakeCategoryLabel(item.category)
                    MistakeMetaTag(categoryLabel)
                    val source = mistakeSourceLabel(item.sources.firstOrNull().orEmpty())
                    if (source.isNotBlank() && source != categoryLabel) MistakeMetaTag(source)
                }

                if (item.kind == "question") {
                    Text(
                        text = item.question.ifBlank { item.zh },
                        fontSize = 17.sp,
                        fontWeight = FontWeight.Bold,
                        color = PompColors.Ink,
                    )
                    if (item.zh.isNotBlank() && item.zh != item.question) {
                        Text(
                            text = item.zh,
                            style = PompTextStyles.hanziSmall,
                            fontSize = 16.sp,
                            lineHeight = 23.sp,
                            color = PompColors.Ink,
                            modifier = Modifier.padding(top = 5.dp),
                        )
                    }
                } else {
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(7.dp),
                        verticalArrangement = Arrangement.Center,
                    ) {
                        Text(
                            text = item.zh,
                            style = PompTextStyles.hanziMedium,
                            fontSize = 20.sp,
                            lineHeight = 28.sp,
                            color = PompColors.Ink,
                        )
                        if (item.pinyin.isNotBlank()) {
                            Text(
                                text = item.pinyin,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Medium,
                                color = PompColors.Cinnabar,
                                modifier = Modifier.align(Alignment.CenterVertically),
                            )
                        }
                    }
                    val meaning = item.meaning.ifBlank { item.translation }
                    if (meaning.isNotBlank()) {
                        Text(
                            text = meaning,
                            fontSize = 13.sp,
                            lineHeight = 18.sp,
                            color = PompColors.InkSecondary,
                            modifier = Modifier.padding(top = 2.dp),
                        )
                    }
                }
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.padding(top = 3.dp)) {
                    if (item.wrong.isNotBlank()) {
                        Text(text = "✗ ${item.wrong}", fontSize = 12.sp, color = PompColors.FlameInk)
                    }
                    if (item.kind == "question" && item.answer.isNotBlank()) {
                        Text(text = "✓ ${item.answer}", fontSize = 12.sp, color = PompColors.JadeInk)
                    }
                }
            }

            MistakeProgress(passed = item.passed, required = item.required)
        }
    }
}

/** Three short bars and "1/3": how many different exercises this mistake has passed. */
@Composable
private fun MistakeProgress(passed: Int, required: Int) {
    val total = required.coerceAtLeast(1)
    val done = passed.coerceIn(0, total)
    val description = stringResource(R.string.mistakes_progress, done, total)
    Column(
        horizontalAlignment = Alignment.End,
        modifier = Modifier.semantics { contentDescription = description },
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(3.dp)) {
            repeat(total) { index ->
                Box(
                    Modifier
                        .size(width = 12.dp, height = 5.dp)
                        .clip(RoundedCornerShape(3.dp))
                        .background(if (index < done) PompColors.Jade else PompColors.Divider),
                )
            }
        }
        Text(
            text = "$done/$total",
            fontSize = 10.sp,
            fontWeight = FontWeight.SemiBold,
            color = PompColors.InkDisabled,
            modifier = Modifier.padding(top = 4.dp),
        )
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
        HskPrimaryButton(
            text = stringResource(R.string.mistakes_to_course),
            onClick = onCourse,
        )
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
            loading -> HskBrandLoader()
            icon != null -> Icon(imageVector = icon, contentDescription = null, tint = stateColor, modifier = Modifier.size(30.dp))
        }
        Spacer(Modifier.height(9.dp))
        Text(text = text, fontSize = 14.sp, color = PompColors.InkSecondary, textAlign = TextAlign.Center)
        if (action != null) {
            Spacer(Modifier.height(14.dp))
            HskPrimaryButton(
                text = action,
                onClick = onAction,
            )
        }
    }
}

/**
 * A mistake, asked again, in the lesson's stage layout: the question as the
 * heading, the coach beside its material, full-width answers, Tekshirish.
 *
 * The verdict is the server's. A tap only picks; Tekshirish sends the pick —
 * the same request as before, one tap later — and the panel with the right
 * answer and its explanation comes up when the reply lands.
 */
@Composable
internal fun MistakesReviewRun(
    state: PracticeUiState,
    onSelect: (Int) -> Unit,
    onAdvance: () -> Unit,
    onCancel: () -> Unit,
    onSpeak: (String) -> Unit,
    modifier: Modifier = Modifier,
    onSubmitTokens: (List<String>) -> Unit = {},
) {
    val session = state.reviewSession ?: return
    val question = session.questions.getOrNull(state.reviewIndex) ?: return
    val feedback = state.reviewFeedback
    val total = session.questions.size.coerceAtLeast(1)
    val progress = (state.reviewIndex + if (feedback != null) 1 else 0).toFloat() / total
    var picked by remember(state.reviewIndex) { mutableStateOf<Int?>(null) }
    // Sentence building: indexes into question.tokens, in the order laid.
    var laid by remember(state.reviewIndex) { mutableStateOf(listOf<Int>()) }
    // Sent, and waiting for the server to say whether it was right.
    val checking = (state.reviewSelectedIndex != null || state.reviewSelectedTokens != null) && feedback == null
    val bottomInset = LocalMainBottomInset.current

    Box(modifier = modifier.fillMaxSize().background(PompColors.Paper)) {
        HskSceneBackground(Modifier.fillMaxSize())
        Column(modifier = Modifier.fillMaxSize()) {
            PracticeStageTopBar(progress = progress, onClose = onCancel)
            HskStageHeading(question.prompt)
            BoxWithConstraints(modifier = Modifier.weight(1f).fillMaxWidth()) {
                val viewport = maxHeight
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .verticalScroll(rememberScrollState())
                        .heightIn(min = viewport)
                        .padding(start = 16.dp, end = 16.dp, top = 14.dp, bottom = 20.dp),
                    verticalArrangement = Arrangement.SpaceBetween,
                ) {
                    // A review is the rabbit's ground (`memory_warning`), but a
                    // mistake keeps the subject it came from — see
                    // `mistakeCharacterFor`. The coach reacts once the verdict lands.
                    HskStageCoach(
                        character = mistakeCharacterFor(question.category),
                        mood = practiceMoodFor(feedback?.correct),
                        reaction = feedback?.let {
                            hskReactionFor(correct = it.correct, streak = state.reviewStreak)
                        },
                        reactionKey = state.reviewIndex to feedback?.correct,
                    ) {
                        // Which kind of mistake this was, and where in the round:
                        // the line that used to sit above the question.
                        Text(
                            text = "${mistakeCategoryLabel(question.category)} · ${stringResource(R.string.mistakes_question)} ${state.reviewIndex + 1} ${stringResource(R.string.mistakes_of)} ${session.questions.size}",
                            style = MaterialTheme.typography.labelMedium,
                            color = PompColors.InkSecondary,
                        )
                        if (question.audioText.isNotBlank() || question.sentence.isNotBlank() || question.pinyin.isNotBlank()) {
                            Spacer(Modifier.height(6.dp))
                            ReviewMaterial(
                                question = question,
                                isAudioLoading = state.isReviewAudioLoading,
                                audioError = state.reviewAudioError,
                                onSpeak = { onSpeak(question.audioText) },
                            )
                        }
                    }
                    Column(
                        modifier = Modifier.fillMaxWidth().padding(top = 20.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        if (question.isBuilder) {
                            ReviewTokenBuilder(
                                tokens = question.tokens,
                                laid = laid,
                                enabled = feedback == null && !checking,
                                onLay = { laid = laid + it },
                                onLift = { position -> laid = laid.filterIndexed { index, _ -> index != position } },
                            )
                        }
                        question.options.forEachIndexed { index, option ->
                            HskAnswerOption(
                                text = option,
                                state = if (feedback != null) {
                                    hskOptionState(
                                        index = index,
                                        correctIndex = feedback.correctIndex,
                                        selectedIndex = state.reviewSelectedIndex,
                                        isAnswered = true,
                                    )
                                } else {
                                    hskOptionState(
                                        index = index,
                                        correctIndex = -1,
                                        selectedIndex = state.reviewSelectedIndex ?: picked,
                                        isAnswered = false,
                                    )
                                },
                                enabled = feedback == null && !checking,
                                onClick = { picked = index },
                            )
                        }
                        if (state.error != null && state.error !is ApiError.LimitReached) {
                            PracticeErrorPill(stringResource(state.error.messageRes), Modifier.padding(top = 4.dp))
                        }
                    }
                }
            }
            if (feedback != null) {
                PracticeFeedbackPanel(
                    isCorrect = feedback.correct,
                    lines = buildList {
                        if (!feedback.correct) {
                            add("${stringResource(R.string.mistakes_explanation)}: ${feedback.correctAnswer}")
                        }
                        if (feedback.explanation != feedback.correctAnswer) add(feedback.explanation)
                    },
                    continueText = stringResource(
                        if (state.reviewIndex >= session.questions.lastIndex) {
                            R.string.mistakes_finish
                        } else {
                            R.string.mistakes_next
                        }
                    ),
                    loading = state.isCompleting,
                    onContinue = onAdvance,
                    bottomInset = bottomInset,
                )
            } else if (question.isBuilder) {
                PracticeCheckFooter(
                    enabled = laid.size == question.tokens.size,
                    loading = checking,
                    onCheck = { onSubmitTokens(laid.map { question.tokens[it] }) },
                    bottomInset = bottomInset,
                )
            } else {
                PracticeCheckFooter(
                    enabled = picked != null,
                    loading = checking,
                    onCheck = { picked?.let(onSelect) },
                    bottomInset = bottomInset,
                )
            }
        }
    }
}

/**
 * Build the sentence from tiles: tap a tile to lay it, tap a laid tile to
 * lift it back. Tekshirish (the footer) sends the order; the server grades.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ReviewTokenBuilder(
    tokens: List<String>,
    laid: List<Int>,
    enabled: Boolean,
    onLay: (Int) -> Unit,
    onLift: (Int) -> Unit,
) {
    Column {
        Surface(
            color = PompColors.PaperRaised,
            shape = RoundedCornerShape(12.dp),
            border = BorderStroke(1.dp, PompColors.Divider),
            modifier = Modifier.fillMaxWidth().heightIn(min = 64.dp),
        ) {
            if (laid.isEmpty()) {
                Text(
                    text = stringResource(R.string.lesson_build_sentence),
                    fontSize = 13.sp,
                    color = PompColors.InkDisabled,
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 22.dp),
                )
            } else {
                FlowRow(modifier = Modifier.padding(10.dp)) {
                    laid.forEachIndexed { position, index ->
                        ReviewTile(text = tokens[index], enabled = enabled, onClick = { onLift(position) })
                    }
                }
            }
        }
        Spacer(Modifier.height(14.dp))
        FlowRow {
            tokens.indices.filterNot { it in laid }.forEach { index ->
                ReviewTile(text = tokens[index], enabled = enabled, onClick = { onLay(index) })
            }
        }
    }
}

/** The lesson's tile (`LessonCards.Tile`): cinnabar edge, dimmed when it cannot be tapped. */
@Composable
private fun ReviewTile(text: String, enabled: Boolean, onClick: () -> Unit) {
    Surface(
        color = if (PompColors.IsDark) PompColors.OptionDepth else PompColors.Paper,
        shape = RoundedCornerShape(10.dp),
        border = BorderStroke(1.dp, PompColors.Cinnabar),
        modifier = Modifier
            .padding(4.dp)
            .heightIn(min = 48.dp)
            .alpha(if (enabled) 1f else 0.4f),
        onClick = onClick,
        enabled = enabled,
    ) {
        Text(
            text = text,
            style = PompTextStyles.hanziMedium,
            fontSize = 20.sp,
            color = PompColors.Ink,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
        )
    }
}

/**
 * What the coach says under the category line: the speaker, the sentence and
 * its pinyin. It sits in the coach's bubble, so it has no card of its own.
 */
@Composable
private fun ReviewMaterial(
    question: MistakeReviewQuestionDto,
    isAudioLoading: Boolean,
    audioError: ApiError?,
    onSpeak: () -> Unit,
) {
    if (question.audioText.isNotBlank()) {
        // A listening exercise has nothing else to look at: the speaker is the
        // question, so it is the biggest thing in the bubble.
        val speaker = if (question.autoplay) 54.dp else 42.dp
        Surface(
            color = PompColors.CinnabarSoft,
            shape = RoundedCornerShape(999.dp),
            modifier = Modifier.size(speaker).clickable(enabled = !isAudioLoading, onClick = onSpeak),
        ) {
            Box(contentAlignment = Alignment.Center) {
                if (isAudioLoading) {
                    HskBrandLoader(compact = true)
                } else {
                    Icon(
                        Icons.Filled.VolumeUp,
                        contentDescription = stringResource(R.string.dictionary_listen),
                        tint = PompColors.Cinnabar,
                        modifier = Modifier.size(if (question.autoplay) 26.dp else 20.dp),
                    )
                }
            }
        }
        if (audioError != null) {
            Text(
                text = stringResource(audioError.messageRes),
                fontSize = 12.sp,
                color = PompColors.Flame,
                modifier = Modifier.padding(top = 6.dp),
            )
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
        )
    }
    if (question.pinyin.isNotBlank()) {
        Text(
            text = question.pinyin,
            fontSize = 13.sp,
            color = PompColors.Cinnabar,
            modifier = Modifier.padding(top = 3.dp),
        )
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
                            color = PompColors.GoldInk,
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

        HskPrimaryButton(
            text = stringResource(R.string.mistakes_done),
            onClick = onDone,
            modifier = Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, top = 10.dp, bottom = 16.dp),
        )
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
    "pronunciation" -> stringResource(R.string.mistakes_source_pronunciation)
    "recognition" -> stringResource(R.string.mistakes_source_recognition)
    "memorize" -> stringResource(R.string.mistakes_source_memorize)
    else -> ""
}

private fun mistakeCategoryIcon(category: String): ImageVector = when (category) {
    "word" -> Icons.Filled.Language
    "grammar" -> Icons.Filled.Code
    "character" -> Icons.Filled.Edit
    "pronunciation" -> Icons.Filled.Mic
    else -> Icons.Filled.WarningAmber
}
