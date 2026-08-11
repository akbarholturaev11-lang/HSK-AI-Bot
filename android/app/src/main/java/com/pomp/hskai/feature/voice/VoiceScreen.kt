package com.pomp.hskai.feature.voice

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles

@Composable
fun VoiceScreen(
    state: VoiceUiState,
    level: String,
    language: String,
    onSelectRole: (String) -> Unit,
    onStartSession: (String, String) -> Unit,
    onToggleRecording: () -> Unit,
    onEndSession: () -> Unit,
    onReset: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        when {
            state.result != null -> VoiceResult(state = state, onDone = onReset)
            state.hasSession -> VoiceSession(
                state = state,
                onToggleRecording = onToggleRecording,
                onEndSession = onEndSession,
            )
            else -> VoiceHome(
                state = state,
                level = level,
                language = language,
                onSelectRole = onSelectRole,
                onStartSession = onStartSession,
            )
        }
    }
}

@Composable
private fun VoiceHome(
    state: VoiceUiState,
    level: String,
    language: String,
    onSelectRole: (String) -> Unit,
    onStartSession: (String, String) -> Unit,
) {
    val roles = remember {
        listOf(
            VoiceRoleSpec("friend", R.string.voice_role_friend, R.string.voice_role_friend_body, "友"),
            VoiceRoleSpec("teacher_li", R.string.voice_role_teacher, R.string.voice_role_teacher_body, "师"),
            VoiceRoleSpec("seller", R.string.voice_role_seller, R.string.voice_role_seller_body, "店"),
            VoiceRoleSpec("classmate", R.string.voice_role_classmate, R.string.voice_role_classmate_body, "同"),
            VoiceRoleSpec("manager_wang", R.string.voice_role_manager, R.string.voice_role_manager_body, "王"),
        )
    }
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text(
                text = stringResource(R.string.voice_title),
                style = MaterialTheme.typography.headlineMedium,
                color = PompColors.Ink,
            )
            Text(
                text = stringResource(R.string.voice_subtitle, level.uppercase()),
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.InkSecondary,
            )
            Spacer(Modifier.height(10.dp))
            VoiceLimit(state)
            state.error?.let {
                Spacer(Modifier.height(10.dp))
                ErrorPill(stringResource(it.messageRes))
            }
        }
        items(roles) { role ->
            RoleCard(
                role = role,
                selected = state.selectedRole == role.id,
                onClick = { onSelectRole(role.id) },
            )
        }
        item {
            Button(
                onClick = { onStartSession(level, language) },
                enabled = !state.isStarting && canStartVoice(state),
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 52.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = PompColors.Cinnabar,
                    contentColor = PompColors.Paper,
                ),
            ) {
                if (state.isStarting) {
                    CircularProgressIndicator(color = PompColors.Paper)
                } else {
                    Text(stringResource(R.string.voice_start))
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

@Composable
private fun VoiceSession(
    state: VoiceUiState,
    onToggleRecording: () -> Unit,
    onEndSession: () -> Unit,
) {
    val context = LocalContext.current
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted) onToggleRecording()
    }
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Column {
                    Text(
                        text = stringResource(R.string.voice_session_title),
                        style = MaterialTheme.typography.titleLarge,
                        color = PompColors.Ink,
                    )
                    Text(
                        text = stringResource(
                            R.string.voice_turn_progress,
                            state.turnCount,
                            state.maxDialogs,
                        ),
                        style = MaterialTheme.typography.bodyMedium,
                        color = PompColors.InkSecondary,
                    )
                }
                OutlinedButton(onClick = onEndSession, shape = RoundedCornerShape(12.dp)) {
                    Text(stringResource(R.string.voice_end))
                }
            }
            state.error?.let {
                Spacer(Modifier.height(10.dp))
                ErrorPill(stringResource(it.messageRes))
            }
        }
        items(state.lines) { line ->
            VoiceBubble(line)
        }
        item {
            val hasPermission = ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.RECORD_AUDIO,
            ) == PackageManager.PERMISSION_GRANTED
            Button(
                onClick = {
                    if (hasPermission) {
                        onToggleRecording()
                    } else {
                        permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                    }
                },
                enabled = !state.isSending,
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 56.dp),
                shape = RoundedCornerShape(16.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (state.isRecording) PompColors.CinnabarDark else PompColors.Cinnabar,
                    contentColor = PompColors.Paper,
                ),
            ) {
                Text(
                    text = when {
                        state.isSending -> stringResource(R.string.voice_sending)
                        state.isRecording -> stringResource(R.string.voice_stop_recording)
                        else -> stringResource(R.string.voice_hold_to_speak)
                    },
                    style = MaterialTheme.typography.labelLarge,
                )
            }
        }
    }
}

@Composable
private fun VoiceBubble(line: VoiceLine) {
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
            if (line.pinyin.isNotBlank()) {
                Text(
                    text = line.pinyin,
                    style = PompTextStyles.pinyin,
                    color = PompColors.InkSecondary,
                )
            }
            Text(
                text = line.text.ifBlank { line.translation },
                style = MaterialTheme.typography.bodyLarge,
                color = PompColors.Ink,
            )
            line.correction?.takeIf { it.isNotBlank() }?.let {
                Spacer(Modifier.height(8.dp))
                Text(
                    text = stringResource(R.string.voice_correction, it),
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.CinnabarDark,
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
private fun ErrorPill(text: String) {
    Surface(
        color = PompColors.CinnabarSoft,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.CinnabarDark,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
        )
    }
}

private fun canStartVoice(state: VoiceUiState): Boolean {
    val status = state.status ?: return false
    return status.isPaid || status.remainingVoiceLimit > 0
}
