package com.pomp.hskai.feature.feedback

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.util.Base64
import android.view.WindowManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.window.DialogWindowProvider
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.repository.FeatureRepository
import java.io.ByteArrayOutputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Screenshot is local until the user explicitly taps Send; never auto-submit. */
internal fun jpegReportScreenshot(bitmap: Bitmap): String? {
    if (bitmap.width <= 0 || bitmap.height <= 0) return null
    val longest = maxOf(bitmap.width, bitmap.height)
    val scaled = if (longest > 900) {
        val ratio = 900f / longest
        Bitmap.createScaledBitmap(
            bitmap,
            (bitmap.width * ratio).toInt().coerceAtLeast(1),
            (bitmap.height * ratio).toInt().coerceAtLeast(1),
            true,
        )
    } else bitmap
    return try {
        val bytes = ByteArrayOutputStream().use { stream ->
            scaled.compress(Bitmap.CompressFormat.JPEG, 60, stream)
            stream.toByteArray()
        }
        if (bytes.isEmpty() || bytes.size > 550 * 1024) null
        else "data:image/jpeg;base64," + Base64.encodeToString(bytes, Base64.NO_WRAP)
    } finally {
        if (scaled !== bitmap) scaled.recycle()
    }
}

/** User-selected screenshot fallback when a device denies direct window capture. */
private fun readScreenshot(context: android.content.Context, uri: Uri): Bitmap? =
    runCatching {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        context.contentResolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, bounds)
        }
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return@runCatching null
        val sample = BitmapFactory.Options().apply {
            var factor = 1
            while (maxOf(bounds.outWidth, bounds.outHeight) / factor > 1500) factor *= 2
            inSampleSize = factor
        }
        context.contentResolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, sample)
        }
    }.getOrNull()

@Composable
fun BugReportDialog(
    repository: FeatureRepository,
    screenshot: Bitmap?,
    screen: String,
    onDismiss: () -> Unit,
    initialDescription: String = "",
) {
    var description by remember(initialDescription) { mutableStateOf(initialDescription.take(2000)) }
    // Preserve the existing bug-report default (screenshot ON, with a picker
    // fallback if capture failed). Only explicit AI-content reports are text-first.
    val aiContentReport = screen == "ai_assistant" || screen == "ai_voice"
    var attachScreenshot by remember(screen) { mutableStateOf(!aiContentReport) }
    var preview by remember(screenshot) { mutableStateOf(screenshot) }
    var busy by remember { mutableStateOf(false) }
    var failed by remember { mutableStateOf(false) }
    var missingScreenshot by remember { mutableStateOf(false) }
    var sent by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    val focusManager = LocalFocusManager.current
    val keyboardController = LocalSoftwareKeyboardController.current
    LaunchedEffect(sent) {
        if (sent) {
            focusManager.clearFocus(force = true)
            keyboardController?.hide()
        }
    }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) {
            preview = readScreenshot(context, uri)
            missingScreenshot = preview == null
        }
    }

    Dialog(
        onDismissRequest = { if (!busy) onDismiss() },
        properties = DialogProperties(
            usePlatformDefaultWidth = false,
            decorFitsSystemWindows = false,
        ),
    ) {
        val dialogView = LocalView.current
        DisposableEffect(dialogView) {
            val window = (dialogView.parent as? DialogWindowProvider)?.window
            window?.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE)
            onDispose { }
        }

        // The keyboard shrinks the available content area; only the fields
        // scroll. The Send button is outside that scroll area and stays visible.
        Box(
            modifier = Modifier.fillMaxSize().statusBarsPadding()
                .navigationBarsPadding().imePadding(),
            contentAlignment = Alignment.Center,
        ) {
            Surface(
                modifier = Modifier.fillMaxWidth(0.96f).fillMaxHeight(0.94f),
                color = PompColors.Paper,
                shape = RoundedCornerShape(24.dp),
            ) {
                Column {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(
                            start = 18.dp, end = 12.dp, top = 16.dp, bottom = 8.dp,
                        ),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            stringResource(
                                if (aiContentReport) R.string.assistant_report_answer
                                else R.string.bug_report_title,
                            ),
                            style = MaterialTheme.typography.titleLarge,
                            color = PompColors.Ink,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.weight(1f),
                        )
                        TextButton(onClick = onDismiss, enabled = !busy) {
                            Text(stringResource(R.string.hsk_common_action_close))
                        }
                    }
                    Column(
                            modifier = Modifier.weight(1f)
                                .verticalScroll(rememberScrollState())
                                .padding(horizontal = 18.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            Text(
                                stringResource(R.string.bug_report_question),
                                style = MaterialTheme.typography.titleMedium,
                                color = PompColors.Ink,
                            )
                            OutlinedTextField(
                                value = description,
                                onValueChange = { description = it.take(2000); failed = false },
                                modifier = Modifier.fillMaxWidth(),
                                placeholder = { Text(stringResource(R.string.bug_report_hint)) },
                                minLines = 3,
                                maxLines = 6,
                                supportingText = { Text("${description.length} / 2000") },
                                enabled = !busy,
                            )
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                Text(
                                    stringResource(R.string.bug_report_screenshot),
                                    color = PompColors.Ink,
                                )
                                Switch(
                                    checked = attachScreenshot,
                                    onCheckedChange = {
                                        attachScreenshot = it
                                        missingScreenshot = false
                                    },
                                    enabled = !busy,
                                )
                            }
                            if (attachScreenshot) {
                                if (preview != null) {
                                    Image(
                                        bitmap = preview!!.asImageBitmap(),
                                        contentDescription = stringResource(R.string.bug_report_screenshot),
                                        modifier = Modifier.fillMaxWidth().height(112.dp),
                                        contentScale = ContentScale.Fit,
                                    )
                                } else {
                                    Text(
                                        stringResource(R.string.bug_report_no_screenshot),
                                        style = MaterialTheme.typography.bodySmall,
                                        color = PompColors.InkSecondary,
                                    )
                                    OutlinedButton(
                                        onClick = { picker.launch("image/*") },
                                        enabled = !busy,
                                    ) {
                                        Text(stringResource(R.string.bug_report_pick_screenshot))
                                    }
                                }
                                Text(
                                    stringResource(R.string.bug_report_privacy),
                                    style = MaterialTheme.typography.bodySmall,
                                    color = PompColors.InkSecondary,
                                )
                            }
                            if (missingScreenshot) {
                                Text(
                                    stringResource(R.string.bug_report_screenshot_required),
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.error,
                                )
                            }
                            if (failed) {
                                Text(
                                    stringResource(R.string.bug_report_failed),
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.error,
                                )
                            }
                        }
                    HorizontalDivider(color = PompColors.Divider)
                    Button(
                        onClick = {
                            if (busy) return@Button
                            if (sent) return@Button
                            if (attachScreenshot && preview == null) {
                                missingScreenshot = true
                                return@Button
                            }
                            busy = true
                            failed = false
                            scope.launch {
                                val encoded = if (attachScreenshot && preview != null) {
                                    withContext(Dispatchers.Default) { jpegReportScreenshot(preview!!) }
                                } else ""
                                if (attachScreenshot && encoded == null) {
                                    busy = false
                                    failed = true
                                    return@launch
                                }
                                val response = repository.sendBugReport(
                                    description = description.trim(),
                                    screenshotDataUrl = encoded.orEmpty(),
                                    screen = screen,
                                )
                                sent = response is ApiResult.Success && response.value.ok
                                failed = !sent
                                busy = false
                            }
                        },
                        modifier = Modifier.fillMaxWidth().padding(
                            start = 18.dp, end = 18.dp, top = 12.dp, bottom = 14.dp,
                        ).heightIn(min = 52.dp),
                        enabled = !sent && description.trim().length >= 5 && !busy,
                    ) {
                        if (busy) {
                            CircularProgressIndicator(
                                modifier = Modifier.height(18.dp),
                                strokeWidth = 2.dp,
                            )
                        } else Text(
                            stringResource(R.string.bug_report_send)
                        )
                    }
                }
            }
        }
    }
    if (sent) {
        AlertDialog(
            onDismissRequest = { /* Explicit acknowledgement keeps OK predictable. */ },
            title = {
                Text(
                    text = stringResource(R.string.bug_report_thanks_title),
                    modifier = Modifier.fillMaxWidth(),
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                    color = PompColors.Ink,
                )
            },
            confirmButton = {
                Button(onClick = onDismiss, modifier = Modifier.fillMaxWidth()) {
                    Text("OK")
                }
            },
            containerColor = PompColors.PaperRaised,
            shape = RoundedCornerShape(28.dp),
        )
    }
}
