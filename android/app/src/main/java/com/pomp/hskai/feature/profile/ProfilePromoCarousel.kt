package com.pomp.hskai.feature.profile

import androidx.compose.foundation.Image
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.layout.ContentScale
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
import kotlinx.coroutines.delay
import java.time.Duration
import java.time.Instant

private val PromoGold = Color(0xFFEFB32B)
private val PromoPaper = Color(0xFF211D17)

/** Native counterpart of the Mini App profile carousel; no new entitlement rules. */
@Composable
internal fun ProfilePromoCarousel(
    state: ProfileUiState,
    accountIsPaid: Boolean,
    checkoutAvailable: Boolean,
    onOpenHsk30: () -> Unit,
    onOpenSubscription: (Boolean) -> Unit,
    onStartTrial: () -> Unit,
) {
    // Do not advertise app downloads inside the installed Android app.
    // Play continues to hide checkout/Pro, without changing purchase policy.
    val slides = remember(checkoutAvailable) {
        if (checkoutAvailable) listOf("hsk30", "pro") else listOf("hsk30")
    }
    var index by remember(slides) { mutableIntStateOf(0) }
    LaunchedEffect(index, slides) {
        if (slides.size > 1) {
            delay(4800)
            index = (index + 1) % slides.size
        }
    }
    val kind = slides[index]
    val subscription = state.profile?.subscription
    val isPaid = subscription?.isPaid == true || accountIsPaid
    val trialActive = !isPaid && state.trial?.active == true
    val isTemporary = !isPaid && subscription?.status == "temporary_trial"
    val canTrial = !isPaid && !trialActive && !isTemporary && state.trial?.eligible == true
    val title: String
    val summary: String
    val action: String
    val mark: String
    when (kind) {
        "hsk30" -> {
            title = "HSK 3.0"
            summary = stringResource(R.string.profile_promo_hsk30_body)
            action = stringResource(R.string.profile_promo_hsk30_open)
            mark = "▤"
        }
        else -> {
            title = when {
                isPaid -> stringResource(R.string.profile_subscription_status_paid)
                trialActive -> stringResource(R.string.profile_subscription_status_trial)
                isTemporary -> stringResource(R.string.profile_subscription_status_temporary)
                else -> stringResource(R.string.hsk_common_navigation_subscription)
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
    }
    val openCard = {
        when (kind) {
            "hsk30" -> onOpenHsk30()
            else -> onOpenSubscription(isPaid)
        }
    }
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .pointerInput(index, slides.size) {
                var drag = 0f
                detectHorizontalDragGestures(
                    onDragStart = { drag = 0f },
                    onDragEnd = {
                        if (slides.size > 1) {
                            if (drag < -35f) index = (index + 1) % slides.size
                            else if (drag > 35f) index = (index + slides.size - 1) % slides.size
                        }
                    },
                    onHorizontalDrag = { change, distance ->
                        if (slides.size > 1) {
                            change.consume()
                            drag += distance
                        }
                    },
                )
            }
            .clickable(onClick = openCard),
        shape = RoundedCornerShape(17.dp),
        color = PromoPaper,
        shadowElevation = 0.dp,
    ) {
        Box(modifier = Modifier.fillMaxWidth()) {
            if (kind == "hsk30" || kind == "pro") {
                // Background-only artwork. Pro actions and Play checkout restrictions are untouched.
                val illustratedGradient = if (kind == "hsk30") {
                    listOf(Color(0xFF31231E), Color(0xFF854627))
                } else {
                    listOf(Color(0xFF241C20), Color(0xFF593728))
                }
                val artwork = if (kind == "hsk30") {
                    R.drawable.profile_promo_pagoda
                } else {
                    R.drawable.profile_promo_pro
                }
                Box(
                    Modifier.matchParentSize()
                        .background(Brush.horizontalGradient(illustratedGradient))
                )
                Image(
                    painter = painterResource(artwork),
                    contentDescription = null,
                    contentScale = ContentScale.FillBounds,
                    modifier = Modifier.matchParentSize(),
                )
                Box(
                    Modifier.matchParentSize().background(
                        Brush.horizontalGradient(
                            listOf(Color(0xDA201916), Color(0x8E2A1E19), Color(0x16251C18))
                        )
                    )
                )
            }
            // Muted artwork only: labels and CTA retain full contrast.
            Box(Modifier.matchParentSize().background(Color(0x18DDD1BE)))
            Column(
                modifier = Modifier.fillMaxWidth().heightIn(min = 150.dp).padding(14.dp),
                verticalArrangement = Arrangement.SpaceBetween,
            ) {
                Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Box(
                        modifier = Modifier.size(40.dp).background(Color.White.copy(alpha = 0.12f), RoundedCornerShape(11.dp)),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(mark, fontSize = 23.sp, fontWeight = FontWeight.Medium, color = PromoGold)
                    }
                    Column(Modifier.weight(1f)) {
                        Text(title, fontSize = 16.sp, fontWeight = FontWeight.Bold, color = Color.White)
                        Text(
                            summary,
                            fontSize = 12.sp,
                            lineHeight = 16.sp,
                            color = Color.White.copy(alpha = 0.77f),
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                    Text("›", color = Color.White.copy(alpha = 0.65f), fontSize = 24.sp)
                }
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Button(
                        enabled = kind != "pro" || (!state.trialStarting && checkoutAvailable),
                        onClick = {
                            if (kind == "pro" && canTrial) onStartTrial()
                            else openCard()
                        },
                        modifier = Modifier.weight(1f, fill = false).heightIn(min = 36.dp),
                        shape = RoundedCornerShape(11.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = PromoGold, contentColor = PromoPaper),
                    ) {
                        Text(action, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, maxLines = 2)
                    }
                    if (slides.size > 1) {
                        Spacer(Modifier.width(9.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) {
                            slides.forEachIndexed { dot, _ ->
                                Box(
                                    Modifier
                                        .size(width = if (dot == index) 19.dp else 6.dp, height = 6.dp)
                                        .background(if (dot == index) PromoGold else Color.White.copy(alpha = 0.35f), CircleShape)
                                        .clickable { index = dot },
                                )
                            }
                        }
                    }
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
                    title = stringResource(R.string.hsk_course_course_picker_version),
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
