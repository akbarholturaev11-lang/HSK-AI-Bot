package com.pomp.hskai.widget

import android.content.Intent
import android.provider.Settings
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Widgets
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.glance.appwidget.GlanceAppWidgetManager
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskGlassButton
import com.pomp.hskai.core.design.components.HskGlassSurface
import com.pomp.hskai.core.design.components.HskPrimaryButton
import kotlinx.coroutines.launch

/**
 * Post-onboarding widget offer.
 *
 * Keep this intentionally small and product-like: one preview, one primary
 * action, compact manual fallback and an independent reminder preference.
 * The system pin dialog still owns the final Android confirmation.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WidgetSetupSheet(
    reminderEnabled: Boolean,
    onReminder: (Boolean) -> Unit,
    onDismiss: () -> Unit,
) {
    val context = LocalContext.current
    val app = context.applicationContext as HskAiApplication
    val scope = rememberCoroutineScope()
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    var installed by remember { mutableStateOf(WidgetScheduler.hasWidgets(context)) }
    var requested by remember { mutableStateOf(false) }
    var requesting by remember { mutableStateOf(false) }

    DisposableEffect(lifecycle) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                installed = WidgetScheduler.hasWidgets(context)
            }
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer) }
    }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        containerColor = if (PompColors.IsDark) {
            PompColors.PaperRaised.copy(alpha = 0.96f)
        } else {
            PompColors.Paper.copy(alpha = 0.96f)
        },
        scrimColor = PompColors.Overlay.copy(alpha = if (PompColors.IsDark) 0.44f else 0.30f),
        tonalElevation = 0.dp,
        shape = RoundedCornerShape(topStart = 30.dp, topEnd = 30.dp),
        dragHandle = { WidgetSheetHandle() },
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .navigationBarsPadding()
                .padding(horizontal = 20.dp)
                .padding(bottom = 22.dp),
        ) {
            WidgetHeader()
            Spacer(Modifier.height(18.dp))

            WidgetPreviewCard()
            Spacer(Modifier.height(16.dp))

            when {
                installed -> WidgetStatusCard(
                    text = stringResource(R.string.widget_setup_added),
                    success = true,
                )
                requested -> WidgetStatusCard(
                    text = stringResource(R.string.widget_setup_pending),
                    success = false,
                )
            }

            if (installed || requested) {
                Spacer(Modifier.height(12.dp))
            }

            HskPrimaryButton(
                text = stringResource(
                    if (installed) R.string.widget_setup_done else R.string.widget_setup_add
                ),
                onClick = if (installed) {
                    onDismiss
                } else {
                    {
                        requesting = true
                        scope.launch {
                            try {
                                app.widgetStore.enqueue(
                                    AndroidWidgetEvent("android_widget_pin_requested")
                                )
                                requested = GlanceAppWidgetManager(context)
                                    .requestPinGlanceAppWidget(
                                        receiver = HskAiWidgetReceiver::class.java,
                                        preview = HskAiSmartWidget(),
                                        previewState = androidx.datastore.preferences.core.emptyPreferences(),
                                    )
                                app.applicationScope.launch {
                                    app.widgetCoordinator.flushEvents()
                                }
                            } catch (cancelled: kotlinx.coroutines.CancellationException) {
                                throw cancelled
                            } catch (_: Exception) {
                                requested = false
                            } finally {
                                requesting = false
                            }
                        }
                    }
                },
                enabled = installed || !requesting,
                loading = requesting,
                modifier = Modifier.fillMaxWidth(),
            )

            if (!installed) {
                Spacer(Modifier.height(14.dp))
                ManualSetupCard()
            }

            Spacer(Modifier.height(14.dp))
            ReminderCard(
                enabled = reminderEnabled,
                onToggle = onReminder,
            )

            if (
                reminderEnabled &&
                !com.pomp.hskai.core.notify.StudyNotifications.canPost(context)
            ) {
                Spacer(Modifier.height(10.dp))
                HskGlassButton(
                    text = stringResource(R.string.widget_setup_permission),
                    onClick = {
                        context.startActivity(
                            Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
                                .putExtra(Settings.EXTRA_APP_PACKAGE, context.packageName)
                        )
                    },
                    modifier = Modifier.fillMaxWidth(),
                )
            }

            if (!installed) {
                Spacer(Modifier.height(8.dp))
                HskGlassButton(
                    text = stringResource(R.string.widget_setup_later),
                    onClick = onDismiss,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

@Composable
private fun WidgetSheetHandle() {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 12.dp, bottom = 8.dp),
        contentAlignment = Alignment.Center,
    ) {
        Box(
            Modifier
                .size(width = 38.dp, height = 4.dp)
                .background(PompColors.Divider, CircleShape)
        )
    }
}

@Composable
private fun WidgetHeader() {
    Column(horizontalAlignment = Alignment.Start) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .background(PompColors.CinnabarSoft, RoundedCornerShape(11.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = Icons.Filled.Widgets,
                    contentDescription = null,
                    tint = PompColors.Cinnabar,
                    modifier = Modifier.size(19.dp),
                )
            }
            Spacer(Modifier.size(10.dp))
            Text(
                text = stringResource(R.string.widget_preview_label),
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.CinnabarDark,
            )
        }
        Spacer(Modifier.height(12.dp))
        Text(
            text = stringResource(R.string.widget_setup_title),
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.SemiBold,
            color = PompColors.Ink,
        )
        Spacer(Modifier.height(6.dp))
        Text(
            text = stringResource(R.string.widget_setup_body),
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.InkSecondary,
        )
    }
}

@Composable
private fun WidgetPreviewCard() {
    val previewShape = RoundedCornerShape(24.dp)
    HskGlassSurface(
        modifier = Modifier
            .fillMaxWidth()
            .aspectRatio(1.72f),
        shape = previewShape,
        shadowElevation = 10.dp,
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    brush = Brush.linearGradient(
                        colors = if (PompColors.IsDark) {
                            listOf(
                                PompColors.PaperRaised.copy(alpha = 0.72f),
                                PompColors.OptionDepth.copy(alpha = 0.78f),
                            )
                        } else {
                            listOf(
                                Color.White.copy(alpha = 0.58f),
                                PompColors.CinnabarSoft.copy(alpha = 0.66f),
                            )
                        },
                    ),
                    shape = previewShape,
                )
                .padding(18.dp),
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth(0.68f)
                    .align(Alignment.CenterStart),
            ) {
                Text(
                    text = "HSK AI",
                    style = MaterialTheme.typography.labelLarge,
                    color = PompColors.Cinnabar,
                    fontWeight = FontWeight.SemiBold,
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    text = stringResource(R.string.widget_continue),
                    style = MaterialTheme.typography.titleMedium,
                    color = PompColors.Ink,
                    fontWeight = FontWeight.SemiBold,
                )
                Spacer(Modifier.height(5.dp))
                Text(
                    text = stringResource(R.string.widget_description),
                    style = MaterialTheme.typography.bodySmall,
                    color = PompColors.InkSecondary,
                )
            }

            Image(
                painter = painterResource(R.drawable.widget_panda_focus),
                contentDescription = null,
                modifier = Modifier
                    .size(88.dp)
                    .align(Alignment.CenterEnd),
            )
        }
    }
}

@Composable
private fun WidgetStatusCard(text: String, success: Boolean) {
    HskGlassSurface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        shadowElevation = 4.dp,
        borderColor = if (success) PompColors.Jade.copy(alpha = 0.45f) else null,
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                imageVector = if (success) Icons.Filled.CheckCircle else Icons.Filled.Widgets,
                contentDescription = null,
                tint = if (success) PompColors.Jade else PompColors.Cinnabar,
                modifier = Modifier.size(20.dp),
            )
            Spacer(Modifier.size(10.dp))
            Text(
                text = text,
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.Ink,
            )
        }
    }
}

@Composable
private fun ManualSetupCard() {
    HskGlassSurface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        shadowElevation = 4.dp,
    ) {
        Column(Modifier.padding(16.dp)) {
            Text(
                text = stringResource(R.string.widget_setup_manual),
                style = MaterialTheme.typography.titleSmall,
                color = PompColors.Ink,
                fontWeight = FontWeight.SemiBold,
            )
            Spacer(Modifier.height(12.dp))
            SetupStep(1, stringResource(R.string.widget_setup_manual_step_1))
            SetupStep(2, stringResource(R.string.widget_setup_manual_step_2))
            SetupStep(3, stringResource(R.string.widget_setup_manual_step_3))
        }
    }
}

@Composable
private fun SetupStep(number: Int, text: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 5.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier
                .size(26.dp)
                .background(PompColors.CinnabarSoft, CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = number.toString(),
                style = MaterialTheme.typography.labelMedium,
                color = PompColors.CinnabarDark,
                fontWeight = FontWeight.SemiBold,
            )
        }
        Spacer(Modifier.size(10.dp))
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.InkSecondary,
        )
    }
}

@Composable
private fun ReminderCard(enabled: Boolean, onToggle: (Boolean) -> Unit) {
    HskGlassSurface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        shadowElevation = 4.dp,
        borderColor = if (enabled) PompColors.Cinnabar.copy(alpha = 0.34f) else null,
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .size(38.dp)
                    .background(
                        if (enabled) PompColors.CinnabarSoft else PompColors.Divider.copy(alpha = 0.58f),
                        RoundedCornerShape(12.dp),
                    ),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = Icons.Filled.Notifications,
                    contentDescription = null,
                    tint = if (enabled) PompColors.Cinnabar else PompColors.InkSecondary,
                    modifier = Modifier.size(20.dp),
                )
            }
            Spacer(Modifier.size(12.dp))
            Column(Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.widget_setup_reminder),
                    style = MaterialTheme.typography.titleSmall,
                    color = PompColors.Ink,
                    fontWeight = FontWeight.Medium,
                )
                Spacer(Modifier.height(3.dp))
                Text(
                    text = stringResource(
                        R.string.widget_setup_reminder_body,
                        "%02d:00".format(WidgetPolicy.REMINDER_HOUR),
                    ),
                    style = MaterialTheme.typography.bodySmall,
                    color = PompColors.InkSecondary,
                )
            }
            Spacer(Modifier.size(10.dp))
            Switch(
                checked = enabled,
                onCheckedChange = onToggle,
                colors = SwitchDefaults.colors(
                    checkedThumbColor = Color.White,
                    checkedTrackColor = PompColors.Cinnabar,
                    uncheckedThumbColor = PompColors.InkDisabled,
                    uncheckedTrackColor = PompColors.Divider,
                    uncheckedBorderColor = Color.Transparent,
                ),
            )
        }
    }
}
