package com.pomp.hskai.widget

import android.content.Intent
import android.provider.Settings
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.appwidget.GlanceAppWidgetManager
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.R
import kotlinx.coroutines.launch

/**
 * One shared, full-screen widget install experience.
 *
 * Onboarding, the daily install reminder and Profile > Settings all open this
 * exact screen. The launcher still owns the final Android confirmation.
 */
@Composable
fun WidgetInstallPromptScreen(
    onDismiss: () -> Unit,
    onInstalled: () -> Unit = onDismiss,
) {
    val context = LocalContext.current
    val app = context.applicationContext as HskAiApplication
    val scope = rememberCoroutineScope()
    val lifecycle = LocalLifecycleOwner.current.lifecycle

    var installed by remember { mutableStateOf(WidgetScheduler.hasWidgets(context)) }
    var requesting by remember { mutableStateOf(false) }
    var pinUnsupported by remember { mutableStateOf(false) }

    BackHandler(onBack = onDismiss)

    DisposableEffect(lifecycle) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                installed = WidgetScheduler.hasWidgets(context)
            }
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer) }
    }

    val requestWidget: () -> Unit = {
        if (installed) {
            onInstalled()
        } else if (!requesting) {
            requesting = true
            pinUnsupported = false
            scope.launch {
                try {
                    app.widgetStore.enqueue(AndroidWidgetEvent("android_widget_pin_requested"))
                    val requested = GlanceAppWidgetManager(context)
                        .requestPinGlanceAppWidget(
                            receiver = HskAiWidgetReceiver::class.java,
                            preview = HskAiSmartWidget(),
                            previewState = androidx.datastore.preferences.core.emptyPreferences(),
                        )
                    pinUnsupported = !requested
                    app.applicationScope.launch { app.widgetCoordinator.flushEvents() }
                } catch (cancelled: kotlinx.coroutines.CancellationException) {
                    throw cancelled
                } catch (_: Exception) {
                    pinUnsupported = true
                } finally {
                    requesting = false
                }
            }
        }
    }

    val background = Brush.verticalGradient(
        listOf(
            Color(0xFF617FE0),
            Color(0xFF263F8D),
            Color(0xFF111A4C),
            Color(0xFF101744),
        )
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(background),
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .fillMaxHeight(0.44f)
                .align(Alignment.TopCenter)
                .background(
                    Brush.radialGradient(
                        colors = listOf(
                            Color.White.copy(alpha = 0.13f),
                            Color.Transparent,
                        )
                    )
                )
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
                .padding(horizontal = 26.dp)
                .padding(top = 34.dp, bottom = 18.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = stringResource(
                    if (installed) R.string.widget_prompt_installed_title
                    else R.string.widget_prompt_title
                ),
                color = Color.White,
                fontSize = 34.sp,
                lineHeight = 39.sp,
                fontWeight = FontWeight.ExtraBold,
                textAlign = TextAlign.Center,
            )

            Spacer(Modifier.height(18.dp))

            Text(
                text = stringResource(
                    if (installed) R.string.widget_prompt_installed_body
                    else R.string.widget_prompt_body
                ),
                color = Color.White.copy(alpha = 0.91f),
                style = MaterialTheme.typography.titleMedium,
                lineHeight = 28.sp,
                textAlign = TextAlign.Center,
                modifier = Modifier.widthIn(max = 390.dp),
            )

            Spacer(Modifier.height(20.dp))

            WidgetPromptHero(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
            )

            if (pinUnsupported && !installed) {
                Text(
                    text = stringResource(R.string.widget_prompt_manual_hint),
                    color = Color.White.copy(alpha = 0.82f),
                    style = MaterialTheme.typography.bodySmall,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .padding(horizontal = 12.dp)
                        .padding(bottom = 10.dp),
                )
            }

            Button(
                onClick = requestWidget,
                enabled = !requesting,
                shape = RoundedCornerShape(20.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color.White,
                    contentColor = Color(0xFF0D1233),
                    disabledContainerColor = Color.White.copy(alpha = 0.80f),
                    disabledContentColor = Color(0xFF0D1233).copy(alpha = 0.70f),
                ),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(64.dp),
            ) {
                if (requesting) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(23.dp),
                        strokeWidth = 2.5.dp,
                        color = Color(0xFF0D1233),
                    )
                } else {
                    Text(
                        text = stringResource(
                            if (installed) R.string.widget_setup_done
                            else R.string.widget_prompt_install
                        ),
                        fontSize = 17.sp,
                        fontWeight = FontWeight.ExtraBold,
                        letterSpacing = 0.7.sp,
                    )
                }
            }

            TextButton(
                onClick = onDismiss,
                enabled = !requesting,
                modifier = Modifier.padding(top = 8.dp),
            ) {
                Text(
                    text = stringResource(
                        if (installed) R.string.widget_setup_done
                        else R.string.widget_prompt_not_now
                    ),
                    color = Color.White,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 0.6.sp,
                )
            }
        }
    }
}

@Composable
private fun WidgetPromptHero(modifier: Modifier = Modifier) {
    Box(
        modifier = modifier,
        contentAlignment = Alignment.Center,
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(0.88f)
                .fillMaxHeight(0.90f)
                .heightIn(max = 430.dp)
                .clip(RoundedCornerShape(42.dp))
                .background(
                    Brush.verticalGradient(
                        listOf(
                            Color(0xFF6D93E8).copy(alpha = 0.88f),
                            Color(0xFF3159B2).copy(alpha = 0.86f),
                            Color(0xFF163778).copy(alpha = 0.88f),
                        )
                    )
                )
                .border(
                    width = 2.dp,
                    color = Color.White.copy(alpha = 0.26f),
                    shape = RoundedCornerShape(42.dp),
                )
                .padding(22.dp),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(146.dp)
                    .align(Alignment.TopCenter)
                    .clip(RoundedCornerShape(28.dp))
                    .background(
                        Brush.linearGradient(
                            listOf(
                                Color(0xFF557BD5),
                                Color(0xFF1B438E),
                            )
                        )
                    )
                    .border(
                        1.dp,
                        Color.White.copy(alpha = 0.20f),
                        RoundedCornerShape(28.dp),
                    )
                    .padding(18.dp),
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth(0.67f)
                        .align(Alignment.CenterStart),
                    verticalArrangement = Arrangement.Center,
                ) {
                    Text(
                        text = "HSK AI",
                        color = Color.White.copy(alpha = 0.86f),
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(Modifier.height(7.dp))
                    Text(
                        text = stringResource(R.string.widget_continue),
                        color = Color.White,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(Modifier.height(5.dp))
                    Text(
                        text = stringResource(R.string.widget_description),
                        color = Color.White.copy(alpha = 0.72f),
                        style = MaterialTheme.typography.bodySmall,
                    )
                }

                Image(
                    painter = painterResource(R.drawable.widget_panda_d01),
                    contentDescription = null,
                    modifier = Modifier
                        .size(92.dp)
                        .align(Alignment.CenterEnd),
                )
            }

            Text(
                text = "✦",
                color = Color.White.copy(alpha = 0.90f),
                fontSize = 28.sp,
                modifier = Modifier
                    .align(Alignment.CenterEnd)
                    .offset(x = (-12).dp, y = 22.dp),
            )
            Text(
                text = "✦",
                color = Color(0xFF89B8FF),
                fontSize = 22.sp,
                modifier = Modifier
                    .align(Alignment.CenterStart)
                    .offset(x = 8.dp, y = 58.dp),
            )

            Image(
                painter = painterResource(R.drawable.widget_panda_d01),
                contentDescription = null,
                modifier = Modifier
                    .size(205.dp)
                    .align(Alignment.BottomCenter)
                    .offset(y = 22.dp),
            )
        }
    }
}

/**
 * Auto-prompt rules are intentionally tiny and testable: once per local day,
 * and never when a real HSK AI widget is already present.
 */
object WidgetInstallPromptPolicy {
    fun shouldAutoShow(
        installed: Boolean,
        lastShownDay: String?,
        today: String,
    ): Boolean = !installed && lastShownDay != today
}
