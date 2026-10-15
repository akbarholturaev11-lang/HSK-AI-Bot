package com.pomp.hskai.feature.feedback

import android.graphics.Bitmap
import android.util.Base64
import android.view.View
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.core.view.drawToBitmap
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.repository.FeatureRepository
import java.io.ByteArrayOutputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Capture the current Android window BEFORE the report modal is shown. */
fun captureReportScreen(view: View): Bitmap? =
    runCatching {
        if (view.width <= 0 || view.height <= 0) null else view.drawToBitmap()
    }.getOrNull()

/**
 * A screenshot is never uploaded simply because the report was opened.
 * Only the explicitly enabled screenshot switch allows transmission.
 */
internal fun jpegReportScreenshot(bitmap: Bitmap): String? {
    if (bitmap.width <= 0 || bitmap.height <= 0) return null
    val maxSide = maxOf(bitmap.width, bitmap.height)
    val scaled = if (maxSide > 900) {
        val ratio = 900f / maxSide
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
        if (bytes.size > 550 * 1024) null
        else "data:image/jpeg;base64," + Base64.encodeToString(bytes, Base64.NO_WRAP)
    } finally {
        if (scaled !== bitmap) scaled.recycle()
    }
}

@Composable
fun BugReportDialog(
    repository: FeatureRepository,
    screenshot: Bitmap?,
    screen: String,
    onDismiss: () -> Unit,
) {
    var description by remember { mutableStateOf("") }
    var attachScreenshot by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    var failed by remember { mutableStateOf(false) }
    var sent by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    Dialog(
        onDismissRequest = { if (!busy) onDismiss() },
        properties = DialogProperties(usePlatformDefaultWidth = false),
    ) {
        Surface(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
            color = PompColors.Paper,
            shape = RoundedCornerShape(24.dp),
        ) {
            Column(
                modifier = Modifier
                    .heightIn(max = 680.dp)
                    .verticalScroll(rememberScrollState())
                    .padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        stringResource(R.string.bug_report_title),
                        style = MaterialTheme.typography.titleLarge,
                        color = PompColors.Ink,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.weight(1f),
                    )
                    TextButton(onClick = onDismiss, enabled = !busy) {
                        Text(stringResource(R.string.action_close))
                    }
                }
                if (sent) {
                    Text(stringResource(R.string.bug_report_success), color = PompColors.Ink)
                    Button(onClick = onDismiss, modifier = Modifier.fillMaxWidth()) {
                        Text(stringResource(R.string.action_close))
                    }
                } else {
                    Text(
                        stringResource(R.string.bug_report_question),
                        style = MaterialTheme.typography.titleMedium,
                        color = PompColors.Ink,
                    )
                    OutlinedTextField(
                        value = description,
                        onValueChange = { description = it.take(2000); failed = false },
                        modifier = Modifier.fillMaxWidth().heightIn(min = 165.dp),
                        placeholder = { Text(stringResource(R.string.bug_report_hint)) },
                        minLines = 4,
                        maxLines = 8,
                        supportingText = { Text("${description.length} / 2000") },
                        enabled = !busy,
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text(stringResource(R.string.bug_report_screenshot), color = PompColors.Ink)
                        Switch(
                            checked = attachScreenshot && screenshot != null,
                            onCheckedChange = { attachScreenshot = it; failed = false },
                            enabled = screenshot != null && !busy,
                        )
                    }
                    if (screenshot != null && attachScreenshot) {
                        Image(
                            bitmap = screenshot.asImageBitmap(),
                            contentDescription = stringResource(R.string.bug_report_screenshot),
                            modifier = Modifier.fillMaxWidth().height(130.dp),
                            contentScale = ContentScale.Fit,
                        )
                    }
                    Text(
                        stringResource(
                            if (screenshot == null) R.string.bug_report_no_screenshot
                            else R.string.bug_report_privacy,
                        ),
                        style = MaterialTheme.typography.bodySmall,
                        color = PompColors.InkSecondary,
                    )
                    if (failed) {
                        Text(stringResource(R.string.bug_report_failed), color = MaterialTheme.colorScheme.error)
                    }
                    Button(
                        onClick = {
                            if (busy) return@Button
                            busy = true
                            failed = false
                            scope.launch {
                                val encoded = if (attachScreenshot && screenshot != null) {
                                    withContext(Dispatchers.Default) { jpegReportScreenshot(screenshot) }
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
                        modifier = Modifier.fillMaxWidth(),
                        enabled = description.trim().length >= 5 && !busy,
                    ) {
                        if (busy) CircularProgressIndicator(
                            modifier = Modifier.height(18.dp),
                            strokeWidth = 2.dp,
                        ) else Text(stringResource(R.string.bug_report_send))
                    }
                }
            }
        }
    }
}
