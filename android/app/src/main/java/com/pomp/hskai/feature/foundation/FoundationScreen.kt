package com.pomp.hskai.feature.foundation

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles

@Composable
internal fun FoundationScreen(
    state: FoundationUiState,
    onChoose: (Int) -> Unit,
    onAddBuilderToken: (String) -> Unit,
    onUndoBuilderToken: () -> Unit,
    onSubmitBuilder: () -> Unit,
    onMarkSpoken: () -> Unit,
    onPlayAudio: () -> Unit,
    onAdvance: () -> Unit,
    onRetry: () -> Unit,
    onClose: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        when {
            state.loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = PompColors.Cinnabar)
            }
            state.cards.isEmpty() -> FoundationFailure(onRetry)
            else -> Column(Modifier.fillMaxSize()) {
                FoundationTopBar(state.progress, onClose)
                val card = state.currentCard
                if (card != null) {
                    Column(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxWidth()
                            .verticalScroll(rememberScrollState())
                            .padding(horizontal = 20.dp, vertical = 18.dp),
                    ) {
                        FoundationCardBody(
                            card = card,
                            state = state,
                            onChoose = onChoose,
                            onAddBuilderToken = onAddBuilderToken,
                            onUndoBuilderToken = onUndoBuilderToken,
                            onSubmitBuilder = onSubmitBuilder,
                            onMarkSpoken = onMarkSpoken,
                            onPlayAudio = onPlayAudio,
                        )
                    }
                    FoundationFooter(state, card, onAdvance, onRetry)
                }
            }
        }
    }
}

@Composable
private fun FoundationTopBar(progress: Float, onClose: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Surface(
            color = Color.Transparent,
            shape = CircleShape,
            modifier = Modifier.size(42.dp).clickable(onClick = onClose),
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(Icons.Filled.Close, contentDescription = null, tint = PompColors.InkSecondary)
            }
        }
        Spacer(Modifier.width(10.dp))
        LinearProgressIndicator(
            progress = { progress },
            modifier = Modifier.weight(1f).height(9.dp),
            color = PompColors.Cinnabar,
            trackColor = PompColors.Divider,
        )
        Spacer(Modifier.width(52.dp))
    }
}

@Composable
private fun FoundationCardBody(
    card: FoundationCard,
    state: FoundationUiState,
    onChoose: (Int) -> Unit,
    onAddBuilderToken: (String) -> Unit,
    onUndoBuilderToken: () -> Unit,
    onSubmitBuilder: () -> Unit,
    onMarkSpoken: () -> Unit,
    onPlayAudio: () -> Unit,
) {
    if (card.title.isNotBlank()) {
        Text(
            text = card.title,
            style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.SemiBold),
            color = PompColors.Ink,
        )
        Spacer(Modifier.height(10.dp))
    }
    if (card.text.isNotBlank()) {
        Text(
            text = card.text,
            style = MaterialTheme.typography.bodyLarge.copy(lineHeight = 24.sp),
            color = PompColors.InkSecondary,
        )
        Spacer(Modifier.height(16.dp))
    }
    if (card.prompt.isNotBlank()) {
        Text(
            text = card.prompt,
            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
            color = PompColors.Ink,
        )
        Spacer(Modifier.height(16.dp))
    }

    card.example?.let {
        FoundationExampleCard(it, card.audioText.isNotBlank(), onPlayAudio)
        Spacer(Modifier.height(14.dp))
    }

    when (card.type) {
        "choice", "listen_choice" -> {
            if (card.type == "listen_choice" && card.audioText.isNotBlank()) {
                AudioButton(onPlayAudio)
                Spacer(Modifier.height(16.dp))
            }
            card.options.forEachIndexed { index, option ->
                val selected = state.selectedChoice == index
                val correct = selected && state.answerCorrect == true
                val wrong = selected && state.answerCorrect == false
                FoundationOption(
                    text = option,
                    selected = selected,
                    correct = correct,
                    wrong = wrong,
                    onClick = { onChoose(index) },
                )
                Spacer(Modifier.height(9.dp))
            }
        }
        "builder" -> {
            Surface(
                color = PompColors.PaperRaised,
                shape = RoundedCornerShape(16.dp),
                border = BorderStroke(1.dp, PompColors.Divider),
                modifier = Modifier.fillMaxWidth().heightIn(min = 76.dp),
            ) {
                Row(
                    modifier = Modifier.padding(14.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    state.builderTokens.forEach { token -> HanziToken(token, onUndoBuilderToken) }
                }
            }
            Spacer(Modifier.height(14.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                card.tokens.forEach { token ->
                    HanziToken(token) { onAddBuilderToken(token) }
                }
            }
            Spacer(Modifier.height(16.dp))
            FoundationAction(
                enabled = state.builderTokens.size == card.answerTokens.size,
                onClick = onSubmitBuilder,
                text = state.builderTokens.joinToString("").ifBlank {
                    stringResource(R.string.lesson_check)
                },
                secondary = true,
            )
        }
        "tones", "parts", "explain" -> {
            card.examples.forEach { example ->
                FoundationExampleCard(example, false, onPlayAudio)
                Spacer(Modifier.height(10.dp))
            }
        }
        "sandhi", "intro" -> if (card.audioText.isNotBlank()) AudioButton(onPlayAudio)
        "speak" -> {
            if (card.audioText.isNotBlank()) AudioButton(onPlayAudio)
            Spacer(Modifier.height(14.dp))
            val speakLabel = card.example?.zh?.takeIf { it.isNotBlank() }
                ?: card.audioText.takeIf { it.isNotBlank() }
                ?: stringResource(R.string.lesson_repeat_after_teacher)
            FoundationAction(
                enabled = true,
                onClick = onMarkSpoken,
                text = speakLabel,
                secondary = state.speakingBonus,
            )
        }
        "result" -> {
            card.objectives.forEach { objective ->
                val mastered = objective.id in state.masteredObjectives
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 7.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Surface(
                        color = if (mastered) PompColors.Jade else PompColors.Divider,
                        shape = CircleShape,
                        modifier = Modifier.size(24.dp),
                    ) {
                        if (mastered) Box(contentAlignment = Alignment.Center) {
                            Icon(
                                Icons.Filled.Check,
                                contentDescription = null,
                                tint = PompColors.Paper,
                                modifier = Modifier.size(15.dp),
                            )
                        }
                    }
                    Spacer(Modifier.width(10.dp))
                    Text(objective.label, color = PompColors.Ink, style = MaterialTheme.typography.bodyLarge)
                }
            }
        }
    }

    if (state.answerCorrect != null && card.explanation.isNotBlank()) {
        Spacer(Modifier.height(16.dp))
        Surface(
            color = if (state.answerCorrect == true) PompColors.JadeSoft else PompColors.CinnabarSoft,
            shape = RoundedCornerShape(14.dp),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(
                text = card.explanation,
                color = if (state.answerCorrect == true) PompColors.Jade else PompColors.CinnabarDark,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(14.dp),
            )
        }
    }
}

@Composable
private fun FoundationExampleCard(
    example: FoundationExample,
    audio: Boolean,
    onPlayAudio: () -> Unit,
) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 18.dp, vertical = 16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                if (example.zh.isNotBlank()) Text(
                    example.zh,
                    style = PompTextStyles.hanziLarge,
                    color = PompColors.Ink,
                    textAlign = TextAlign.Center,
                )
                if (example.pinyin.isNotBlank()) Text(
                    example.pinyin,
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.CinnabarDark,
                )
                if (example.translation.isNotBlank()) Text(
                    example.translation,
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                    textAlign = TextAlign.Center,
                )
            }
            if (audio) {
                Spacer(Modifier.width(8.dp))
                Surface(
                    color = PompColors.CinnabarSoft,
                    shape = CircleShape,
                    modifier = Modifier.size(44.dp).clickable(onClick = onPlayAudio),
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(Icons.Filled.VolumeUp, contentDescription = null, tint = PompColors.Cinnabar)
                    }
                }
            }
        }
    }
}

@Composable
private fun AudioButton(onClick: () -> Unit) {
    Surface(
        color = PompColors.CinnabarSoft,
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth().heightIn(min = 54.dp).clickable(onClick = onClick),
    ) {
        Box(contentAlignment = Alignment.Center) {
            Icon(Icons.Filled.VolumeUp, contentDescription = null, tint = PompColors.Cinnabar)
        }
    }
}

@Composable
private fun FoundationOption(
    text: String,
    selected: Boolean,
    correct: Boolean,
    wrong: Boolean,
    onClick: () -> Unit,
) {
    val border = when {
        correct -> PompColors.Jade
        wrong -> PompColors.Cinnabar
        selected -> PompColors.Cinnabar
        else -> PompColors.Divider
    }
    Surface(
        color = when {
            correct -> PompColors.JadeSoft
            wrong -> PompColors.CinnabarSoft
            else -> PompColors.PaperRaised
        },
        shape = RoundedCornerShape(15.dp),
        border = BorderStroke(if (selected) 2.dp else 1.dp, border),
        modifier = Modifier.fillMaxWidth().heightIn(min = 54.dp).clickable(onClick = onClick),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 15.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(text, modifier = Modifier.weight(1f), color = PompColors.Ink)
            if (correct) Icon(Icons.Filled.Check, contentDescription = null, tint = PompColors.Jade)
        }
    }
}

@Composable
private fun HanziToken(text: String, onClick: () -> Unit) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(12.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.size(54.dp).clickable(onClick = onClick),
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text(text, style = PompTextStyles.hanziSmall.copy(fontSize = 22.sp), color = PompColors.Ink)
        }
    }
}

@Composable
private fun FoundationFooter(
    state: FoundationUiState,
    card: FoundationCard,
    onAdvance: () -> Unit,
    onRetry: () -> Unit,
) {
    val interactiveBlocked = card.type in setOf("choice", "listen_choice", "builder") && state.answerCorrect != true
    Surface(color = PompColors.PaperRaised, shadowElevation = 8.dp) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 14.dp)) {
            if (state.error != null) {
                FoundationAction(
                    enabled = !state.saving,
                    onClick = onRetry,
                    text = stringResource(R.string.action_retry),
                    secondary = true,
                    leadingRefresh = true,
                )
                Spacer(Modifier.height(8.dp))
            }
            FoundationAction(
                enabled = !interactiveBlocked && !state.saving && (card.type != "result" || state.canFinish),
                onClick = onAdvance,
                text = stringResource(R.string.action_continue),
                secondary = false,
                loading = state.saving,
            )
        }
    }
}

@Composable
private fun FoundationAction(
    enabled: Boolean,
    onClick: () -> Unit,
    text: String,
    secondary: Boolean,
    loading: Boolean = false,
    leadingRefresh: Boolean = false,
) {
    Surface(
        color = when {
            !enabled -> PompColors.Divider
            secondary -> PompColors.PaperRaised
            else -> PompColors.Cinnabar
        },
        shape = RoundedCornerShape(14.dp),
        border = if (secondary) BorderStroke(1.dp, PompColors.Divider) else null,
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 52.dp)
            .then(if (enabled) Modifier.clickable(onClick = onClick) else Modifier),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (loading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(20.dp),
                    strokeWidth = 2.dp,
                    color = PompColors.Paper,
                )
            } else {
                if (leadingRefresh) {
                    Icon(Icons.Filled.Refresh, contentDescription = null, tint = PompColors.CinnabarDark)
                    Spacer(Modifier.width(7.dp))
                }
                Text(
                    text = text,
                    color = if (secondary) PompColors.CinnabarDark else PompColors.Paper,
                    fontWeight = FontWeight.SemiBold,
                )
            }
        }
    }
}

@Composable
private fun FoundationFailure(onRetry: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        FoundationAction(
            enabled = true,
            onClick = onRetry,
            text = stringResource(R.string.action_retry),
            secondary = true,
            leadingRefresh = true,
        )
    }
}
