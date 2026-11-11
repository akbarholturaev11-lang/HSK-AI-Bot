package com.pomp.hskai.feature.subscription

import androidx.compose.material3.Text
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.lifecycle.ViewModelStore
import androidx.lifecycle.ViewModelStoreOwner
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.network.ApiResult
import kotlinx.coroutines.CompletableDeferred
import org.junit.Rule
import org.junit.Test
import org.junit.Assert.assertTrue
import retrofit2.Response
import kotlin.math.abs

class NativeLavaCheckoutTest {
    @get:Rule val compose=createComposeRule()
    private class Fake: AndroidLavaApi {
        val reply=CompletableDeferred<Response<LavaOverview>>()
        override suspend fun providerOverview(auth:String,body:LavaContext)=reply.await()
        override suspend fun start(auth:String,body:LavaStart):Response<LavaReply> = error("No real purchase in UI tests")
        override suspend fun status(auth:String,body:LavaId)=Response.success(LavaReply(ok=true,status="pending"))
        override suspend fun cancel(auth:String,body:Map<String,String>)=Response.success(LavaReply(ok=true))
        override suspend fun exitOffer(auth:String,body:ExitAction)=Response.success(ExitReply(ok=true))
    }
    private fun show(api: Fake) {
        val owner=object:ViewModelStoreOwner { override val viewModelStore=ViewModelStore() }
        val repository=LavaCheckoutRepository(api,{ ApiResult.Success("synthetic") })
        compose.setContent { PompHskAiTheme { if (!NativeLavaCheckout(owner,"course_limit",{},repository)) Text("Manual fallback") } }
    }
    @Test fun primaryPlanAndEmailGeometryStayStableWhenServerPricesArrive() {
        val api=Fake(); show(api)
        val plans=compose.onNodeWithTag("provider-plans").fetchSemanticsNode().boundsInRoot
        val email=compose.onNodeWithTag("provider-email").fetchSemanticsNode().boundsInRoot
        api.reply.complete(Response.success(LavaOverview(true,LavaBlock(mode="both",plans=listOf(
            LavaPlan("1_month",1,30,"10.00","USD"), LavaPlan("3_months",3,90,"27.00","USD"),
            LavaPlan("6_months",6,180,"50.00","USD"), LavaPlan("12_months",12,365,"90.00","USD"))))))
        compose.waitUntil(5000) { compose.onAllNodesWithText("10.00 USD").fetchSemanticsNodes().isNotEmpty() }
        val readyPlans=compose.onNodeWithTag("provider-plans").fetchSemanticsNode().boundsInRoot
        val readyEmail=compose.onNodeWithTag("provider-email").fetchSemanticsNode().boundsInRoot
        assertTrue(abs(plans.top-readyPlans.top)<2f && abs(plans.height-readyPlans.height)<2f)
        assertTrue(abs(email.top-readyEmail.top)<2f)
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        compose.onNodeWithText(context.getString(R.string.lava_other_plans)).performClick()
        compose.onNodeWithText(context.getString(R.string.lava_months,6)+" · 50.00 USD").assertExists()
        compose.onNodeWithText(context.getString(R.string.lava_manual)).assertExists()
    }
    @Test fun disabledProviderKeepsExistingNativeManualCheckout() {
        val api=Fake(); show(api)
        api.reply.complete(Response.success(LavaOverview(ok=true)))
        compose.waitUntil(5000) { compose.onAllNodesWithText("Manual fallback").fetchSemanticsNodes().isNotEmpty() }
        compose.onNodeWithText("Manual fallback").assertIsDisplayed()
    }
}
