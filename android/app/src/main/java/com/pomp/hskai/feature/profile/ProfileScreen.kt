package com.pomp.hskai.feature.profile

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.LinkedAccount
import com.pomp.hskai.core.design.PompColors

/**
 * Phase D scope: the account facts the server already gives us, plus the two
 * session actions that are genuinely implemented. Statistics, referral,
 * language and notification settings arrive with Phase I.
 */
@Composable
fun ProfileScreen(
    account: LinkedAccount,
    onLogout: () -> Unit,
    onUnlinkDevice: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
        ) {
            Text(
                text = account.displayName,
                style = MaterialTheme.typography.headlineMedium,
                color = PompColors.Ink,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = "${stringResource(R.string.synced_level)}: " +
                    account.level.uppercase(),
                style = MaterialTheme.typography.bodyLarge,
                color = PompColors.InkSecondary,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = stringResource(
                    if (account.isPaid) {
                        R.string.synced_access_paid
                    } else {
                        R.string.synced_access_free
                    }
                ),
                style = MaterialTheme.typography.bodyLarge,
                color = if (account.isPaid) PompColors.Jade else PompColors.InkSecondary,
            )

            Spacer(Modifier.height(32.dp))
            OutlinedButton(
                onClick = onLogout,
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 48.dp),
                shape = RoundedCornerShape(14.dp),
            ) {
                Text(
                    text = stringResource(R.string.profile_logout),
                    style = MaterialTheme.typography.labelLarge,
                    color = PompColors.Ink,
                )
            }

            Spacer(Modifier.height(12.dp))
            Text(
                text = stringResource(R.string.profile_unlink_explain),
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.InkSecondary,
            )
            Spacer(Modifier.height(8.dp))
            OutlinedButton(
                onClick = onUnlinkDevice,
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 48.dp),
                shape = RoundedCornerShape(14.dp),
            ) {
                Text(
                    text = stringResource(R.string.profile_unlink_device),
                    style = MaterialTheme.typography.labelLarge,
                    color = PompColors.CinnabarDark,
                )
            }
        }
    }
}
