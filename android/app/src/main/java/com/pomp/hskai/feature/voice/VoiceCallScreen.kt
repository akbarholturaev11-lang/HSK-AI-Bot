package com.pomp.hskai.feature.voice

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Keyboard
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
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
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.data.api.VoiceSuggestionDto
import com.pomp.hskai.data.api.VoiceWordDto
import com.pomp.hskai.feature.course.CoursePandaMascot
import com.pomp.hskai.feature.course.PandaMood

/**
 * Mini App `course_v3_voice.html` — the conversation as a call.
 *
 * The previous Android screen was a scrolling list with a "record" button at
 * the bottom: correct, and nothing like the thing the Mini App learner knows.
 * The call has a shape — who you are talking to at the top, the panda in the
 * middle, what is happening right now under it, the dialogue below, and one
 * dock with the microphone, the keyboard beside it and "what to say" above.
 *
 * The keyboard matters as much as the microphone: a learner on a bus, or one
 * whose microphone permission is refused, still gets to answer.
 */
@Composable
internal fun VoiceCallScreen(
    state: VoiceUiState,
    subtitlesOn: Boolean,
    slowSpeech: Boolean,
    onToggleSubtitles: (Boolean) -> Unit,
    onToggleSlowSpeech: (Boolean) -> Unit,
    onToggleRecording: () -> Unit,
    onSendText: (String) -> Unit,
    onEndSession: () -> Unit,
    onSwapPartner: (String) -> Unit,
) {
    val context = LocalContext.current
    var settingsOpen by remember { mutableStateOf(false) }
    var partnerSheetOpen by remember { mutableStateOf(false) }
    var hintsOpen by remember { mutableStateOf(false) }
    var keyboardOpen by remember { mutableStateOf(false) }
    var draft by remember { mutableStateOf("") }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted) onToggleRecording()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding(),
    ) {
        CallTopBar(
            title = stringResource(partnerTitleRes(state.selectedRole)),
            subtitle = stringResource(
                R.string.voice_turn_progress,
                state.turnCount,
                state.maxDialogs,
            ),
            onClose = onEndSession,
            onOpenSettings = { settingsOpen = true },
            settingsEnabled = state.canAnswer,
        )

        // The stage: the partner, and one line saying what is happening.
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .height(200.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            CoursePandaMascot(mood = PandaMood.Talk, modifier = Modifier.size(130.dp))
        }
        Text(
            text = when {
                state.isStarting -> stringResource(R.string.voice_status_connecting)
                state.isRecording -> stringResource(R.string.voice_status_listening)
                state.isSending -> stringResource(R.string.voice_status_analyzing)
                else -> stringResource(R.string.voice_status_speaking)
            },
            style = MaterialTheme.typography.bodyMedium.copy(fontSize = 13.sp),
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 18.dp),
        )

        CallChat(
            state = state,
            subtitlesOn = subtitlesOn,
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f),
        )

        CallDock(
            state = state,
            keyboardOpen = keyboardOpen,
            draft = draft,
            onDraftChange = { draft = it },
            onOpenHints = { hintsOpen = true },
            onOpenKeyboard = { keyboardOpen = true },
            onCloseKeyboard = { keyboardOpen = false },
            onSend = {
                val text = draft.trim()
                if (text.isNotEmpty()) {
                    draft = ""
                    onSendText(text)
                }
            },
            onMic = {
                val granted = ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.RECORD_AUDIO,
                ) == PackageManager.PERMISSION_GRANTED
                if (granted) onToggleRecording() else {
                    permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                }
            },
        )
    }

    if (settingsOpen) {
        CallSettingsSheet(
            partnerLabel = stringResource(partnerTitleRes(state.selectedRole)),
            subtitlesOn = subtitlesOn,
            slowSpeech = slowSpeech,
            onOpenPartner = {
                settingsOpen = false
                partnerSheetOpen = true
            },
            onToggleSubtitles = { onToggleSubtitles(!subtitlesOn) },
            onToggleSlowSpeech = { onToggleSlowSpeech(!slowSpeech) },
            onDismiss = { settingsOpen = false },
        )
    }

    if (partnerSheetOpen) {
        PartnerPicker(
            current = state.selectedRole,
            onPick = { role ->
                partnerSheetOpen = false
                if (role != state.selectedRole) onSwapPartner(role)
            },
            onDismiss = { partnerSheetOpen = false },
        )
    }

    if (hintsOpen) {
        HintSheet(
            words = (state.lessonWords + state.reviewWords).take(6),
            suggestions = state.suggestions,
            onPick = { phrase ->
                // The whole point of the sheet is "I don't know what to say",
                // so a choice becomes the answer at once — the Mini App does
                // not open the keyboard here either.
                hintsOpen = false
                onSendText(phrase)
            },
            onDismiss = { hintsOpen = false },
        )
    }
}

@Composable
private fun CallTopBar(
    title: String,
    subtitle: String,
    onClose: () -> Unit,
    onOpenSettings: () -> Unit,
    settingsEnabled: Boolean,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(start = 14.dp, end = 14.dp, top = 10.dp, bottom = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        RoundIconButton(
            icon = Icons.Filled.Close,
            contentDescription = stringResource(R.string.voice_end),
            onClick = onClose,
        )
        Column(
            modifier = Modifier.weight(1f),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium.copy(fontSize = 15.sp),
                fontWeight = FontWeight.SemiBold,
                color = PompColors.Ink,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.sp),
                color = PompColors.InkSecondary,
            )
        }
        RoundIconButton(
            icon = Icons.Filled.Settings,
            contentDescription = stringResource(R.string.voice_partner),
            onClick = onOpenSettings,
            enabled = settingsEnabled,
        )
    }
}

@Composable
private fun RoundIconButton(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    contentDescription: String,
    onClick: () -> Unit,
    enabled: Boolean = true,
) {
    Surface(
        onClick = onClick,
        enabled = enabled,
        shape = CircleShape,
        color = PompColors.PaperRaised,
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.size(38.dp),
    ) {
        Box(contentAlignment = Alignment.Center) {
            Icon(
                imageVector = icon,
                contentDescription = contentDescription,
                tint = PompColors.InkSecondary,
                modifier = Modifier.size(18.dp),
            )
        }
    }
}

/** `.chat` — the dialogue on its own raised sheet. */
@Composable
private fun CallChat(
    state: VoiceUiState,
    subtitlesOn: Boolean,
    modifier: Modifier = Modifier,
) {
    val listState = rememberLazyListState()
    LaunchedEffect(state.lines.size) {
        if (state.lines.isNotEmpty()) listState.animateScrollToItem(state.lines.lastIndex)
    }
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(topStart = 22.dp, topEnd = 22.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = modifier.padding(top = 6.dp),
    ) {
        if (state.lines.isEmpty()) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = stringResource(R.string.voice_empty_chat),
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkDisabled,
                )
            }
            return@Surface
        }
        LazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(start = 14.dp, end = 14.dp, top = 14.dp, bottom = 6.dp),
            verticalArrangement = Arrangement.spacedBy(9.dp),
        ) {
            items(state.lines) { line -> VoiceBubble(line, subtitlesOn) }
            state.error?.let { error ->
                item { ErrorPill(stringResource(error.messageRes)) }
            }
        }
    }
}

/** `.dock` — what to say, the keyboard, and the microphone. */
@Composable
private fun CallDock(
    state: VoiceUiState,
    keyboardOpen: Boolean,
    draft: String,
    onDraftChange: (String) -> Unit,
    onOpenHints: () -> Unit,
    onOpenKeyboard: () -> Unit,
    onCloseKeyboard: () -> Unit,
    onSend: () -> Unit,
    onMic: () -> Unit,
) {
    val keyboardController = LocalSoftwareKeyboardController.current
    Surface(
        color = PompColors.PaperRaised,
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier
                .navigationBarsPadding()
                .imePadding()
                .padding(start = 14.dp, end = 14.dp, top = 10.dp, bottom = 14.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            if (!keyboardOpen) {
                Surface(
                    onClick = onOpenHints,
                    enabled = state.canAnswer,
                    shape = RoundedCornerShape(999.dp),
                    color = PompColors.CinnabarSoft,
                    border = BorderStroke(1.dp, PompColors.Cinnabar.copy(alpha = 0.2f)),
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 14.dp, vertical = 7.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(
                            imageVector = Icons.Filled.Lightbulb,
                            contentDescription = null,
                            tint = PompColors.CinnabarDark,
                            modifier = Modifier.size(16.dp),
                        )
                        Spacer(Modifier.width(6.dp))
                        Text(
                            text = stringResource(R.string.voice_what_to_say),
                            style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp),
                            color = PompColors.CinnabarDark,
                        )
                    }
                }
                Spacer(Modifier.height(9.dp))
            }

            if (keyboardOpen) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.Bottom,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    SquareIconButton(
                        icon = Icons.Filled.Mic,
                        contentDescription = stringResource(R.string.voice_a11y_mic),
                        onClick = {
                            keyboardController?.hide()
                            onCloseKeyboard()
                        },
                    )
                    OutlinedTextField(
                        value = draft,
                        onValueChange = { if (it.length <= MAX_TYPED_CHARS) onDraftChange(it) },
                        placeholder = { Text(stringResource(R.string.voice_keyboard_hint)) },
                        maxLines = 3,
                        shape = RoundedCornerShape(16.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = PompColors.Cinnabar,
                            unfocusedBorderColor = PompColors.Divider,
                            focusedContainerColor = PompColors.Paper,
                            unfocusedContainerColor = PompColors.Paper,
                        ),
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                        keyboardActions = KeyboardActions(onSend = { onSend() }),
                        modifier = Modifier.weight(1f),
                    )
                    SquareIconButton(
                        icon = Icons.AutoMirrored.Filled.Send,
                        contentDescription = stringResource(R.string.voice_a11y_send),
                        onClick = onSend,
                        enabled = draft.isNotBlank() && state.canAnswer,
                        filled = true,
                    )
                }
            } else {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    SquareIconButton(
                        icon = Icons.Filled.Keyboard,
                        contentDescription = stringResource(R.string.voice_a11y_keyboard),
                        onClick = onOpenKeyboard,
                        enabled = state.canAnswer,
                    )
                    Box(
                        modifier = Modifier.weight(1f),
                        contentAlignment = Alignment.Center,
                    ) {
                        MicButton(
                            isRecording = state.isRecording,
                            enabled = state.hasSession && !state.isSending,
                            onClick = onMic,
                        )
                    }
                    // Keeps the microphone centred against the keyboard key.
                    Spacer(Modifier.size(48.dp))
                }
                Spacer(Modifier.height(7.dp))
                Text(
                    text = when {
                        state.isSending -> stringResource(R.string.voice_sending)
                        state.isRecording -> stringResource(R.string.voice_tap_to_stop)
                        else -> stringResource(R.string.voice_tap_to_speak)
                    },
                    style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.5.sp),
                    color = PompColors.InkDisabled,
                    textAlign = TextAlign.Center,
                )
            }
        }
    }
}

@Composable
private fun MicButton(isRecording: Boolean, enabled: Boolean, onClick: () -> Unit) {
    val pulse = rememberInfiniteTransition(label = "micPulse")
    val progress by pulse.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1200),
            repeatMode = RepeatMode.Restart,
        ),
        label = "micPulseProgress",
    )
    Box(contentAlignment = Alignment.Center) {
        if (isRecording) {
            Canvas(modifier = Modifier.size(78.dp)) {
                val radius = (size.minDimension / 2f) * (1f + 0.5f * progress)
                drawCircle(
                    color = PompColors.Cinnabar.copy(alpha = 0.6f * (1f - progress)),
                    radius = radius,
                    center = Offset(size.width / 2f, size.height / 2f),
                    style = Stroke(width = 3.dp.toPx()),
                )
            }
        }
        Surface(
            onClick = onClick,
            enabled = enabled,
            shape = CircleShape,
            color = if (isRecording) PompColors.CinnabarDark else PompColors.Cinnabar,
            border = BorderStroke(3.dp, PompColors.PaperRaised),
            modifier = Modifier.size(78.dp),
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = Icons.Filled.Mic,
                    contentDescription = stringResource(R.string.voice_a11y_mic),
                    tint = PompColors.Paper,
                    modifier = Modifier.size(31.dp),
                )
            }
        }
    }
}

@Composable
private fun SquareIconButton(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    contentDescription: String,
    onClick: () -> Unit,
    enabled: Boolean = true,
    filled: Boolean = false,
) {
    Surface(
        onClick = onClick,
        enabled = enabled,
        shape = RoundedCornerShape(16.dp),
        color = if (filled) PompColors.Cinnabar else PompColors.Paper,
        border = if (filled) null else BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.size(48.dp),
    ) {
        Box(contentAlignment = Alignment.Center) {
            Icon(
                imageVector = icon,
                contentDescription = contentDescription,
                tint = if (filled) PompColors.Paper else PompColors.InkSecondary,
                modifier = Modifier.size(21.dp),
            )
        }
    }
}

/** Mini App hint sheet: the lesson's words first, then phrases that fit now. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun HintSheet(
    words: List<VoiceWordDto>,
    suggestions: List<VoiceSuggestionDto>,
    onPick: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState()
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = PompColors.PaperRaised,
    ) {
        LazyColumn(
            modifier = Modifier.padding(horizontal = 20.dp),
            contentPadding = PaddingValues(bottom = 24.dp),
        ) {
            item {
                Text(
                    text = stringResource(R.string.voice_hints_title),
                    style = MaterialTheme.typography.titleMedium,
                    color = PompColors.Ink,
                )
                Spacer(Modifier.height(10.dp))
            }
            if (words.isNotEmpty()) {
                item { HintGroupLabel(stringResource(R.string.voice_hints_words)) }
                items(words) { word ->
                    HintRow(
                        hanzi = word.hanzi,
                        pinyin = word.pinyin,
                        meaning = word.meaning,
                        onClick = { onPick(word.hanzi) },
                    )
                }
            }
            if (suggestions.isNotEmpty()) {
                item { HintGroupLabel(stringResource(R.string.voice_hints_phrases)) }
                items(suggestions) { phrase ->
                    HintRow(
                        hanzi = phrase.hanzi,
                        pinyin = phrase.pinyin,
                        meaning = phrase.translation,
                        onClick = { onPick(phrase.hanzi) },
                    )
                }
            }
        }
    }
}

@Composable
private fun HintGroupLabel(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.labelLarge.copy(fontSize = 12.sp),
        fontWeight = FontWeight.SemiBold,
        color = PompColors.InkSecondary,
        modifier = Modifier.padding(top = 10.dp, bottom = 6.dp),
    )
}

@Composable
private fun HintRow(
    hanzi: String,
    pinyin: String,
    meaning: String,
    onClick: () -> Unit,
) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(14.dp),
        color = PompColors.Paper,
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 8.dp),
    ) {
        Column(modifier = Modifier.padding(horizontal = 13.dp, vertical = 11.dp)) {
            Text(
                text = hanzi,
                style = PompTextStyles.hanziSmall.copy(fontSize = 19.sp),
                color = PompColors.Ink,
            )
            if (pinyin.isNotBlank()) {
                Text(
                    text = pinyin,
                    style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.5.sp),
                    fontWeight = FontWeight.Medium,
                    color = PompColors.CinnabarDark,
                )
            }
            if (meaning.isNotBlank()) {
                Text(
                    text = meaning,
                    style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.5.sp),
                    color = PompColors.InkSecondary,
                )
            }
        }
    }
}

/** The Mini App's own ceiling for a typed turn. */
private const val MAX_TYPED_CHARS = 200

/**
 * Mini App call settings: who you are talking to, whether the pinyin and the
 * translation are shown, and how fast the partner speaks.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CallSettingsSheet(
    partnerLabel: String,
    subtitlesOn: Boolean,
    slowSpeech: Boolean,
    onOpenPartner: () -> Unit,
    onToggleSubtitles: () -> Unit,
    onToggleSlowSpeech: () -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState()
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = PompColors.PaperRaised,
    ) {
        Column(Modifier.padding(horizontal = 20.dp, vertical = 8.dp)) {
            Text(
                text = stringResource(R.string.voice_settings_title),
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.Ink,
            )
            Spacer(Modifier.height(10.dp))
            CallSettingRow(
                label = stringResource(R.string.voice_setting_partner),
                value = partnerLabel,
                onClick = onOpenPartner,
            )
            CallSettingRow(
                label = stringResource(R.string.voice_setting_subtitles),
                value = stringResource(
                    if (subtitlesOn) R.string.voice_setting_on else R.string.voice_setting_off
                ),
                onClick = onToggleSubtitles,
            )
            CallSettingRow(
                label = stringResource(R.string.voice_setting_rate),
                value = stringResource(
                    if (slowSpeech) R.string.voice_rate_slow else R.string.voice_rate_normal
                ),
                onClick = onToggleSlowSpeech,
            )
            Spacer(Modifier.height(16.dp))
        }
    }
}

@Composable
private fun CallSettingRow(label: String, value: String, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        color = PompColors.Paper,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = label,
                style = MaterialTheme.typography.bodyLarge,
                color = PompColors.Ink,
                modifier = Modifier.weight(1f),
            )
            Text(
                text = value,
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.InkSecondary,
            )
        }
    }
}
