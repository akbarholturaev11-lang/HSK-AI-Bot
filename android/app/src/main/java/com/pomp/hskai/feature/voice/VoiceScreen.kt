package com.pomp.hskai.feature.voice

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
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
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskSceneSurface
import com.pomp.hskai.core.design.components.HskGlassSurface
import com.pomp.hskai.core.design.components.HskPrimaryButton
import com.pomp.hskai.core.design.components.HskSectionTitle
import com.pomp.hskai.core.navigation.LocalMainBottomInset
import com.pomp.hskai.data.api.AndroidHintDto
import com.pomp.hskai.data.api.VoiceTranscriptDto
import com.pomp.hskai.feature.hint.SectionHint
import com.pomp.hskai.feature.limit.LimitGate
import com.pomp.hskai.feature.limit.SectionLimitOverlay
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.feature.assistant.AssistantScreen
import com.pomp.hskai.feature.assistant.voiceAssistantContext

@Composable
fun VoiceScreen(
    state: VoiceUiState,
    level: String,
    language: String,
    limit: LimitGate,
    hints: List<AndroidHintDto> = emptyList(),
    onDismissHint: (String) -> Unit = {},
    /** Markazdagi limit tanlovi yopilganda. */
    onDismissLimit: () -> Unit = {},
    onSelectRole: (String) -> Unit,
    /** Opens the full-screen AI Voice V8 conversation (VoiceV8Screen). */
    onOpenVoice: () -> Unit,
    onEndSession: () -> Unit,
    onReset: () -> Unit,
    onRetryStatus: () -> Unit = {},
    modifier: Modifier = Modifier,
) {
    // A pending start must be cancellable before its late response opens a
    // conversation in the background; the open V8 screen owns Back itself.
    BackHandler(enabled = state.isStarting && !state.hasSession, onBack = onEndSession)
    val endSessionOnExit by rememberUpdatedState(onEndSession)
    val sessionActiveOnExit by rememberUpdatedState(state.hasSession || state.isStarting)
    DisposableEffect(Unit) {
        onDispose {
            if (sessionActiveOnExit) endSessionOnExit()
        }
    }
    AssistantScreen(
        voiceAssistantContext(state, level),
        bottomBar = true,
        showButton = false,
    )
    HskSceneSurface(modifier = modifier.fillMaxSize()) {
      Box(Modifier.fillMaxSize()) {
        when {
            state.result != null -> VoiceResult(state = state, onDone = onReset)
            else -> VoiceHome(
                state = state,
                level = level,
                language = language,
                limit = limit,
                hints = hints,
                onDismissHint = onDismissHint,
                onSelectRole = onSelectRole,
                onStartSession = { _, _ -> onOpenVoice() },
                onRetryStatus = onRetryStatus,
            )
        }

        // Kunlik bepul ovoz tugagan bo'lsa — tanlov markazda, xira fon
        // ustida. Boshqa bo'limlardagidek AYNI blok, faqat matni shu
        // bo'limga tegishli.
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
                sourceKey = "voice_limit",
                limit = limit,
                reason = state.status?.limitStatus?.limitText ?: stringResource(R.string.limit_voice_reason),
                // The server says when the daily allowance reopens; the hour
                // is never assumed on the client.
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

/**
 * Mini App `renderVoice()`: one dark card, the panda, and a single button.
 *
 * The five partners the backend supports are not a menu here — the Mini App
 * asks for the partner inside the conversation, and a learner opening the tab
 * should be one tap away from speaking, not choosing.
 */
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
    onRetryStatus: () -> Unit,
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(
            start = 16.dp,
            end = 16.dp,
            top = 16.dp,
            // The tab bar floats over the list; without this the limit card
            // would sit behind it with no way to scroll it out.
            bottom = 16.dp + LocalMainBottomInset.current,
        ),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
          Row(verticalAlignment = Alignment.CenterVertically) {
            HskSectionTitle(stringResource(R.string.nav_ai))
            Spacer(Modifier.width(8.dp))
            SectionHint(hints = hints, section = "voice", onDismiss = onDismissHint)
          }
        }
        if (state.status == null && state.isLoading) {
            item {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(18.dp),
                        strokeWidth = 2.dp,
                        color = PompColors.Cinnabar,
                    )
                    Spacer(Modifier.width(8.dp))
                    Text(
                        text = stringResource(R.string.voice_status_loading),
                        style = MaterialTheme.typography.bodySmall,
                        color = PompColors.InkSecondary,
                    )
                }
            }
        }
        item {
            VoiceBox(
                state = state,
                onStart = { onStartSession(level, language) },
            )
        }
        item {
            state.error?.let {
                Spacer(Modifier.height(10.dp))
                ErrorPill(stringResource(it.messageRes))
                if (!state.isLoading) {
                    OutlinedButton(
                        onClick = onRetryStatus,
                        modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                        shape = RoundedCornerShape(14.dp),
                    ) {
                        Text(stringResource(R.string.voice_retry_status), color = PompColors.CinnabarDark)
                    }
                }
            }
        }
    }
}

/**
 * The AI Voice card as the start of the V8 call: black, the call's orb, the
 * topic the call opens with, and one red "Start conversation" pill.
 */
@Composable
private fun VoiceBox(
    state: VoiceUiState,
    onStart: () -> Unit,
) {
    val topic = VoiceV8Topic.forRole(state.selectedRole)
    val enabled = canStartVoice(state)
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val quotaText = when {
        state.isLoading -> stringResource(R.string.hsk_common_state_loading)
        state.status == null -> stringResource(R.string.error_voice_unavailable)
        state.status?.isPaid == true -> stringResource(R.string.voice_limit_premium)
        else -> stringResource(
            R.string.voice_limit_free,
            state.status?.remainingVoiceLimit ?: state.remainingLimit,
        )
    }
    Surface(
        color = Color.Black,
        shape = RoundedCornerShape(24.dp),
        border = BorderStroke(1.dp, Color(0xFF262626)),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.padding(start = 20.dp, end = 20.dp, top = 26.dp, bottom = 22.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            VoiceV8HomeOrb(Modifier.size(112.dp))
            Spacer(Modifier.height(16.dp))
            Text(
                text = stringResource(R.string.hsk_course_voice_title),
                style = MaterialTheme.typography.titleLarge.copy(fontSize = 18.sp, letterSpacing = (-0.2).sp),
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = stringResource(topic.titleRes) + " · " + topic.zh,
                style = MaterialTheme.typography.bodyMedium.copy(fontSize = 13.sp, lineHeight = 18.sp),
                color = Color(0xFFB5B5B8),
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(12.dp))
            Text(
                text = quotaText,
                style = MaterialTheme.typography.labelMedium.copy(lineHeight = 17.sp),
                color = Color(0xFF8E8E91),
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(18.dp))
            // Full width up to 300 dp: a long ru/tg label wraps inside the pill.
            Box(
                modifier = Modifier
                    .widthIn(max = 300.dp)
                    .fillMaxWidth()
                    .heightIn(min = 48.dp)
                    .graphicsLayer { alpha = if (enabled) 1f else 0.55f }
                    .clip(RoundedCornerShape(24.dp))
                    .background(if (pressed && enabled) Color(0xFFB23530) else Color(0xFFE04A40))
                    .clickable(
                        enabled = enabled && !state.isStarting,
                        interactionSource = interaction,
                        indication = null,
                        role = Role.Button,
                        onClick = onStart,
                    )
                    .padding(horizontal = 22.dp, vertical = 12.dp),
                contentAlignment = Alignment.Center,
            ) {
                if (state.isStarting) {
                    CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp, color = Color.White)
                } else {
                    Text(
                        text = stringResource(R.string.hsk_course_voice_start),
                        fontSize = 16.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.White,
                        textAlign = TextAlign.Center,
                    )
                }
            }
        }
    }
}

@Composable
private fun RoleCard(
    role: VoiceRoleSpec,
    selected: Boolean,
    onClick: () -> Unit,
) {
    HskGlassSurface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        shadowElevation = 6.dp,
        borderColor = if (selected) PompColors.Cinnabar else null,
        onClick = onClick,
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
private fun VoiceResult(
    state: VoiceUiState,
    onDone: () -> Unit,
) {
    val result = state.result ?: return
    val mistakes = result.transcript.filter { !it.correction.isNullOrBlank() }
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(
            start = 20.dp,
            end = 20.dp,
            top = 16.dp,
            bottom = 20.dp + LocalMainBottomInset.current,
        ),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        item {
            HskGlassSurface(
                modifier = Modifier.fillMaxWidth().widthIn(max = 520.dp),
                shape = RoundedCornerShape(22.dp),
                shadowElevation = 8.dp,
            ) {
                Column(
                    modifier = Modifier.fillMaxWidth().padding(20.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text(
                        text = stringResource(R.string.voice_result_title),
                        style = MaterialTheme.typography.headlineMedium,
                        color = PompColors.Ink,
                        textAlign = TextAlign.Center,
                    )
                    Text(
                        text = stringResource(
                            R.string.voice_result_body,
                            result.messageCount,
                            result.goodCount,
                            result.mistakeCount,
                        ),
                        style = MaterialTheme.typography.bodyLarge,
                        color = PompColors.InkSecondary,
                        textAlign = TextAlign.Center,
                    )
                    result.scenario?.title?.takeIf { it.isNotBlank() }?.let { title ->
                        Text(
                            text = stringResource(R.string.voice_scenario_practiced, title),
                            style = MaterialTheme.typography.bodyMedium,
                            color = PompColors.InkSecondary,
                            textAlign = TextAlign.Center,
                        )
                    }
                }
            }
        }
        if (mistakes.isEmpty()) {
            item {
                Text(
                    text = stringResource(R.string.voice_result_no_mistakes),
                    modifier = Modifier.fillMaxWidth().widthIn(max = 520.dp).padding(top = 12.dp),
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.Jade,
                    textAlign = TextAlign.Center,
                )
            }
        } else {
            item {
                Text(
                    text = stringResource(R.string.voice_result_mistakes_title),
                    modifier = Modifier.fillMaxWidth().widthIn(max = 520.dp).padding(top = 12.dp),
                    style = MaterialTheme.typography.titleMedium,
                    color = PompColors.Ink,
                )
            }
            items(mistakes) { item -> VoiceMistakeReview(item) }
        }
        item {
            HskPrimaryButton(
                text = stringResource(R.string.voice_again),
                onClick = onDone,
                modifier = Modifier.fillMaxWidth().widthIn(max = 520.dp).padding(top = 12.dp),
            )
        }
    }
}

@Composable
private fun VoiceMistakeReview(item: VoiceTranscriptDto) {
    HskGlassSurface(
        modifier = Modifier.fillMaxWidth().widthIn(max = 520.dp),
        shape = RoundedCornerShape(16.dp),
        shadowElevation = 4.dp,
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                text = stringResource(R.string.voice_result_user_said, item.user),
                style = MaterialTheme.typography.bodyLarge,
                color = PompColors.Flame,
            )
            Text(
                text = stringResource(R.string.voice_result_correction, item.correction.orEmpty()),
                style = PompTextStyles.hanziMedium,
                color = PompColors.Jade,
            )
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
