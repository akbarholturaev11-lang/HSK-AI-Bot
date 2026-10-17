package com.pomp.hskai.core.auth

/** Invitation metadata only. The server decides attribution after proving a new account. */
object SignupReferral {
    private val codeFormat = Regex("^(?:ref_|r[ai]_)?[0-9a-f]{8}$")
    private val uriFormat = Regex("^pomp-hsk-ai://referral/((?:ref_|r[ai]_)?[0-9a-f]{8})$")

    fun code(raw: String?): String? = raw?.trim()?.takeIf(codeFormat::matches)

    /** Exact path, no query, fragments, credentials, escaping or extra segments. */
    fun fromUri(raw: String?): String? = uriFormat.matchEntire(raw.orEmpty())?.groupValues?.get(1)
}
