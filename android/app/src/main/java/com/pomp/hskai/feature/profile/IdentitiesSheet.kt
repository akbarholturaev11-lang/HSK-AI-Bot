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
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.AuthProvider
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.data.api.AndroidProfileResponse

private val PROFILE_AVATARS = listOf("panda_cheer", "panda_streak", "panda_worried")

/**
 * Account/profile editor. Telegram identity is intentionally read-only; the
 * editable display name and avatar are HSK AI profile fields shared by clients.
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
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val context = LocalContext.current
    val user = profile?.user
    var displayName by remember(user?.name) { mutableStateOf(user?.name.orEmpty()) }
    var avatarKey by remember(user?.avatarKey) { mutableStateOf(user?.avatarKey.orEmpty()) }

    LaunchedEffect(state.pendingBrowserUrl) {
        state.pendingBrowserUrl?.takeIf { it.isNotEmpty() }?.let {
            openProviderTab(context, it)
            onBrowserUrlOpened()
        }
    }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = PompColors.Paper,
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp).padding(bottom = 28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                stringResource(R.string.profile_account_title),
                color = PompColors.Ink,
                fontSize = 20.sp,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.fillMaxWidth(),
            )
            Text(
                stringResource(R.string.profile_account_subtitle),
                color = PompColors.InkSecondary,
                fontSize = 13.sp,
                modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
            )
            Spacer(Modifier.height(18.dp))

            Surface(
                color = PompColors.GoldSoft,
                shape = CircleShape,
                modifier = Modifier.size(92.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Image(
                        painter = painterResource(profileAvatarDrawable(avatarKey)),
                        contentDescription = null,
                        modifier = Modifier.size(82.dp),
                    )
                }
            }
            Spacer(Modifier.height(8.dp))
            Text(
                stringResource(R.string.profile_account_avatar),
                color = PompColors.CinnabarDark,
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold,
            )
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                PROFILE_AVATARS.forEach { key ->
                    val selected = avatarKey == key
                    Surface(
                        color = if (selected) PompColors.CinnabarSoft else PompColors.PaperRaised,
                        shape = CircleShape,
                        border = BorderStroke(
                            if (selected) 2.dp else 1.dp,
                            if (selected) PompColors.Cinnabar else PompColors.Divider,
                        ),
                        modifier = Modifier.size(58.dp).clickable { avatarKey = key },
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Image(
                                painter = painterResource(profileAvatarDrawable(key)),
                                contentDescription = null,
                                modifier = Modifier.size(50.dp),
                            )
                        }
                    }
                }
            }
            Text(
                stringResource(R.string.profile_account_avatar_hint),
                color = PompColors.InkSecondary,
                fontSize = 12.sp,
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
            )

            Spacer(Modifier.height(16.dp))
            OutlinedTextField(
                value = displayName,
                onValueChange = { if (it.length <= 80) displayName = it },
                label = { Text(stringResource(R.string.profile_account_name)) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(10.dp))
            ReadOnlyField(
                label = stringResource(R.string.profile_account_telegram),
                value = user?.telegramUsername?.takeIf { it.isNotBlank() }?.let { "@$it" } ?: "—",
            )
            user?.phone?.takeIf { it.isNotBlank() }?.let { phone ->
                Spacer(Modifier.height(10.dp))
                ReadOnlyField(
                    label = stringResource(R.string.profile_account_phone),
                    value = phone,
                )
            }

            Spacer(Modifier.height(16.dp))
            Surface(
                color = PompColors.PaperRaised,
                shape = RoundedCornerShape(16.dp),
                border = BorderStroke(1.dp, PompColors.Divider),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column {
                    ProviderAccountRow(
                        provider = AuthProvider.GOOGLE,
                        state = state,
                        onConnect = onConnect,
                        onDisconnect = onDisconnect,
                    )
                    ProviderAccountRow(
                        provider = AuthProvider.APPLE,
                        state = state,
                        onConnect = onConnect,
                        onDisconnect = onDisconnect,
                    )
                }
            }

            Spacer(Modifier.height(16.dp))
            Button(
                onClick = { onSaveProfile(displayName.trim(), avatarKey) },
                enabled = !savingProfile && displayName.trim().isNotEmpty(),
                modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp),
                shape = RoundedCornerShape(14.dp),
            ) {
                Text(if (savingProfile) "…" else stringResource(R.string.profile_account_save))
            }

            state.sessionsRevoked?.let {
                Spacer(Modifier.height(10.dp))
                IdentityNotice(stringResource(R.string.profile_identity_unlinked))
            }
            state.error?.let { error ->
                Spacer(Modifier.height(10.dp))
                IdentityNotice(stringResource(error.messageRes))
            }
        }
    }
}

@Composable
private fun ReadOnlyField(label: String, value: String) {
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(12.dp),
        border = BorderStroke(1.dp, PompColors.Divider),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
            Text(label, color = PompColors.InkSecondary, fontSize = 11.sp)
            Text(value, color = PompColors.Ink, fontSize = 15.sp)
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
    Row(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Column(Modifier.weight(1f)) {
            Text(
                stringResource(
                    if (provider == AuthProvider.GOOGLE) R.string.profile_account_google
                    else R.string.profile_account_apple
                ),
                color = PompColors.Ink,
                fontSize = 14.sp,
            )
            Text(
                identity?.emailMasked ?: identity?.displayName
                    ?: stringResource(R.string.profile_account_connect),
                color = PompColors.InkDisabled,
                fontSize = 12.sp,
            )
        }
        if (identity != null) {
            TextButton(
                onClick = { onDisconnect(identity.id) },
                enabled = state.busyProvider == null,
            ) {
                Text(stringResource(R.string.profile_account_disconnect), color = PompColors.Flame)
            }
        } else if (canConnect) {
            OutlinedButton(
                onClick = { onConnect(provider, context as? Activity) },
                enabled = state.busyProvider == null,
            ) {
                Text(stringResource(R.string.profile_account_connect))
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
