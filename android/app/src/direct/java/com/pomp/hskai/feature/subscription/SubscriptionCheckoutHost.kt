package com.pomp.hskai.feature.subscription

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import android.util.Base64
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.HeadsetMic
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.lifecycle.ViewModelStoreOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.data.api.SubscriptionPriceDto
import com.pomp.hskai.data.repository.FeatureRepository
import java.util.Locale

/**
 * Light follows the Mini App checkout (`subscription.html`), dark follows the
 * app's own dark palette, so the screen matches whichever theme is on.
 */
private class CheckoutColors(
    val bg: Color,
    val surface: Color,
    val card: Color,
    val text: Color,
    val muted: Color,
    val accent: Color,
    val accentInk: Color,
    val accentSoft: Color,
    val accentLine: Color,
    val onAccent: Color,
    val goldSoft: Color,
    val goldLine: Color,
    val goldInk: Color,
    val line: Color,
    val line2: Color,
)

private val LightCheckout = CheckoutColors(
    bg = Color(0xFFFFFFFF), surface = Color(0xFFFFFFFF), card = Color(0xFFF6F8F7),
    text = Color(0xFF14201B), muted = Color(0xFF687770),
    accent = Color(0xFF0E9A64), accentInk = Color(0xFF0A7A4F), accentSoft = Color(0xFFE9F7F0),
    accentLine = Color(0xFFBFE6D3), onAccent = Color(0xFFFFFFFF),
    goldSoft = Color(0xFFFFF7E6), goldLine = Color(0xFFF3D9A4), goldInk = Color(0xFF8A5A00),
    line = Color(0xFFE3E8E6), line2 = Color(0xFFCBD5D1),
)

private val DarkCheckout = CheckoutColors(
    bg = Color(0xFF002F49), surface = Color(0xFF073B55), card = Color(0xFF0A435F),
    text = Color(0xFFF5FAFD), muted = Color(0xFFB8CDDA),
    accent = Color(0xFF48D99A), accentInk = Color(0xFF48D99A), accentSoft = Color(0xFF0A5146),
    accentLine = Color(0xFF1F7A5A), onAccent = Color(0xFF002F49),
    goldSoft = Color(0xFF584819), goldLine = Color(0xFF7A6526), goldInk = Color(0xFFF4C95D),
    line = Color(0xFF17617D), line2 = Color(0xFF2A7896),
)

/** Read during composition, so switching the app theme recomposes the screen. */
private val C: CheckoutColors get() = if (PompColors.IsDark) DarkCheckout else LightCheckout

/** Brand names, the same in every language. */
private val BANK_NAMES = mapOf("dc_city" to "Dushanbe City", "alif" to "Alif")
private val REGION_FLAGS = mapOf("tj" to "🇹🇯", "uz" to "🇺🇿", "ru" to "🇷🇺", "cn" to "🇨🇳", "other" to "🌐")

/** The direct APK uses the same server checkout as the Telegram Mini App. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SubscriptionCheckoutHost(
    repository: FeatureRepository,
    viewModelStoreOwner: ViewModelStoreOwner,
    origin: String,
    onClose: () -> Unit,
) {
    val context = LocalContext.current
    val app = context.applicationContext as HskAiApplication
    val model: SubscriptionCheckoutViewModel = viewModel(
        viewModelStoreOwner = viewModelStoreOwner,
        factory = SubscriptionCheckoutViewModel.Factory(
            repository,
            origin,
            onPendingPayment = { paymentId -> app.paymentDecisionMonitor.watch(paymentId) },
            savedRegion = { app.appSettings.paymentRegion() },
            saveRegion = { region -> app.appSettings.setPaymentRegion(region) },
        ),
    )
    val state by model.state.collectAsStateWithLifecycle()
    val copy = remember(context, state.language) { localizedContext(context, state.language) }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        model.selectReceipt(context, uri)
    }
    var supportOpen by remember { mutableStateOf(false) }
    var routeOpen by remember { mutableStateOf(false) }
    var inviteOpen by remember { mutableStateOf(false) }
    var waitingInvite by remember { mutableStateOf(false) }
    var qrPreview by remember { mutableStateOf(false) }
    var qrActions by remember { mutableStateOf(false) }
    var hintExpanded by remember { mutableStateOf(false) }
    val stepIndex = state.flow.indexOf(state.step)

    LaunchedEffect(Unit) { model.load() }
    LaunchedEffect(state.discount, state.discountStarting) {
        if (waitingInvite && !state.discountStarting && state.discount?.referralLink?.isNotBlank() == true) {
            waitingInvite = false
            inviteOpen = true
        }
    }
    BackHandler {
        when {
            qrPreview -> qrPreview = false
            inviteOpen -> inviteOpen = false
            supportOpen -> supportOpen = false
            stepIndex > 0 -> model.back()
            else -> onClose()
        }
    }

    Column(Modifier.fillMaxSize().background(C.bg).safeDrawingPadding()) {
        Column(
            Modifier.weight(1f).verticalScroll(rememberScrollState())
                .padding(horizontal = 15.dp).padding(top = 16.dp, bottom = 22.dp),
        ) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text(copy.getString(R.string.sub_heading), color = C.text, fontSize = 27.sp,
                    lineHeight = 30.sp, fontWeight = FontWeight.Black, modifier = Modifier.weight(1f))
                Box(Modifier.size(38.dp).border(1.dp, C.line, CircleShape)
                    .background(C.surface, CircleShape).clickable { supportOpen = true },
                    contentAlignment = Alignment.Center) {
                    Icon(Icons.Filled.HeadsetMic, contentDescription = copy.getString(R.string.sub_help_title),
                        tint = C.accentInk, modifier = Modifier.size(20.dp))
                }
                IconButton(onClick = onClose, modifier = Modifier.size(38.dp)) {
                    Icon(Icons.Filled.Close, contentDescription = stringResource(R.string.action_close),
                        tint = C.muted, modifier = Modifier.size(19.dp))
                }
            }
            Spacer(Modifier.height(16.dp))

            val pending = state.overview?.pendingPayment != null
            val paid = state.overview?.access?.isPaid == true
            if (state.loading) {
                Spacer(Modifier.height(80.dp))
                CircularProgressIndicator(color = C.accent, modifier = Modifier.align(Alignment.CenterHorizontally))
            } else if (state.submitted || pending) {
                DoneContent(copy, pending = pending || state.alreadyPending, onClose = onClose)
            } else if (state.overview?.checkoutAllowed != true) {
                MessageCard(copy.getString(R.string.sub_unavailable))
                Spacer(Modifier.height(12.dp))
                SmallAction(copy.getString(R.string.sub_retry), onClick = model::load)
            } else {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    state.flow.indices.forEach { slot ->
                        Box(Modifier.weight(1f).height(5.dp)
                            .background(if (slot <= stepIndex) C.accent else C.line, CircleShape))
                    }
                }
                Spacer(Modifier.height(16.dp))
                if (paid) {
                    MessageCard(copy.getString(R.string.sub_renewal_period_note))
                    Spacer(Modifier.height(12.dp))
                }
                when (state.step) {
                    CheckoutStep.PLANS -> PlansContent(
                        state = state, copy = copy, onPlan = model::choosePlan,
                        onCurrency = model::openCurrencySelector,
                        onRoute = { routeOpen = true },
                        onDiscount = { waitingInvite = true; model.startDiscount() },
                    )
                    CheckoutStep.METHOD -> MethodContent(
                        state = state, copy = copy, onBank = model::chooseBank, onMethod = model::chooseMethod,
                    )
                    CheckoutStep.PAY -> PayContent(
                        state = state, copy = copy,
                        hintExpanded = hintExpanded, onToggleHint = { hintExpanded = !hintExpanded },
                        qrActions = qrActions, onToggleQr = { qrActions = !qrActions },
                        onQrPreview = { qrPreview = true },
                        onUpload = { picker.launch("image/*") },
                        onCopy = { value -> copyValue(context, value) },
                    )
                    CheckoutStep.DONE -> DoneContent(copy, pending = state.alreadyPending, onClose = onClose)
                }
            }
            state.errorRes?.let { error ->
                Spacer(Modifier.height(12.dp))
                MessageCard(copy.getString(error))
            }
        }
        if (!state.loading && state.overview?.checkoutAllowed == true &&
            state.overview?.pendingPayment == null && !state.submitted && state.step != CheckoutStep.DONE) {
            Row(Modifier.fillMaxWidth().background(C.bg)
                .border(BorderStroke(1.dp, C.line)).padding(horizontal = 15.dp, vertical = 11.dp),
                horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                if (stepIndex > 0) {
                    CheckoutButton(copy.getString(R.string.action_back), false, true, model::back,
                        modifier = Modifier.width(96.dp), secondary = true)
                }
                val label = copy.getString(when (state.step) {
                    CheckoutStep.PAY -> R.string.sub_submit
                    CheckoutStep.PLANS ->
                        if (hasMethodStep(state.region)) R.string.action_continue else R.string.sub_continue_country
                    else -> when (state.method) {
                        "alipay" -> R.string.sub_continue_alipay
                        "wechat" -> R.string.sub_continue_wechat
                        else -> R.string.sub_continue_country
                    }
                })
                val enabled = when (state.step) {
                    CheckoutStep.PAY -> state.quote != null && state.receiptName.isNotBlank()
                    else -> state.overview?.prices?.get(state.method)?.get(state.plan) != null
                }
                CheckoutButton(label, state.submitting || state.quoting, enabled,
                    onClick = if (state.step == CheckoutStep.PAY) model::submit else model::next,
                    modifier = Modifier.weight(1f))
            }
        }
    }

    if (supportOpen) {
        CheckoutSheet(onDismiss = { supportOpen = false }) {
            Text(copy.getString(R.string.sub_help_title), color = C.text, fontSize = 18.sp, fontWeight = FontWeight.Black)
            Text(copy.getString(R.string.sub_help_body), color = C.muted, fontSize = 13.sp)
            Spacer(Modifier.height(12.dp))
            CheckoutButton(copy.getString(R.string.sub_help_button), false,
                state.overview?.supportUrl?.isNotBlank() == true, onClick = {
                    openUrl(context, state.overview?.supportUrl.orEmpty())
                    supportOpen = false
                })
        }
    }
    if (routeOpen) {
        CheckoutSheet(onDismiss = { routeOpen = false }) {
            RegionContent(state = state, copy = copy, onRegion = {
                model.chooseRegion(it)
                routeOpen = false
            })
        }
    }
    if (state.currencyDialogOpen) {
        CurrencyPreferenceDialog(
            state = state,
            copy = copy,
            onDismiss = model::dismissCurrencySelector,
            onChoose = model::chooseCurrency,
        )
    }
    if (inviteOpen) {
        val link = state.discount?.referralLink.orEmpty()
        CheckoutSheet(onDismiss = { inviteOpen = false }) {
            Text(copy.getString(R.string.sub_invite_title), color = C.text, fontSize = 18.sp, fontWeight = FontWeight.Black)
            Text(copy.getString(R.string.sub_invite_body), color = C.muted, fontSize = 13.sp)
            Text(copy.getString(R.string.sub_discount_invite), color = C.muted, fontSize = 13.sp)
            MessageCard(link)
            Spacer(Modifier.height(8.dp))
            CheckoutButton(copy.getString(R.string.sub_invite_share), false, link.isNotBlank(), onClick = {
                shareReferral(context, copy.getString(R.string.sub_invite_share_text), link)
            })
            CheckoutButton(copy.getString(R.string.sub_invite_copy), false, link.isNotBlank(),
                onClick = { copyValue(context, link); inviteOpen = false }, secondary = true)
        }
    }
    if (qrPreview) {
        val bitmap = remember(state.quote?.qr?.imageDataUrl) { decodeQr(state.quote?.qr?.imageDataUrl) }
        Dialog(onDismissRequest = { qrPreview = false },
            properties = DialogProperties(usePlatformDefaultWidth = false)) {
            Column(Modifier.fillMaxSize().background(C.bg).safeDrawingPadding().padding(16.dp)) {
                Text(copy.getString(R.string.sub_qr_title), color = C.text,
                    fontSize = 20.sp, fontWeight = FontWeight.Black)
                Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
                    if (bitmap != null) Image(bitmap, contentDescription = copy.getString(R.string.sub_qr_title),
                        modifier = Modifier.fillMaxWidth().background(Color.White, RoundedCornerShape(18.dp)).padding(12.dp))
                }
                CheckoutButton(copy.getString(R.string.action_back), false, true,
                    onClick = { qrPreview = false }, secondary = true)
            }
        }
    }
}

@Composable
private fun RegionContent(state: SubscriptionCheckoutState, copy: Context, onRegion: (String) -> Unit) {
    Text(copy.getString(R.string.sub_route_title), color = C.text, fontSize = 22.sp,
        lineHeight = 26.sp, fontWeight = FontWeight.Black)
    Spacer(Modifier.height(7.dp))
    Text(copy.getString(R.string.sub_route_body), color = C.muted, fontSize = 13.sp, lineHeight = 19.sp)
    Spacer(Modifier.height(16.dp))
    availableRegions(state.overview?.prices.orEmpty()).forEach { region ->
        ChoiceCard(REGION_FLAGS[region], copy.getString(regionTitleId(region)),
            copy.getString(regionBodyId(region)), state.region == region, onClick = { onRegion(region) })
        Spacer(Modifier.height(9.dp))
    }
}

@Composable
private fun PlansContent(
    state: SubscriptionCheckoutState, copy: Context,
    onPlan: (String) -> Unit,
    onCurrency: () -> Unit,
    onRoute: () -> Unit,
    onDiscount: () -> Unit,
) {
    Text(copy.getString(R.string.sub_plans_heading), color = C.text, fontSize = 16.sp, fontWeight = FontWeight.Black)
    Spacer(Modifier.height(10.dp))
    CurrencySelectorButton(state, copy, onCurrency)
    Spacer(Modifier.height(8.dp))
    PaymentRouteButton(state, copy, onClick = onRoute)
    Spacer(Modifier.height(12.dp))
    val prices = state.overview?.prices?.get(state.method).orEmpty()
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(9.dp)) {
        listOf("1_month", "10_days").forEach { plan ->
            prices[plan]?.let { price ->
                PlanCard(plan, planPrice(state, plan, price), price.discountApplied, state.plan == plan, copy,
                    onClick = { onPlan(plan) }, modifier = Modifier.weight(1f))
            }
        }
    }
    prices["3_months"]?.let { price ->
        Spacer(Modifier.height(9.dp))
        PlanCard("3_months", planPrice(state, "3_months", price), price.discountApplied,
            state.plan == "3_months", copy, onClick = { onPlan("3_months") },
            modifier = Modifier.fillMaxWidth(), wide = true)
    }
    val discount = state.discount
    val offer = state.overview?.offer
    val mode = state.overview?.mode.orEmpty()
    // The regular checkout also carries the learner's active admin discount; it replaces the referral block.
    val showOffer = offer != null &&
        (mode in setOf("admin_discount", "feedback_discount") || (offer.available && offer.type == "admin_discount"))
    if (offer != null && showOffer) {
        Spacer(Modifier.height(14.dp))
        CardBlock(border = C.goldLine, background = C.goldSoft) {
            Text(if (offer.available) "${offer.percent}%" else "!", color = C.goldInk,
                fontSize = 26.sp, fontWeight = FontWeight.Black)
            Text(if (offer.available) localizedOfferTitle(offer, state.language).ifBlank { "${offer.percent}%" }
                else copy.getString(R.string.sub_offer_expired), color = C.text, fontWeight = FontWeight.Bold)
            if (offer.available) Text(localizedOfferReason(offer, state.language), color = C.muted, fontSize = 12.sp)
        }
    } else if (discount != null && !discount.discountUsed) {
        Spacer(Modifier.height(14.dp))
        CardBlock(border = C.goldLine, background = C.goldSoft) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Box(Modifier.size(58.dp).background(Color(0xFFFFC65F), RoundedCornerShape(15.dp)),
                    contentAlignment = Alignment.Center) {
                    Text("20%", color = Color(0xFF2A1C00), fontSize = 18.sp, fontWeight = FontWeight.Black)
                }
                Column {
                    Text(copy.getString(if (discount.referral20Available) R.string.sub_discount_ready else R.string.sub_discount_locked),
                        color = C.text, fontSize = 14.sp, fontWeight = FontWeight.Black)
                    Text(if (discount.referral20Available) copy.getString(R.string.sub_discount_active)
                        else copy.getString(R.string.sub_discount_progress,
                            discount.referralCount, discount.referralRequired), color = C.muted, fontSize = 12.sp)
                }
            }
            if (!discount.referral20Available) {
                Spacer(Modifier.height(10.dp))
                Box(Modifier.fillMaxWidth().height(6.dp).background(C.goldLine, CircleShape)) {
                    Box(Modifier.fillMaxWidth((discount.referralCount.toFloat() /
                        discount.referralRequired.coerceAtLeast(1)).coerceIn(0f, 1f))
                        .height(6.dp).background(C.accent, CircleShape))
                }
                Spacer(Modifier.height(10.dp))
                CheckoutButton(copy.getString(R.string.sub_discount_button), state.discountStarting,
                    true, onDiscount, secondary = true)
            }
        }
    }
}

@Composable
private fun MethodContent(
    state: SubscriptionCheckoutState, copy: Context,
    onBank: (String) -> Unit, onMethod: (String) -> Unit,
) {
    Text(copy.getString(R.string.sub_method), color = C.text, fontSize = 22.sp, fontWeight = FontWeight.Black)
    Spacer(Modifier.height(16.dp))
    if (state.region == "cn") {
        CHINA_METHODS.filter { !state.overview?.prices?.get(it).isNullOrEmpty() }.forEach { method ->
            ChoiceCard(null, copy.getString(if (method == "alipay") R.string.sub_alipay else R.string.sub_wechat),
                copy.getString(R.string.sub_qr_yuan), state.method == method, onClick = { onMethod(method) })
            Spacer(Modifier.height(9.dp))
        }
    } else {
        CARD_BANKS.forEach { bank ->
            ChoiceCard(null, BANK_NAMES.getValue(bank),
                copy.getString(if (bank == "alif") R.string.sub_bank_alif_body else R.string.sub_bank_dc_body),
                state.bank == bank, onClick = { onBank(bank) })
            Spacer(Modifier.height(9.dp))
        }
    }
}

@Composable
private fun PayContent(
    state: SubscriptionCheckoutState, copy: Context,
    hintExpanded: Boolean, onToggleHint: () -> Unit,
    qrActions: Boolean, onToggleQr: () -> Unit, onQrPreview: () -> Unit,
    onUpload: () -> Unit, onCopy: (String) -> Unit,
) {
    if (state.overview?.readOnlyReason == "course_locked") {
        Text(copy.getString(R.string.sub_pay_locked_body), color = C.muted, fontSize = 13.sp, lineHeight = 19.sp)
        Spacer(Modifier.height(12.dp))
    }
    val quote = state.quote
    if (quote == null) {
        if (state.quoting) CircularProgressIndicator(color = C.accent)
        else MessageCard(copy.getString(state.errorRes ?: R.string.sub_unavailable))
        return
    }
    CardBlock(background = C.card) {
        Text(copy.getString(R.string.sub_amount_label), color = C.accentInk,
            fontSize = 12.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(5.dp))
        Row(verticalAlignment = Alignment.Bottom) {
            Text(quote.payAmount, color = C.text, fontSize = 36.sp, fontWeight = FontWeight.Black)
            Spacer(Modifier.width(5.dp))
            Text(quote.payCurrency, color = C.muted, fontSize = 15.sp, fontWeight = FontWeight.Bold)
        }
        if (quote.discountApplied && quote.payBaseAmount.isNotBlank() && quote.payBaseAmount != quote.payAmount) {
            Text("${quote.payBaseAmount} ${quote.payBaseCurrency}", color = C.muted,
                fontSize = 12.sp, textDecoration = TextDecoration.LineThrough)
        }
    }
    Spacer(Modifier.height(14.dp))
    SummaryRow(copy.getString(R.string.sub_row_plan), copy.getString(planLabelId(state.plan)))
    if (state.method == "visa") {
        SummaryRow(copy.getString(R.string.sub_row_bank), BANK_NAMES[state.cardBank.orEmpty()].orEmpty())
        if (state.country != "tj" && quote.exchangeRate.isNotBlank()) {
            SummaryRow(copy.getString(R.string.sub_row_rate), quote.exchangeRate)
        }
    }
    Spacer(Modifier.height(14.dp))
    CardBlock {
        if (state.method == "visa") {
            Text(copy.getString(R.string.sub_payment_details), color = C.text,
                fontSize = 15.sp, fontWeight = FontWeight.Black)
            Spacer(Modifier.height(8.dp))
            if (state.country == "tj") {
                // A short step-by-step instruction for the chosen bank: always in full.
                Text(copy.getString(if (state.cardBank == "alif") R.string.sub_details_alif_hint
                    else R.string.sub_details_tj_hint), color = C.muted, fontSize = 12.sp, lineHeight = 17.sp)
                Spacer(Modifier.height(10.dp))
            } else {
                Text(copy.getString(R.string.sub_details_foreign_hint), color = C.muted, fontSize = 12.sp,
                    lineHeight = 17.sp, maxLines = if (hintExpanded) Int.MAX_VALUE else 2,
                    overflow = TextOverflow.Ellipsis, modifier = Modifier.clickable(onClick = onToggleHint))
                TextButton(onClick = onToggleHint) {
                    Text(copy.getString(if (hintExpanded) R.string.sub_show_less else R.string.sub_show_more),
                        color = C.accentInk)
                }
            }
            if (quote.paymentDetails.isBlank()) {
                MessageCard(copy.getString(R.string.sub_no_details))
            } else {
                quote.paymentDetails.lines().map { it.trim() }.filter { it.isNotBlank() }.forEach { line ->
                    val number = Regex("\\+?\\d[\\d\\s\\-()]{7,}\\d").find(line)?.value
                        ?.filter { it.isDigit() }.orEmpty().takeIf { it.length >= 8 }
                    Row(Modifier.fillMaxWidth().padding(bottom = 8.dp)
                        .border(1.dp, if (number != null) C.accentLine else C.line, RoundedCornerShape(13.dp))
                        .background(if (number != null) C.accentSoft else C.card, RoundedCornerShape(13.dp))
                        .padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                        Text(line, color = C.text, fontSize = 13.sp, fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.weight(1f))
                        if (number != null) {
                            TextButton(onClick = { onCopy(number) }) {
                                Text(copy.getString(R.string.sub_copy), color = C.accentInk,
                                    fontSize = 12.sp, fontWeight = FontWeight.Black)
                            }
                        }
                    }
                }
            }
        } else {
            Text(copy.getString(R.string.sub_qr_title), color = C.text,
                fontSize = 15.sp, fontWeight = FontWeight.Black)
            val bitmap = remember(quote.qr?.imageDataUrl) { decodeQr(quote.qr?.imageDataUrl) }
            if (bitmap != null) {
                Box(Modifier.fillMaxWidth().height(240.dp).background(Color.White, RoundedCornerShape(13.dp))
                    .clickable(onClick = onToggleQr).padding(8.dp), contentAlignment = Alignment.Center) {
                    Image(bitmap, contentDescription = copy.getString(R.string.sub_qr_title),
                        modifier = Modifier.fillMaxSize())
                }
                Text(copy.getString(R.string.sub_qr_hint), color = C.muted, fontSize = 12.sp,
                    textAlign = TextAlign.Center)
                if (qrActions) CheckoutButton(copy.getString(R.string.sub_qr_enlarge), false, true, onQrPreview)
            } else MessageCard(copy.getString(R.string.sub_qr_missing))
        }
    }
    Spacer(Modifier.height(14.dp))
    val selected = state.receiptName.isNotBlank()
    Column(Modifier.fillMaxWidth().heightIn(min = 150.dp)
        .border(2.dp, if (selected) C.accent else C.line2, RoundedCornerShape(18.dp))
        .background(if (selected) C.accentSoft else C.card, RoundedCornerShape(18.dp)).clickable(onClick = onUpload)
        .padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center) {
        Box(Modifier.size(62.dp).background(if (selected) C.accent else C.accentSoft, CircleShape),
            contentAlignment = Alignment.Center) {
            Text(if (selected) "✓" else "+", color = if (selected) C.onAccent else C.accent, fontSize = 36.sp)
        }
        Spacer(Modifier.height(8.dp))
        Text(if (selected) copy.getString(R.string.sub_upload_selected, state.receiptName)
            else copy.getString(R.string.sub_upload_title), color = C.text,
            fontSize = 15.sp, fontWeight = FontWeight.Black, textAlign = TextAlign.Center)
        val size = if (state.receiptBytes >= 1024 * 1024) "%.1f MB".format(state.receiptBytes / 1048576.0)
            else "${(state.receiptBytes / 1024).coerceAtLeast(1)} KB"
        val note = when {
            state.receiptNoteRes != null -> copy.getString(state.receiptNoteRes)
            selected -> copy.getString(
                if (state.receiptBytes > 600 * 1024) R.string.sub_upload_heavy else R.string.sub_upload_size, size)
            else -> copy.getString(R.string.sub_upload_body)
        }
        Text(note, color = if (state.receiptNoteRes != null) C.goldInk else C.muted,
            fontSize = 12.sp, textAlign = TextAlign.Center)
    }
}

/** A plan's price in the region's currency: TJS and ¥ as priced, UZS/RUB/USD from `card_prices`. */
private class PlanPrice(val amount: String, val base: String, val currency: String)

private fun planPrice(state: SubscriptionCheckoutState, plan: String, price: SubscriptionPriceDto): PlanPrice {
    if (price.displayFinalAmount.isNotBlank() && price.displayCurrency.isNotBlank()) {
        return PlanPrice(
            price.displayFinalAmount,
            price.displayBaseAmount.ifBlank { price.baseAmount.toString() },
            price.displayCurrency,
        )
    }
    val local = if (state.method == "visa" && state.country != "tj") {
        state.overview?.cardPrices?.get(state.country)?.get(plan)
    } else null
    return if (local != null && local.finalAmount.isNotBlank()) {
        PlanPrice(local.finalAmount, local.baseAmount, local.currency)
    } else {
        PlanPrice(price.finalAmount.toString(), price.baseAmount.toString(), price.currency)
    }
}

@Composable
private fun CurrencySelectorButton(
    state: SubscriptionCheckoutState,
    copy: Context,
    onClick: () -> Unit,
) {
    val currency = state.overview?.displayCurrency.orEmpty()
    Row(
        Modifier.fillMaxWidth().border(1.dp, C.accentLine, RoundedCornerShape(14.dp))
            .background(C.accentSoft, RoundedCornerShape(14.dp)).clickable(onClick = onClick)
            .padding(horizontal = 13.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(copy.getString(R.string.sub_currency_label), color = C.muted, fontSize = 11.sp,
                fontWeight = FontWeight.Bold)
            Text(
                if (currency.isBlank()) copy.getString(R.string.sub_currency_loading)
                else "$currency — ${copy.getString(currencyTitleId(currency))}",
                color = C.text,
                fontSize = 14.sp,
                fontWeight = FontWeight.Black,
            )
        }
        Text("⌄", color = C.accentInk, fontSize = 20.sp, fontWeight = FontWeight.Black)
    }
}

@Composable
private fun PaymentRouteButton(state: SubscriptionCheckoutState, copy: Context, onClick: () -> Unit) {
    val route = if (state.region == "cn") {
        copy.getString(if (state.method == "wechat") R.string.sub_wechat else R.string.sub_alipay)
    } else {
        "${copy.getString(R.string.sub_card)} · ${copy.getString(regionTitleId(state.region))}"
    }
    Row(
        Modifier.fillMaxWidth().border(1.dp, C.line, RoundedCornerShape(14.dp))
            .background(C.surface, RoundedCornerShape(14.dp)).clickable(onClick = onClick)
            .padding(horizontal = 13.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(copy.getString(R.string.sub_payment_route_label), color = C.muted, fontSize = 11.sp,
                fontWeight = FontWeight.Bold)
            Text(route, color = C.text, fontSize = 13.sp, fontWeight = FontWeight.ExtraBold)
        }
        Text(copy.getString(R.string.sub_change), color = C.accentInk, fontSize = 12.sp,
            fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun CurrencyPreferenceDialog(
    state: SubscriptionCheckoutState,
    copy: Context,
    onDismiss: () -> Unit,
    onChoose: (String) -> Unit,
) {
    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(
            usePlatformDefaultWidth = false,
            dismissOnBackPress = !state.currencyDialogRequired,
            dismissOnClickOutside = !state.currencyDialogRequired,
        ),
    ) {
        Column(
            Modifier.fillMaxWidth(0.92f).heightIn(max = 620.dp)
                .background(C.surface, RoundedCornerShape(24.dp)).padding(18.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(9.dp),
        ) {
            Text(copy.getString(R.string.sub_currency_title), color = C.text, fontSize = 20.sp,
                lineHeight = 24.sp, fontWeight = FontWeight.Black)
            Text(copy.getString(R.string.sub_currency_body), color = C.muted, fontSize = 13.sp,
                lineHeight = 19.sp)
            SUBSCRIPTION_DISPLAY_CURRENCIES.forEach { currency ->
                ChoiceCard(
                    null,
                    currency,
                    copy.getString(currencyTitleId(currency)),
                    state.overview?.displayCurrency == currency,
                    onClick = { if (!state.currencySaving) onChoose(currency) },
                )
            }
            state.currencyErrorRes?.let { MessageCard(copy.getString(it)) }
            if (state.currencySaving) {
                CircularProgressIndicator(color = C.accent, modifier = Modifier.align(Alignment.CenterHorizontally))
            }
            if (!state.currencyDialogRequired) {
                TextButton(onClick = onDismiss, enabled = !state.currencySaving,
                    modifier = Modifier.align(Alignment.End)) {
                    Text(copy.getString(R.string.action_close), color = C.accentInk)
                }
            }
        }
    }
}

@Composable
private fun PlanCard(plan: String, price: PlanPrice, discounted: Boolean, selected: Boolean,
    copy: Context, onClick: () -> Unit, modifier: Modifier = Modifier, wide: Boolean = false) {
    Column(modifier.heightIn(min = if (wide) 95.dp else 130.dp)
        .border(if (selected) 2.dp else 1.dp, if (selected) C.accent else C.line, RoundedCornerShape(18.dp))
        .background(if (selected) C.accentSoft else C.surface, RoundedCornerShape(18.dp))
        .clickable(onClick = onClick).padding(14.dp), verticalArrangement = Arrangement.SpaceBetween) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(copy.getString(planLabelId(plan)), color = C.muted, fontSize = 13.sp, fontWeight = FontWeight.ExtraBold)
            Spacer(Modifier.weight(1f))
            val badge = when (plan) {
                "10_days" -> R.string.sub_plan_fast
                "3_months" -> R.string.sub_plan_value
                else -> R.string.sub_plan_best
            }
            Text(copy.getString(badge), color = C.goldInk, fontSize = 10.sp, fontWeight = FontWeight.Black,
                modifier = Modifier.border(1.dp, C.goldLine, CircleShape).background(C.goldSoft, CircleShape)
                    .padding(horizontal = 7.dp, vertical = 4.dp))
        }
        Row(verticalAlignment = Alignment.Bottom) {
            // A UZS amount such as "116 000" must still fit a half-width card.
            Text(price.amount, color = C.text, fontSize = if (price.amount.length > 5) 23.sp else 30.sp,
                fontWeight = FontWeight.Black)
            Spacer(Modifier.width(3.dp))
            Text(price.currency, color = C.muted, fontSize = 12.sp, fontWeight = FontWeight.Bold)
        }
        if (discounted) {
            Text("${price.base} ${price.currency}", color = C.muted, fontSize = 12.sp,
                textDecoration = TextDecoration.LineThrough)
        }
    }
}

@Composable
private fun ChoiceCard(icon: String?, title: String, subtitle: String,
    selected: Boolean, onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth().heightIn(min = 66.dp)
        .border(if (selected) 2.dp else 1.dp, if (selected) C.accent else C.line, RoundedCornerShape(18.dp))
        .background(if (selected) C.accentSoft else C.surface, RoundedCornerShape(18.dp))
        .clickable(onClick = onClick).padding(horizontal = 14.dp, vertical = 11.dp),
        verticalAlignment = Alignment.CenterVertically) {
        if (icon != null) {
            Text(icon, fontSize = 30.sp)
            Spacer(Modifier.width(12.dp))
        }
        Column(Modifier.weight(1f)) {
            Text(title, color = C.text, fontSize = 14.sp, fontWeight = FontWeight.ExtraBold)
            Text(subtitle, color = C.muted, fontSize = 12.sp, lineHeight = 16.sp)
        }
        SelectionDot(selected)
    }
}

@Composable
private fun SelectionDot(selected: Boolean) {
    Box(Modifier.size(20.dp).border(2.dp, if (selected) C.accent else C.line2, CircleShape),
        contentAlignment = Alignment.Center) {
        if (selected) Box(Modifier.size(8.dp).background(C.accent, CircleShape))
    }
}

@Composable
private fun SummaryRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth().padding(bottom = 8.dp)
        .border(1.dp, C.line, RoundedCornerShape(13.dp))
        .background(C.surface, RoundedCornerShape(13.dp)).padding(12.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Text(label, color = C.muted, fontSize = 12.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.weight(1f))
        Text(value, color = C.text, fontSize = 13.sp, fontWeight = FontWeight.ExtraBold,
            textAlign = TextAlign.End)
    }
}

@Composable
private fun DoneContent(copy: Context, pending: Boolean, onClose: () -> Unit) {
    Column(Modifier.fillMaxWidth().padding(top = 54.dp), horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Box(Modifier.size(84.dp).background(C.accent, CircleShape), contentAlignment = Alignment.Center) {
            Text(if (pending) "…" else "✓", color = C.onAccent, fontSize = 42.sp, fontWeight = FontWeight.Black)
        }
        Text(copy.getString(if (pending) R.string.sub_pending_title else R.string.sub_done_title),
            color = C.text, fontSize = 25.sp, fontWeight = FontWeight.Black, textAlign = TextAlign.Center)
        Text(copy.getString(if (pending) R.string.sub_pending_body else R.string.sub_done_body),
            color = C.muted, fontSize = 13.sp, textAlign = TextAlign.Center)
        CheckoutButton(copy.getString(R.string.sub_return_app), false, true, onClose)
    }
}

@Composable
private fun CardBlock(modifier: Modifier = Modifier, border: Color = C.line, background: Color = C.surface,
    content: @Composable ColumnScope.() -> Unit) {
    Column(modifier.fillMaxWidth().border(1.dp, border, RoundedCornerShape(18.dp))
        .background(background, RoundedCornerShape(18.dp))
        .padding(16.dp), verticalArrangement = Arrangement.spacedBy(2.dp), content = content)
}

@Composable
private fun MessageCard(message: String) {
    Text(message, color = C.goldInk, fontSize = 12.sp, lineHeight = 17.sp,
        modifier = Modifier.fillMaxWidth().border(1.dp, C.goldLine, RoundedCornerShape(13.dp))
            .background(C.goldSoft, RoundedCornerShape(13.dp)).padding(12.dp))
}

@Composable
private fun CheckoutButton(label: String, busy: Boolean, enabled: Boolean,
    onClick: () -> Unit, modifier: Modifier = Modifier, secondary: Boolean = false) {
    Button(onClick = onClick, enabled = enabled && !busy,
        modifier = modifier.fillMaxWidth().heightIn(min = 54.dp),
        shape = RoundedCornerShape(16.dp),
        border = if (secondary) BorderStroke(1.dp, C.line) else null,
        colors = ButtonDefaults.buttonColors(
            containerColor = if (secondary) C.surface else C.accent,
            contentColor = if (secondary) C.text else C.onAccent,
            disabledContainerColor = if (secondary) C.surface else C.accent.copy(alpha = 0.45f),
            disabledContentColor = if (secondary) C.muted else C.onAccent.copy(alpha = 0.85f),
        )) {
        if (busy) CircularProgressIndicator(color = if (secondary) C.accent else C.onAccent,
            strokeWidth = 2.dp, modifier = Modifier.size(20.dp))
        else Text(label, fontSize = 15.sp, fontWeight = FontWeight.Black, textAlign = TextAlign.Center)
    }
}

@Composable
private fun SmallAction(label: String, onClick: () -> Unit) {
    TextButton(onClick = onClick) { Text(label, color = C.accentInk) }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CheckoutSheet(onDismiss: () -> Unit, content: @Composable ColumnScope.() -> Unit) {
    ModalBottomSheet(onDismissRequest = onDismiss, containerColor = C.surface, contentColor = C.text) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(bottom = 20.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp), content = content)
    }
}

private fun regionTitleId(region: String): Int = when (region) {
    "tj" -> R.string.sub_country_tj
    "uz" -> R.string.sub_country_uz
    "ru" -> R.string.sub_country_ru
    "cn" -> R.string.sub_country_cn
    else -> R.string.sub_country_other
}

private fun currencyTitleId(currency: String): Int = when (currency.uppercase()) {
    "TJS" -> R.string.sub_currency_tjs_name
    "UZS" -> R.string.sub_currency_uzs_name
    "RUB" -> R.string.sub_currency_rub_name
    "CNY" -> R.string.sub_currency_cny_name
    else -> R.string.sub_currency_usd_name
}

private fun regionBodyId(region: String): Int = when (region) {
    "tj" -> R.string.sub_country_tj_body
    "uz" -> R.string.sub_country_uz_body
    "ru" -> R.string.sub_country_ru_body
    "cn" -> R.string.sub_country_cn_body
    else -> R.string.sub_country_other_body
}

private fun planLabelId(plan: String): Int = when (plan) {
    "10_days" -> R.string.sub_plan_10
    "3_months" -> R.string.sub_plan_3
    else -> R.string.sub_plan_1
}

private fun localizedContext(context: Context, language: String): Context {
    val locale = Locale.forLanguageTag(if (language == "tj") "tg" else language)
    val configuration = android.content.res.Configuration(context.resources.configuration)
    configuration.setLocale(locale)
    return context.createConfigurationContext(configuration)
}

private fun localizedOfferTitle(offer: com.pomp.hskai.data.api.SubscriptionOfferDto, language: String): String =
    when (language) { "ru" -> offer.titleRu; "tj" -> offer.titleTj; else -> offer.titleUz }.ifBlank { offer.title }

private fun localizedOfferReason(offer: com.pomp.hskai.data.api.SubscriptionOfferDto, language: String): String =
    when (language) { "ru" -> offer.reasonRu; "tj" -> offer.reasonTj; else -> offer.reasonUz }.ifBlank { offer.reason }

private fun decodeQr(dataUrl: String?): androidx.compose.ui.graphics.ImageBitmap? = runCatching {
    val encoded = dataUrl?.substringAfter(",").orEmpty()
    val bytes = Base64.decode(encoded, Base64.DEFAULT)
    BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.asImageBitmap()
}.getOrNull()

private fun copyValue(context: Context, value: String) {
    val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    clipboard.setPrimaryClip(ClipData.newPlainText("HSK AI", value))
}

private fun openUrl(context: Context, url: String) {
    if (url.isBlank()) return
    runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }
}

private fun shareReferral(context: Context, message: String, link: String) {
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"
        putExtra(Intent.EXTRA_TEXT, "$message\n$link")
    }
    runCatching { context.startActivity(Intent.createChooser(intent, null).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }
}
