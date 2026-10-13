package com.pomp.hskai.feature.limit

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.LockOpen
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.pomp.hskai.R

/**
 * The same limit-only bottom sheet as Telegram Mini App.
 * Permission, limits and the purchase channel remain server-controlled.
 * No trial button or payment footnote is rendered here.
 */
@Composable
fun SectionLimitOverlay(
    sectionTitle: String,
    sourceKey: String,
    limit: LimitGate,
    onClose: () -> Unit,
    modifier: Modifier = Modifier,
    reason: String? = null,
    resetAt: String? = null,
) {
    DisposableEffect(Unit) {
        limit.actions.onPresented()
        onDispose { limit.actions.onDismissed() }
    }

    val copy = limitOfferCopy(sourceKey)
    val title = stringResource(copy.first)
    val description = stringResource(copy.second)
    val heading = stringResource(R.string.limit_sheet_heading)
    val canSubscribe = limit.state.canSubscribe
    val actionLabel = if (canSubscribe) {
        stringResource(R.string.limit_sheet_get_pro)
    } else {
        // The Play build must not link users to an external checkout.
        stringResource(R.string.limit_sheet_check_access)
    }

    Dialog(
        onDismissRequest = onClose,
        properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false),
    ) {
        Box(
            modifier = modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.56f)),
            contentAlignment = Alignment.BottomCenter,
        ) {
            Surface(
                modifier = Modifier.fillMaxWidth().heightIn(max = 760.dp),
                shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp),
                color = Color(0xFFFFFDF7),
                shadowElevation = 20.dp,
            ) {
                Column(
                    modifier = Modifier.fillMaxWidth()
                        .verticalScroll(rememberScrollState())
                        .navigationBarsPadding()
                        .padding(start = 20.dp, end = 20.dp, top = 12.dp, bottom = 20.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(13.dp),
                ) {
                    Box(Modifier.fillMaxWidth().height(35.dp)) {
                        Box(
                            Modifier.align(Alignment.TopCenter)
                                .padding(top = 2.dp)
                                .size(width = 58.dp, height = 5.dp)
                                .background(Color(0xFFDCD8D1), CircleShape),
                        )
                        IconButton(
                            onClick = onClose,
                            modifier = Modifier.align(Alignment.TopEnd).size(38.dp),
                        ) {
                            Icon(
                                Icons.Filled.Close,
                                contentDescription = stringResource(R.string.action_close),
                                tint = Color(0xFF77716C),
                            )
                        }
                    }

                    Box(
                        modifier = Modifier.size(76.dp)
                            .border(BorderStroke(3.dp, Color(0xFFEFB34A)), RoundedCornerShape(20.dp))
                            .background(
                                Brush.linearGradient(listOf(Color(0xFFC96B60), Color(0xFFAC4C46))),
                                RoundedCornerShape(20.dp),
                            ),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text("会", color = Color(0xFFFFD568), fontSize = 42.sp, fontWeight = FontWeight.ExtraBold)
                    }
                    Text(
                        heading,
                        fontSize = 19.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color(0xFF33312F),
                        textAlign = TextAlign.Center,
                    )

                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        color = Color.White.copy(alpha = 0.73f),
                        shape = RoundedCornerShape(17.dp),
                        border = BorderStroke(1.dp, Color(0xFFE6DCD0)),
                    ) {
                        Row(
                            modifier = Modifier.padding(14.dp),
                            horizontalArrangement = Arrangement.spacedBy(10.dp),
                            verticalAlignment = Alignment.Top,
                        ) {
                            Icon(
                                Icons.Filled.Info, contentDescription = null,
                                tint = Color(0xFFBC803B), modifier = Modifier.size(20.dp),
                            )
                            Text(
                                text = reason?.takeIf { it.isNotBlank() }
                                    ?: stringResource(R.string.limit_sheet_reason_fallback, sectionTitle),
                                color = Color(0xFF605D59),
                                fontSize = 14.sp,
                                lineHeight = 21.sp,
                            )
                        }
                    }

                    Box(
                        modifier = Modifier.fillMaxWidth()
                            .border(1.dp, Color(0xFFECD8CE), RoundedCornerShape(21.dp))
                            .background(
                                Brush.linearGradient(
                                    listOf(Color(0xFFFFF0ED), Color(0xFFFFE6DC), Color(0xFFFFF4EF)),
                                ),
                                RoundedCornerShape(21.dp),
                            )
                            .padding(horizontal = 16.dp, vertical = 23.dp),
                    ) {
                        Column(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(10.dp),
                        ) {
                            Box(
                                modifier = Modifier.size(74.dp)
                                    .background(
                                        Brush.linearGradient(
                                            listOf(Color(0xFFD5786B), Color(0xFFC2645A)),
                                        ),
                                        CircleShape,
                                    ),
                                contentAlignment = Alignment.Center,
                            ) {
                                Icon(
                                    Icons.Filled.Check, contentDescription = null,
                                    tint = Color(0xFF231D1B), modifier = Modifier.size(34.dp),
                                )
                            }
                            Spacer(Modifier.height(2.dp))
                            Text(
                                title, color = Color(0xFF302C2B), fontSize = 20.sp,
                                fontWeight = FontWeight.ExtraBold, textAlign = TextAlign.Center,
                                lineHeight = 25.sp,
                            )
                            Text(
                                description, color = Color(0xFF6B625F), fontSize = 14.sp,
                                lineHeight = 21.sp, textAlign = TextAlign.Center,
                            )
                            Row(
                                modifier = Modifier.padding(top = 7.dp),
                                horizontalArrangement = Arrangement.spacedBy(6.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                // Stable single-feature card; no carousel timer in Compose.
                                repeat(5) { index ->
                                    Box(
                                        Modifier.size(
                                            width = if (index == 2) 22.dp else 6.dp,
                                            height = 6.dp,
                                        ).background(
                                            if (index == 2) Color(0xFFD2766B) else Color(0xFFDFCFCE),
                                            CircleShape,
                                        ),
                                    )
                                }
                            }
                        }
                    }

                    Button(
                        onClick = {
                            if (canSubscribe) limit.actions.onUnlock(sourceKey)
                            else limit.actions.onRecheck()
                        },
                        enabled = !limit.state.isBusy,
                        modifier = Modifier.fillMaxWidth().heightIn(min = 58.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFFD2766B),
                            contentColor = Color(0xFF241917),
                        ),
                        shape = RoundedCornerShape(17.dp),
                    ) {
                        if (limit.state.isBusy) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                color = Color(0xFF241917),
                                strokeWidth = 2.dp,
                            )
                        } else {
                            Icon(Icons.Filled.LockOpen, contentDescription = null, modifier = Modifier.size(19.dp))
                            Spacer(Modifier.size(9.dp))
                            Text(actionLabel, fontSize = 17.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                    // Intentionally no 7-day trial, secondary button or checkout hint.
                }
            }
        }
    }
}

private fun limitOfferCopy(sourceKey: String): Pair<Int, Int> = when {
    sourceKey.contains("voice") -> R.string.limit_sheet_voice_title to R.string.limit_sheet_voice_desc
    sourceKey.contains("mistake") -> R.string.limit_sheet_mistakes_title to R.string.limit_sheet_mistakes_desc
    sourceKey.contains("mock") || sourceKey.contains("test") || sourceKey.contains("placement") ->
        R.string.limit_sheet_test_title to R.string.limit_sheet_test_desc
    sourceKey.contains("course") || sourceKey.contains("lesson") ->
        R.string.limit_sheet_lesson_title to R.string.limit_sheet_lesson_desc
    sourceKey.contains("pronunc") ->
        R.string.limit_sheet_pron_title to R.string.limit_sheet_pron_desc
    sourceKey.contains("recognition") ->
        R.string.limit_sheet_recognition_title to R.string.limit_sheet_recognition_desc
    sourceKey.contains("memorize") ->
        R.string.limit_sheet_memorize_title to R.string.limit_sheet_memorize_desc
    else -> R.string.limit_sheet_practice_title to R.string.limit_sheet_practice_desc
}
