package com.pomp.hskai.core.navigation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotSame
import org.junit.Assert.assertTrue
import org.junit.Test

class NavigationSessionTest {

    @Test
    fun `same deep link can refresh again when it is delivered as a new request`() {
        val gate = DeepLinkRefreshGate()
        val first = DestinationRequest("request-1", AppDestination.Lesson(7))
        val repeated = DestinationRequest("request-2", AppDestination.Lesson(7))

        assertTrue(gate.claim(first.id))
        assertFalse(gate.claim(first.id))
        assertTrue(gate.claim(repeated.id))
    }

    @Test
    fun `auth sessions own and clear separate view models`() {
        val firstOwner = SessionViewModelStoreOwner()
        val secondOwner = SessionViewModelStoreOwner()
        val factory = TrackingViewModelFactory()
        val first = ViewModelProvider(firstOwner, factory)[TrackingViewModel::class.java]
        val second = ViewModelProvider(secondOwner, factory)[TrackingViewModel::class.java]

        assertNotSame(first, second)
        firstOwner.clear()

        assertTrue(first.cleared)
        assertFalse(second.cleared)
        secondOwner.clear()
        assertTrue(second.cleared)
    }
}

private class TrackingViewModel : ViewModel() {
    var cleared = false

    override fun onCleared() {
        cleared = true
    }
}

private class TrackingViewModelFactory : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T = TrackingViewModel() as T
}
