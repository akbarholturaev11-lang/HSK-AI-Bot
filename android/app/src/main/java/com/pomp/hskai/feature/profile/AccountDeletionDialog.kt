package com.pomp.hskai.feature.profile

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle

@Composable
internal fun AccountDeletionDialog(
    state: AccountDeletionUiState,
    onConfirm: () -> Unit,
    onRetry: () -> Unit,
    onOpenWeb: () -> Unit,
    onDismiss: () -> Unit,
) {
    val receipt = state.receipt
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = PompColors.Paper,
        title = {
            Text(stringResource(if (receipt == null) R.string.profile_delete_account else R.string.account_deletion_received))
        },
        text = {
            Column(
                modifier = Modifier.heightIn(max = 400.dp).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                when {
                    receipt != null -> {
                        Text(stringResource(R.string.account_deletion_submitted))
                        Text(
                            stringResource(R.string.account_deletion_request_id, receipt.requestId),
                            modifier = Modifier.testTag("accountDeletionReceipt"),
                        )
                        Text(stringResource(R.string.account_deletion_due, deletionDate(receipt.dueAt)))
                        Text(stringResource(R.string.account_deletion_retention))
                    }
                    state.isPreparing -> {
                        CircularProgressIndicator()
                        Text(stringResource(R.string.account_deletion_verifying))
                    }
                    else -> {
                        state.accountLabel?.let { Text(stringResource(R.string.account_deletion_account, it)) }
                        Text(stringResource(R.string.account_deletion_scope))
                        Text(stringResource(R.string.account_deletion_retention))
                    }
                }
                state.error?.let { Text(stringResource(it.messageRes), color = PompColors.CinnabarInk) }
                if (state.isSubmitting) {
                    CircularProgressIndicator()
                    Text(stringResource(R.string.account_deletion_submitting))
                }
                TextButton(onClick = onOpenWeb, enabled = !state.isSubmitting) {
                    Text(stringResource(R.string.account_deletion_open_web))
                }
            }
        },
        confirmButton = {
            when {
                receipt != null -> TextButton(onClick = onDismiss) { Text(stringResource(R.string.hsk_common_action_close)) }
                state.accountLabel == null && state.error != null -> TextButton(onClick = onRetry) {
                    Text(stringResource(R.string.hsk_course_lesson_flow_retry))
                }
                else -> TextButton(
                    onClick = onConfirm,
                    enabled = state.canConfirm,
                    modifier = Modifier.testTag("accountDeletionConfirm"),
                ) { Text(stringResource(R.string.account_deletion_confirm)) }
            }
        },
        dismissButton = {
            if (receipt == null) TextButton(onClick = onDismiss, enabled = !state.isSubmitting) {
                Text(stringResource(R.string.action_cancel))
            }
        },
    )
}

private fun deletionDate(raw: String): String = runCatching {
    OffsetDateTime.parse(raw).toLocalDate().format(DateTimeFormatter.ofLocalizedDate(FormatStyle.MEDIUM))
}.getOrDefault(raw.take(10))
