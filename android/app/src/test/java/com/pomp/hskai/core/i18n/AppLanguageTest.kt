package com.pomp.hskai.core.i18n

import java.util.Locale
import org.junit.Assert.assertEquals
import org.junit.Test

class AppLanguageTest {

    @Test
    fun `tajik uses tj on the backend and tg on android`() {
        assertEquals("tj", AppLanguage.TAJIK.backendCode)
        assertEquals("tg", AppLanguage.TAJIK.androidTag)
    }

    @Test
    fun `backend codes map to the right language`() {
        assertEquals(AppLanguage.UZBEK, AppLanguage.fromBackendCode("uz"))
        assertEquals(AppLanguage.RUSSIAN, AppLanguage.fromBackendCode("ru"))
        assertEquals(AppLanguage.TAJIK, AppLanguage.fromBackendCode("tj"))
        assertEquals(AppLanguage.TAJIK, AppLanguage.fromBackendCode(" TJ "))
    }

    @Test
    fun `android tg tag resolves to tajik but is never a backend code`() {
        assertEquals(AppLanguage.TAJIK, AppLanguage.fromAndroidTag("tg"))
        assertEquals(AppLanguage.TAJIK, AppLanguage.fromAndroidTag("tg-TJ"))
        // "tg" must never be accepted as a backend value.
        assertEquals(AppLanguage.DEFAULT, AppLanguage.fromBackendCode("tg"))
    }

    @Test
    fun `unknown values fall back to the backend default`() {
        assertEquals(AppLanguage.RUSSIAN, AppLanguage.DEFAULT)
        assertEquals(AppLanguage.DEFAULT, AppLanguage.fromBackendCode(null))
        assertEquals(AppLanguage.DEFAULT, AppLanguage.fromBackendCode("en"))
        assertEquals(AppLanguage.DEFAULT, AppLanguage.fromAndroidTag("fr"))
        assertEquals(AppLanguage.DEFAULT, AppLanguage.fromDeviceLocale(Locale.FRANCE))
    }

    @Test
    fun `device locale maps tajik and uzbek`() {
        assertEquals(AppLanguage.TAJIK, AppLanguage.fromDeviceLocale(Locale("tg", "TJ")))
        assertEquals(AppLanguage.UZBEK, AppLanguage.fromDeviceLocale(Locale("uz", "UZ")))
    }
}
