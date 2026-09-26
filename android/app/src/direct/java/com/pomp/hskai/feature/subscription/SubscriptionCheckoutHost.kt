package com.pomp.hskai.feature.subscription

import android.graphics.BitmapFactory
import android.util.Base64
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
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
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModelStoreOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.compose.ui.platform.LocalContext
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.data.api.SubscriptionPriceDto
import com.pomp.hskai.data.repository.FeatureRepository

/** APK checkout: the server supplies all prices and payment instructions. */
@Composable
fun SubscriptionCheckoutHost(
    repository: FeatureRepository,
    viewModelStoreOwner: ViewModelStoreOwner,
    onClose: () -> Unit,
) {
    val model: SubscriptionCheckoutViewModel = viewModel(
        viewModelStoreOwner = viewModelStoreOwner,
        factory = SubscriptionCheckoutViewModel.Factory(repository),
    )
    val state by model.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        model.selectReceipt(context, uri)
    }
    LaunchedEffect(Unit) { model.load() }
    BackHandler { if (state.quote != null && !state.submitted) model.backToPlans() else onClose() }

    Surface(color = PompColors.Paper, modifier = Modifier.fillMaxSize()) {
        Column(
            Modifier.fillMaxSize().safeDrawingPadding()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 16.dp),
        ) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = { if (state.quote != null && !state.submitted) model.backToPlans() else onClose() }) {
                    Icon(Icons.Filled.ArrowBack, contentDescription = stringResource(R.string.action_back), tint = PompColors.Ink)
                }
                Spacer(Modifier.weight(1f))
                Text("HSK AI", color = PompColors.Cinnabar, fontWeight = FontWeight.Bold)
                Spacer(Modifier.weight(1f))
                IconButton(onClick = onClose) {
                    Icon(Icons.Filled.Close, contentDescription = stringResource(R.string.action_close), tint = PompColors.InkSecondary)
                }
            }
            Spacer(Modifier.height(24.dp))
            Text(stringResource(R.string.sub_title) + " ⭐", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold, color = PompColors.Ink)
            Spacer(Modifier.height(8.dp))
            Text(stringResource(R.string.sub_intro), style = MaterialTheme.typography.bodyLarge, color = PompColors.InkSecondary)
            Spacer(Modifier.height(28.dp))

            when {
                state.loading -> CircularProgressIndicator(color = PompColors.Cinnabar, modifier = Modifier.align(Alignment.CenterHorizontally))
                state.submitted || state.overview?.pendingPayment != null -> {
                    StatusCard(stringResource(if (state.submitted) R.string.sub_pending else R.string.sub_already_pending))
                    Spacer(Modifier.height(16.dp))
                    TextButton(onClick = model::load) { Text(stringResource(R.string.sub_retry)) }
                }
                state.overview?.access?.isPaid == true -> StatusCard(stringResource(R.string.sub_paid))
                state.overview?.checkoutAllowed != true -> StatusCard(stringResource(R.string.sub_unavailable))
                state.quote == null -> {
                    val priceMap = state.overview?.prices?.get(state.method).orEmpty()
                    listOf("10_days", "1_month", "3_months").forEach { plan ->
                        val price = priceMap[plan]
                        PlanOption(
                            label = planLabel(plan),
                            price = price,
                            selected = state.plan == plan,
                            onClick = { model.choosePlan(plan) },
                        )
                        Spacer(Modifier.height(10.dp))
                    }
                    Spacer(Modifier.height(18.dp))
                    Text(stringResource(R.string.sub_method), fontWeight = FontWeight.SemiBold, color = PompColors.Ink)
                    Spacer(Modifier.height(10.dp))
                    listOf("visa", "alipay", "wechat").forEach { method ->
                        val label = when (method) {
                            "alipay" -> stringResource(R.string.sub_alipay)
                            "wechat" -> stringResource(R.string.sub_wechat)
                            else -> stringResource(R.string.sub_card)
                        }
                        OutlinedButton(
                            onClick = { model.chooseMethod(method) },
                            modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp),
                            shape = RoundedCornerShape(14.dp),
                            border = BorderStroke(1.dp, if (state.method == method) PompColors.Cinnabar else PompColors.Divider),
                        ) { Text(label, color = if (state.method == method) PompColors.CinnabarDark else PompColors.Ink) }
                        Spacer(Modifier.height(8.dp))
                    }
                    if (state.method == "visa") {
                        Spacer(Modifier.height(12.dp))
                        Text(stringResource(R.string.sub_country), fontWeight = FontWeight.SemiBold, color = PompColors.Ink)
                        listOf("tj", "uz", "ru", "other").forEach { country ->
                            val label = when (country) {
                                "tj" -> stringResource(R.string.sub_country_tj)
                                "uz" -> stringResource(R.string.sub_country_uz)
                                "ru" -> stringResource(R.string.sub_country_ru)
                                else -> stringResource(R.string.sub_country_other)
                            }
                            Row(
                                Modifier.fillMaxWidth().heightIn(min = 44.dp)
                                    .selectable(selected = state.country == country, onClick = { model.chooseCountry(country) }),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Text(if (state.country == country) "◉" else "○", color = PompColors.Cinnabar)
                                Spacer(Modifier.width(12.dp))
                                Text(label, color = PompColors.Ink)
                            }
                        }
                    }
                    Spacer(Modifier.height(22.dp))
                    PrimaryAction(stringResource(R.string.sub_continue), state.quoting, priceMap[state.plan] != null, model::loadQuote)
                }
                else -> {
                    val quote = checkNotNull(state.quote)
                    Text(planLabel(state.plan), style = MaterialTheme.typography.titleLarge, color = PompColors.Ink, fontWeight = FontWeight.SemiBold)
                    Spacer(Modifier.height(12.dp))
                    StatusCard(stringResource(R.string.sub_amount, quote.payAmount, quote.payCurrency))
                    Spacer(Modifier.height(20.dp))
                    if (state.method == "visa") {
                        Text(stringResource(R.string.sub_payment_details), style = MaterialTheme.typography.titleMedium, color = PompColors.Ink)
                        Spacer(Modifier.height(8.dp))
                        androidx.compose.foundation.text.selection.SelectionContainer {
                            StatusCard(quote.paymentDetails)
                        }
                    } else {
                        val bitmap = remember(quote.qr?.imageDataUrl) {
                            runCatching {
                                val bytes = Base64.decode(quote.qr?.imageDataUrl.orEmpty().substringAfter(","), Base64.DEFAULT)
                                BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.asImageBitmap()
                            }.getOrNull()
                        }
                        if (bitmap != null) Image(
                            bitmap = bitmap,
                            contentDescription = stringResource(R.string.sub_payment_details),
                            modifier = Modifier.align(Alignment.CenterHorizontally).size(240.dp),
                        )
                    }
                    Spacer(Modifier.height(20.dp))
                    HorizontalDivider(color = PompColors.Divider)
                    Spacer(Modifier.height(16.dp))
                    OutlinedButton(
                        onClick = { picker.launch("image/*") },
                        enabled = !state.submitting,
                        modifier = Modifier.fillMaxWidth().heightIn(min = 54.dp),
                    ) { Text(stringResource(if (state.receiptSelected) R.string.sub_selected else R.string.sub_receipt), color = PompColors.CinnabarDark) }
                    Spacer(Modifier.height(12.dp))
                    PrimaryAction(stringResource(R.string.sub_submit), state.submitting, state.receiptSelected, model::submit)
                    Spacer(Modifier.height(14.dp))
                    Text(stringResource(R.string.sub_approval_note), color = PompColors.InkSecondary, textAlign = TextAlign.Center, style = MaterialTheme.typography.bodySmall)
                }
            }
            state.errorRes?.let { errorRes ->
                Spacer(Modifier.height(16.dp))
                Text(stringResource(errorRes), color = PompColors.Flame, style = MaterialTheme.typography.bodyMedium)
                if (state.overview == null && !state.loading) {
                    TextButton(onClick = model::load) { Text(stringResource(R.string.sub_retry)) }
                }
            }
            Spacer(Modifier.height(36.dp))
        }
    }
}

@Composable
private fun PlanOption(label: String, price: SubscriptionPriceDto?, selected: Boolean, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(18.dp),
        color = if (selected) PompColors.CinnabarSoft else PompColors.PaperRaised,
        border = BorderStroke(1.dp, if (selected) PompColors.Cinnabar else PompColors.Divider),
    ) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 16.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(label, color = PompColors.Ink, fontWeight = FontWeight.Bold)
            Spacer(Modifier.weight(1f))
            if (price != null) {
                Column(horizontalAlignment = Alignment.End) {
                    Text("${price.finalAmount} ${price.currency}", color = PompColors.CinnabarDark, fontWeight = FontWeight.Bold)
                    if (price.discountPercent > 0) Text(
                        "${price.baseAmount} ${price.currency} · −${price.discountPercent}%",
                        color = PompColors.InkSecondary, textDecoration = TextDecoration.LineThrough,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }
    }
}

@Composable
private fun planLabel(plan: String): String = stringResource(when (plan) {
    "10_days" -> R.string.sub_plan_10
    "3_months" -> R.string.sub_plan_3
    else -> R.string.sub_plan_1
})

@Composable
private fun PrimaryAction(label: String, busy: Boolean, enabled: Boolean, onClick: () -> Unit) {
    Button(
        onClick = onClick, enabled = enabled && !busy,
        modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp),
        shape = RoundedCornerShape(16.dp),
        colors = ButtonDefaults.buttonColors(containerColor = PompColors.Cinnabar),
    ) {
        if (busy) CircularProgressIndicator(color = PompColors.Paper, strokeWidth = 2.dp, modifier = Modifier.size(20.dp))
        else Text(label)
    }
}

@Composable
private fun StatusCard(message: String) {
    Surface(color = PompColors.PaperRaised, shape = RoundedCornerShape(16.dp), border = BorderStroke(1.dp, PompColors.Divider)) {
        Text(message, modifier = Modifier.fillMaxWidth().padding(18.dp), color = PompColors.Ink, style = MaterialTheme.typography.bodyLarge)
    }
}
