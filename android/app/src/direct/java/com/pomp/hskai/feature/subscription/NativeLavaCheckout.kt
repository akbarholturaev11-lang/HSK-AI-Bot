package com.pomp.hskai.feature.subscription

import android.content.Intent
import android.net.Uri
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.background
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.Alignment
import androidx.compose.ui.unit.sp
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.*
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.R
import com.pomp.hskai.core.design.components.HskSceneSurface

internal data class NativeLavaRoute(val ownsSurface: Boolean, val providerEntryId: Int? = null)

/** Returns route ownership plus the committed opening receipt for a manual fallback. No WebView. */
@Composable
internal fun NativeLavaCheckout(owner: ViewModelStoreOwner, origin: String, onClose: () -> Unit,
    repositoryOverride: LavaCheckoutRepository? = null,
    regionOverride: String? = null,
    routeOverride: String? = null,
    onRegionResolved: (String) -> Unit = {},
    onRegionSelected: (String) -> Unit = {},
    onRouteSelected: ((String) -> Unit)? = null,
    onProviderAvailable: (Boolean) -> Unit = {},
    limitOffer: Boolean = false,
    telemetry: ProCheckoutTelemetry? = null,
    allPlansOverride: Boolean? = null,
    onAllPlansChange: ((Boolean) -> Unit)? = null,
): NativeLavaRoute {
    // Keep the separate permanent-course product and existing discount entry routes manual.
    if (origin.startsWith("hsk30") || origin.contains("discount")) return NativeLavaRoute(false)
    val context = LocalContext.current
    val app = context.applicationContext as HskAiApplication
    val repository = remember(app, repositoryOverride, origin) { repositoryOverride ?: LavaCheckoutRepository(app.nativeApi(AndroidLavaApi::class.java),
        app.authRepository::accessToken, app.authRepository::invalidateSession, origin) }
    // One provider model per visible host. A reused session model could expose
    // its previous manual fallback before the next provider read starts, mounting
    // and loading the manual host twice on reopen.
    val providerOwner = remember(owner, origin) { object : ViewModelStoreOwner {
        override val viewModelStore = ViewModelStore()
    } }
    DisposableEffect(providerOwner) { onDispose { providerOwner.viewModelStore.clear() } }
    val model: LavaCheckoutViewModel = viewModel(viewModelStoreOwner = providerOwner, key = "lava:$origin",
        factory = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T =
                LavaCheckoutViewModel(repository, context.resources.configuration.locales[0].language.let {
                    if (it == "tg") "tj" else if (it in setOf("uz", "ru", "tj")) it else "uz"
                }, savedRegion = { if (repositoryOverride == null) app.appSettings.paymentRegion() else null },
                    saveRegion = { if (repositoryOverride == null) app.appSettings.setPaymentRegion(it) },
                    regionHint = { if (repositoryOverride == null) localCheckoutRegion(context.resources.configuration.locales[0].language) else "other" },
                    telemetry = telemetry) as T
        })
    val state by model.state.collectAsStateWithLifecycle()
    var localAllPlans by rememberSaveable(origin) { mutableStateOf(false) }
    val allPlans = allPlansOverride ?: localAllPlans
    val setAllPlans: (Boolean) -> Unit = { if (allPlansOverride == null) localAllPlans = it; onAllPlansChange?.invoke(it) }
    var emailStep by rememberSaveable(origin) { mutableStateOf(false) }
    var manual by rememberSaveable(origin) { mutableStateOf(false) }
    val block = state.block
    val effectiveRegion = regionOverride ?: state.region
    val canChooseRoute = !state.loading && !state.busy && !state.error && state.mode == "subscription" &&
        state.checkoutId == 0 && !state.uncertainStart && block?.subscription == null && block?.blocked_reason == null
    val canUseManual = canChooseRoute && block?.mode == "both"
    LaunchedEffect(state.region, regionOverride) {
        if (state.region.isNotBlank()) {
            if (regionOverride == null) onRegionResolved(state.region)
            else if (regionOverride != state.region) model.chooseRegion(regionOverride)
        }
    }
    val providerAvailable = canUseManual && block?.providerCurrencies()?.isNotEmpty() == true
    LaunchedEffect(providerAvailable) { onProviderAvailable(providerAvailable) }
    val lifecycle = LocalLifecycleOwner.current
    val close by rememberUpdatedState(onClose)
    LaunchedEffect(model) { model.closeEvents.collect { close() } }
    LaunchedEffect(state.launchUrl) {
        state.launchUrl?.let { url ->
            val success = runCatching {
                val allowed = safeLavaPaymentUrl(url) ?: error("invalid_provider_url")
                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(allowed)))
            }.isSuccess
            model.urlOpened(success)
        }
    }
    // Manual receipt recovery is not a new sale. Never hide it behind a blocked provider screen.
    if (state.hasManualPending()) return NativeLavaRoute(false, state.providerEntryId)
    val automaticManual = block?.prefersManual(effectiveRegion) == true
    if ((canUseManual && (routeOverride == "manual" ||
            (routeOverride != "lava" && (manual || automaticManual)))) ||
        (!state.loading && block == null && state.mode == "subscription")) return NativeLavaRoute(false, state.providerEntryId)
    if (block?.mode == "manual_only" && block.subscription == null && state.checkoutId == 0 &&
        block.blocked_reason == null && !state.error) return NativeLavaRoute(false, state.providerEntryId)
    var supportOpen by remember { mutableStateOf(false) }
    val primaryPlans = providerDisplayPlans(state.visiblePlans, limitOffer && !allPlans)
    LaunchedEffect(primaryPlans.map { it.plan_type }, emailStep, state.loading) {
        if (!state.loading && !emailStep && primaryPlans.isNotEmpty() && primaryPlans.none { it.plan_type == state.plan })
            model.chooseProviderPlan(primaryPlans.first().plan_type, userAction = false)
    }
    val terminal = state.checkoutId > 0 || block?.subscription != null
    val firstStep = state.offer == null && !terminal && !emailStep && !(limitOffer && allPlans)
    val focus = androidx.compose.ui.platform.LocalFocusManager.current
    val keyboard = androidx.compose.ui.platform.LocalSoftwareKeyboardController.current
    val navigate: () -> Unit = {
        focus.clearFocus()
        keyboard?.hide()
        when {
            state.offer != null -> model.dismissOffer()
            emailStep -> emailStep = false
            limitOffer && allPlans -> setAllPlans(false)
            terminal -> model.close()
            else -> model.requestProviderClose()
        }
    }
    BackHandler { if (!state.busy) navigate() }
    // A return before the webhook is normal. Keep checking the same invoice,
    // only in the foreground; backgrounding cancels the timer, never starts a sale.
    LaunchedEffect(lifecycle, model, state.checkoutId, state.uncertainStart) {
        lifecycle.lifecycle.repeatOnLifecycle(Lifecycle.State.RESUMED) {
            if (model.state.value.uncertainStart) model.load()
            if (model.state.value.checkoutId > 0) {
                repeat(180) {
                    val current = model.state.value
                    if (current.status !in setOf("pending", "")) return@repeatOnLifecycle
                    model.refresh()
                    kotlinx.coroutines.delay(5_000)
                }
            }
        }
    }
    HskSceneSurface(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize().background(com.pomp.hskai.core.design.ProColors.Paper)
            .safeDrawingPadding().imePadding().widthIn(max = 520.dp).padding(horizontal = 16.dp)) {
            CheckoutHeader(firstStep, navigate, { supportOpen = true }, enabled = !state.busy)
            if (!limitOffer && !terminal && state.offer == null) CheckoutProgress(if (emailStep) 1 else 0,
                if (block?.email.isNullOrBlank()) 2 else 1)
            Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(vertical = 16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)) {
                when {
                    state.offer != null -> {
                        CheckoutPanda(Modifier.align(Alignment.CenterHorizontally).size(172.dp), pose = "gift")
                        Text(stringResource(R.string.checkout_exit_title), fontSize = 28.sp,
                            fontWeight = FontWeight.ExtraBold, textAlign = TextAlign.Center,
                            color = com.pomp.hskai.core.design.ProColors.Ink, modifier = Modifier.fillMaxWidth())
                        Text(stringResource(R.string.checkout_exit_body), textAlign = TextAlign.Center,
                            color = com.pomp.hskai.core.design.ProColors.Muted, modifier = Modifier.fillMaxWidth())
                    }
                    state.loading -> {
                        if (limitOffer) LimitOfferHero(origin)
                        else Text(stringResource(R.string.sub_plans_heading), color = com.pomp.hskai.core.design.ProColors.Ink,
                            fontSize = 16.sp, fontWeight = FontWeight.ExtraBold)
                        ProviderPlanSkeleton(limitOffer)
                    }
                    state.checkoutId > 0 -> {
                        ProviderStatus(state)
                    }
                    block?.subscription != null -> {
                        CheckoutPanda(Modifier.align(Alignment.CenterHorizontally).size(148.dp))
                        Text(stringResource(R.string.checkout_heading), fontSize = 28.sp, fontWeight = FontWeight.ExtraBold,
                            color = com.pomp.hskai.core.design.ProColors.Ink, textAlign = TextAlign.Center,
                            modifier = Modifier.fillMaxWidth())
                        Text(stringResource(if (block.subscription.auto_renew) R.string.lava_terms else R.string.lava_cancelled),
                            color = com.pomp.hskai.core.design.ProColors.Muted)
                        block.subscription.pro_until?.let { Text(it.substringBefore('T'), color = com.pomp.hskai.core.design.ProColors.Ink) }
                        if (block.subscription.auto_renew) TextButton(onClick = model::cancelRenewal, enabled = !state.busy) {
                            Text(stringResource(R.string.lava_cancel), color = com.pomp.hskai.core.design.ProColors.CtaDeep)
                        }
                    }
                    block != null && emailStep -> {
                        val plan = state.visiblePlans.firstOrNull { it.plan_type == state.plan }
                        Text(stringResource(R.string.checkout_email), fontSize = 24.sp,
                            fontWeight = FontWeight.ExtraBold, color = com.pomp.hskai.core.design.ProColors.Ink)
                        plan?.let { ProviderPlanCard(it, true, {}, Modifier.fillMaxWidth(), enabled = false) }
                        OutlinedTextField(value = state.email, onValueChange = model::email,
                            enabled = !state.busy, singleLine = true, label = { Text(stringResource(R.string.lava_email)) },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                            shape = RoundedCornerShape(16.dp), modifier = Modifier.fillMaxWidth().testTag("provider-email"))
                        Text(stringResource(R.string.lava_terms), color = com.pomp.hskai.core.design.ProColors.Muted,
                            style = MaterialTheme.typography.bodySmall)
                    }
                    block != null -> {
                        if (limitOffer && !allPlans) LimitOfferHero(origin)
                        else Text(stringResource(R.string.sub_plans_heading), fontSize = 16.sp,
                            fontWeight = FontWeight.ExtraBold, color = com.pomp.hskai.core.design.ProColors.Ink)
                        val plans = providerDisplayPlans(state.visiblePlans, limitOffer && !allPlans)
                        if (plans.isEmpty()) {
                            Text(stringResource(R.string.sub_unavailable), color = com.pomp.hskai.core.design.ProColors.Muted)
                            TextButton(onClick = model::load, enabled = !state.busy) { Text(stringResource(R.string.sub_retry)) }
                        }
                        ProviderPlans(plans, state.plan, !state.busy, limitOffer,
                            { model.chooseProviderPlan(it) })
                        if (state.mode == "subscription") ProviderRegionSelector(effectiveRegion, canChooseRoute) {
                            model.chooseRegion(it); manual = false; onRegionSelected(it)
                        }
                        if (canUseManual && (!limitOffer || allPlans)) {
                            OutlinedButton(onClick = { manual = true; onRouteSelected?.invoke("manual") },
                                enabled = !state.busy, shape = RoundedCornerShape(16.dp),
                                border = androidx.compose.foundation.BorderStroke(1.dp, com.pomp.hskai.core.design.ProColors.Line),
                                modifier = Modifier.fillMaxWidth().heightIn(min = 64.dp)) {
                                Column(Modifier.weight(1f)) {
                                    Text(stringResource(R.string.checkout_manual), color = com.pomp.hskai.core.design.ProColors.Ink)
                                    Text(stringResource(R.string.checkout_manual_hint), color = com.pomp.hskai.core.design.ProColors.Muted,
                                        fontSize = 12.sp)
                                }
                            }
                        }
                        if (!limitOffer) Text(stringResource(R.string.lava_terms), color = com.pomp.hskai.core.design.ProColors.Muted,
                            fontSize = 12.sp, lineHeight = 18.sp)
                        if (block.blocked_reason != null) Text(stringResource(R.string.lava_blocked),
                            color = com.pomp.hskai.core.design.ProColors.Muted)
                    }
                }
                if (state.uncertainStart) Text(stringResource(R.string.lava_uncertain), color = com.pomp.hskai.core.design.ProColors.Muted)
                if (state.error) {
                    Text(stringResource(R.string.lava_error), color = MaterialTheme.colorScheme.error)
                    TextButton(onClick = { if (state.checkoutId > 0) model.refresh() else model.load() }, enabled = !state.busy) {
                        Text(stringResource(R.string.hsk_course_lesson_flow_retry))
                    }
                }
            }
            Column(Modifier.fillMaxWidth().padding(top = 12.dp, bottom = 16.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp)) {
                when {
                    state.offer != null -> {
                        CheckoutPrimary(stringResource(R.string.checkout_exit_accept), busy = state.busy, onClick = model::claim)
                        TextButton(onClick = model::declineOffer, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) {
                            Text(stringResource(R.string.checkout_exit_decline), color = com.pomp.hskai.core.design.ProColors.Muted)
                        }
                        Text(stringResource(R.string.checkout_exit_renewal), fontSize = 12.sp,
                            color = com.pomp.hskai.core.design.ProColors.Muted, textAlign = TextAlign.Center,
                            modifier = Modifier.fillMaxWidth())
                    }
                    state.checkoutId > 0 -> {
                        if (state.status == "paid") CheckoutPrimary(stringResource(R.string.sub_return_app), onClick = onClose)
                        else {
                            CheckoutPrimary(stringResource(R.string.lava_check), busy = state.busy, onClick = model::refresh)
                            if (state.paymentUrl != null) TextButton(onClick = model::reopenPayment,
                                enabled = !state.busy, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.lava_open)) }
                        }
                    }
                    block?.subscription != null -> CheckoutPrimary(stringResource(R.string.sub_return_app), onClick = onClose)
                    else -> {
                        CheckoutPrimary(stringResource(if (limitOffer && !emailStep) R.string.limit_sheet_get_pro else R.string.lava_pay),
                            busy = state.busy, enabled = !state.loading && !state.uncertainStart &&
                                block?.blocked_reason == null && state.region == effectiveRegion && state.plan.isNotBlank() &&
                                (!emailStep || validCheckoutEmail(state.email))) {
                            telemetry?.record("plan_selected", state.plan, "lava")
                            if (block?.email.isNullOrBlank() && !emailStep) emailStep = true else model.start()
                        }
                        if (limitOffer && !allPlans && !emailStep) TextButton(onClick = { telemetry?.record("more_opened", state.plan, "lava"); setAllPlans(true) },
                            enabled = !state.loading && !state.busy, modifier = Modifier.fillMaxWidth()) {
                            Text(stringResource(R.string.lava_other_plans), color = com.pomp.hskai.core.design.ProColors.Muted)
                        }
                    }
                }
            }
        }
    }
    if (supportOpen) ProviderSupportSheet(onDismiss = { supportOpen = false })
    return NativeLavaRoute(true)
}

internal fun providerDisplayPlans(plans: List<LavaPlan>, compact: Boolean): List<LavaPlan> {
    val priced = plans.filter { it.amount != null && it.months in setOf(1, 3, 6, 12) }
    if (!compact) return priced
    return priced.filter { it.plan_type in setOf("1_month", "12_months") }.ifEmpty { priced.take(2) }
}

@Composable
private fun ProviderPlans(plans: List<LavaPlan>, selected: String, enabled: Boolean, compact: Boolean, onSelect: (String) -> Unit) {
    BoxWithConstraints(Modifier.fillMaxWidth().testTag("provider-plans")) {
        val singleColumn = !compact && maxWidth <= 400.dp && plans.size == 2
        val rows = when {
            singleColumn -> plans.map { listOf(it) }
            !compact && maxWidth <= 400.dp && plans.size == 3 -> listOf(plans.take(1), plans.drop(1))
            else -> plans.chunked(2)
        }
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            rows.forEach { row ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    row.forEach { plan ->
                        ProviderPlanCard(plan, selected == plan.plan_type, { onSelect(plan.plan_type) },
                            Modifier.weight(1f).testTag("provider-plan:${plan.plan_type}"), compact, enabled)
                    }
                }
            }
        }
    }
}

@Composable
private fun ProviderPlanCard(plan: LavaPlan, selected: Boolean, onClick: () -> Unit,
    modifier: Modifier = Modifier, compact: Boolean = false, enabled: Boolean = true) {
    CheckoutPlanTile(if (plan.months == 12) stringResource(R.string.checkout_year) else stringResource(R.string.lava_months, plan.months), plan.amount.orEmpty(), plan.currency,
        if ((plan.discount_percent ?: 0) > 0) plan.base_amount else comparisonPrice(plan.amount.orEmpty()),
        selected, onClick, modifier, compact,
        badge = plan.discount_percent?.takeIf { it > 0 }?.let { "−$it%" }, enabled = enabled)
}

@Composable
private fun ProviderStatus(state: NativeLavaState) {
    Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp)) {
        CheckoutPanda(Modifier.size(148.dp), pose = if (state.status == "paid") "celebrate" else "read")
        Text(stringResource(when (state.status) {
            "paid" -> R.string.checkout_paid_title
            "pending", "" -> R.string.checkout_pending_title
            else -> R.string.sub_pro_rejected_title
        }), color = com.pomp.hskai.core.design.ProColors.Ink, fontSize = 24.sp,
            lineHeight = 30.sp, fontWeight = FontWeight.ExtraBold, textAlign = TextAlign.Center)
        Text(stringResource(when (state.status) {
            "paid" -> R.string.sub_pro_approved_body
            "pending", "" -> R.string.lava_pending
            else -> R.string.lava_failed
        }),
            color = com.pomp.hskai.core.design.ProColors.Muted, textAlign = TextAlign.Center)
        if (state.status == "pending") CircularProgressIndicator(Modifier.size(24.dp),
            color = com.pomp.hskai.core.design.ProColors.Cta, strokeWidth = 2.dp)
    }
}

@Composable
private fun ProviderPlanSkeleton(compact: Boolean) {
    Column(Modifier.fillMaxWidth().testTag("provider-plans"), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        repeat(if (compact) 1 else 2) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                repeat(2) {
                    com.pomp.hskai.core.design.components.HskContentSkeleton(rows = 2, leadingCircle = false,
                        modifier = Modifier.weight(1f).height(if (compact) 112.dp else 130.dp))
                }
            }
        }
    }
}

@Composable
private fun ProviderRegionSelector(region: String, enabled: Boolean, onSelect: (String) -> Unit) {
    CheckoutCountrySelector(region, CHECKOUT_REGIONS, onSelect, enabled)

}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ProviderSupportSheet(onDismiss: () -> Unit) {
    val context = LocalContext.current
    val app = context.applicationContext as HskAiApplication
    var url by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(true) }
    var attempt by remember { mutableIntStateOf(0) }
    LaunchedEffect(attempt) {
        loading = true
        val result = app.featureRepository.profile()
        if (result is com.pomp.hskai.core.network.ApiResult.Success) url = result.value.supportUrl
        loading = false
    }
    ModalBottomSheet(onDismissRequest = onDismiss, containerColor = com.pomp.hskai.core.design.ProColors.Surface) {
        Column(Modifier.fillMaxWidth().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(stringResource(R.string.sub_help_title), fontSize = 22.sp, fontWeight = FontWeight.Bold)
            Text(stringResource(R.string.sub_help_body))
            CheckoutPrimary(stringResource(if (url.isNotBlank()) R.string.sub_help_button else R.string.sub_retry), busy = loading) {
                if (url.isNotBlank()) runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) }
                else attempt++
            }
        }
    }
}
