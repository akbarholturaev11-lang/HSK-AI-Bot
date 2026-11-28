package com.pomp.hskai.feature.limit

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.HeadsetMic
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.pomp.hskai.R
import com.pomp.hskai.core.design.ProColors
import com.pomp.hskai.core.text.ResetTime
import com.pomp.hskai.feature.assistant.AssistantHidden

/** Direct reuses the inline Pro checkout. Play presents the same calm full-screen
 * task anatomy with its permitted access recheck, never an external purchase. */
@Composable
fun SectionLimitOverlay(
    sectionTitle: String,
    sourceKey: String,
    limit: LimitGate,
    onClose: () -> Unit,
    modifier: Modifier = Modifier,
    reason: String? = null,
    resetAt: String? = null,
) {
    AssistantHidden()
    DisposableEffect(Unit) {
        limit.actions.onPresented()
        onDispose { limit.actions.onDismissed() }
    }
    if (ChannelLimitCheckout(sourceKey, limit, onClose, modifier)) return
    val daily = ResetTime.localClock(resetAt) != null
    val parentContext = androidx.compose.ui.platform.LocalContext.current
    val parentConfiguration = androidx.compose.ui.platform.LocalConfiguration.current
    val parentDensity = androidx.compose.ui.platform.LocalDensity.current
    Dialog(onDismissRequest = onClose,
        properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false)) {
        androidx.compose.runtime.CompositionLocalProvider(
            androidx.compose.ui.platform.LocalContext provides parentContext,
            androidx.compose.ui.platform.LocalConfiguration provides parentConfiguration,
            androidx.compose.ui.platform.LocalDensity provides parentDensity,
        ) {
        LimitDialogInsets()
        Column(modifier.fillMaxSize().background(ProColors.Paper).safeDrawingPadding()
            .padding(horizontal = 20.dp).testTag("section-limit-sheet")) {
            Row(Modifier.fillMaxWidth().heightIn(min = 48.dp), verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onClose, modifier = Modifier.size(48.dp)) {
                    Icon(Icons.Default.Close, stringResource(R.string.action_close), tint = ProColors.Muted)
                }
                Spacer(Modifier.weight(1f))
                IconButton(onClick = {
                    if (limit.state.supportUrl.isNotBlank()) limit.actions.onSupport()
                    else android.widget.Toast.makeText(parentContext, R.string.profile_help_unavailable,
                        android.widget.Toast.LENGTH_SHORT).show()
                }, modifier = Modifier.size(48.dp).testTag("limit-support")) {
                    Icon(Icons.Default.HeadsetMic, stringResource(R.string.profile_help), tint = ProColors.Muted)
                }
            }
            Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(vertical = 24.dp),
                horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                ProPanda(Modifier.size(148.dp))
                Text(stringResource(if (daily) R.string.play_limit_daily_heading else R.string.play_limit_heading),
                    color = ProColors.Ink, fontSize = 28.sp, lineHeight = 32.sp, fontWeight = FontWeight.ExtraBold,
                    textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp))
                Text(stringResource(R.string.play_limit_required), color = ProColors.Ink,
                    fontSize = 20.sp, lineHeight = 26.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
                Text(stringResource(R.string.play_limit_description), color = ProColors.Muted,
                    fontSize = 16.sp, lineHeight = 24.sp, textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth().padding(top = 12.dp))
                if (daily) Text(stringResource(R.string.play_limit_renewal), color = ProColors.Muted,
                    fontSize = 14.sp, lineHeight = 20.sp, textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth().padding(top = 12.dp))
                if (limit.state.recheckFoundNothing) Text(stringResource(R.string.limit_recheck_none),
                    color = ProColors.Muted, modifier = Modifier.padding(top = 12.dp))
                limit.state.error?.let { Text(stringResource(it.messageRes), color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.padding(top = 12.dp)) }
            }
            Button(onClick = limit.actions.onRecheck, enabled = !limit.state.isBusy,
                modifier = Modifier.fillMaxWidth().padding(top = 12.dp, bottom = 16.dp).heightIn(min = 56.dp),
                shape = androidx.compose.foundation.shape.RoundedCornerShape(16.dp),
                colors = ButtonDefaults.buttonColors(containerColor = ProColors.Cta, contentColor = ProColors.OnCta)) {
                if (limit.state.isBusy) CircularProgressIndicator(Modifier.size(20.dp), color = ProColors.OnCta, strokeWidth = 2.dp)
                else Text(stringResource(R.string.play_limit_check_access), fontSize = 17.sp, fontWeight = FontWeight.Bold)
            }
        }
        }
    }
}

/** Compose 1.7 measures full display height on Android 15+. Match the actual
 * dialog window to that viewport before applying native safeDrawingPadding. */
@Composable
internal fun LimitDialogInsets() {
    val view = androidx.compose.ui.platform.LocalView.current
    DisposableEffect(view) {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.R) {
            (view.parent as? androidx.compose.ui.window.DialogWindowProvider)?.window?.let { window ->
                window.attributes = window.attributes.apply {
                    setFitInsetsTypes(0)
                    layoutInDisplayCutoutMode = android.view.WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS
                }
            }
        }
        onDispose { }
    }
}
