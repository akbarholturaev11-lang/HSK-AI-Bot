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
import androidx.compose.material3.Surface
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
import androidx.compose.ui.graphics.Brush
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
import com.pomp.hskai.data.api.SubscriptionPriceDto
import com.pomp.hskai.data.repository.FeatureRepository
import java.util.Locale

private val Bg = Color(0xFF05110D)
private val Raised = Color(0xFF11271F)
private val TextMain = Color(0xFFEAFFF6)
private val Muted = Color(0xFF93B7AB)
private val Emerald = Color(0xFF34E3A4)
private val Mint = Color(0xFF8FF5CF)
private val Gold = Color(0xFFFFD27D)
private val Line = Color(0xFF285143)
private val InkOnMint = Color(0xFF04130D)

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
        factory = SubscriptionCheckoutViewModel.Factory(repository, origin) { paymentId ->
            app.paymentDecisionMonitor.watch(paymentId)
        },
    )
    val state by model.state.collectAsStateWithLifecycle()
    val copy = remember(context, state.language) { localizedContext(context, state.language) }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        model.selectReceipt(context, uri)
    }
    var supportOpen by remember { mutableStateOf(false) }
    var inviteOpen by remember { mutableStateOf(false) }
    var waitingInvite by remember { mutableStateOf(false) }
    var qrPreview by remember { mutableStateOf(false) }
    var qrActions by remember { mutableStateOf(false) }
    var hintExpanded by remember { mutableStateOf(false) }

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
            state.step == CheckoutStep.PAY || state.step == CheckoutStep.COUNTRY -> model.back()
            else -> onClose()
        }
    }

    Column(
        Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(Color(0xFF0D3127), Bg, Bg)))
            .safeDrawingPadding(),
    ) {
        Column(
            Modifier.weight(1f).verticalScroll(rememberScrollState())
                .padding(horizontal = 15.dp).padding(top = 16.dp, bottom = 22.dp),
        ) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
                Column(Modifier.weight(1f)) {
                    Text("HSK AI", color = Emerald, fontSize = 11.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = 1.5.sp)
                    Text(copy.getString(R.string.sub_heading), color = TextMain, fontSize = 27.sp,
                        lineHeight = 30.sp, fontWeight = FontWeight.Black)
                }
                Box(Modifier.size(38.dp).border(1.dp, Line, CircleShape)
                    .background(Raised, CircleShape).clickable { supportOpen = true },
                    contentAlignment = Alignment.Center) {
                    Icon(Icons.Filled.HeadsetMic, contentDescription = copy.getString(R.string.sub_help_title),
                        tint = Mint, modifier = Modifier.size(20.dp))
                }
                IconButton(onClick = onClose, modifier = Modifier.size(38.dp)) {
                    Icon(Icons.Filled.Close, contentDescription = stringResource(R.string.action_close),
                        tint = Muted, modifier = Modifier.size(19.dp))
                }
            }
            Spacer(Modifier.height(16.dp))

            val pending = state.overview?.pendingPayment != null
            val paid = state.overview?.access?.isPaid == true
            if (state.loading) {
                Spacer(Modifier.height(80.dp))
                CircularProgressIndicator(color = Emerald, modifier = Modifier.align(Alignment.CenterHorizontally))
            } else if (state.submitted || pending) {
                DoneContent(copy, pending = pending || state.alreadyPending, onClose = onClose)
            } else if (paid || state.overview?.checkoutAllowed != true) {
                MessageCard(copy.getString(if (paid) R.string.sub_paid else R.string.sub_unavailable))
                Spacer(Modifier.height(12.dp))
                SmallAction(copy.getString(R.string.sub_retry), onClick = model::load)
            } else {
                val foreign = state.method == "visa" && state.country != "tj"
                val progressCount = if (foreign) 3 else 2
                val index = when (state.step) {
                    CheckoutStep.START -> 0
                    CheckoutStep.COUNTRY -> 1
                    else -> progressCount - 1
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    repeat(progressCount) { slot ->
                        Box(Modifier.weight(1f).height(5.dp).background(
                            if (slot <= index) Brush.horizontalGradient(listOf(Emerald, Mint))
                            else Brush.horizontalGradient(listOf(Color(0xFF183A2F), Color(0xFF183A2F))),
                            CircleShape))
                    }
                }
                Spacer(Modifier.height(16.dp))
                when (state.step) {
                    CheckoutStep.START -> StartContent(
                        state = state, copy = copy,
                        onPlan = model::choosePlan, onMethod = model::chooseMethod,
                        onDiscount = { waitingInvite = true; model.startDiscount() },
                    )
                    CheckoutStep.COUNTRY -> CountryContent(
                        state = state, copy = copy, onCountry = model::chooseCountry,
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
            Row(Modifier.fillMaxWidth().background(Color(0xF005110D))
                .border(BorderStroke(1.dp, Line)).padding(horizontal = 15.dp, vertical = 11.dp),
                horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                if (state.step != CheckoutStep.START) {
                    CheckoutButton(copy.getString(R.string.action_back), false, true, model::back,
                        modifier = Modifier.width(96.dp), secondary = true)
                }
                val label = when (state.step) {
                    CheckoutStep.PAY -> copy.getString(R.string.sub_submit)
                    CheckoutStep.COUNTRY -> copy.getString(R.string.sub_continue_country)
                    else -> copy.getString(when {
                        state.method == "alipay" -> R.string.sub_continue_alipay
                        state.method == "wechat" -> R.string.sub_continue_wechat
                        state.method == "visa" && state.country != "tj" -> R.string.sub_continue_foreign
                        else -> R.string.sub_continue_tj
                    })
                }
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
            Text(copy.getString(R.string.sub_help_title), color = TextMain, fontSize = 18.sp, fontWeight = FontWeight.Black)
            Text(copy.getString(R.string.sub_help_body), color = Muted, fontSize = 13.sp)
            Spacer(Modifier.height(12.dp))
            CheckoutButton(copy.getString(R.string.sub_help_button), false,
                state.overview?.supportUrl?.isNotBlank() == true, onClick = {
                    openUrl(context, state.overview?.supportUrl.orEmpty())
                    supportOpen = false
                })
        }
    }
    if (inviteOpen) {
        val link = state.discount?.referralLink.orEmpty()
        CheckoutSheet(onDismiss = { inviteOpen = false }) {
            Text(copy.getString(R.string.sub_invite_title), color = TextMain, fontSize = 18.sp, fontWeight = FontWeight.Black)
            Text(copy.getString(R.string.sub_invite_body), color = Muted, fontSize = 13.sp)
            Text(copy.getString(R.string.sub_discount_invite), color = Muted, fontSize = 13.sp)
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
            Column(Modifier.fillMaxSize().background(Bg).safeDrawingPadding().padding(16.dp)) {
                Text(copy.getString(R.string.sub_qr_title), color = TextMain,
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
private fun StartContent(
    state: SubscriptionCheckoutState, copy: Context,
    onPlan: (String) -> Unit, onMethod: (String, String) -> Unit,
    onDiscount: () -> Unit,
) {
    Text(copy.getString(R.string.sub_plans_heading), color = TextMain, fontSize = 16.sp, fontWeight = FontWeight.Black)
    Spacer(Modifier.height(7.dp))
    Text(copy.getString(R.string.sub_value), color = Muted, fontSize = 12.sp,
        lineHeight = 17.sp, fontWeight = FontWeight.SemiBold)
    Spacer(Modifier.height(10.dp))
    val prices = state.overview?.prices?.get(state.method).orEmpty()
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(9.dp)) {
        listOf("1_month", "10_days").forEach { plan ->
            prices[plan]?.let { price ->
                PlanCard(plan, price, state.plan == plan, copy, onClick = { onPlan(plan) },
                    modifier = Modifier.weight(1f))
            }
        }
    }
    prices["3_months"]?.let { price ->
        Spacer(Modifier.height(9.dp))
        PlanCard("3_months", price, state.plan == "3_months", copy,
            onClick = { onPlan("3_months") }, modifier = Modifier.fillMaxWidth(), wide = true)
    }
    val discount = state.discount
    val offer = state.overview?.offer
    if (offer != null && state.overview.mode in setOf("admin_discount", "feedback_discount")) {
        Spacer(Modifier.height(14.dp))
        CardBlock(border = Gold) {
            Text(if (offer.available) "${offer.percent}%" else "!", color = Gold,
                fontSize = 26.sp, fontWeight = FontWeight.Black)
            Text(if (offer.available) localizedOfferTitle(offer, state.language).ifBlank { "${offer.percent}%" }
                else copy.getString(R.string.sub_offer_expired), color = TextMain, fontWeight = FontWeight.Bold)
            if (offer.available) Text(localizedOfferReason(offer, state.language), color = Muted, fontSize = 12.sp)
        }
    } else if (discount != null && !discount.discountUsed) {
        Spacer(Modifier.height(14.dp))
        CardBlock(border = Gold) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Box(Modifier.size(58.dp).background(Gold, RoundedCornerShape(15.dp)), contentAlignment = Alignment.Center) {
                    Text("20%", color = Color(0xFF2A1C00), fontSize = 18.sp, fontWeight = FontWeight.Black)
                }
                Column {
                    Text(copy.getString(if (discount.referral20Available) R.string.sub_discount_ready else R.string.sub_discount_locked),
                        color = TextMain, fontSize = 14.sp, fontWeight = FontWeight.Black)
                    Text(if (discount.referral20Available) copy.getString(R.string.sub_discount_active)
                        else copy.getString(R.string.sub_discount_progress,
                            discount.referralCount, discount.referralRequired), color = Muted, fontSize = 12.sp)
                }
            }
            if (!discount.referral20Available) {
                Spacer(Modifier.height(10.dp))
                Box(Modifier.fillMaxWidth().height(6.dp).background(Line, CircleShape)) {
                    Box(Modifier.fillMaxWidth((discount.referralCount.toFloat() /
                        discount.referralRequired.coerceAtLeast(1)).coerceIn(0f, 1f))
                        .height(6.dp).background(Gold, CircleShape))
                }
                Spacer(Modifier.height(10.dp))
                CheckoutButton(copy.getString(R.string.sub_discount_button), state.discountStarting,
                    true, onDiscount, secondary = true)
            }
        }
    }
    Spacer(Modifier.height(16.dp))
    Text(copy.getString(R.string.sub_method), color = TextMain, fontSize = 16.sp, fontWeight = FontWeight.Black)
    Spacer(Modifier.height(9.dp))
    if (!state.overview?.prices?.get("visa").isNullOrEmpty()) {
        ChoiceCard("🇹🇯", copy.getString(R.string.sub_method_tj),
            copy.getString(R.string.sub_method_tj_body), state.method == "visa" && state.country == "tj",
            onClick = { onMethod("visa", "tj") })
        Spacer(Modifier.height(9.dp))
        ChoiceCard("💳", copy.getString(R.string.sub_method_foreign),
            copy.getString(R.string.sub_method_foreign_body), state.method == "visa" && state.country != "tj",
            onClick = { onMethod("visa", "other") })
        Spacer(Modifier.height(9.dp))
    }
    val china = listOf("alipay", "wechat").filter { !state.overview?.prices?.get(it).isNullOrEmpty() }
    if (china.isNotEmpty()) {
        CardBlock {
            Row(Modifier.fillMaxWidth().clickable { onMethod(china.first(), "tj") },
                verticalAlignment = Alignment.CenterVertically) {
                Text("🇨🇳", fontSize = 34.sp)
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text(copy.getString(R.string.sub_method_china), color = TextMain,
                        fontSize = 14.sp, fontWeight = FontWeight.Black)
                    Text(copy.getString(R.string.sub_method_china_body), color = Muted, fontSize = 12.sp)
                }
                SelectionDot(state.method in china)
            }
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                china.forEach { method ->
                    Box(Modifier.weight(1f).height(42.dp)
                        .border(1.dp, if (state.method == method) Emerald else Line, RoundedCornerShape(12.dp))
                        .background(if (state.method == method) Color(0xFF173D30) else Raised, RoundedCornerShape(12.dp))
                        .clickable { onMethod(method, "tj") }, contentAlignment = Alignment.Center) {
                        Text(if (method == "alipay") "Alipay" else "WeChat Pay",
                            color = if (state.method == method) Mint else Muted,
                            fontSize = 12.sp, fontWeight = FontWeight.Black)
                    }
                }
            }
        }
    }
}

@Composable
private fun CountryContent(state: SubscriptionCheckoutState, copy: Context, onCountry: (String) -> Unit) {
    CardBlock {
        Text(copy.getString(R.string.sub_country_title), color = TextMain, fontSize = 22.sp, fontWeight = FontWeight.Black)
        Spacer(Modifier.height(7.dp))
        Text(copy.getString(R.string.sub_country_body), color = Muted, fontSize = 13.sp)
        Spacer(Modifier.height(18.dp))
        val options = listOf(
            Triple("uz", "🇺🇿", R.string.sub_country_uz to R.string.sub_country_uz_body),
            Triple("ru", "🇷🇺", R.string.sub_country_ru to R.string.sub_country_ru_body),
            Triple("other", "🌐", R.string.sub_country_other to R.string.sub_country_other_body),
        )
        options.forEach { (code, icon, labels) ->
            ChoiceCard(icon, copy.getString(labels.first), copy.getString(labels.second),
                state.country == code, onClick = { onCountry(code) })
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
    CardBlock {
        Text(copy.getString(R.string.sub_pay_title), color = TextMain, fontSize = 22.sp, fontWeight = FontWeight.Black)
        Spacer(Modifier.height(7.dp))
        Text(copy.getString(if (state.overview?.readOnlyReason == "course_locked")
            R.string.sub_pay_locked_body else R.string.sub_pay_body), color = Muted, fontSize = 13.sp)
        Spacer(Modifier.height(14.dp))
        val quote = state.quote
        if (quote == null) {
            if (state.quoting) CircularProgressIndicator(color = Emerald)
            else MessageCard(copy.getString(state.errorRes ?: R.string.sub_unavailable))
            return@CardBlock
        }
        CardBlock(border = Emerald) {
            Text(copy.getString(R.string.sub_amount_label), color = Mint,
                fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(5.dp))
            Row(verticalAlignment = Alignment.Bottom) {
                Text(quote.payAmount, color = TextMain, fontSize = 36.sp, fontWeight = FontWeight.Black)
                Spacer(Modifier.width(5.dp))
                Text(quote.payCurrency, color = Mint, fontSize = 15.sp, fontWeight = FontWeight.Bold)
            }
            if (quote.discountApplied && quote.payBaseAmount.isNotBlank() && quote.payBaseAmount != quote.payAmount) {
                Text("${quote.payBaseAmount} ${quote.payBaseCurrency}", color = Muted,
                    fontSize = 12.sp, textDecoration = TextDecoration.LineThrough)
            }
        }
        Spacer(Modifier.height(14.dp))
        SummaryRow(copy.getString(R.string.sub_row_plan), copy.getString(planLabelId(state.plan)))
        SummaryRow(copy.getString(R.string.sub_row_method), copy.getString(when {
            state.method == "visa" && state.country != "tj" -> R.string.sub_method_foreign
            state.method == "visa" -> R.string.sub_method_tj
            state.method == "alipay" -> R.string.sub_alipay
            else -> R.string.sub_wechat
        }))
        if (state.method == "visa") {
            SummaryRow(copy.getString(R.string.sub_row_bank), "Dushanbe City")
            if (state.country != "tj" && quote.exchangeRate.isNotBlank()) {
                SummaryRow(copy.getString(R.string.sub_row_rate), quote.exchangeRate)
            }
        }
        Spacer(Modifier.height(14.dp))
        CardBlock {
            if (state.method == "visa") {
                Text(copy.getString(R.string.sub_payment_details), color = TextMain,
                    fontSize = 15.sp, fontWeight = FontWeight.Black)
                Spacer(Modifier.height(8.dp))
                Text(copy.getString(if (state.country == "tj") R.string.sub_details_tj_hint
                    else R.string.sub_details_foreign_hint), color = Mint, fontSize = 12.sp,
                    maxLines = if (hintExpanded) Int.MAX_VALUE else 2,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.clickable(onClick = onToggleHint))
                TextButton(onClick = onToggleHint) {
                    Text(copy.getString(if (hintExpanded) R.string.sub_show_less else R.string.sub_show_more), color = Mint)
                }
                if (quote.paymentDetails.isBlank()) {
                    MessageCard(copy.getString(R.string.sub_no_details))
                } else {
                    quote.paymentDetails.lines().map { it.trim() }.filter { it.isNotBlank() }.forEach { line ->
                        val number = Regex("\\+?\\d[\\d\\s\\-()]{7,}\\d").find(line)?.value
                            ?.filter { it.isDigit() }.orEmpty().takeIf { it.length >= 8 }
                        Row(Modifier.fillMaxWidth().padding(bottom = 8.dp)
                            .border(1.dp, Line, RoundedCornerShape(13.dp))
                            .background(Raised, RoundedCornerShape(13.dp))
                            .padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                            Text(line, color = TextMain, fontSize = 13.sp, fontWeight = FontWeight.SemiBold,
                                modifier = Modifier.weight(1f))
                            if (number != null) {
                                TextButton(onClick = { onCopy(number) }) {
                                    Text(copy.getString(R.string.sub_copy), color = Mint, fontSize = 12.sp)
                                }
                            }
                        }
                    }
                }
            } else {
                Text(copy.getString(R.string.sub_qr_title), color = TextMain,
                    fontSize = 15.sp, fontWeight = FontWeight.Black)
                val bitmap = remember(quote.qr?.imageDataUrl) { decodeQr(quote.qr?.imageDataUrl) }
                if (bitmap != null) {
                    Box(Modifier.fillMaxWidth().height(240.dp).background(Color.White, RoundedCornerShape(13.dp))
                        .clickable(onClick = onToggleQr).padding(8.dp), contentAlignment = Alignment.Center) {
                        Image(bitmap, contentDescription = copy.getString(R.string.sub_qr_title),
                            modifier = Modifier.fillMaxSize())
                    }
                    Text(copy.getString(R.string.sub_qr_hint), color = Muted, fontSize = 12.sp,
                        textAlign = TextAlign.Center)
                    if (qrActions) CheckoutButton(copy.getString(R.string.sub_qr_enlarge), false, true, onQrPreview)
                } else MessageCard(copy.getString(R.string.sub_qr_missing))
            }
        }
        Spacer(Modifier.height(14.dp))
        Column(Modifier.fillMaxWidth().heightIn(min = 150.dp)
            .border(2.dp, if (state.receiptName.isNotBlank()) Emerald else Line, RoundedCornerShape(18.dp))
            .background(Raised, RoundedCornerShape(18.dp)).clickable(onClick = onUpload)
            .padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center) {
            Box(Modifier.size(62.dp).background(Color(0xFF173D30), CircleShape), contentAlignment = Alignment.Center) {
                Text(if (state.receiptName.isNotBlank()) "✓" else "+", color = Emerald, fontSize = 36.sp)
            }
            Spacer(Modifier.height(8.dp))
            Text(if (state.receiptName.isNotBlank()) copy.getString(R.string.sub_upload_selected, state.receiptName)
                else copy.getString(R.string.sub_upload_title), color = TextMain,
                fontSize = 15.sp, fontWeight = FontWeight.Black, textAlign = TextAlign.Center)
            val size = if (state.receiptBytes >= 1024 * 1024) "%.1f MB".format(state.receiptBytes / 1048576.0)
                else "${(state.receiptBytes / 1024).coerceAtLeast(1)} KB"
            val note = when {
                state.receiptNoteRes != null -> copy.getString(state.receiptNoteRes)
                state.receiptName.isNotBlank() -> copy.getString(
                    if (state.receiptBytes > 600 * 1024) R.string.sub_upload_heavy else R.string.sub_upload_size, size)
                else -> copy.getString(R.string.sub_upload_body)
            }
            Text(note, color = if (state.receiptNoteRes != null) Gold else Muted,
                fontSize = 12.sp, textAlign = TextAlign.Center)
        }
    }
}

@Composable
private fun PlanCard(plan: String, price: SubscriptionPriceDto, selected: Boolean,
    copy: Context, onClick: () -> Unit, modifier: Modifier = Modifier, wide: Boolean = false) {
    Column(modifier.heightIn(min = if (wide) 95.dp else 130.dp)
        .border(1.dp, if (selected) Emerald else Line, RoundedCornerShape(18.dp))
        .background(if (selected) Color(0xFF113D2F) else Raised, RoundedCornerShape(18.dp))
        .clickable(onClick = onClick).padding(14.dp), verticalArrangement = Arrangement.SpaceBetween) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(copy.getString(planLabelId(plan)), color = Muted, fontSize = 13.sp, fontWeight = FontWeight.ExtraBold)
            Spacer(Modifier.weight(1f))
            val badge = when (plan) {
                "10_days" -> R.string.sub_plan_fast
                "3_months" -> R.string.sub_plan_value
                else -> R.string.sub_plan_best
            }
            Text(copy.getString(badge), color = Gold, fontSize = 10.sp, fontWeight = FontWeight.Black,
                modifier = Modifier.background(Color(0xFF4B4023), CircleShape)
                    .padding(horizontal = 7.dp, vertical = 4.dp))
        }
        Row(verticalAlignment = Alignment.Bottom) {
            Text(price.finalAmount.toString(), color = TextMain, fontSize = 30.sp, fontWeight = FontWeight.Black)
            Spacer(Modifier.width(3.dp))
            Text(price.currency, color = Muted, fontSize = 12.sp, fontWeight = FontWeight.Bold)
        }
        if (price.discountApplied) {
            Text("${price.baseAmount} ${price.currency}", color = Muted, fontSize = 12.sp,
                textDecoration = TextDecoration.LineThrough)
        }
    }
}

@Composable
private fun ChoiceCard(icon: String, title: String, subtitle: String,
    selected: Boolean, onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth().heightIn(min = 66.dp)
        .border(1.dp, if (selected) Emerald else Line, RoundedCornerShape(18.dp))
        .background(if (selected) Color(0xFF113D2F) else Raised, RoundedCornerShape(18.dp))
        .clickable(onClick = onClick).padding(horizontal = 14.dp, vertical = 11.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Text(icon, fontSize = 30.sp)
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f)) {
            Text(title, color = TextMain, fontSize = 14.sp, fontWeight = FontWeight.ExtraBold)
            Text(subtitle, color = Muted, fontSize = 12.sp, lineHeight = 16.sp)
        }
        SelectionDot(selected)
    }
}

@Composable
private fun SelectionDot(selected: Boolean) {
    Box(Modifier.size(20.dp).border(2.dp, if (selected) Emerald else Line, CircleShape),
        contentAlignment = Alignment.Center) {
        if (selected) Box(Modifier.size(8.dp).background(Emerald, CircleShape))
    }
}

@Composable
private fun SummaryRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth().padding(bottom = 8.dp)
        .border(1.dp, Line, RoundedCornerShape(13.dp))
        .background(Raised, RoundedCornerShape(13.dp)).padding(12.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Text(label, color = Muted, fontSize = 12.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.weight(1f))
        Text(value, color = TextMain, fontSize = 13.sp, fontWeight = FontWeight.ExtraBold,
            textAlign = TextAlign.End)
    }
}

@Composable
private fun DoneContent(copy: Context, pending: Boolean, onClose: () -> Unit) {
    Column(Modifier.fillMaxWidth().padding(top = 54.dp), horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Box(Modifier.size(84.dp).background(Emerald, CircleShape), contentAlignment = Alignment.Center) {
            Text(if (pending) "…" else "✓", color = InkOnMint, fontSize = 42.sp, fontWeight = FontWeight.Black)
        }
        Text(copy.getString(if (pending) R.string.sub_pending_title else R.string.sub_done_title),
            color = TextMain, fontSize = 25.sp, fontWeight = FontWeight.Black, textAlign = TextAlign.Center)
        Text(copy.getString(if (pending) R.string.sub_pending_body else R.string.sub_done_body),
            color = Muted, fontSize = 13.sp, textAlign = TextAlign.Center)
        CheckoutButton(copy.getString(R.string.sub_return_app), false, true, onClose)
    }
}

@Composable
private fun CardBlock(modifier: Modifier = Modifier, border: Color = Line,
    content: @Composable ColumnScope.() -> Unit) {
    Column(modifier.fillMaxWidth().border(1.dp, border, RoundedCornerShape(18.dp))
        .background(Brush.verticalGradient(listOf(Color(0xFF103C2E), Raised)), RoundedCornerShape(18.dp))
        .padding(16.dp), verticalArrangement = Arrangement.spacedBy(2.dp), content = content)
}

@Composable
private fun MessageCard(message: String) {
    Text(message, color = Gold, fontSize = 12.sp, lineHeight = 17.sp,
        modifier = Modifier.fillMaxWidth().border(1.dp, Color(0xFF6A5A2C), RoundedCornerShape(13.dp))
            .background(Color(0xFF283A28), RoundedCornerShape(13.dp)).padding(12.dp))
}

@Composable
private fun CheckoutButton(label: String, busy: Boolean, enabled: Boolean,
    onClick: () -> Unit, modifier: Modifier = Modifier, secondary: Boolean = false) {
    Button(onClick = onClick, enabled = enabled && !busy,
        modifier = modifier.fillMaxWidth().heightIn(min = 54.dp),
        shape = RoundedCornerShape(16.dp),
        border = if (secondary) BorderStroke(1.dp, Line) else null,
        colors = ButtonDefaults.buttonColors(
            containerColor = if (secondary) Raised else Emerald,
            contentColor = if (secondary) TextMain else InkOnMint,
            disabledContainerColor = if (secondary) Raised else Color(0xFF28654F),
            disabledContentColor = Muted,
        )) {
        if (busy) CircularProgressIndicator(color = Mint, strokeWidth = 2.dp, modifier = Modifier.size(20.dp))
        else Text(label, fontSize = 15.sp, fontWeight = FontWeight.Black, textAlign = TextAlign.Center)
    }
}

@Composable
private fun SmallAction(label: String, onClick: () -> Unit) {
    TextButton(onClick = onClick) { Text(label, color = Mint) }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CheckoutSheet(onDismiss: () -> Unit, content: @Composable ColumnScope.() -> Unit) {
    ModalBottomSheet(onDismissRequest = onDismiss, containerColor = Raised, contentColor = TextMain) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(bottom = 20.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp), content = content)
    }
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
