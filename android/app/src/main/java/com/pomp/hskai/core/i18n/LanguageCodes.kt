package com.pomp.hskai.core.i18n

import java.util.Locale

/**
 * The backend speaks `uz` / `ru` / `tj`. Android resource qualifiers are
 * `uz` / `ru` / `tg`, because Tajik is ISO 639-1 `tg`.
 *
 * This is the single place that conversion lives. `tg` must never be sent to
 * the API and `tj` must never be used as a resource folder name.
 */
enum class AppLanguage(val backendCode: String, val androidTag: String) {
    UZBEK("uz", "uz"),
    RUSSIAN("ru", "ru"),
    TAJIK("tj", "tg"),
    ;

    companion object {
        /** The backend falls back to `ru`, so the client must agree. */
        val DEFAULT = RUSSIAN

        fun fromBackendCode(value: String?): AppLanguage =
            entries.firstOrNull {
                it.backendCode.equals(value?.trim(), ignoreCase = true)
            } ?: DEFAULT

        fun fromAndroidTag(value: String?): AppLanguage {
            val tag = value?.trim()?.lowercase(Locale.ROOT)?.substringBefore('-')
            return entries.firstOrNull { it.androidTag == tag } ?: DEFAULT
        }

        /** Best guess from the device locale, used only before the first sync. */
        fun fromDeviceLocale(locale: Locale): AppLanguage =
            fromAndroidTag(locale.language)
    }
}
