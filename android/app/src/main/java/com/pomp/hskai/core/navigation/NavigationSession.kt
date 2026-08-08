package com.pomp.hskai.core.navigation

import androidx.lifecycle.ViewModelStore
import androidx.lifecycle.ViewModelStoreOwner

/** One delivery of an allowlisted destination, including repeated identical URIs. */
internal data class DestinationRequest(
    val id: String,
    val destination: AppDestination,
)

/** Prevents an automatic refresh loop without suppressing a newly delivered link. */
internal class DeepLinkRefreshGate {
    private var attemptedRequestId: String? = null

    fun claim(requestId: String): Boolean {
        if (requestId == attemptedRequestId) return false
        attemptedRequestId = requestId
        return true
    }

    fun reset() {
        attemptedRequestId = null
    }
}

/**
 * Owns ViewModels for one auth branch only.
 *
 * Clearing this store stops link polling, course requests and lesson state as
 * soon as the user leaves that branch, so another account cannot reuse them.
 */
internal class SessionViewModelStoreOwner : ViewModelStoreOwner {
    override val viewModelStore = ViewModelStore()

    fun clear() {
        viewModelStore.clear()
    }
}
