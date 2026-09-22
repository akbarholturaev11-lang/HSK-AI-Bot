package com.pomp.hskai.feature.auth

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
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
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Language
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.AuthProvider
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskBrandLoader
import com.pomp.hskai.core.design.components.HskCharacter
import com.pomp.hskai.core.design.components.HskCharacterMood
import com.pomp.hskai.core.design.components.HskCharacterStage
import com.pomp.hskai.core.design.components.HskGlassSurface
import com.pomp.hskai.core.i18n.AppLanguage

/**
 * The way into the app: one card per sign-in provider.
 *
 * Telegram is always offered, because it is the only flow that can create an
 * account. Google and Apple appear only when the server reports them, so a
 * build or deployment without OAuth credentials shows a Telegram-only screen
 * rather than a button that fails when tapped.
 *
 * Nothing on this screen asks the learner to read, copy or type a code: the
 * Telegram card opens the bot, the bot shows one confirm button, and the
 * session arrives through the poll that is already running.
 */
@Composable
fun LinkScreen(
    state: LinkUiState,
    modifier: Modifier = Modifier,
    language: AppLanguage = AppLanguage.DEFAULT,
    onLanguageSelected: (AppLanguage) -> Unit = {},
    onContinueWithTelegram: () -> Unit = {},
    onSignInWithGoogle: () -> Unit = {},
    onSignInWithApple: () -> Unit = {},
    onBrowserUrlOpened: () -> Unit = {},
    onTelegramUrlOpened: () -> Unit = {},
    onDismissWaiting: () -> Unit = {},
) {
    val context = LocalContext.current
    // Apple has no native SDK, so its leg runs in a Custom Tab. The result
    // comes back through the poll that is already running, which is why the
    // app needs no inbound auth deep link and no new allowlisted destination.
    LaunchedEffect(state.pendingBrowserUrl) {
        val url = state.pendingBrowserUrl
        if (!url.isNullOrEmpty()) {
            openCustomTab(context, url)
            onBrowserUrlOpened()
        }
    }
    // Telegram is handed over the same way: the view model publishes the bot
    // link once, the screen opens it once, so a recomposition cannot reopen
    // Telegram behind the learner's back.
    LaunchedEffect(state.pendingTelegramUrl) {
        val url = state.pendingTelegramUrl
        if (!url.isNullOrEmpty()) {
            openTelegram(context, url)
            onTelegramUrlOpened()
        }
    }
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            BrandHeader(language = language, onLanguageSelected = onLanguageSelected)
            Spacer(Modifier.height(12.dp))
            HeroPanda()
            Spacer(Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.auth_welcome_greeting),
                style = MaterialTheme.typography.headlineLarge,
                color = PompColors.Ink,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(6.dp))
            Text(
                text = stringResource(R.string.auth_choose_method),
                style = MaterialTheme.typography.bodyLarge,
                color = PompColors.InkSecondary,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(24.dp))
            val started = state.busyProvider != null && state.isWaitingForApproval
            if (started || state.isRequestingCode || state.isLinked) {
                WaitingBlock(
                    telegram = state.busyProvider != AuthProvider.GOOGLE &&
                        state.busyProvider != AuthProvider.APPLE,
                    onOpenTelegramAgain = onContinueWithTelegram,
                    onDismiss = onDismissWaiting,
                )
            } else {
                ProviderCards(
                    state = state,
                    onContinueWithTelegram = onContinueWithTelegram,
                    onSignInWithGoogle = onSignInWithGoogle,
                    onSignInWithApple = onSignInWithApple,
                )
            }
            Spacer(Modifier.height(28.dp))
            Tagline()
            Spacer(Modifier.height(12.dp))
        }
    }
}

/**
 * Wordmark and language switch.
 *
 * The switch is three tappable codes wide, which on a 360dp phone leaves no
 * room for a centred wordmark beside it — so the wordmark takes the start of
 * the row rather than colliding with the switch.
 */
@Composable
private fun BrandHeader(
    language: AppLanguage,
    onLanguageSelected: (AppLanguage) -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(
            text = brandWordmark(),
            style = MaterialTheme.typography.titleLarge,
        )
        LanguageSwitch(language = language, onLanguageSelected = onLanguageSelected)
    }
}

/** "HSK" in ink, "AI" in the brand red — the same lockup as the Mini App. */
@Composable
private fun brandWordmark(): AnnotatedString {
    val name = stringResource(R.string.app_name)
    val ink = PompColors.Ink
    val accent = PompColors.Cinnabar
    return buildAnnotatedString {
        val split = name.lastIndexOf(' ')
        if (split <= 0) {
            withStyle(SpanStyle(color = ink)) { append(name) }
            return@buildAnnotatedString
        }
        withStyle(SpanStyle(color = ink)) { append(name.substring(0, split + 1)) }
        withStyle(SpanStyle(color = accent)) { append(name.substring(split + 1)) }
    }
}

/**
 * Language switch.
 *
 * The account owns the language once the learner is signed in, but this screen
 * runs before there is an account, so the choice made here is stored locally
 * and replaced by the account's language on the first bootstrap.
 */
@Composable
private fun LanguageSwitch(
    language: AppLanguage,
    onLanguageSelected: (AppLanguage) -> Unit,
) {
    Surface(
        shape = CircleShape,
        color = if (PompColors.IsDark) PompColors.PaperRaised else Color.White,
        shadowElevation = 3.dp,
    ) {
        Row(
            modifier = Modifier.padding(start = 10.dp, end = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                imageVector = Icons.Filled.Language,
                contentDescription = stringResource(R.string.cd_language_switch),
                tint = PompColors.InkSecondary,
                modifier = Modifier.size(16.dp),
            )
            Spacer(Modifier.size(6.dp))
            AppLanguage.entries.forEach { entry ->
                val selected = entry == language
                Text(
                    text = stringResource(languageCodeRes(entry)),
                    style = MaterialTheme.typography.labelMedium,
                    color = if (selected) PompColors.Paper else PompColors.InkSecondary,
                    modifier = Modifier
                        .padding(vertical = 4.dp, horizontal = 2.dp)
                        .clip(CircleShape)
                        .background(if (selected) PompColors.Cinnabar else Color.Transparent)
                        .clickable(enabled = !selected) { onLanguageSelected(entry) }
                        .widthIn(min = 34.dp)
                        .padding(horizontal = 8.dp, vertical = 6.dp),
                    textAlign = TextAlign.Center,
                )
            }
        }
    }
}

private fun languageCodeRes(language: AppLanguage): Int = when (language) {
    AppLanguage.UZBEK -> R.string.language_code_uz
    AppLanguage.RUSSIAN -> R.string.language_code_ru
    AppLanguage.TAJIK -> R.string.language_code_tj
}

/**
 * The coach, reading.
 *
 * It is the same panda the lessons draw, on a soft brand wash, rather than a
 * bitmap: one source of truth for the character, and it follows the palette
 * into the dark theme.
 */
@Composable
private fun HeroPanda() {
    Box(
        modifier = Modifier
            .size(216.dp)
            .background(
                brush = Brush.radialGradient(
                    0f to PompColors.CinnabarSoft,
                    1f to PompColors.Paper,
                ),
                shape = CircleShape,
            ),
        contentAlignment = Alignment.Center,
    ) {
        HskCharacterStage(
            character = HskCharacter.Panda,
            mood = HskCharacterMood.Loading,
            modifier = Modifier.size(168.dp),
        )
    }
}

@Composable
private fun ProviderCards(
    state: LinkUiState,
    onContinueWithTelegram: () -> Unit,
    onSignInWithGoogle: () -> Unit,
    onSignInWithApple: () -> Unit,
) {
    val errorRes = state.error?.messageRes ?: R.string.auth_link_expired.takeIf { state.isExpired }
    Column(modifier = Modifier.fillMaxWidth()) {
        if (errorRes != null) {
            Text(
                text = stringResource(errorRes),
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.Flame,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(14.dp))
        }
        ProviderCard(
            iconRes = R.drawable.ic_brand_telegram,
            label = stringResource(R.string.auth_continue_telegram),
            enabled = !state.isRequestingCode,
            onClick = onContinueWithTelegram,
        )
        state.providers.forEach { provider ->
            Spacer(Modifier.height(12.dp))
            when (provider) {
                AuthProvider.GOOGLE -> ProviderCard(
                    iconRes = R.drawable.ic_brand_google,
                    label = stringResource(R.string.auth_continue_google_short),
                    enabled = state.busyProvider == null,
                    onClick = onSignInWithGoogle,
                )

                AuthProvider.APPLE -> ProviderCard(
                    iconRes = R.drawable.ic_brand_apple,
                    label = stringResource(R.string.auth_continue_apple_short),
                    enabled = state.busyProvider == null,
                    onClick = onSignInWithApple,
                    // Apple ships one mark in two colours; ink keeps it legible
                    // on paper and in the dark theme alike.
                    tint = PompColors.Ink,
                )

                AuthProvider.TELEGRAM -> Unit // Already the card above.
            }
        }
    }
}

@Composable
private fun ProviderCard(
    iconRes: Int,
    label: String,
    enabled: Boolean,
    onClick: () -> Unit,
    tint: Color? = null,
) {
    HskGlassSurface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(22.dp),
        shadowElevation = 8.dp,
        onClick = onClick,
        enabled = enabled,
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 68.dp)
                .padding(horizontal = 18.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Image(
                painter = painterResource(iconRes),
                contentDescription = null,
                modifier = Modifier.size(30.dp),
                colorFilter = tint?.let { ColorFilter.tint(it) },
            )
            Spacer(Modifier.size(16.dp))
            Text(
                text = label,
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.Ink,
            )
            Spacer(Modifier.weight(1f))
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = PompColors.InkSecondary.copy(alpha = 0.55f),
                modifier = Modifier.size(22.dp),
            )
        }
    }
}

/** Shown from the moment a provider is started until the session arrives. */
@Composable
private fun WaitingBlock(
    telegram: Boolean,
    onOpenTelegramAgain: () -> Unit,
    onDismiss: () -> Unit,
) {
    HskGlassSurface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(22.dp),
        shadowElevation = 8.dp,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp, vertical = 22.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                HskBrandLoader(compact = true)
                Spacer(Modifier.size(10.dp))
                Text(
                    text = stringResource(
                        if (telegram) {
                            R.string.auth_waiting_telegram
                        } else {
                            R.string.auth_provider_waiting
                        }
                    ),
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                    textAlign = TextAlign.Center,
                )
            }
            if (telegram) {
                Spacer(Modifier.height(6.dp))
                TextButton(
                    onClick = onOpenTelegramAgain,
                    modifier = Modifier.heightIn(min = 44.dp),
                ) {
                    Text(
                        text = stringResource(R.string.auth_open_telegram_again),
                        style = MaterialTheme.typography.labelLarge,
                        color = PompColors.CinnabarDark,
                    )
                }
            }
            TextButton(
                onClick = onDismiss,
                modifier = Modifier.heightIn(min = 44.dp),
            ) {
                Text(
                    text = stringResource(R.string.action_cancel),
                    style = MaterialTheme.typography.labelLarge,
                    color = PompColors.InkSecondary,
                )
            }
        }
    }
}

@Composable
private fun Tagline() {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
    ) {
        HorizontalDivider(
            modifier = Modifier.weight(1f),
            color = PompColors.Divider,
        )
        Text(
            text = stringResource(R.string.auth_tagline),
            style = MaterialTheme.typography.bodySmall,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(horizontal = 12.dp),
        )
        HorizontalDivider(
            modifier = Modifier.weight(1f),
            color = PompColors.Divider,
        )
    }
}

/** Opens a provider page in a Custom Tab; the URL is server-built, never user input. */
private fun openCustomTab(context: Context, url: String) {
    if (!url.startsWith("https://")) return
    val intent = CustomTabsIntent.Builder().setShowTitle(true).build()
    intent.intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    runCatching { intent.launchUrl(context, Uri.parse(url)) }
}

private fun openTelegram(context: Context, deepLink: String) {
    if (deepLink.isEmpty()) return
    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(deepLink))
        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    runCatching { context.startActivity(intent) }
}
