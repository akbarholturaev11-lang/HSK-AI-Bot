package com.pomp.hskai.feature.subscription

import androidx.compose.runtime.Composable
import androidx.lifecycle.ViewModelStoreOwner
import com.pomp.hskai.data.repository.FeatureRepository

/** There is no manual checkout in the Play distribution. */
@Composable
fun SubscriptionCheckoutHost(
    repository: FeatureRepository,
    viewModelStoreOwner: ViewModelStoreOwner,
    origin: String,
    onClose: () -> Unit,
) = Unit
