package com.pomp.hskai.feature.voice

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.data.api.AndroidHintDto
import com.pomp.hskai.feature.course.CoursePandaMascot
import com.pomp.hskai.feature.course.PandaMood
import com.pomp.hskai.feature.hint.SectionHint
import com.pomp.hskai.feature.limit.LimitGate
import com.pomp.hskai.feature.limit.SectionLimitOverlay

@Composable
fun VoiceScreen(
    state: VoiceUiState,
    level: String,
    language: String,
    limit: LimitGate,
    hints: List<AndroidHintDto> = emptyList(),
    onDismissHint: (String) -> Unit = {},
    onDismissLimit: () -> Unit = {},
    subtitlesOn: Boolean,
    slowSpeech: Boolean,
    onToggleSubtitles: (Boolean) -> Unit,
    onToggleSlowSpeech: (Boolean) -> Unit,
    onSelectRole: (String) -> Unit,
    onStartSession: (String, String) -> Unit,
    onToggleRecording: () -> Unit,
    onSendText: (String) -> Unit,
    onEndSession: () -> Unit,
    onSwapPartner: (String) -> Unit,
    onReset: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        Box(Modifier.fillMaxSize()) {
            when {
                state.result != null -> VoiceResult(state = state, onDone = onReset)
                state.hasSession -> VoiceCallScreen(
                    state = state,
                    subtitlesOn = subtitlesOn,
                    slowSpeech = slowSpeech,
                    onToggleSubtitles = onToggleSubtitles,
                    onToggleSlowSpeech = onToggleSlowSpeech,
                    onToggleRecording = onToggleRecording,
                    onSendText = onSendText,
                    onEndSession = onEndSession,
                    onSwapPartner = onSwapPartner,
                )
                else -> VoiceHome(
                    state = state,
                    level = level,
                    language = language,
                    limit = limit,
                    hints = hints,
                    onDismissHint = onDismissHint,
                    onSelectRole = onSelectRole,
                    onStartSession = onStartSession,
                )
            }

            var limitDismissed by rememberSaveable(state.status?.resetAt) {
                mutableStateOf(false)
            }
            if (!state.hasSession &&
                state.result == null &&
                state.status != null &&
                !canStartVoice(state) &&
                !limitDismissed
            ) {
                SectionLimitOverlay(
                    sectionTitle = stringResource(R.string.nav_ai),
                    limit = limit,
                    reason = state.status?.limitStatus?.limitText ?: stringResource(R.string.limit_voice_reason),
                    resetAt = state.status?.resetAt,
                    onClose = {
                        limitDismissed = true
                        onDismissLimit()
                    },
                )
            }
        }
    }
}

@Composable
private fun VoiceHome(
    state: VoiceUiState,
    level: String,
    language: String,
    limit: LimitGate,
    hints: List<AndroidHintDto>,
    onDismissHint: (String) -> Unit,
    onSelectRole: (String) -> Unit,
    onStartSession: (String, String) -> Unit,
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(
                    color = PompColors.Cinnabar,
                    shape = RoundedCornerShape(999.dp),
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 13.dp, vertical = 7.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(
                            imageVector = Icons.Filled.Mic,
                            contentDescription = null,
                            tint = PompColors.Paper,
                            modifier = Modifier.size(16.dp),
                        )
                        Spacer(Modifier.width(6.dp))
                        Text(
                            text = stringResource(R.string.nav_ai),
                            style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp),
                            color = PompColors.Paper,
                        )
                    }
                }
                Spacer(Modifier.width(8.dp))
                SectionHint(hints = hints, section = "voice", onDismiss = onDismissHint)
            }
        }
        item {
            VoiceBox(
                isStarting = state.isStarting,
                enabled = canStartVoice(state),
                onStart = { onStartSession(level, language) },
            )
        }
        item {
            VoiceLimit(state)
            state.error?.let {
                Spacer(Modifier.height(10.dp))
                ErrorPill(stringResource(it.messageRes))
            }
        }
    }
}

@Composable
private fun VoiceBox(
    isStarting: Boolean,
    enabled: Boolean,
    onStart: () -> Unit,
) {
    val boxSurface = if (PompColors.IsDark) PompColors.PaperRaised else PompColors.Ink
    val boxInk = if (PompColors.IsDark) PompColors.Ink else PompColors.Paper
    val boxMuted = if (PompColors.IsDark) PompColors.InkSecondary else PompColors.Paper.copy(alpha = 0.72f)
    Surface(
        color = boxSurface,
        shape = RoundedCornerShape(18.dp),
        border = if (PompColors.IsDark) BorderStroke(1.dp, PompColors.Divider) else null,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            CoursePandaMascot(mood = PandaMood.Talk, modifier = Modifier.size(90.dp))
            Spacer(Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.voice_box_title),
                style = MaterialTheme.typography.titleLarge.copy(fontSize = 18.sp),
                fontWeight = FontWeight.Medium,
                color = boxInk,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = stringResource(R.string.voice_box_body),
                style = MaterialTheme.typography.bodyMedium.copy(fontSize = 13.sp),
                color = boxMuted,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(16.dp))
            Surface(
                onClick = onStart,
                enabled = enabled && !isStarting,
                color = PompColors.Cinnabar,
                shape = RoundedCornerShape(13.dp),
            ) {
                Box(
                    modifier = Modifier.padding(horizontal = 26.dp, vertical = 14.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    if (isStarting) {
                        CircularProgressIndicator(
                            color = PompColors.Paper,
                            modifier = Modifier.size(18.dp),
                            strokeWidth = 2.dp,
                        )
                    } else {
                        Text(
                            text = stringResource(R.string.voice_start),
                            style = MaterialTheme.typography.labelLarge.copy(fontSize = 15.sp),
                            fontWeight = FontWeight.Medium,
                            color = PompColors.Paper,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun VoiceLimit(state: VoiceUiState) {
    val status = state.status
    val text = when {
        state.isLoading -> stringResource(R.string.state_loading)
        status?.isPaid == true -> stringResource(R.string.voice_limit_premium)
        else -> stringResource(
            R.string.voice_limit_free,
            status?.remainingVoiceLimit ?: state.remainingLimit,
        )
    }
    Surface(
        color = PompColors.GoldSoft,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.Ink,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
        )
    }
}

@Composable
private fun RoleCard(
    role: VoiceRoleSpec,
    selected: Boolean,
    onClick: () -> Unit,
) {
    Surface(
        color = if (selected) PompColors.CinnabarSoft else PompColors.PaperRaised,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, if (selected) PompColors.Cinnabar else PompColors.Divider),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
    ) {
        Row(Modifier.padding(16.dp)) {
            Text(
                text = role.glyph,
                style = PompTextStyles.hanziMedium,
                color = PompColors.CinnabarDark,
            )
            Column(Modifier.padding(start = 14.dp)) {
                Text(
                    text = stringResource(role.titleRes),
                    style = MaterialTheme.typography.titleMedium,
                    color = PompColors.Ink,
                )
                Text(
                    text = stringResource(role.bodyRes),
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun PartnerPicker(
    current: String,
    onPick: (String) -> Unit,
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
                text = stringResource(R.string.voice_partner),
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.Ink,
            )
            Spacer(Modifier.height(10.dp))
            VOICE_PARTNERS.forEach { role ->
                val selected = role.id == current
                Surface(
                    color = if (selected) PompColors.CinnabarSoft else PompColors.PaperRaised,
                    shape = RoundedCornerShape(14.dp),
                    border = BorderStroke(
                        if (selected) 2.dp else 1.dp,
                        if (selected) PompColors.Cinnabar else PompColors.Divider,
                    ),
                    onClick = { onPick(role.id) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp),
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        Text(
                            text = role.glyph,
                            style = PompTextStyles.hanziSmall,
                            color = if (selected) PompColors.Cinnabar else PompColors.InkSecondary,
                        )
                        Column(Modifier.weight(1f)) {
                            Text(
                                text = stringResource(role.titleRes),
                                style = MaterialTheme.typography.bodyLarge,
                                color = PompColors.Ink,
                            )
                            Text(
                                text = stringResource(role.bodyRes),
                                style = MaterialTheme.typography.bodySmall,
                                color = PompColors.InkSecondary,
                            )
                        }
                    }
                }
            }
            Spacer(Modifier.height(16.dp))
        }
    }
}

private val VOICE_PARTNERS = listOf(
    VoiceRoleSpec("friend", R.string.voice_role_friend, R.string.voice_role_friend_body, "友"),
    VoiceRoleSpec("teacher_li", R.string.voice_role_teacher, R.string.voice_role_teacher_body, "师"),
    VoiceRoleSpec("seller", R.string.voice_role_seller, R.string.voice_role_seller_body, "店"),
    VoiceRoleSpec("classmate", R.string.voice_role_classmate, R.string.voice_role_classmate_body, "同"),
    VoiceRoleSpec("manager_wang", R.string.voice_role_manager, R.string.voice_role_manager_body, "王"),
)

internal fun partnerTitleRes(role: String): Int =
    VOICE_PARTNERS.firstOrNull { it.id == role }?.titleRes ?: R.string.voice_session_title

@Composable
internal fun VoiceBubble(line: VoiceLine, subtitlesOn: Boolean = true) {
    val isUser = line.speaker == VoiceSpeaker.USER
    Surface(
        color = if (isUser) PompColors.CinnabarSoft else PompColors.PaperRaised,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, if (isUser) PompColors.Cinnabar else PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(16.dp)) {
            Text(
                text = if (isUser) stringResource(R.string.voice_you) else stringResource(R.string.voice_ai),
                style = MaterialTheme.typography.labelLarge,
                color = if (isUser) PompColors.CinnabarDark else PompColors.Jade,
            )
            if (line.hanzi.isNotBlank()) {
                Text(
                    text = line.hanzi,
                    style = PompTextStyles.hanziMedium,
                    color = PompColors.Ink,
                )
            }
            if (subtitlesOn && line.pinyin.isNotBlank()) {
                Text(
                    text = line.pinyin,
                    style = PompTextStyles.pinyin,
                    color = PompColors.InkSecondary,
                )
            }
            if (subtitlesOn || line.hanzi.isBlank()) {
                Text(
                    text = line.text.ifBlank { line.translation },
                    style = MaterialTheme.typography.bodyLarge,
                    color = PompColors.Ink,
                )
            }
            line.correction?.takeIf { it.isNotBlank() }?.let {
                Spacer(Modifier.height(8.dp))
                Text(
                    text = stringResource(R.string.voice_correction, it),
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.Flame,
                    fontWeight = FontWeight.SemiBold,
                )
            }
        }
    }
}

@Composable
private fun VoiceResult(
    state: VoiceUiState,
    onDone: () -> Unit,
) {
    val result = state.result ?: return
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(20.dp),
    ) {
        Text(
            text = stringResource(R.string.voice_result_title),
            style = MaterialTheme.typography.headlineMedium,
            color = PompColors.Ink,
        )
        Spacer(Modifier.height(10.dp))
        Text(
            text = stringResource(
                R.string.voice_result_body,
                result.messageCount,
                result.goodCount,
                result.mistakeCount,
            ),
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.InkSecondary,
        )
        Spacer(Modifier.height(18.dp))
        Button(
            onClick = onDone,
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 52.dp),
            shape = RoundedCornerShape(14.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = PompColors.Cinnabar,
                contentColor = PompColors.Paper,
            ),
        ) {
            Text(stringResource(R.string.voice_again))
        }
    }
}

@Composable
internal fun ErrorPill(text: String) {
    Surface(
        color = PompColors.FlameSoft,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.Flame,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
        )
    }
}

private fun canStartVoice(state: VoiceUiState): Boolean {
    val status = state.status ?: return false
    return status.isPaid || status.remainingVoiceLimit != 0
}
