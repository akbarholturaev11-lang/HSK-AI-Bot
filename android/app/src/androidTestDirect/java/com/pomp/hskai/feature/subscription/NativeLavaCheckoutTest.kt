package com.pomp.hskai.feature.subscription

import android.content.res.Configuration
import android.graphics.Bitmap
import androidx.compose.runtime.*
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.unit.Density
import androidx.compose.ui.platform.*
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.lifecycle.*
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.network.ApiResult
import java.io.File
import java.util.Locale
import kotlinx.coroutines.CompletableDeferred
import org.junit.Rule
import org.junit.Test
import org.junit.Assert.*
import retrofit2.Response
import kotlin.math.abs

class NativeLavaCheckoutTest {
    @get:Rule val compose = createComposeRule()
    private val context = InstrumentationRegistry.getInstrumentation().targetContext
    private class Fake : AndroidLavaApi {
        val reply = CompletableDeferred<Response<LavaOverview>>()
        @Volatile var statusValue = "pending"
        @Volatile var checks = 0
        var offer = ExitReply(ok = true)
        override suspend fun providerOverview(auth: String, body: LavaContext) = reply.await()
        override suspend fun start(auth: String, body: LavaStart): Response<LavaReply> = error("No real purchase in UI tests")
        override suspend fun status(auth: String, body: LavaId): Response<LavaReply> {
            checks++
            return Response.success(LavaReply(ok = true, status = statusValue))
        }
        override suspend fun cancel(auth: String, body: Map<String, String>) = Response.success(LavaReply(ok = true))
        override suspend fun exitOffer(auth: String, body: ExitAction) = Response.success(offer)
    }
    private val plans = listOf(LavaPlan("1_month", 1, 30, "10.00", "USD"),
        LavaPlan("3_months", 3, 90, "27.00", "USD"), LavaPlan("6_months", 6, 180, "50.00", "USD"),
        LavaPlan("12_months", 12, 365, "90.00", "USD"))

    private fun show(api: Fake, limit: Boolean = false, language: String = "uz", lifecycle: LifecycleOwner? = null, fontScale: Float = 1f, telemetry: ProCheckoutTelemetry? = null) {
        val owner = object : ViewModelStoreOwner { override val viewModelStore = ViewModelStore() }
        val repository = LavaCheckoutRepository(api, { ApiResult.Success("synthetic") })
        compose.setContent {
            val copy = context.createConfigurationContext(Configuration(context.resources.configuration).apply {
                setLocale(Locale.forLanguageTag(language))
            })
            CompositionLocalProvider(LocalContext provides copy, LocalConfiguration provides copy.resources.configuration,
                LocalDensity provides Density(LocalDensity.current.density, fontScale)) {
                val currentLifecycle = lifecycle ?: LocalLifecycleOwner.current
                CompositionLocalProvider(LocalLifecycleOwner provides currentLifecycle) {
                    PompHskAiTheme {
                        if (!NativeLavaCheckout(owner, "course_limit", {}, repository, limitOffer = limit, telemetry = telemetry).ownsSurface)
                            androidx.compose.material3.Text("Manual fallback")
                    }
                }
            }
        }
    }
    private fun ready(api: Fake, email: String? = null, rows: List<LavaPlan> = plans, pending: Int? = null) {
        api.reply.complete(Response.success(LavaOverview(true, LavaBlock(mode = "both", plans = rows,
            email = email, pending_checkout_id = pending))))
        compose.waitUntil(5_000) { compose.onAllNodesWithText(if (pending == null) "10.00 USD" else context.getString(R.string.checkout_pending_title))
            .fetchSemanticsNodes().isNotEmpty() }
    }
    private fun screenshot(name: String) {
        InstrumentationRegistry.getInstrumentation().waitForIdleSync()
        Thread.sleep(300)
        compose.onRoot().captureToImage().asAndroidBitmap().let { bitmap ->
            File(context.getExternalFilesDir(null), "$name.png").outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
        }
    }

    @Test fun providerUsesTheSharedCenteredHeaderAndEmailIsASingleBackStep() {
        val api = Fake(); show(api); ready(api)
        val header = compose.onNodeWithTag("checkout-header").fetchSemanticsNode().boundsInRoot
        val title = compose.onNodeWithTag("checkout-title").fetchSemanticsNode().boundsInRoot
        assertTrue(abs(header.center.x - title.center.x) < 2f)
        compose.onNodeWithTag("checkout-support").assertIsDisplayed()
        compose.onNodeWithContentDescription(context.getString(R.string.action_close)).assertIsDisplayed()
        compose.onNodeWithText(context.getString(R.string.lava_pay)).performClick()
        compose.onNodeWithTag("provider-email").assertIsDisplayed().performTextInput("learner@example.com")
        compose.onNodeWithContentDescription(context.getString(R.string.action_close)).assertDoesNotExist()
        compose.onNodeWithContentDescription(context.getString(R.string.action_back)).performClick()
        compose.onNodeWithTag("provider-plan:1_month").assertIsSelected()
        compose.onNodeWithTag("provider-email").assertDoesNotExist()
        screenshot("checkout-provider-plans")
    }

    @Test fun limitStartsWithPrimaryTermsAndMoreReturnsInOneStep() {
        val api = Fake(); show(api, limit = true); ready(api)
        compose.onNodeWithTag("limit-panda").assertExists()
        compose.onNodeWithTag("provider-plan:1_month").assertExists()
        compose.onNodeWithTag("provider-plan:12_months").assertExists()
        compose.onNodeWithTag("provider-plan:3_months").assertDoesNotExist()
        compose.onNodeWithText(context.getString(R.string.lava_terms)).assertDoesNotExist()
        screenshot("checkout-limit-primary")
        compose.onNodeWithText(context.getString(R.string.lava_other_plans)).performClick()
        compose.onNodeWithTag("provider-plan:3_months").assertExists()
        compose.onNodeWithContentDescription(context.getString(R.string.action_close)).assertDoesNotExist()
        compose.onNodeWithContentDescription(context.getString(R.string.action_back)).performClick()
        compose.onNodeWithTag("provider-plan:3_months").assertDoesNotExist()
    }

    @Test fun realPlanMoreAndEmailActionsEmitUiStagesWithoutClaimingPayment() {
        val events = java.util.Collections.synchronizedList(mutableListOf<String>())
        val telemetry = object : ProCheckoutTelemetry {
            override val attemptId = "native-attempt"
            override val source = "course_limit"
            override fun record(event: String, plan: String?, method: String?) { events += event }
        }
        val api = Fake(); show(api, limit = true, telemetry = telemetry); ready(api)
        assertTrue(events.isEmpty())
        compose.onNodeWithTag("provider-plan:12_months").performClick()
        compose.onNodeWithText(context.getString(R.string.lava_other_plans)).performClick()
        compose.onNodeWithContentDescription(context.getString(R.string.action_back)).performClick()
        compose.onNodeWithText(context.getString(R.string.limit_sheet_get_pro)).performClick()
        compose.onNodeWithTag("provider-email").assertIsDisplayed()
        assertEquals(listOf("plan_selected", "more_opened", "plan_selected"), events.toList())
        assertFalse(events.any { it in setOf("checkout_started", "checkout_paid", "dismissed") })
    }

    @Test fun limitLoadingKeepsThePrimaryGridAnchor() {
        val api = Fake(); show(api, limit = true)
        val loading = compose.onNodeWithTag("provider-plans").fetchSemanticsNode().boundsInRoot
        ready(api)
        val loaded = compose.onNodeWithTag("provider-plans").fetchSemanticsNode().boundsInRoot
        assertTrue(abs(loading.top - loaded.top) < 2f)
        assertTrue(abs(loading.height - loaded.height) < 2f)
    }

    @Test fun knownEmailSkipsTheEmailStep() {
        val api = Fake(); show(api); ready(api, email = "learner@example.com")
        compose.onNodeWithTag("provider-email").assertDoesNotExist()
        compose.onNodeWithText(context.getString(R.string.lava_pay)).assertIsEnabled()
    }

    @Test fun pendingPollStopsInBackgroundAndRefreshesImmediatelyOnReturn() {
        val lifecycle = object : LifecycleOwner {
            val registry = LifecycleRegistry(this)
            override val lifecycle: Lifecycle get() = registry
        }
        val api = Fake()
        compose.runOnUiThread { lifecycle.registry.currentState = Lifecycle.State.RESUMED }
        show(api, lifecycle = lifecycle)
        ready(api, pending = 7)
        compose.waitUntil(5_000) { api.checks >= 1 }
        compose.runOnUiThread { lifecycle.registry.currentState = Lifecycle.State.CREATED }
        val before = api.checks
        Thread.sleep(5_200)
        assertEquals(before, api.checks)
        api.statusValue = "paid"
        compose.runOnUiThread { lifecycle.registry.currentState = Lifecycle.State.RESUMED }
        compose.waitUntil(5_000) { api.checks > before }
        compose.onNodeWithText(context.getString(R.string.checkout_paid_title)).assertIsDisplayed()
        screenshot("checkout-provider-paid")
    }

    @Test fun delayedWebhookIsObservedWithoutLeavingThePendingScreen() {
        val api = Fake(); show(api); ready(api, pending = 7)
        compose.waitUntil(5_000) { api.checks >= 1 }
        api.statusValue = "paid"
        compose.waitUntil(7_000) { compose.onAllNodesWithText(context.getString(R.string.checkout_paid_title)).fetchSemanticsNodes().isNotEmpty() }
        compose.onNodeWithText(context.getString(R.string.sub_return_app)).assertIsDisplayed()
    }

    @Test fun disabledProviderKeepsExistingNativeManualCheckout() {
        val api = Fake(); show(api)
        api.reply.complete(Response.success(LavaOverview(ok = true)))
        compose.waitUntil(5_000) { compose.onAllNodesWithText("Manual fallback").fetchSemanticsNodes().isNotEmpty() }
    }
    @Test fun russianLimitRemainsReadable() = localizedLimit("ru")
    @Test fun tajikLimitRemainsReadable() = localizedLimit("tg")
    private fun localizedLimit(locale: String) {
        val api = Fake(); show(api, limit = true, language = locale); ready(api)
        val copy = context.createConfigurationContext(Configuration(context.resources.configuration).apply {
            setLocale(Locale.forLanguageTag(locale))
        })
        compose.onNodeWithTag("checkout-header").assertIsDisplayed()
        compose.onNodeWithText(copy.getString(R.string.checkout_limit_title)).assertIsDisplayed()
        compose.onNodeWithText(copy.getString(R.string.limit_sheet_get_pro)).assertIsDisplayed()
        screenshot("checkout-limit-$locale")
    }
    @Test fun exitOfferKeepsSharedHeaderAndBackWithoutAnotherX() {
        val api = Fake(); api.offer = ExitReply(ok = true, available = true, percent = 20)
        show(api, limit = true); ready(api)
        compose.onNodeWithContentDescription(context.getString(R.string.action_close)).performClick()
        compose.onNodeWithText(context.getString(R.string.checkout_exit_title)).assertIsDisplayed()
        compose.onNodeWithTag("checkout-support").assertIsDisplayed()
        compose.onNodeWithContentDescription(context.getString(R.string.action_close)).assertDoesNotExist()
        compose.onNodeWithText(context.getString(R.string.checkout_exit_accept)).assertIsDisplayed()
        screenshot("checkout-exit-offer")
        compose.onNodeWithContentDescription(context.getString(R.string.action_back)).performClick()
        compose.onNodeWithTag("provider-plan:1_month").assertIsSelected()
        compose.onNodeWithText(context.getString(R.string.checkout_limit_title)).assertIsDisplayed()
    }

    @Test fun largeTextKeepsLimitActionsAndHeaderReachable() {
        val api = Fake(); show(api, limit = true, fontScale = 2f); ready(api)
        compose.onNodeWithText(context.getString(R.string.limit_sheet_get_pro)).assertIsDisplayed()
        compose.onNodeWithContentDescription(context.getString(R.string.action_close)).assertIsDisplayed()
        compose.onNodeWithTag("provider-plan:12_months").performScrollTo().assertIsDisplayed()
        screenshot("checkout-limit-large-text")
    }

    @Test fun countryMatchesPwaLabelsAndRetainsMoreUntilBack() {
        val api = Fake(); show(api, limit = true); ready(api)
        compose.onNodeWithText(context.getString(R.string.lava_other_plans)).performClick()
        compose.onNodeWithTag("checkout-country").onChildren().filter(hasClickAction()).onFirst().performClick()
        compose.onNodeWithText("🇺🇿 " + context.getString(R.string.checkout_country_uz)).performClick()
        compose.onNodeWithTag("provider-plan:3_months").assertExists()
        compose.onNodeWithContentDescription(context.getString(R.string.action_back)).performClick()
        compose.onNodeWithTag("provider-plan:3_months").assertDoesNotExist()
        compose.onNodeWithText(context.getString(R.string.lava_terms)).assertDoesNotExist()
        compose.onNodeWithText("🇺🇿 " + context.getString(R.string.checkout_country_uz)).assertIsDisplayed()
        screenshot("checkout-country-pwa-parity")
    }

}
