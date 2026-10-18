package com.pomp.hskai.feature.profile

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.focusable
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
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.input.key.Key
import androidx.compose.ui.input.key.KeyEventType
import androidx.compose.ui.input.key.key
import androidx.compose.ui.input.key.type
import androidx.compose.ui.input.key.onPreviewKeyEvent
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.Role
import com.pomp.hskai.core.auth.AuthProvider
import kotlinx.coroutines.launch
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.feature.course.Hsk30BookSecondary
import com.pomp.hskai.feature.course.Hsk30BookPrimary
import com.pomp.hskai.feature.course.Hsk30BookPrice
import com.pomp.hskai.feature.course.Hsk30BookTitle
import com.pomp.hskai.feature.course.Hsk30BookDialog
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.domain.model.CourseHsk30
import java.time.Duration
import java.time.Instant

private val PromoGold = Color(0xFFEFB32B)
private val PromoPaper = Color(0xFF211D17)

internal enum class ProfilePromoPage(val key: String, val provider: AuthProvider? = null) {
    HSK30("hsk30"),
    PRO("pro"),
    TELEGRAM("telegram", AuthProvider.TELEGRAM),
    GOOGLE("google", AuthProvider.GOOGLE),
    APPLE("apple", AuthProvider.APPLE),
}

/** Offer account links only after an authoritative successful identity read. */
internal fun profilePromoPages(
    checkoutAvailable: Boolean,
    identities: IdentitiesUiState,
): List<ProfilePromoPage> = buildList {
    add(ProfilePromoPage.HSK30)
    if (checkoutAvailable) add(ProfilePromoPage.PRO)
    if (!identities.hasLoaded || identities.isLoading || identities.error != null) return@buildList
    if (!identities.telegramLinked) add(ProfilePromoPage.TELEGRAM)
    val linked = identities.identities.map { it.provider }.toSet()
    if (AuthProvider.GOOGLE in identities.available && AuthProvider.GOOGLE !in linked) add(ProfilePromoPage.GOOGLE)
    if (AuthProvider.APPLE in identities.available && AuthProvider.APPLE !in linked) add(ProfilePromoPage.APPLE)
}

/** Native counterpart of the Mini App profile carousel; no new entitlement rules. */
@Composable
internal fun ProfilePromoCarousel(
    state: ProfileUiState,
    accountIsPaid: Boolean,
    checkoutAvailable: Boolean,
    onOpenHsk30: () -> Unit,
    onOpenSubscription: (Boolean) -> Unit,
    onStartTrial: () -> Unit,
    identities: IdentitiesUiState = IdentitiesUiState(),
    onConnectIdentity: (AuthProvider) -> Unit = {},
) {
    // Play still has no Pro/checkout promotion; linking is available on both builds.
    val pages = remember(checkoutAvailable, identities) { profilePromoPages(checkoutAvailable, identities) }
    val pager = rememberPagerState(pageCount = { pages.size })
    val scope = rememberCoroutineScope()
    LaunchedEffect(pages) {
        // Removing a newly linked final page must never leave an invalid selection.
        if (pager.currentPage >= pages.size) pager.scrollToPage(pages.lastIndex)
    }
    Column(modifier = Modifier.fillMaxWidth()) {
        HorizontalPager(
            state = pager,
            key = { pages[it].key },
            pageSpacing = 10.dp,
            modifier = Modifier.fillMaxWidth().testTag("profile-promo-pager")
                .onPreviewKeyEvent { event ->
                    val direction = when (event.key) {
                        Key.DirectionRight -> 1
                        Key.DirectionLeft -> -1
                        else -> 0
                    }
                    if (event.type != KeyEventType.KeyDown || direction == 0) false
                    else {
                        val target = (pager.currentPage + direction).coerceIn(0, pages.lastIndex)
                        if (target == pager.currentPage) false
                        else { scope.launch { pager.animateScrollToPage(target) }; true }
                    }
                }.focusable(),
        ) { page ->
            ProfilePromoCard(
                kind = pages[page], state = state, accountIsPaid = accountIsPaid,
                checkoutAvailable = checkoutAvailable, identities = identities,
                onOpenHsk30 = onOpenHsk30, onOpenSubscription = onOpenSubscription,
                onStartTrial = onStartTrial, onConnectIdentity = onConnectIdentity,
            )
        }
        if (pages.size > 1) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                pages.forEachIndexed { index, page ->
                    val label = stringResource(R.string.profile_promo_page, index + 1, pages.size)
                    Box(
                        modifier = Modifier.size(48.dp)
                            .semantics { contentDescription = label; selected = pager.currentPage == index }
                            .testTag("profile-promo-dot-${page.key}")
                            .clickable(role = Role.Tab) { scope.launch { pager.animateScrollToPage(index) } },
                        contentAlignment = Alignment.Center,
                    ) {
                        Box(
                            Modifier.size(width = if (pager.currentPage == index) 19.dp else 6.dp, height = 6.dp)
                                .background(if (pager.currentPage == index) PromoGold else Color(0xFFB7AA98), CircleShape),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ProfilePromoCard(
    kind: ProfilePromoPage,
    state: ProfileUiState,
    accountIsPaid: Boolean,
    checkoutAvailable: Boolean,
    identities: IdentitiesUiState,
    onOpenHsk30: () -> Unit,
    onOpenSubscription: (Boolean) -> Unit,
    onStartTrial: () -> Unit,
    onConnectIdentity: (AuthProvider) -> Unit,
) {
    val subscription = state.profile?.subscription
    val isPaid = subscription?.isPaid == true || accountIsPaid
    val trialActive = !isPaid && state.trial?.active == true
    val isTemporary = !isPaid && subscription?.status == "temporary_trial"
    val canTrial = !isPaid && !trialActive && !isTemporary && state.trial?.eligible == true
    val title: String
    val summary: String
    val action: String
    val mark: String
    val icon = when (kind.provider) {
        AuthProvider.TELEGRAM -> R.drawable.ic_brand_telegram
        AuthProvider.GOOGLE -> R.drawable.ic_brand_google
        AuthProvider.APPLE -> R.drawable.ic_brand_apple
        null -> null
    }
    when (kind) {
        ProfilePromoPage.HSK30 -> {
            title = "HSK 3.0"
            summary = stringResource(R.string.profile_promo_hsk30_body)
            action = stringResource(R.string.profile_promo_hsk30_open)
            mark = "▤"
        }
        ProfilePromoPage.PRO -> {
            title = when {
                isPaid -> stringResource(R.string.profile_subscription_status_paid)
                trialActive -> stringResource(R.string.profile_subscription_status_trial)
                isTemporary -> stringResource(R.string.profile_subscription_status_temporary)
                else -> stringResource(R.string.profile_subscription_title)
            }
            summary = when {
                isPaid || isTemporary ->
                    subscription?.until?.let { stringResource(R.string.profile_subscription_until, it.take(10)) }
                        ?: stringResource(R.string.profile_promo_pro_body)
                trialActive -> trialTimeRemaining(state.trial?.endsAt)
                else -> stringResource(R.string.profile_promo_pro_body)
            }
            action = when {
                isPaid -> stringResource(R.string.profile_subscription_renew)
                canTrial -> stringResource(R.string.profile_promo_start_trial)
                else -> stringResource(R.string.profile_subscription_buy)
            }
            mark = "★"
        }
        else -> {
            val brand = when (kind.provider) {
                AuthProvider.TELEGRAM -> "Telegram"
                AuthProvider.GOOGLE -> "Google"
                else -> "Apple"
            }
            title = stringResource(R.string.profile_identity_connect_provider, brand)
            summary = stringResource(R.string.profile_promo_link_body, brand)
            action = stringResource(R.string.profile_account_connect)
            mark = ""
        }
    }
    val actionEnabled = when (kind) {
        ProfilePromoPage.PRO -> !state.trialStarting && checkoutAvailable
        ProfilePromoPage.HSK30 -> true
        else -> identities.busyProvider == null && !identities.isLoading
    }
    val openCard: () -> Unit = {
        when (kind) {
            ProfilePromoPage.HSK30 -> onOpenHsk30()
            ProfilePromoPage.PRO -> onOpenSubscription(isPaid)
            else -> kind.provider?.let(onConnectIdentity)
        }
    }
    Surface(
        modifier = Modifier.fillMaxWidth().testTag("profile-promo-card-${kind.key}")
            .clickable(enabled = actionEnabled, onClick = openCard),
        shape = RoundedCornerShape(17.dp),
        color = PromoPaper,
        shadowElevation = 0.dp,
    ) {
        Box(modifier = Modifier.fillMaxWidth()) {
            val gradient = when (kind) {
                ProfilePromoPage.HSK30 -> listOf(Color(0xFF31231E), Color(0xFF854627))
                ProfilePromoPage.PRO -> listOf(Color(0xFF241C20), Color(0xFF593728))
                ProfilePromoPage.TELEGRAM -> listOf(Color(0xFF182C3B), Color(0xFF275775))
                ProfilePromoPage.GOOGLE -> listOf(Color(0xFF28362D), Color(0xFF415C48))
                ProfilePromoPage.APPLE -> listOf(Color(0xFF242A36), Color(0xFF4C5062))
            }
            Box(Modifier.matchParentSize().background(Brush.horizontalGradient(gradient)))
            if (kind == ProfilePromoPage.HSK30 || kind == ProfilePromoPage.PRO) {
                val artwork = if (kind == ProfilePromoPage.HSK30) R.drawable.profile_promo_pagoda else R.drawable.profile_promo_pro
                Image(
                    painter = painterResource(artwork), contentDescription = null,
                    contentScale = ContentScale.FillBounds, modifier = Modifier.matchParentSize(),
                )
                Box(Modifier.matchParentSize().background(Brush.horizontalGradient(
                    listOf(Color(0xDA201916), Color(0x8E2A1E19), Color(0x16251C18))
                )))
            }
            Box(Modifier.matchParentSize().background(Color(0x18DDD1BE)))
            Column(
                modifier = Modifier.fillMaxWidth().heightIn(min = 150.dp).padding(14.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp, Alignment.Top),
            ) {
                Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Box(
                        modifier = Modifier.size(40.dp).background(
                            if (icon != null) Color.White else Color.White.copy(alpha = 0.12f), RoundedCornerShape(11.dp)),
                        contentAlignment = Alignment.Center,
                    ) {
                        if (icon != null) Image(painterResource(icon), contentDescription = null, modifier = Modifier.size(26.dp))
                        else Text(mark, fontSize = 23.sp, fontWeight = FontWeight.Medium, color = PromoGold)
                    }
                    Column(Modifier.weight(1f)) {
                        Text(title, fontSize = 16.sp, fontWeight = FontWeight.Bold, color = Color.White)
                        Text(
                            summary, fontSize = 12.sp, lineHeight = 16.sp,
                            color = Color.White.copy(alpha = 0.82f), maxLines = 3, overflow = TextOverflow.Ellipsis,
                        )
                    }
                    Text("›", color = Color.White.copy(alpha = 0.65f), fontSize = 24.sp)
                }
                Button(
                    enabled = actionEnabled,
                    onClick = { if (kind == ProfilePromoPage.PRO && canTrial) onStartTrial() else openCard() },
                    modifier = Modifier.heightIn(min = 40.dp).testTag("profile-promo-action-${kind.key}"),
                    shape = RoundedCornerShape(11.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = PromoGold, contentColor = PromoPaper),
                ) {
                    Text(action, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, maxLines = 2)
                }
            }
        }
    }
}

@Composable
private fun trialTimeRemaining(endsAt: String?): String {
    val end = endsAt?.let { runCatching { Instant.parse(it) }.getOrNull() }
        ?: return stringResource(R.string.profile_trial_active_body)
    val remainingMinutes = Duration.between(Instant.now(), end).toMinutes()
    return when {
        remainingMinutes > 1440L ->
            stringResource(R.string.profile_promo_trial_days, (remainingMinutes + 1439L) / 1440L)
        remainingMinutes > 60L ->
            stringResource(R.string.profile_promo_trial_hours, (remainingMinutes + 59L) / 60L)
        else -> stringResource(R.string.profile_promo_trial_soon)
    }
}

/** Same book-cover entry as the native course promo and the Mini App.
 * Permissions, saved levels, and actual course switching remain outside this UI. */
@Composable
internal fun ProfileHsk30BookEntryDialog(
    hsk30: CourseHsk30,
    currentTrack: String,
    onContinue: () -> Unit,
    onUnlock: () -> Unit,
    onReturnHsk20: () -> Unit,
    onDismiss: () -> Unit,
) {
    val on30 = currentTrack == "hsk30"
    val enabled = hsk30.access.featureEnabled
    val accessGranted = enabled && hsk30.access.allowed
    val paymentAvailable = enabled && hsk30.paymentEnabled &&
        hsk30.priceTjs > 0 && hsk30.priceDisplay.isNotBlank()

    Hsk30BookDialog(isNew = false, onDismiss = onDismiss) {
        when {
            on30 -> {
                Hsk30BookTitle(
                    title = stringResource(R.string.profile_course_version),
                    body = stringResource(R.string.profile_course_version_confirm_body),
                )
                Spacer(Modifier.height(20.dp))
                Hsk30BookPrimary(
                    label = stringResource(R.string.hsk30_access_back_hsk20),
                    onClick = onReturnHsk20,
                )
            }
            !enabled -> {
                Hsk30BookTitle(
                    title = stringResource(R.string.hsk30_promo_title),
                    body = stringResource(R.string.hsk30_unlock_unavailable),
                )
                Spacer(Modifier.height(20.dp))
            }
            !accessGranted -> {
                Hsk30BookTitle(
                    title = stringResource(
                        if (hsk30.access.paymentRejected) R.string.hsk30_payment_rejected_title
                        else R.string.hsk30_access_required_title,
                    ),
                    body = stringResource(
                        if (hsk30.access.paymentRejected) R.string.hsk30_payment_rejected_body
                        else R.string.hsk30_access_required_body,
                    ),
                )
                if (hsk30.priceDisplay.isNotBlank()) {
                    Hsk30BookPrice(hsk30.priceDisplay)
                } else {
                    Spacer(Modifier.height(20.dp))
                }
                if (!paymentAvailable) {
                    Text(
                        stringResource(R.string.hsk30_unlock_unavailable),
                        color = PompColors.InkSecondary,
                        modifier = Modifier.padding(bottom = 12.dp),
                    )
                }
                Hsk30BookPrimary(
                    label = stringResource(R.string.hsk30_access_unlock_button),
                    enabled = paymentAvailable,
                    onClick = onUnlock,
                )
            }
            else -> {
                Hsk30BookTitle(
                    title = stringResource(R.string.hsk30_promo_switch),
                    body = stringResource(R.string.hsk30_promo_body_unlocked),
                )
                Spacer(Modifier.height(20.dp))
                Hsk30BookPrimary(
                    label = stringResource(R.string.hsk30_promo_switch),
                    onClick = onContinue,
                )
            }
        }
        Hsk30BookSecondary(
            label = stringResource(if (on30) R.string.action_cancel else R.string.hsk30_promo_stay),
            onClick = onDismiss,
        )
    }
}
