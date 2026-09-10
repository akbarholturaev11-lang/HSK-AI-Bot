package com.pomp.hskai.widget

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.glance.appwidget.GlanceAppWidgetManager
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WidgetSetupSheet(reminderEnabled: Boolean, onReminder: (Boolean) -> Unit, onDismiss: () -> Unit) {
    val context = LocalContext.current
    val app = context.applicationContext as HskAiApplication
    val scope = rememberCoroutineScope()
    var installed by remember { mutableStateOf(WidgetScheduler.hasWidgets(context)) }
    var requested by remember { mutableStateOf(false) }
    var requesting by remember { mutableStateOf(false) }
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    DisposableEffect(lifecycle) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) installed = WidgetScheduler.hasWidgets(context)
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer) }
    }
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        containerColor = PompColors.Paper,
    ) {
        Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal = 24.dp).padding(bottom = 24.dp)) {
            Image(painterResource(R.drawable.widget_panda_invite), null, Modifier.size(88.dp))
            Text(stringResource(R.string.widget_setup_title), style = MaterialTheme.typography.headlineSmall, color = PompColors.Ink)
            Spacer(Modifier.height(10.dp))
            Text(stringResource(R.string.widget_setup_body), color = PompColors.InkSecondary)
            Spacer(Modifier.height(20.dp))
            Button(
                onClick = {
                    requesting = true
                    scope.launch {
                        try {
                            // Persist the intent before the system dialog; do not wait on analytics.
                            app.widgetStore.enqueue(AndroidWidgetEvent("android_widget_pin_requested"))
                            requested = GlanceAppWidgetManager(context).requestPinGlanceAppWidget(
                                receiver = HskAiWidgetReceiver::class.java,
                                preview = HskAiSmartWidget(),
                                previewState = androidx.datastore.preferences.core.emptyPreferences(),
                            )
                            app.applicationScope.launch { app.widgetCoordinator.flushEvents() }
                        } catch (cancelled: kotlinx.coroutines.CancellationException) {
                            throw cancelled
                        } catch (_: Exception) {
                            requested = false // Unsupported/failed launcher: manual instructions remain visible.
                        } finally { requesting = false }
                    }
                },
                enabled = !installed && !requesting,
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
            ) { Text(stringResource(R.string.widget_setup_add)) }
            if (installed || requested) Text(
                stringResource(if (installed) R.string.widget_setup_added else R.string.widget_setup_pending),
                style = MaterialTheme.typography.bodySmall, color = PompColors.InkSecondary,
            )
            Spacer(Modifier.height(8.dp))
            Text(stringResource(R.string.widget_setup_manual), style = MaterialTheme.typography.bodySmall, color = PompColors.InkSecondary)
            Spacer(Modifier.height(20.dp))
            Row(Modifier.fillMaxWidth(), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Text(stringResource(R.string.widget_setup_reminder), Modifier.weight(1f), color = PompColors.Ink)
                Switch(checked = reminderEnabled, onCheckedChange = onReminder)
            }
            Text(
                stringResource(R.string.widget_setup_reminder_body, "%02d:00".format(WidgetPolicy.REMINDER_HOUR)),
                style = MaterialTheme.typography.bodySmall, color = PompColors.InkSecondary,
            )
            if (reminderEnabled && !com.pomp.hskai.core.notify.StudyNotifications.canPost(context)) {
                TextButton(onClick = {
                    context.startActivity(android.content.Intent(android.provider.Settings.ACTION_APP_NOTIFICATION_SETTINGS)
                        .putExtra(android.provider.Settings.EXTRA_APP_PACKAGE, context.packageName))
                }) { Text(stringResource(R.string.widget_setup_permission)) }
            }
            TextButton(onClick = onDismiss, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                Text(stringResource(if (installed) R.string.widget_setup_done else R.string.widget_setup_later))
            }
        }
    }
}
