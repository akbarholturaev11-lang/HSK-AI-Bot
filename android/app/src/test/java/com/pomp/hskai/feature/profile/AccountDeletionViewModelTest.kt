package com.pomp.hskai.feature.profile

import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AccountDeletionApi
import com.pomp.hskai.data.api.AccountDeletionConfirmation
import com.pomp.hskai.data.api.AccountDeletionPrepared
import com.pomp.hskai.data.api.AccountDeletionReceipt
import com.pomp.hskai.data.repository.AccountDeletionRepository
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlinx.serialization.json.JsonObject
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class AccountDeletionViewModelTest {
    private val dispatcher = StandardTestDispatcher()
    @Before fun setUp() = Dispatchers.setMain(dispatcher)
    @After fun tearDown() = Dispatchers.resetMain()

    private class FakeDeletionApi : AccountDeletionApi {
        var prepares = 0
        var confirmations = 0
        var prepareReply = CompletableDeferred<Response<AccountDeletionPrepared>>()
        var confirmReply = CompletableDeferred<Response<AccountDeletionReceipt>>()
        override suspend fun prepare(authorization: String, body: JsonObject): Response<AccountDeletionPrepared> {
            prepares++
            return prepareReply.await()
        }
        override suspend fun confirm(body: AccountDeletionConfirmation): Response<AccountDeletionReceipt> {
            confirmations++
            assertEquals("DELETE", body.confirmation)
            return confirmReply.await()
        }
    }

    private fun model(api: FakeDeletionApi) = AccountDeletionViewModel(
        AccountDeletionRepository(api, { ApiResult.Success("session") }),
    )

    @Test fun `opening verifies ownership without submitting and confirm ignores repeated taps`() = runTest(dispatcher) {
        val api = FakeDeletionApi()
        val vm = model(api)
        vm.open()
        vm.open()
        vm.confirm()
        runCurrent()
        assertEquals(1, api.prepares)
        assertEquals(0, api.confirmations)
        assertTrue(vm.state.value.isPreparing)
        api.prepareReply.complete(Response.success(prepared()))
        runCurrent()
        assertTrue(vm.state.value.canConfirm)
        assertNull(vm.state.value.receipt)
        vm.confirm()
        vm.confirm()
        vm.dismiss()
        runCurrent()
        assertEquals(1, api.confirmations)
        assertTrue(vm.state.value.isOpen)
        assertTrue(vm.state.value.isSubmitting)
        api.confirmReply.complete(Response.success(receipt()))
        runCurrent()
        assertEquals("submitted", vm.state.value.receipt?.status)
        assertFalse(vm.state.value.canConfirm)
        vm.dismiss()
        vm.open()
        runCurrent()
        assertTrue(vm.state.value.isOpen)
        assertEquals(requestId, vm.state.value.receipt?.requestId)
        assertEquals(1, api.prepares)
        assertEquals(1, api.confirmations)
    }

    @Test fun `late verification cannot reopen a dismissed dialog or allow a stale confirmation`() = runTest(dispatcher) {
        val api = FakeDeletionApi()
        val vm = model(api)
        vm.open()
        runCurrent()
        vm.dismiss()
        api.prepareReply.complete(Response.success(prepared()))
        runCurrent()
        vm.confirm()
        runCurrent()
        assertFalse(vm.state.value.isOpen)
        assertNull(vm.state.value.accountLabel)
        assertEquals(0, api.confirmations)
    }

    @Test fun `failed confirmation keeps the receipt absent and permits an explicit retry`() = runTest(dispatcher) {
        val api = FakeDeletionApi()
        api.prepareReply.complete(Response.success(prepared()))
        val vm = model(api)
        vm.open()
        runCurrent()
        vm.confirm()
        runCurrent()
        api.confirmReply.complete(Response.error(503, "unavailable".toResponseBody()))
        runCurrent()
        assertNull(vm.state.value.receipt)
        assertTrue(vm.state.value.canConfirm)
        assertTrue(vm.state.value.error != null)
        api.confirmReply = CompletableDeferred(Response.success(receipt()))
        vm.confirm()
        runCurrent()
        assertEquals(2, api.confirmations)
        assertEquals(requestId, vm.state.value.receipt?.requestId)
    }

    @Test fun `expired ownership requires a fresh prepare rather than retrying the stale proof`() = runTest(dispatcher) {
        val api = FakeDeletionApi()
        api.prepareReply.complete(Response.success(prepared()))
        val vm = model(api)
        vm.open()
        runCurrent()
        vm.confirm()
        runCurrent()
        api.confirmReply.complete(Response.error(410,
            """{"ok":false,"error":"deletion_expired"}""".toResponseBody()))
        runCurrent()
        assertFalse(vm.state.value.canConfirm)
        assertNull(vm.state.value.accountLabel)
        vm.confirm()
        runCurrent()
        assertEquals(1, api.confirmations)
        api.prepareReply = CompletableDeferred(Response.success(prepared()))
        vm.open()
        runCurrent()
        assertEquals(2, api.prepares)
        assertTrue(vm.state.value.canConfirm)
    }

    companion object {
        private const val requestId = "806c055a-4c34-4aee-b06f-2c27a6080096"
        private fun prepared() = AccountDeletionPrepared(true, requestId, "s".repeat(43), "verified", "Google learner")
        private fun receipt() = AccountDeletionReceipt(true, "submitted", requestId, "2026-10-15T12:00:00Z", "2026-11-14T12:00:00Z")
    }
}
