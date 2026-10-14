package com.pomp.hskai.feature.subscription

import androidx.compose.runtime.Composable
import androidx.lifecycle.ViewModelStoreOwner
import com.pomp.hskai.data.repository.FeatureRepository

/**
 * Temporary consumption-only Play checkout host.
 *
 * Future Play-native subscription and HSK 3.0 purchase flows belong here,
 * using Google Play Billing and server-verified entitlements. Do not reuse the
 * direct APK bank/manual checkout or add external payment steering to Play.
 * The shared function signature must remain compatible with the direct host.
 */
@Composable
fun SubscriptionCheckoutHost(
    repository: FeatureRepository,
    viewModelStoreOwner: ViewModelStoreOwner,
    origin: String,
    onClose: () -> Unit,
) = Unit
