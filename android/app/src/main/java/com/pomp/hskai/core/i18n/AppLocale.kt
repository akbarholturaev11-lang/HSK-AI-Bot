package com.pomp.hskai.core.i18n

import android.content.Context
import android.content.res.Configuration
import java.util.Locale

/**
 * Makes the account's language the language on screen.
 *
 * The language is server-owned: the bot, the Mini App and this app all read it
 * from the account, and picking one here writes it there. But Android resolves
 * `values-uz` / `values-ru` / `values-tg` from the *device* locale, so until
 * now the account choice reached the lesson content and nothing else — the
 * buttons around it stayed in whatever language the phone was set to.
 *
 * Resources are chosen before the first frame, long before the account can be
 * read over the network, so the choice is mirrored into a small preference
 * file and applied in `attachBaseContext`.
 */
object AppLocale {

    private const val PREFERENCES = "pomp_app_locale"
    private const val KEY_LANGUAGE = "android_tag"

    /** The language on screen, or null while the account has never been read. */
    fun stored(context: Context): AppLanguage? {
        val tag = context
            .getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)
            .getString(KEY_LANGUAGE, null)
            ?: return null
        return AppLanguage.entries.firstOrNull { it.androidTag == tag }
    }

    /**
     * Records the account's language and reports whether the screen has to be
     * rebuilt: resources are read once per activity, so a language that
     * changed while the app is open only reaches the strings after a recreate.
     *
     * Until the first sync the activity was never wrapped, and what is on
     * screen is whatever Android resolved from the device locale — for a
     * device set to a language the app does not translate that is the default
     * resource folder, which cannot be derived from the locale. So the first
     * sync always rebuilds rather than guessing what is already showing.
     */
    fun sync(context: Context, language: AppLanguage): Boolean {
        val current = stored(context)
        context
            .getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_LANGUAGE, language.androidTag)
            .apply()
        return current != language
    }

    /** Clears the account override so unauthenticated screens follow the device locale. */
    fun clear(context: Context): Boolean {
        val hadOverride = stored(context) != null
        context
            .getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)
            .edit()
            .remove(KEY_LANGUAGE)
            .apply()
        return hadOverride
    }

    /** The context an activity should run in, in the account's language. */
    fun wrap(context: Context): Context {
        val language = stored(context) ?: return context
        val configuration = Configuration(context.resources.configuration)
        configuration.setLocale(Locale.forLanguageTag(language.androidTag))
        return context.createConfigurationContext(configuration)
    }
}
