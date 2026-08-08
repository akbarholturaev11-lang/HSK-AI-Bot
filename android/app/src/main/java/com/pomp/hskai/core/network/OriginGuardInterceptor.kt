package com.pomp.hskai.core.network

import java.io.IOException
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.Interceptor
import okhttp3.Response

/**
 * Refuses to send anything anywhere except the compile-time API origin.
 *
 * This mirrors the desktop client's allowlisted origin: a redirect or a
 * server-supplied URL can never make the app attach `Authorization` to a
 * third-party host, and cleartext HTTP is impossible.
 */
class OriginGuardInterceptor(allowedOrigin: String) : Interceptor {

    private val allowed: HttpUrl = requireNotNull(allowedOrigin.toHttpUrlOrNull()) {
        "API_ORIGIN is not a valid URL: $allowedOrigin"
    }

    override fun intercept(chain: Interceptor.Chain): Response {
        if (!chain.request().url.isAllowed()) {
            throw IOException("Blocked request to a non-allowlisted origin")
        }
        return chain.proceed(chain.request())
    }

    private fun HttpUrl.isAllowed(): Boolean =
        scheme == "https" &&
            host.equals(allowed.host, ignoreCase = true) &&
            port == allowed.port
}
