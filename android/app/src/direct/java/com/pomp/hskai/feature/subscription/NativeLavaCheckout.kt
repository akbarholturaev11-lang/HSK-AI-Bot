package com.pomp.hskai.feature.subscription

import android.content.Intent
import android.net.Uri
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.background
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.unit.dp
import androidx.lifecycle.*
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.R
import com.pomp.hskai.core.design.components.HskSceneSurface

/** Returns true while the provider surface owns this native route. No WebView. */
@Composable
internal fun NativeLavaCheckout(owner: ViewModelStoreOwner, origin: String, onClose: () -> Unit,
    repositoryOverride: LavaCheckoutRepository? = null): Boolean {
    // Keep the separate permanent-course product and existing discount entry routes manual.
    if (origin.startsWith("hsk30") || origin.contains("discount")) return false
    val context = LocalContext.current
    val app = context.applicationContext as HskAiApplication
    val repository = remember(app, repositoryOverride) { repositoryOverride ?: LavaCheckoutRepository(app.nativeApi(AndroidLavaApi::class.java),
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
                }) as T
        })
    val state by model.state.collectAsStateWithLifecycle()
    var otherPlansOpen by remember { mutableStateOf(false) }
    var manual by rememberSaveable(origin) { mutableStateOf(false) }
    val block = state.block
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
    DisposableEffect(lifecycle, model) {
        val observer = LifecycleEventObserver { _, event -> if (event == Lifecycle.Event.ON_RESUME) model.refresh() }
        lifecycle.lifecycle.addObserver(observer)
        onDispose { lifecycle.lifecycle.removeObserver(observer) }
    }
    if ((manual && state.mode == "subscription" && block?.mode == "both") ||
        (!state.loading && block == null && state.mode == "subscription")) return false
    if (block?.mode == "manual_only" && block.subscription == null && state.checkoutId == 0 &&
        block.blocked_reason == null && !state.error) return false
    BackHandler { model.requestProviderClose() }
    HskSceneSurface(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize().safeDrawingPadding().padding(20.dp)) {
            Row(Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.sub_heading), style = MaterialTheme.typography.headlineMedium, modifier = Modifier.weight(1f))
                IconButton(onClick = model::requestProviderClose, enabled = !state.busy) {
                    Icon(Icons.Default.Close, contentDescription = stringResource(R.string.hsk_common_action_close))
                }
            }
            Column(Modifier.weight(1f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                when {
                    state.loading -> {
                        Text(stringResource(R.string.lava_title), style = MaterialTheme.typography.titleLarge)
                        ProviderPlanSkeleton()
                        Spacer(Modifier.height(48.dp))
                        OutlinedTextField(value = "", onValueChange = {}, enabled = false, singleLine = true,
                            label = { Text(stringResource(R.string.lava_email)) }, modifier = Modifier.fillMaxWidth().testTag("provider-email"))
                        Text(stringResource(R.string.lava_terms), style = MaterialTheme.typography.bodySmall)
                        Button(onClick = {}, enabled = false, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.lava_pay)) }
                    }
                    state.checkoutId > 0 -> {
                        Text(stringResource(when (state.status) {
                            "paid" -> R.string.sub_pro_approved_body
                            "pending" -> R.string.lava_pending
                            else -> R.string.lava_failed
                        }))
                        if (state.status != "paid") {
                            OutlinedButton(onClick = model::refresh, enabled = !state.busy) { Text(stringResource(R.string.lava_check)) }
                            if (state.paymentUrl != null) TextButton(onClick = model::reopenPayment, enabled = !state.busy) { Text(stringResource(R.string.lava_open)) }
                        } else Button(onClick = onClose) { Text(stringResource(R.string.sub_return_app)) }
                    }
                    block?.subscription != null -> {
                        Text(stringResource(if (block.subscription.auto_renew) R.string.lava_terms else R.string.lava_cancelled))
                        if (block.subscription.auto_renew) TextButton(onClick = model::cancelRenewal, enabled = !state.busy) {
                            Text(stringResource(R.string.lava_cancel))
                        }
                    }
                    block != null -> {
                        Text(stringResource(R.string.lava_title), style = MaterialTheme.typography.titleLarge)
                        val plans = block.plans.filter { it.amount != null && it.months in setOf(1, 3, 6, 12) }
                        val primary = plans.filter { it.months in setOf(1, 12) }.ifEmpty { plans.take(2) }
                        Row(Modifier.fillMaxWidth().height(110.dp).testTag("provider-plans"), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            primary.forEach { plan ->
                                FilterChip(selected = state.plan == plan.plan_type, enabled = !state.busy,
                                    onClick = { model.chooseProviderPlan(plan.plan_type) }, modifier = Modifier.weight(1f).fillMaxHeight(), label = {
                                        Column {
                                            Text(stringResource(R.string.lava_months, plan.months))
                                            Text(stringResource(R.string.lava_price, plan.amount.orEmpty(), plan.currency))
                                        }
                                    })
                            }
                        }
                        val others = plans.filter { it !in primary }
                        if (others.isNotEmpty()) {
                            TextButton(onClick = { otherPlansOpen = !otherPlansOpen }, modifier = Modifier.height(48.dp)) {
                                Text(stringResource(R.string.lava_other_plans))
                            }
                            if (otherPlansOpen) others.forEach { plan ->
                                FilterChip(selected = state.plan == plan.plan_type, enabled = !state.busy,
                                    onClick = { model.chooseProviderPlan(plan.plan_type) }, label = {
                                        Text(stringResource(R.string.lava_months, plan.months) + " · " + stringResource(R.string.lava_price, plan.amount.orEmpty(), plan.currency))
                                    })
                            }
                        } else Spacer(Modifier.height(48.dp))
                        OutlinedTextField(value = state.email, onValueChange = model::email,
                            enabled = !state.busy, singleLine = true, label = { Text(stringResource(R.string.lava_email)) },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email), modifier = Modifier.fillMaxWidth().testTag("provider-email"))
                        Text(stringResource(R.string.lava_terms), style = MaterialTheme.typography.bodySmall)
                        if (block.blocked_reason != null) Text(stringResource(R.string.lava_blocked))
                        Button(onClick = model::start, enabled = !state.busy && !state.uncertainStart &&
                            block.blocked_reason == null && state.plan.isNotBlank() && state.email.contains("@"),
                            modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.lava_pay)) }
                    }
                }
                if (state.uncertainStart) Text(stringResource(R.string.lava_uncertain))
                if (state.error) {
                    Text(stringResource(R.string.lava_error), color = MaterialTheme.colorScheme.error)
                    TextButton(onClick = { if (state.checkoutId > 0) model.refresh() else model.load() }, enabled = !state.busy) {
                        Text(stringResource(R.string.hsk_course_lesson_flow_retry))
                    }
                }
                if (state.mode == "subscription" && block?.mode == "both" && state.checkoutId == 0 && !state.uncertainStart && !state.busy) {
                    TextButton(onClick = { manual = true }) { Text(stringResource(R.string.lava_manual)) }
                }
            }
        }
    }
    state.offer?.let { offer ->
        AlertDialog(onDismissRequest = model::close,
            title = { Text(stringResource(R.string.lava_exit_title, offer.percent)) },
            text = { Text(stringResource(R.string.lava_exit_body, offer.expires_at.orEmpty())) },
            confirmButton = { TextButton(onClick = model::claim, enabled = !state.busy) { Text(stringResource(R.string.lava_exit_claim)) } },
            dismissButton = { TextButton(onClick = model::close, enabled = !state.busy) { Text(stringResource(R.string.lava_exit_later)) } })
    }
    return true
}

/** Same two primary plan slots as ready; static bars respect disabled system animations. */
@Composable
private fun ProviderPlanSkeleton() {
    Row(Modifier.fillMaxWidth().height(110.dp).testTag("provider-plans"), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        repeat(2) {
            Column(Modifier.weight(1f).fillMaxHeight().background(MaterialTheme.colorScheme.surfaceVariant,
                RoundedCornerShape(12.dp)).padding(12.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Box(Modifier.fillMaxWidth(0.55f).height(18.dp).background(MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(4.dp)))
                Box(Modifier.fillMaxWidth(0.8f).height(22.dp).background(MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(4.dp)))
            }
        }
    }
}
