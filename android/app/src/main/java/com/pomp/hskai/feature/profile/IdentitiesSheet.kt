package com.pomp.hskai.feature.profile

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.AuthProvider
import com.pomp.hskai.core.auth.authActivity
import com.pomp.hskai.core.auth.isTelegramIdentityLinkUrl
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.data.api.AndroidProfileResponse

private val PROFILE_AVATARS = listOf("panda_cheer", "panda_streak", "panda_worried")

/**
 * Account/profile editor. An attached Telegram identity remains read-only;
 * provider-only accounts can attach one after explicit bot confirmation.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun IdentitiesSheet(
    state: IdentitiesUiState,
    profile: AndroidProfileResponse?,
    savingProfile: Boolean,
    onSaveProfile: (String, String) -> Unit,
    onConnect: (AuthProvider, Activity?) -> Unit,
    onDisconnect: (String) -> Unit,
    onBrowserUrlOpened: () -> Unit,
    onDismiss: () -> Unit,
    onCancelConnection: () -> Unit = {},
    onReopenTelegram: () -> Unit = {},
    profileError: ApiError? = null,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val context = LocalContext.current
    val user = profile?.user
    var displayName by remember(user?.name) { mutableStateOf(user?.name.orEmpty()) }
    var avatarKey by remember(user?.avatarKey) { mutableStateOf(user?.avatarKey.orEmpty()) }

    DisposableEffect(Unit) {
        onDispose { onCancelConnection() }
    }

    LaunchedEffect(state.pendingBrowserUrl) {
        state.pendingBrowserUrl?.takeIf { it.isNotEmpty() }?.let {
            if (state.busyProvider != AuthProvider.TELEGRAM || isTelegramIdentityLinkUrl(it)) {
                openProviderTab(context, it)
            }
            onBrowserUrlOpened()
        }
    }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = PompColors.Paper,
    ) {
        Column(Modifier.fillMaxWidth().imePadding().padding(horizontal = 20.dp, vertical = 8.dp).testTag("profile-account")) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text(stringResource(R.string.profile_account_title), color = PompColors.Ink,
                    style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1f))
                IconButton(onClick = onDismiss) {
                    Icon(Icons.Filled.Close, contentDescription = stringResource(R.string.hsk_common_action_close), tint = PompColors.InkSecondary)
                }
            }
            Column(
                modifier = Modifier.weight(1f, fill = false).verticalScroll(rememberScrollState())
                    .testTag("profile-account-scroll"),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Text(stringResource(R.string.profile_account_avatar), color = PompColors.InkSecondary,
                    style = MaterialTheme.typography.labelLarge)
                Row(Modifier.fillMaxWidth().selectableGroup(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    PROFILE_AVATARS.forEachIndexed { index, key ->
                        val selected = avatarKey == key || (avatarKey.isBlank() && index == 0)
                        val label = stringResource(R.string.profile_account_avatar_option, index + 1)
                        Surface(
                            color = if (selected) PompColors.CinnabarSoft else PompColors.CardSurface,
                            shape = CircleShape,
                            border = BorderStroke(if (selected) 2.dp else 1.dp,
                                if (selected) PompColors.Cinnabar else PompColors.Divider),
                            modifier = Modifier.size(64.dp).selectable(selected = selected, role = Role.RadioButton,
                                enabled = !savingProfile, onClick = { avatarKey = key })
                                .semantics { contentDescription = label },
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Image(painter = painterResource(profileAvatarDrawable(key)), contentDescription = null,
                                    modifier = Modifier.size(54.dp))
                            }
                        }
                    }
                }
                OutlinedTextField(
                    value = displayName,
                    onValueChange = { if (it.length <= 80) displayName = it },
                    label = { Text(stringResource(R.string.profile_account_name)) },
                    enabled = !savingProfile,
                    singleLine = true,
                    shape = RoundedCornerShape(16.dp),
                    modifier = Modifier.fillMaxWidth(),
                )
                profileError?.let { IdentityNotice(stringResource(it.messageRes)) }
                Text(stringResource(R.string.profile_account_sign_in_methods), color = PompColors.InkSecondary,
                    style = MaterialTheme.typography.labelLarge)
                Surface(color = PompColors.CardSurface, shape = RoundedCornerShape(20.dp),
                    border = BorderStroke(1.dp, PompColors.Divider), modifier = Modifier.fillMaxWidth()) {
                    Column {
                        TelegramAccountRow(state, user?.telegramUsername, onConnect)
                        listOf(AuthProvider.GOOGLE, AuthProvider.APPLE).forEach { provider ->
                            if (provider in state.available || state.identities.any { it.provider == provider }) {
                                HorizontalDivider(color = PompColors.Divider, modifier = Modifier.padding(horizontal = 16.dp))
                                ProviderAccountRow(provider, state, onConnect, onDisconnect)
                            }
                        }
                    }
                }
                if (state.isLoading) {
                    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator(Modifier.size(24.dp), color = PompColors.Cinnabar, strokeWidth = 2.dp)
                    }
                }
                // This notice explains a disabled safety action, rather than
                // repeating general account/provider implementation details.
                if (!state.isLoading && state.identities.size == 1 && !state.telegramLinked) {
                    IdentityNotice(stringResource(R.string.error_oauth_last_identity))
                }
                if (state.telegramApprovalUrl != null && state.busyProvider == AuthProvider.TELEGRAM) {
                    IdentityNotice(stringResource(R.string.profile_telegram_link_waiting))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        TextButton(onClick = onReopenTelegram, modifier = Modifier.weight(1f).testTag("telegram-link-reopen")) {
                            Text(stringResource(R.string.auth_open_telegram_again))
                        }
                        TextButton(onClick = onCancelConnection, modifier = Modifier.testTag("telegram-link-cancel")) {
                            Text(stringResource(R.string.action_cancel))
                        }
                    }
                }
                state.sessionsRevoked?.let { IdentityNotice(stringResource(R.string.profile_identity_unlinked)) }
                state.error?.let { IdentityNotice(stringResource(it.messageRes)) }
            }
            val hasChanges = displayName.trim() != user?.name.orEmpty().trim() || avatarKey != user?.avatarKey.orEmpty()
            Button(
                onClick = { onSaveProfile(displayName.trim(), avatarKey) },
                enabled = !savingProfile && user != null && hasChanges && displayName.trim().isNotEmpty(),
                modifier = Modifier.fillMaxWidth().padding(top = 16.dp, bottom = 12.dp).heightIn(min = 52.dp),
                shape = RoundedCornerShape(16.dp),
                colors = androidx.compose.material3.ButtonDefaults.buttonColors(containerColor = PompColors.Cinnabar, contentColor = PompColors.Paper),
            ) {
                if (savingProfile) CircularProgressIndicator(Modifier.size(20.dp), color = PompColors.Paper, strokeWidth = 2.dp)
                else Text(stringResource(R.string.profile_account_save))
            }
        }
    }
}

@Composable
private fun TelegramAccountRow(state: IdentitiesUiState, username: String?, onConnect: (AuthProvider, Activity?) -> Unit) {
    val context = LocalContext.current
    Column(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 12.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(stringResource(R.string.hsk_course_rating_write_telegram), color = PompColors.Ink, fontSize = 16.sp, modifier = Modifier.weight(1f))
            if (!state.telegramLinked) {
                OutlinedButton(
                    onClick = { onConnect(AuthProvider.TELEGRAM, context.authActivity()) },
                    enabled = state.busyProvider == null && !state.isLoading,
                    modifier = Modifier.testTag("telegram-identity-connect"),
                ) {
                    Text(stringResource(R.string.profile_account_connect))
                }
            }
        }
        if (state.telegramLinked) {
            Text(username?.takeIf { it.isNotBlank() }?.let { "@${it.removePrefix("@")}" }
                ?: stringResource(R.string.profile_identity_connected),
                color = PompColors.InkSecondary, style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(top = 3.dp))
        }
    }
}

@Composable
private fun ProviderAccountRow(
    provider: AuthProvider,
    state: IdentitiesUiState,
    onConnect: (AuthProvider, Activity?) -> Unit,
    onDisconnect: (String) -> Unit,
) {
    val context = LocalContext.current
    val identity = state.identities.firstOrNull { it.provider == provider }
    val canConnect = provider in state.available
    Column(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 12.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(
                stringResource(
                    if (provider == AuthProvider.GOOGLE) R.string.profile_account_google
                    else R.string.profile_account_apple
                ),
                color = PompColors.Ink,
                fontSize = 16.sp,
                modifier = Modifier.weight(1f),
            )
            if (identity != null) {
                TextButton(
                    onClick = { onDisconnect(identity.id) },
                    enabled = state.busyProvider == null && state.canUnlinkProvider,
                ) {
                    Text(stringResource(R.string.profile_account_disconnect), color = PompColors.FlameInk)
                }
            } else if (canConnect) {
                OutlinedButton(
                    onClick = { onConnect(provider, context.authActivity()) },
                    enabled = state.busyProvider == null && !state.isLoading,
                    modifier = Modifier.testTag("${provider.wire}-identity-connect"),
                ) {
                    Text(stringResource(R.string.profile_account_connect))
                }
            }
        }
        (identity?.emailMasked ?: identity?.displayName)?.takeIf { it.isNotBlank() }?.let {
            Text(it, color = PompColors.InkSecondary, style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.fillMaxWidth().padding(top = 3.dp))
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

private fun profileAvatarDrawable(key: String): Int = when (key) {
    "panda_streak" -> R.drawable.widget_panda_streak
    "panda_worried" -> R.drawable.widget_panda_worried
    else -> R.drawable.widget_panda_cheer
}

private fun openProviderTab(context: Context, url: String) {
    if (!url.startsWith("https://")) return
    val intent = CustomTabsIntent.Builder().setShowTitle(true).build()
    intent.intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    runCatching { intent.launchUrl(context, Uri.parse(url)) }
}
