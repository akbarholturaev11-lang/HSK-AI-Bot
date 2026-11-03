package com.pomp.hskai.core.i18n

import android.content.Context
import android.content.res.Configuration
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import java.util.Locale
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AppLocaleSyncTest {
    private val base = InstrumentationRegistry.getInstrumentation().targetContext
    private val prefs = base.getSharedPreferences("pomp_app_locale", Context.MODE_PRIVATE)
    private var saved: Map<String, *> = emptyMap<String, Any>()
    @Before fun isolateLanguagePreferences() { saved = prefs.all; prefs.edit().clear().commit() }
    @After fun restoreLanguagePreferences() {
        prefs.edit().clear().apply {
            saved.forEach { (key, value) -> when(value) {
                is String -> putString(key, value)
                is Boolean -> putBoolean(key, value)
            } }
        }.commit()
    }
    private fun localized(tag: String) = base.createConfigurationContext(Configuration(base.resources.configuration).apply {
        setLocale(Locale.forLanguageTag(tag))
    })
    @Test fun firstLoginDoesNotRecreateAnAlreadyMatchingSupportedActivity() {
        val context = localized("ru")
        assertFalse(AppLocale.sync(context, AppLanguage.RUSSIAN))
        assertEquals(AppLanguage.RUSSIAN, AppLocale.stored(context))
        assertFalse(AppLocale.sync(context, AppLanguage.RUSSIAN))
    }
    @Test fun aDifferentAccountLanguageStillRequiresTheActivityToRebuild() {
        val context = localized("ru")
        assertTrue(AppLocale.sync(context, AppLanguage.TAJIK))
        val rebuilt = AppLocale.wrap(context)
        assertEquals("tg", rebuilt.resources.configuration.locales[0].language)
        assertFalse(AppLocale.sync(rebuilt, AppLanguage.TAJIK))
    }
    @Test fun unsupportedActivityLocaleKeepsTheConservativeFirstSyncRebuild() {
        assertTrue(AppLocale.sync(localized("en"), AppLanguage.UZBEK))
    }
}
