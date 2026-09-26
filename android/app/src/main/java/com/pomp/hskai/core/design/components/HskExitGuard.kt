package com.pomp.hskai.core.design.components

import androidx.activity.compose.BackHandler
import androidx.annotation.StringRes
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.res.stringResource
import com.pomp.hskai.R

/**
 * The way out of a lesson or an exercise, for its ✕ and the system back alike.
 *
 * These screens are state inside one activity, not destinations of their own,
 * so Android's back used to fall straight through them and close the whole
 * app mid-lesson. While [running], both ways out ask first and only «Chiqish»
 * leaves. Once the run is over — a result, an error, a loader — back simply
 * leaves, the same as the ✕.
 *
 * Returns what the screen's own ✕ should call.
 */
@Composable
fun rememberExitGuard(
    running: Boolean,
    @StringRes title: Int,
    @StringRes body: Int,
    onExit: () -> Unit,
): () -> Unit {
    var asking by remember { mutableStateOf(false) }
    val exit by rememberUpdatedState(onExit)
    val isRunning by rememberUpdatedState(running)
    val request: () -> Unit = remember {
        {
            if (isRunning) {
                asking = true
            } else {
                exit()
            }
        }
    }

    // A run that ends while the question is open (the last answer landed)
    // takes the question with it rather than leaving it for the next run.
    LaunchedEffect(running) { if (!running) asking = false }

    BackHandler(onBack = request)

    if (asking && running) {
        AlertDialog(
            onDismissRequest = { asking = false },
            title = { Text(stringResource(title)) },
            text = { Text(stringResource(body)) },
            confirmButton = {
                TextButton(onClick = { asking = false }) {
                    Text(stringResource(R.string.exit_confirm_stay))
                }
            },
            dismissButton = {
                TextButton(
                    onClick = {
                        asking = false
                        exit()
                    },
                ) {
                    Text(stringResource(R.string.exit_confirm_leave))
                }
            },
        )
    }
    return request
}
