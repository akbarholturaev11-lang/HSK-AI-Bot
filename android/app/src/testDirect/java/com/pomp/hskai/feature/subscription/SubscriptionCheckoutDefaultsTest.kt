package com.pomp.hskai.feature.subscription

import org.junit.Assert.assertEquals
import org.junit.Test

class SubscriptionCheckoutDefaultsTest {

    @Test
    fun `checkout country follows the app language by default`() {
        assertEquals("tj", defaultCheckoutCountry("tj"))
        assertEquals("uz", defaultCheckoutCountry("uz"))
        assertEquals("ru", defaultCheckoutCountry("ru"))
    }

    @Test
    fun `unknown language follows the Uzbek normalization fallback`() {
        assertEquals("uz", defaultCheckoutCountry(""))
        assertEquals("uz", defaultCheckoutCountry("de"))
    }
}
