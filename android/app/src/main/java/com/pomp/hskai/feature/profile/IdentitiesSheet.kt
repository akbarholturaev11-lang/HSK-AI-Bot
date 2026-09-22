package com.pomp.hskai.feature.profile

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.AuthProvider
import com.pomp.hskai.core.design.PompColors

/**
 * Sign-in methods for the current account.
 *
 * Every row belongs to one internal account: connecting Google or Apple here
 * adds a way in, never a second account, so subscription and progress are
 * untouched. Telegram is shown as a fixed row because in this phase it is
 * always present and is what created the account.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun IdentitiesSheet(
    state: IdentitiesUiState,
    onConnect: (AuthProvider) -> Unit,
    onDisconnect: (String) -> Unit,
    onBrowserUrlOpened: () -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val context = LocalContext.current
    LaunchedEffect(state.pendingBrowserUrl) {
        val url = state.pendingBrowserUrl
        if (!url.isNullOrEmpty()) {
            openProviderTab(context, url)
            onBrowserUrlOpened()
        }
    }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = PompColors.Paper,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp)
                .padding(bottom = 28.dp)
        ) {
            Text(
                stringResource(R.string.profile_identities_title),
                color = PompColors.Ink,
                fontSize = 20.sp,
                fontWeight = FontWeight.SemiBold,
            )
            Spacer(Modifier.height(6.dp))
            Text(
                stringResource(R.string.profile_identities_explain),
                color = PompColors.InkSecondary,
                fontSize = 13.sp,
            )
            Spacer(Modifier.height(16.dp))

            Surface(
                color = PompColors.PaperRaised,
                shape = RoundedCornerShape(16.dp),
                border = BorderStroke(1.dp, PompColors.Divider),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column {
                    if (state.telegramLinked) {
                        IdentityRow(
                            label = stringResource(R.string.profile_identity_telegram),
                            detail = stringResource(R.string.profile_identity_connected),
                            action = null,
                        )
                    }
                    state.identities.forEach { identity ->
                        IdentityRow(
                            label = stringResource(identity.provider.labelRes()),
                            detail = identity.emailMasked
                                ?: stringResource(R.string.profile_identity_connected),
                            action = {
                                TextButton(
                                    onClick = { onDisconnect(identity.id) },
                                    enabled = state.busyProvider == null,
                                ) {
                                    Text(
                                        stringResource(R.string.profile_identity_disconnect),
                                        color = PompColors.Flame,
                                        fontSize = 13.sp,
                                    )
                                }
                            },
                        )
                    }
                }
            }

            val connectable = state.available.filter { provider ->
                provider != AuthProvider.TELEGRAM &&
                    state.identities.none { it.provider == provider }
            }
            if (connectable.isNotEmpty()) {
                Spacer(Modifier.height(16.dp))
                connectable.forEach { provider ->
                    OutlinedButton(
                        onClick = { onConnect(provider) },
                        enabled = state.busyProvider == null,
                        shape = RoundedCornerShape(14.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(min = 48.dp),
                    ) {
                        Text(
                            stringResource(
                                R.string.profile_identity_connect_provider,
                                stringResource(provider.labelRes()),
                            ),
                            color = PompColors.Ink,
                            fontSize = 14.sp,
                        )
                    }
                    Spacer(Modifier.height(8.dp))
                }
            }

            if (state.identities.isNotEmpty()) {
                Spacer(Modifier.height(4.dp))
                Text(
                    stringResource(R.string.profile_identity_unlink_warning),
                    color = PompColors.InkSecondary,
                    fontSize = 12.sp,
                )
            }
            state.sessionsRevoked?.let {
                Spacer(Modifier.height(10.dp))
                Box { IdentityNotice(stringResource(R.string.profile_identity_unlinked)) }
            }
            state.error?.let { error ->
                Spacer(Modifier.height(10.dp))
                Box { IdentityNotice(stringResource(error.messageRes)) }
            }
        }
    }
}

@Composable
private fun IdentityNotice(text: String) {
    Surface(
        color = PompColors.CinnabarSoft,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(
            text,
            color = PompColors.CinnabarDark,
            fontSize = 12.sp,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
        )
    }
}

@Composable
private fun IdentityRow(label: String, detail: String, action: (@Composable () -> Unit)?) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(label, color = PompColors.Ink, fontSize = 14.sp)
            Text(detail, color = PompColors.InkDisabled, fontSize = 12.sp)
        }
        action?.invoke()
    }
}

private fun AuthProvider.labelRes(): Int = when (this) {
    AuthProvider.TELEGRAM -> R.string.profile_identity_telegram
    AuthProvider.GOOGLE -> R.string.profile_identity_google
    AuthProvider.APPLE -> R.string.profile_identity_apple
}

/** The URL is always server-built; user input never reaches this. */
private fun openProviderTab(context: Context, url: String) {
    if (!url.startsWith("https://")) return
    val intent = CustomTabsIntent.Builder().setShowTitle(true).build()
    intent.intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    runCatching { intent.launchUrl(context, Uri.parse(url)) }
}
