package com.pomp.hskai.feature.subscription

import android.content.Context
import android.content.res.Configuration
import android.graphics.Bitmap
import android.net.Uri
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.lifecycle.ViewModelProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.navigation.SessionViewModelStoreOwner
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidFeatureApi
import com.pomp.hskai.data.api.SubscriptionCheckoutEventResponse
import com.pomp.hskai.data.api.SubscriptionCheckoutOverviewDto
import com.pomp.hskai.data.api.SubscriptionPendingDto
import com.pomp.hskai.data.api.SubscriptionPriceDto
import com.pomp.hskai.data.api.SubscriptionQuoteDto
import com.pomp.hskai.data.api.SubscriptionQuoteRequest
import com.pomp.hskai.data.api.SubscriptionQuoteResponse
import com.pomp.hskai.data.api.SubscriptionSubmitRequest
import com.pomp.hskai.data.api.SubscriptionSubmitResponse
import com.pomp.hskai.data.repository.FeatureRepository
import java.io.File
import java.lang.reflect.Proxy
import java.util.Locale
import kotlin.coroutines.Continuation
import kotlin.coroutines.intrinsics.COROUTINE_SUSPENDED
import kotlin.coroutines.resume
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import retrofit2.Response

/** Exercises the real host with the same session owner used by MainActivity. */
@RunWith(AndroidJUnit4::class)
class SubscriptionCheckoutHostTest {
    @get:Rule
    val compose = createComposeRule()

    private val context = InstrumentationRegistry.getInstrumentation().targetContext
    private val copy: Context = context.createConfigurationContext(
        Configuration(context.resources.configuration).apply { setLocale(Locale.forLanguageTag("uz")) },
    )
    private val owner = SessionViewModelStoreOwner()
    private val origin = mutableStateOf("profile_subscription")
    private val visible = mutableStateOf(true)
    private val requestedOrigins = mutableListOf<String>()
    private val quoteRequests = mutableListOf<SubscriptionQuoteRequest>()
    private val submitRequests = mutableListOf<SubscriptionSubmitRequest>()
    private var pending: SubscriptionPendingDto? = null
    private var closeCount = 0
    private var deferSubmit = false
    @Volatile private var submitContinuation: Continuation<Any?>? = null

    @After
    fun tearDown() {
        compose.runOnIdle { owner.clear() }
        (context.applicationContext as HskAiApplication).paymentDecisionMonitor.clear()
    }

    private fun repository(): FeatureRepository {
        val api = Proxy.newProxyInstance(
            AndroidFeatureApi::class.java.classLoader,
            arrayOf(AndroidFeatureApi::class.java),
        ) { _, method, args ->
            when (method.name) {
                "checkoutOverview" -> {
                    val requestOrigin = args[1] as String
                    // These are actual origins accepted by the backend contract.
                    require(requestOrigin in setOf("profile_subscription", "hsk30_content"))
                    requestedOrigins += requestOrigin
                    val mode = if (requestOrigin == "hsk30_content") "hsk30_unlock" else "subscription"
                    val plan = if (mode == "hsk30_unlock") mode else "1_month"
                    Response.success(SubscriptionCheckoutOverviewDto(
                        ok = true,
                        language = "uz",
                        mode = mode,
                        preferredCurrency = "TJS",
                        displayCurrency = "TJS",
                        attemptId = "android-test-attempt-$requestOrigin",
                        checkoutAllowed = pending == null,
                        pendingPayment = pending,
                        prices = if (pending == null) mapOf("visa" to mapOf(plan to SubscriptionPriceDto(
                            baseAmount = 10, finalAmount = 10, currency = "TJS",
                        ))) else emptyMap(),
                    ))
                }
                "checkoutQuote" -> {
                    quoteRequests += args[1] as SubscriptionQuoteRequest
                    Response.success(SubscriptionQuoteResponse(
                        ok = true,
                        quote = SubscriptionQuoteDto(
                            payAmount = "10", payCurrency = "TJS", paymentDetails = "TEST RECEIPT CHECKOUT",
                        ),
                    ))
                }
                "checkoutEvent" -> Response.success(SubscriptionCheckoutEventResponse(ok = true))
                "checkoutSubmit" -> {
                    submitRequests += args[1] as SubscriptionSubmitRequest
                    if (deferSubmit) {
                        @Suppress("UNCHECKED_CAST")
                        val continuation = args.last() as Continuation<Any?>
                        submitContinuation = continuation
                        COROUTINE_SUSPENDED
                    } else Response.success(SubscriptionSubmitResponse(
                        ok = true, paymentId = 71, status = "pending", provisionalAccess = true,
                    ))
                }
                else -> error("Unexpected endpoint: ${method.name}")
            }
        } as AndroidFeatureApi
        return FeatureRepository(api, { ApiResult.Success("test-token") })
    }

    private fun show() {
        val repository = repository()
        compose.setContent {
            PompHskAiTheme {
                if (visible.value) {
                    SubscriptionCheckoutHost(
                        repository = repository,
                        viewModelStoreOwner = owner,
                        origin = origin.value,
                        onClose = {
                            closeCount++
                            visible.value = false
                        },
                    )
                }
            }
        }
        compose.waitUntil(10_000) { requestedOrigins.isNotEmpty() }
        compose.waitForIdle()
    }

    private fun expectPlan(resource: Int) {
        compose.onNodeWithText(copy.getString(resource)).assertIsDisplayed()
    }

    private fun reopen(nextOrigin: String) {
        compose.runOnIdle { visible.value = false }
        compose.runOnIdle {
            origin.value = nextOrigin
            visible.value = true
        }
        compose.waitForIdle()
    }

    private fun readyReceipt(): SubscriptionCheckoutViewModel {
        val continueLabel = copy.getString(R.string.action_continue)
        if (compose.onAllNodesWithText(continueLabel).fetchSemanticsNodes().isNotEmpty()) {
            compose.onNodeWithText(continueLabel).performClick()
        }
        compose.onNodeWithText(copy.getString(R.string.sub_continue_country)).performClick()
        compose.waitForIdle()
        lateinit var model: SubscriptionCheckoutViewModel
        compose.runOnIdle {
            model = ViewModelProvider(owner).get(
                "subscription-checkout:${origin.value}", SubscriptionCheckoutViewModel::class.java,
            )
        }
        val receipt = File(context.cacheDir, "checkout-delayed-test-receipt.png")
        val bitmap = Bitmap.createBitmap(16, 16, Bitmap.Config.ARGB_8888)
        receipt.outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
        bitmap.recycle()
        try {
            compose.runOnIdle { model.selectReceipt(context, Uri.fromFile(receipt)) }
            compose.waitUntil(10_000) { model.state.value.receiptBytes > 0 }
        } finally {
            receipt.delete()
        }
        return model
    }

    private fun finishDelayedSubmit() {
        compose.runOnIdle {
            requireNotNull(submitContinuation).resume(Response.success(SubscriptionSubmitResponse(
                ok = true, paymentId = 71, status = "pending", provisionalAccess = true,
            )))
        }
        compose.waitForIdle()
    }

    @Test
    fun delayedHskReceiptResponseCannotCloseNewProCheckout() {
        origin.value = "hsk30_content"
        deferSubmit = true
        show()
        readyReceipt()
        compose.onNodeWithText(copy.getString(R.string.sub_submit)).performClick()
        compose.waitUntil(10_000) { submitContinuation != null }
        reopen("profile_subscription")
        expectPlan(R.string.sub_plan_1)

        finishDelayedSubmit()

        expectPlan(R.string.sub_plan_1)
        compose.runOnIdle {
            assertTrue(visible.value)
            assertEquals(0, closeCount)
        }
    }

    @Test
    fun delayedReceiptResponseCannotCloseReopenedHskReview() {
        origin.value = "hsk30_content"
        deferSubmit = true
        show()
        val model = readyReceipt()
        compose.onNodeWithText(copy.getString(R.string.sub_submit)).performClick()
        compose.waitUntil(10_000) { submitContinuation != null }
        pending = SubscriptionPendingDto(id = 71, planType = "hsk30_unlock", provisionalAccess = true)
        reopen("hsk30_content")
        finishDelayedSubmit()
        compose.waitUntil(10_000) { !model.state.value.loading && !model.state.value.submitting }

        compose.onNodeWithText(copy.getString(R.string.sub_hsk30_provisional_title)).assertIsDisplayed()
        compose.runOnIdle {
            assertTrue(visible.value)
            assertEquals(0, closeCount)
            assertEquals(71, model.state.value.pendingPaymentId)
        }
    }

    @Test
    fun pickerResultFromPreviousPaymentStepCannotAttachToNewQuote() {
        origin.value = "hsk30_content"
        show()
        val model = readyReceipt()
        val token = requireNotNull(model.receiptSelectionToken())
        compose.runOnIdle { model.back() }
        compose.onNodeWithText(copy.getString(R.string.sub_continue_country)).performClick()
        compose.waitForIdle()
        compose.runOnIdle {
            // A picker may return after Back and a new payment quote.
            model.selectReceipt(context, Uri.parse("file:///obsolete-picker-receipt.png"), token)
            assertEquals(0, model.state.value.receiptBytes)
            assertEquals("", model.state.value.receiptName)
            assertEquals(null, model.state.value.receiptNoteRes)
        }
        compose.onNodeWithText(copy.getString(R.string.sub_submit)).assertIsNotEnabled()
    }

    @Test
    fun reopeningProAndHskCheckoutInOneSessionKeepsTheRequestedProduct() {
        show()
        expectPlan(R.string.sub_plan_1)

        reopen("hsk30_content")
        expectPlan(R.string.sub_plan_hsk30)
        compose.onNodeWithText(copy.getString(R.string.sub_plan_1)).assertDoesNotExist()

        reopen("profile_subscription")
        expectPlan(R.string.sub_plan_1)
        compose.onNodeWithText(copy.getString(R.string.sub_plan_hsk30)).assertDoesNotExist()
        assertEquals(listOf("profile_subscription", "hsk30_content", "profile_subscription"), requestedOrigins)
    }

    @Test
    fun changingOriginWhileHostStaysVisibleLoadsTheNewModel() {
        show()
        expectPlan(R.string.sub_plan_1)
        compose.runOnIdle { origin.value = "hsk30_content" }
        compose.waitForIdle()
        expectPlan(R.string.sub_plan_hsk30)
        assertEquals(listOf("profile_subscription", "hsk30_content"), requestedOrigins)
    }

    @Test
    fun ordinaryPendingPaymentOpenedFromHskHasAWorkingReturnAction() {
        origin.value = "hsk30_content"
        pending = SubscriptionPendingDto(id = 71, planType = "1_month")
        show()

        compose.onNodeWithText(copy.getString(R.string.sub_pending_title)).assertIsDisplayed()
        compose.onNodeWithText(copy.getString(R.string.sub_payment_refresh)).assertDoesNotExist()
        compose.onNodeWithContentDescription(context.getString(R.string.action_close)).assertIsDisplayed()
        compose.onNodeWithText(copy.getString(R.string.sub_return_app)).performClick()
        compose.runOnIdle { assertEquals(1, closeCount) }
    }

    @Test
    fun existingHskProvisionalPaymentOpenedFromProfileReturnsToCourse() {
        pending = SubscriptionPendingDto(id = 71, planType = "hsk30_unlock", provisionalAccess = true)
        show()

        compose.onNodeWithText(copy.getString(R.string.sub_hsk30_provisional_title)).assertIsDisplayed()
        compose.onNode(
            hasText(copy.getString(R.string.sub_hsk30_open_course)) and hasClickAction(),
        ).performClick()
        compose.runOnIdle { assertEquals(1, closeCount) }
    }

    @Test
    fun hskReceiptAfterProCheckoutSubmitsUnlockAndReturnsWithProvisionalAccess() {
        show()
        reopen("hsk30_content")
        expectPlan(R.string.sub_plan_hsk30)

        val continueLabel = copy.getString(R.string.action_continue)
        if (compose.onAllNodesWithText(continueLabel).fetchSemanticsNodes().isNotEmpty()) {
            compose.onNodeWithText(continueLabel).performClick()
        }
        compose.onNodeWithText(copy.getString(R.string.sub_continue_country)).performClick()
        compose.waitForIdle()
        assertEquals("hsk30_unlock", quoteRequests.single().planType)

        lateinit var model: SubscriptionCheckoutViewModel
        compose.runOnIdle {
            model = ViewModelProvider(owner).get(
                "subscription-checkout:hsk30_content", SubscriptionCheckoutViewModel::class.java,
            )
        }
        val receipt = File(context.cacheDir, "checkout-test-receipt.png")
        val bitmap = Bitmap.createBitmap(16, 16, Bitmap.Config.ARGB_8888)
        receipt.outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
        bitmap.recycle()
        try {
            // The platform picker delivers this same URI to the real preparation path.
            compose.runOnIdle { model.selectReceipt(context, Uri.fromFile(receipt)) }
            compose.waitUntil(10_000) { model.state.value.receiptBytes > 0 }
            compose.onNodeWithText(copy.getString(R.string.sub_submit)).assertIsEnabled().performClick()
            compose.waitUntil(10_000) { !visible.value }

            val submitted = submitRequests.single()
            assertEquals("hsk30_unlock", submitted.planType)
            assertEquals("visa", submitted.paymentMethod)
            assertEquals("android-test-attempt-hsk30_content", submitted.attemptId)
            assertTrue(submitted.screenshotDataUrl.startsWith("data:image/"))
            compose.runOnIdle { assertEquals(1, closeCount) }
        } finally {
            receipt.delete()
        }
    }
}
