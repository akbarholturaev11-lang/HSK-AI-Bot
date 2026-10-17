package com.pomp.hskai.core.auth

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class SignupReferralTest {
    @Test fun invitationPayloadRetainsItsTrialOrDiscountMode() {
        for (code in listOf("abcdef12", "ref_abcdef12", "ra_abcdef12", "ri_abcdef12")) {
            assertEquals(code, SignupReferral.code(" $code "))
            assertEquals(code, SignupReferral.fromUri("pomp-hsk-ai://referral/$code"))
        }
    }

    @Test fun onlyTheExactReferralDeepLinkCanPrefillSignup() {
        for (uri in listOf(
            "https://evil.example/referral/abcdef12",
            "pomp-hsk-ai://referral/abcdef12?admin=true",
            "pomp-hsk-ai://referral/abcdef12#fragment",
            "pomp-hsk-ai://referral@evil.example/abcdef12",
            "pomp-hsk-ai://referral/abcdef12/extra",
            "pomp-hsk-ai://referral/%61bcdef12",
            "pomp-hsk-ai://referral/ABCDEF12",
            "pomp-hsk-ai://referral/abcdef12\n",
        )) assertNull(uri, SignupReferral.fromUri(uri))
    }

    @Test fun malformedOrOversizedInvitationIsNotAccepted() {
        for (code in listOf("", "abc123", "x".repeat(65), "ref_ref_abcdef12", "ra_abcdef12?x=1")) {
            assertNull(code, SignupReferral.code(code))
        }
    }
}
