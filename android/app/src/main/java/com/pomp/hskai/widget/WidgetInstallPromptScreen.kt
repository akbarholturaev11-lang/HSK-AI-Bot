package com.pomp.hskai.widget

import android.animation.ValueAnimator
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.BackHandler
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.BlurredEdgeTreatment
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalWindowInfo
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.appwidget.GlanceAppWidgetManager
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.R
import com.pomp.hskai.feature.assistant.AssistantHidden
import java.time.ZonedDateTime
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.drop
import kotlinx.coroutines.launch

/**
 * One shared, full-screen widget install experience.
 *
 * Onboarding, the daily install reminder and Profile > Settings all open this
 * exact screen. The launcher still owns the final Android confirmation; the
 * moment a widget actually lands, [onPlaced] closes the screen.
 */
@Composable
fun WidgetInstallPromptScreen(
    onDismiss: () -> Unit,
    onInstalled: () -> Unit = onDismiss,
    onPlaced: () -> Unit = onInstalled,
) {
    val context = LocalContext.current
    val app = context.applicationContext as HskAiApplication
    val scope = rememberCoroutineScope()
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    val windowInfo = LocalWindowInfo.current

    // Opened with a widget already on the home screen (from Profile), this is
    // a status screen and stays until closed. Otherwise a widget arriving is
    // the whole point, and the screen gets out of the way at once.
    val startedInstalled = remember { WidgetScheduler.hasWidgets(context) }
    var installed by remember { mutableStateOf(startedInstalled) }
    var requesting by remember { mutableStateOf(false) }
    var pinUnsupported by remember { mutableStateOf(false) }
    var pinBlocked by remember { mutableStateOf(false) }
    // Anything that covered the app after a request: the launcher's sheet,
    // a system dialog. Its absence is what a silently dropped pin looks like.
    var systemUiSeen by remember { mutableStateOf(false) }
    val placed by rememberUpdatedState(onPlaced)

    AssistantHidden()
    BackHandler(onBack = onDismiss)

    DisposableEffect(lifecycle) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_PAUSE) {
                systemUiSeen = true
            } else if (event == Lifecycle.Event.ON_RESUME) {
                installed = WidgetScheduler.hasWidgets(context)
                // Back from the permission screen: offer the pin again.
                pinBlocked = false
            }
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer) }
    }
    LaunchedEffect(windowInfo) {
        snapshotFlow { windowInfo.isWindowFocused }.collect { focused ->
            if (!focused) systemUiSeen = true
        }
    }
    LaunchedEffect(Unit) {
        HskAiWidgetReceiver.placements.drop(1).collect {
            installed = WidgetScheduler.hasWidgets(context)
        }
    }
    LaunchedEffect(installed) {
        if (installed && !startedInstalled) placed()
    }

    val requestWidget: () -> Unit = {
        if (installed) {
            onInstalled()
        } else if (pinBlocked) {
            openPinPermission(context)
        } else if (!requesting) {
            requesting = true
            pinUnsupported = false
            systemUiSeen = false
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
                    if (requested) {
                        scope.launch {
                            delay(WidgetInstallPromptPolicy.PIN_BLOCK_CHECK_MILLIS)
                            pinBlocked = WidgetInstallPromptPolicy.pinLooksBlocked(
                                manufacturer = Build.MANUFACTURER,
                                systemUiSeen = systemUiSeen,
                                placed = installed,
                            )
                        }
                    }
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
    val hint = when {
        pinBlocked -> R.string.widget_prompt_blocked_hint
        pinUnsupported && !installed -> R.string.widget_prompt_manual_hint
        else -> null
    }

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

        // No horizontal padding here: the home-screen slice is wider than the copy.
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
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
                modifier = Modifier.padding(horizontal = 26.dp),
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
                modifier = Modifier
                    .padding(horizontal = 26.dp)
                    .widthIn(max = 390.dp),
            )

            Spacer(Modifier.height(20.dp))

            WidgetPromptHero(
                compact = hint != null,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
            )

            if (hint != null) {
                Text(
                    text = stringResource(hint),
                    color = Color.White.copy(alpha = 0.82f),
                    style = MaterialTheme.typography.bodySmall,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .padding(horizontal = 38.dp)
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
                    .padding(horizontal = 26.dp)
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
                            when {
                                installed -> R.string.widget_setup_done
                                pinBlocked -> R.string.widget_prompt_open_permission
                                else -> R.string.widget_prompt_install
                            }
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

/**
 * A slice of a home screen at the phone's own scale, with the widget in the
 * 2x2 cells `smart_widget_info.xml` asks the launcher for, and the panda in
 * front of it.
 */
@Composable
private fun WidgetPromptHero(compact: Boolean, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val app = context.applicationContext as HskAiApplication
    val session by app.widgetStore.state.collectAsStateWithLifecycle<WidgetSession?>(initialValue = null)
    val motion = remember { ValueAnimator.areAnimatorsEnabled() }

    BoxWithConstraints(
        modifier = modifier.padding(bottom = 10.dp),
        contentAlignment = Alignment.Center,
    ) {
        val pandaSize = if (compact) 150.dp else 196.dp
        // The panda's lower 56% stands below the slice; the rest overlaps it.
        val below = pandaSize * 0.56f
        val homeHeight = (maxHeight - below).coerceIn(240.dp, 392.dp)
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(homeHeight + below),
        ) {
            HomeScreenSlice(
                session = session,
                modifier = Modifier
                    .padding(horizontal = 16.dp)
                    .fillMaxWidth()
                    .height(homeHeight),
            )
            PromptPanda(
                motion = motion,
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .size(pandaSize),
            )
        }
    }
}

private class HomeApp(val column: Int, val row: Int, val light: Long, val dark: Long)

/** Neutral stand-ins for the learner's other apps: no names, no brands. */
private val HOME_APPS = listOf(
    HomeApp(0, 0, 0xFFFF8A65, 0xFFF4511E),
    HomeApp(3, 0, 0xFF81C784, 0xFF388E3C),
    HomeApp(0, 1, 0xFF64B5F6, 0xFF1976D2),
    HomeApp(3, 1, 0xFFFFD54F, 0xFFFFA000),
    HomeApp(0, 2, 0xFFBA68C8, 0xFF7B1FA2),
    HomeApp(1, 2, 0xFF4DD0E1, 0xFF0097A7),
    HomeApp(2, 2, 0xFFF06292, 0xFFC2185B),
    HomeApp(3, 2, 0xFFA1887F, 0xFF5D4037),
    HomeApp(0, 3, 0xFF90A4AE, 0xFF455A64),
    HomeApp(3, 3, 0xFFAED581, 0xFF689F38),
)

@Composable
private fun HomeScreenSlice(session: WidgetSession?, modifier: Modifier = Modifier) {
    BoxWithConstraints(modifier.clip(RoundedCornerShape(30.dp))) {
        // Four launcher columns across the slice; the widget takes the middle two.
        val cell = maxWidth / 4

        // Wallpaper and the other apps are blurred and dimmed (blur needs
        // Android 12; older phones get the dimming only), the widget is not.
        Box(
            modifier = Modifier
                .fillMaxSize()
                .blur(7.dp)
                .drawBehind {
                    drawRect(
                        Brush.linearGradient(
                            0f to Color(0xFF5AA7B8),
                            0.4f to Color(0xFF2C7C8F),
                            1f to Color(0xFF173E6B),
                            start = Offset(size.width * 0.3f, 0f),
                            end = Offset(size.width * 0.7f, size.height),
                        )
                    )
                    drawRect(
                        Brush.radialGradient(
                            colors = listOf(Color(0xFF3FD0B0), Color.Transparent),
                            center = Offset(size.width * 0.85f, size.height * 0.2f),
                            radius = size.width * 0.46f,
                        )
                    )
                    drawRect(
                        Brush.radialGradient(
                            colors = listOf(Color(0xFF1F6FB8), Color.Transparent),
                            center = Offset(size.width * 0.1f, size.height * 0.9f),
                            radius = size.width * 0.6f,
                        )
                    )
                    drawRect(Color.Black.copy(alpha = 0.38f))
                }
        )
        Box(
            modifier = Modifier
                .fillMaxSize()
                .blur(2.dp)
                .alpha(0.55f)
        ) {
            HOME_APPS.forEach { app ->
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier
                        .offset(x = cell * app.column + (cell - 56.dp) / 2, y = 24.dp + 104.dp * app.row)
                        .width(56.dp),
                ) {
                    Box(
                        Modifier
                            .size(56.dp)
                            .clip(RoundedCornerShape(17.dp))
                            .background(Brush.linearGradient(listOf(Color(app.light), Color(app.dark))))
                    )
                    Spacer(Modifier.height(9.dp))
                    Box(
                        Modifier
                            .width(40.dp)
                            .height(6.dp)
                            .clip(RoundedCornerShape(3.dp))
                            .background(Color.White.copy(alpha = 0.7f))
                    )
                }
            }
        }

        if (session != null) {
            PromptWidget(
                session = session,
                modifier = Modifier
                    .offset(x = cell + 7.dp, y = 18.dp)
                    .width(cell * 2 - 13.dp)
                    .height(206.dp),
            )
        }
    }
}

/**
 * The widget exactly as the launcher will draw it now: same state engine,
 * same drawing, same words ([widgetCopy]) as [WidgetContent].
 */
@Composable
private fun PromptWidget(session: WidgetSession, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val now = remember(session) { ZonedDateTime.now() }
    val access = WidgetStateResolver.resolve(session.linked, session.snapshot, now)
    val visual = WidgetVisualResolver.resolve(session.snapshot, session.epoch, now)
    val asset = WidgetArt.assetFor(access, visual)
    val copy = widgetCopy(context, session, access, visual)
    val shape = RoundedCornerShape(20.dp)

    Box(
        modifier = modifier
            .shadow(10.dp, shape)
            .clip(shape),
        contentAlignment = Alignment.BottomStart,
    ) {
        Image(
            painter = painterResource(asset.drawable()),
            contentDescription = copy.message,
            contentScale = ContentScale.Crop,
            modifier = Modifier.fillMaxSize(),
        )
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(8.dp)
                .clip(RoundedCornerShape(14.dp))
                .background(Color.Black.copy(alpha = 0.58f))
                .padding(horizontal = 10.dp, vertical = 7.dp),
        ) {
            Text(
                text = copy.message,
                color = Color.White,
                fontSize = 13.sp,
                lineHeight = 16.sp,
                fontWeight = FontWeight.Bold,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = copy.stats,
                color = Color.White.copy(alpha = 0.84f),
                fontSize = 10.sp,
                lineHeight = 13.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

/** The widget's own panda, cut out of its scene, breathing slowly. */
@Composable
private fun PromptPanda(motion: Boolean, modifier: Modifier = Modifier) {
    val breath = if (motion) {
        rememberInfiniteTransition(label = "widget-prompt-panda").animateFloat(
            initialValue = 1f,
            targetValue = 1.02f,
            animationSpec = infiniteRepeatable(tween(1300), RepeatMode.Reverse),
            label = "widget-prompt-panda-breathe",
        )
    } else {
        null
    }
    val painter = painterResource(R.drawable.widget_prompt_panda)

    Box(
        modifier = modifier.graphicsLayer {
            val scale = breath?.value ?: 1f
            scaleX = scale
            scaleY = scale
            transformOrigin = TransformOrigin(0.5f, 1f)
        },
    ) {
        // A soft shadow needs blur; without it a hard silhouette looks wrong.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            Image(
                painter = painter,
                contentDescription = null,
                colorFilter = ColorFilter.tint(Color.Black),
                alpha = 0.35f,
                modifier = Modifier
                    .matchParentSize()
                    .offset(y = 12.dp)
                    .blur(9.dp, BlurredEdgeTreatment.Unbounded),
            )
        }
        Image(
            painter = painter,
            contentDescription = null,
            modifier = Modifier.matchParentSize(),
        )
    }
}

/** Shown for a moment after the prompt closed itself because a widget landed. */
@Composable
fun WidgetPlacedNotice(onDone: () -> Unit) {
    val done by rememberUpdatedState(onDone)
    LaunchedEffect(Unit) {
        delay(WidgetInstallPromptPolicy.PLACED_NOTICE_MILLIS)
        done()
    }
    val shape = RoundedCornerShape(26.dp)

    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier
                .width(214.dp)
                .shadow(16.dp, shape)
                .clip(shape)
                .background(Color(0xFF171310).copy(alpha = 0.86f))
                .padding(start = 18.dp, end = 18.dp, top = 26.dp, bottom = 22.dp)
                .semantics { liveRegion = LiveRegionMode.Polite },
        ) {
            Box(
                modifier = Modifier
                    .size(64.dp)
                    .clip(CircleShape)
                    .background(Color(0xFF2FA06A)),
                contentAlignment = Alignment.Center,
            ) {
                Canvas(Modifier.size(34.dp)) {
                    val unit = size.width / 24f
                    val check = Path().apply {
                        moveTo(5f * unit, 12.5f * unit)
                        lineTo(9.2f * unit, 16.7f * unit)
                        lineTo(19f * unit, 7f * unit)
                    }
                    drawPath(
                        path = check,
                        color = Color.White,
                        style = Stroke(width = 2.8f * unit, cap = StrokeCap.Round, join = StrokeJoin.Round),
                    )
                }
            }
            Spacer(Modifier.height(14.dp))
            Text(
                text = stringResource(R.string.widget_prompt_placed),
                color = Color.White,
                fontSize = 17.sp,
                lineHeight = 22.sp,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
            )
        }
    }
}

/** MIUI/HyperOS's own screen for the app's permissions, else the app's info page. */
private fun openPinPermission(context: Context) {
    val miui = Intent("miui.intent.action.APP_PERM_EDITOR")
        .setClassName("com.miui.securitycenter", "com.miui.permcenter.permissions.PermissionsEditorActivity")
        .putExtra("extra_pkgname", context.packageName)
    val details = Intent(
        Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
        Uri.fromParts("package", context.packageName, null),
    )
    for (intent in listOf(miui, details)) {
        if (context !is Activity) intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        if (runCatching { context.startActivity(intent) }.isSuccess) return
    }
}

/**
 * Auto-prompt rules are intentionally tiny and testable: once per local day,
 * and never when a real HSK AI widget is already present.
 */
object WidgetInstallPromptPolicy {
    /** How long the launcher gets to show its add-widget sheet. */
    const val PIN_BLOCK_CHECK_MILLIS = 2_000L

    /** How long "widget installed" stays in the middle of the screen. */
    const val PLACED_NOTICE_MILLIS = 1_500L

    fun shouldAutoShow(
        installed: Boolean,
        lastShownDay: String?,
        today: String,
    ): Boolean = !installed && lastShownDay != today

    /**
     * MIUI/HyperOS accepts a pin request and then drops it without a word
     * while its home-screen-shortcuts permission is off. Nothing covering the
     * app and no widget arriving is the only sign of that, and only there.
     */
    fun pinLooksBlocked(
        manufacturer: String,
        systemUiSeen: Boolean,
        placed: Boolean,
    ): Boolean = manufacturer.equals("Xiaomi", ignoreCase = true) && !systemUiSeen && !placed
}
