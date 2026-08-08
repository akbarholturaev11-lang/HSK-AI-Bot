package com.pomp.hskai.feature.auth

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles

/**
 * Telegram device-link screen.
 *
 * The code is displayed, never embedded in the Telegram URL. Opening Telegram
 * only starts the manual-entry conversation, so possessing the link can never
 * reserve or approve a device.
 */
@Composable
fun LinkScreen(
    state: LinkUiState,
    onRequestCode: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = stringResource(R.string.link_title),
                style = MaterialTheme.typography.headlineMedium,
                color = PompColors.Ink,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(12.dp))
            Text(
                text = stringResource(R.string.link_subtitle),
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.InkSecondary,
                textAlign = TextAlign.Center,
            )

            Spacer(Modifier.height(28.dp))

            when {
                state.isRequestingCode -> LoadingBlock()
                state.pending == null || state.isExpired -> ExpiredBlock(
                    isExpired = state.isExpired,
                    errorRes = state.error?.messageRes,
                    onRequestCode = onRequestCode,
                )

                else -> CodeBlock(state = state, context = context)
            }

            Spacer(Modifier.height(24.dp))
            Text(
                text = stringResource(R.string.link_security_note),
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.InkSecondary,
                textAlign = TextAlign.Center,
            )
        }
    }
}

@Composable
private fun LoadingBlock() {
    Column(
        modifier = Modifier.heightIn(min = 220.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        CircularProgressIndicator(color = PompColors.Cinnabar)
        Spacer(Modifier.height(16.dp))
        Text(
            text = stringResource(R.string.state_loading),
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.InkSecondary,
        )
    }
}

@Composable
private fun ExpiredBlock(
    isExpired: Boolean,
    errorRes: Int?,
    onRequestCode: () -> Unit,
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        if (errorRes != null) {
            Text(
                text = stringResource(errorRes),
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.CinnabarDark,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(16.dp))
        } else if (isExpired) {
            Text(
                text = stringResource(R.string.link_expired),
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.CinnabarDark,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(16.dp))
        }
        Button(
            onClick = onRequestCode,
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 48.dp),
            shape = RoundedCornerShape(14.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = PompColors.Cinnabar,
                contentColor = PompColors.Paper,
            ),
        ) {
            Text(
                text = stringResource(
                    if (isExpired || errorRes != null) {
                        R.string.link_new_code
                    } else {
                        R.string.action_continue
                    }
                ),
                style = MaterialTheme.typography.labelLarge,
            )
        }
    }
}

@Composable
private fun CodeBlock(state: LinkUiState, context: Context) {
    val copiedLabel = stringResource(R.string.link_code_copied)
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        StepRow(1, stringResource(R.string.link_step_1))
        StepRow(2, stringResource(R.string.link_step_2))
        StepRow(3, stringResource(R.string.link_step_3))

        Spacer(Modifier.height(24.dp))

        Text(
            text = stringResource(R.string.link_code_label),
            style = MaterialTheme.typography.labelLarge,
            color = PompColors.InkSecondary,
        )
        Spacer(Modifier.height(8.dp))
        Surface(
            color = PompColors.CinnabarSoft,
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 18.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center,
            ) {
                Text(
                    text = state.displayCode,
                    style = PompTextStyles.linkCode,
                    color = PompColors.CinnabarDark,
                )
            }
        }

        Spacer(Modifier.height(12.dp))
        OutlinedButton(
            onClick = { copyCode(context, state.displayCode, copiedLabel) },
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 48.dp)
                .semantics { contentDescription = copiedLabel },
            shape = RoundedCornerShape(14.dp),
        ) {
            Text(
                text = stringResource(R.string.cd_copy_code),
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.CinnabarDark,
            )
        }

        Spacer(Modifier.height(16.dp))
        Button(
            onClick = { openTelegram(context, state.botDeepLink) },
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 48.dp),
            shape = RoundedCornerShape(14.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = PompColors.Cinnabar,
                contentColor = PompColors.Paper,
            ),
        ) {
            Text(
                text = stringResource(R.string.link_open_telegram),
                style = MaterialTheme.typography.labelLarge,
            )
        }

        if (state.isWaitingForApproval) {
            Spacer(Modifier.height(20.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(
                    modifier = Modifier.size(18.dp),
                    strokeWidth = 2.dp,
                    color = PompColors.Jade,
                )
                Spacer(Modifier.size(10.dp))
                Text(
                    text = stringResource(R.string.link_waiting),
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                )
            }
            Spacer(Modifier.height(6.dp))
            Text(
                text = stringResource(
                    R.string.link_expires_in,
                    formatRemaining(state.secondsRemaining),
                ),
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.InkSecondary,
            )
        }
    }
}

@Composable
private fun StepRow(index: Int, text: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier
                .size(26.dp)
                .background(PompColors.CinnabarSoft, CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = index.toString(),
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.CinnabarDark,
            )
        }
        Spacer(Modifier.size(12.dp))
        Text(
            text = text,
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.Ink,
        )
    }
}

internal fun formatRemaining(totalSeconds: Int): String {
    val safe = totalSeconds.coerceAtLeast(0)
    return "%d:%02d".format(safe / 60, safe % 60)
}

private fun copyCode(context: Context, code: String, label: String) {
    if (code.isEmpty()) return
    val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
    clipboard?.setPrimaryClip(ClipData.newPlainText(label, code))
}

private fun openTelegram(context: Context, deepLink: String) {
    if (deepLink.isEmpty()) return
    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(deepLink))
        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    runCatching { context.startActivity(intent) }
}
