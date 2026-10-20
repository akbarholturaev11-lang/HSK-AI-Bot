package com.pomp.hskai.feature.profile

import com.pomp.hskai.core.auth.AuthProvider
import com.pomp.hskai.core.auth.LinkedIdentity
import com.pomp.hskai.core.network.ApiError
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class ProfilePromoCarouselTest {
    private fun identity(provider: AuthProvider) = LinkedIdentity(provider.wire, provider, null, null)
    private val loaded = IdentitiesUiState(hasLoaded = true, available = listOf(AuthProvider.GOOGLE, AuthProvider.APPLE))

    @Test fun eachUnlinkedConfiguredMethodGetsItsOwnCard() {
        assertEquals(listOf(ProfilePromoPage.HSK30, ProfilePromoPage.PRO,
            ProfilePromoPage.TELEGRAM, ProfilePromoPage.GOOGLE, ProfilePromoPage.APPLE), profilePromoPages(true, loaded))
    }

    @Test fun aTelegramAccountOnlySeesTheUnlinkedGoogleAndAppleCards() {
        assertEquals(listOf(ProfilePromoPage.HSK30, ProfilePromoPage.GOOGLE, ProfilePromoPage.APPLE),
            profilePromoPages(false, loaded.copy(telegramLinked = true)))
    }

    @Test fun providerOnlyAccountsSeeTelegramAndTheOtherConfiguredProvider() {
        assertEquals(listOf(ProfilePromoPage.HSK30, ProfilePromoPage.TELEGRAM, ProfilePromoPage.APPLE),
            profilePromoPages(false, loaded.copy(identities = listOf(identity(AuthProvider.GOOGLE)))))
        assertEquals(listOf(ProfilePromoPage.HSK30, ProfilePromoPage.TELEGRAM, ProfilePromoPage.GOOGLE),
            profilePromoPages(false, loaded.copy(identities = listOf(identity(AuthProvider.APPLE)))))
    }

    @Test fun allLinkedMethodsLeaveOnlyTheOriginalPromos() {
        assertEquals(listOf(ProfilePromoPage.HSK30, ProfilePromoPage.PRO), profilePromoPages(true,
            loaded.copy(telegramLinked = true, identities = listOf(identity(AuthProvider.GOOGLE), identity(AuthProvider.APPLE)))))
    }

    @Test fun unknownLoadingAndErrorStatesNeverGuessAnUnlinkedIdentity() {
        for (state in listOf(IdentitiesUiState(), loaded.copy(isLoading = true),
            loaded.copy(error = ApiError.Offline), loaded.copy(hasLoaded = false))) {
            assertEquals(listOf(ProfilePromoPage.HSK30), profilePromoPages(false, state))
        }
    }

    @Test fun disabledProvidersAreNotAdvertisedEvenWhenTheirMethodsAreUnlinked() {
        assertEquals(listOf(ProfilePromoPage.HSK30, ProfilePromoPage.TELEGRAM),
            profilePromoPages(false, loaded.copy(available = emptyList())))
    }

    @Test fun playNeverGetsAProPurchaseOrTrialCardButKeepsAccountLinks() {
        val pages = profilePromoPages(false, loaded)
        assertFalse(ProfilePromoPage.PRO in pages)
        assertEquals(setOf(AuthProvider.TELEGRAM, AuthProvider.GOOGLE, AuthProvider.APPLE),
            pages.mapNotNull { it.provider }.toSet())
    }
}
