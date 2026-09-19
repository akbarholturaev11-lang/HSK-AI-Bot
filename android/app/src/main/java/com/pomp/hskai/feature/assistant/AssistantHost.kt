package com.pomp.hskai.feature.assistant

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import android.media.MediaPlayer
import android.util.Base64
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.snap
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.MenuBook
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import kotlin.math.roundToInt
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.AuthState
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskBrandLoader
import com.pomp.hskai.core.design.components.HskGlassSurface
import com.pomp.hskai.core.navigation.DeepLinkRouter
import java.io.ByteArrayOutputStream
import java.io.File
import kotlinx.coroutines.*

data class VisibleScreen(val context: ScreenContext, val bottomBar: Boolean, val priority: Int)

/** Explicit registration avoids scraping UI, secrets or hidden answer keys. */
class ScreenRegistry {
    private val entries = mutableStateMapOf<Any, VisibleScreen>()
    private val order = mutableListOf<Any>()
    var current by mutableStateOf<VisibleScreen?>(null)
        private set

    fun put(owner: Any, value: VisibleScreen) {
        if (owner !in entries) order.add(owner)
        entries[owner] = value
        refreshCurrent()
    }

    fun remove(owner: Any) {
        entries.remove(owner)
        order.remove(owner)
        refreshCurrent()
    }

    private fun refreshCurrent() {
        current = order.mapIndexedNotNull { index, key ->
            entries[key]?.let { index to it }
        }.maxWithOrNull(compareBy<Pair<Int, VisibleScreen>> { it.second.priority }.thenBy { it.first })?.second
    }
}
class AssistantBinding(val registry: ScreenRegistry, val controller: AssistantController, val open: () -> Unit)
val LocalAssistant = staticCompositionLocalOf<AssistantBinding?> { null }

@Composable
fun AssistantScreen(context: ScreenContext, bottomBar: Boolean = false, priority: Int = 0) {
    val host = LocalAssistant.current ?: return
    val owner = remember { Any() }
    SideEffect { host.registry.put(owner, VisibleScreen(context.copy(details = context.details.take(8000), title = context.title.take(160)), bottomBar, priority)) }
    DisposableEffect(host, owner) { onDispose { host.registry.remove(owner) } }
}

@Composable
fun AssistantHost(app: HskAiApplication, onNavigate: (String) -> Unit, content: @Composable () -> Unit) {
    val registry = remember { ScreenRegistry() }
    val auth by app.authRepository.state.collectAsStateWithLifecycle()
    var open by rememberSaveable { mutableStateOf(false) }
    var destination by remember { mutableStateOf<String?>(null) }
    val binding = remember { AssistantBinding(registry, app.assistant) { open = true; app.assistant.open() } }
    val scope = rememberCoroutineScope()
    val visible = registry.current
    val availableOnScreen = auth is AuthState.Authenticated && visible != null
    LaunchedEffect(auth) {
        if (auth is AuthState.Authenticated) app.assistant.attach(app.widgetStore.read().epoch.toString())
        else open = false
    }
    CompositionLocalProvider(LocalAssistant provides binding) {
        BoxWithConstraints(Modifier.fillMaxSize()) {
            // The button floats and the learner can park it, so no screen has to
            // reserve a shelf for it: inner screens keep their own bottom action alone.
            Box(Modifier.fillMaxSize()) { content() }
            if (availableOnScreen && !open) DraggableAssistantButton(
                onClick = binding.open,
                areaWidth = maxWidth,
                areaHeight = maxHeight,
                bottomBar = visible?.bottomBar == true,
            )
        }
        if (open && availableOnScreen) AssistantChat(app, visible!!.context, { open = false }) { action ->
            // Native allowlist is independent of model/server output. No external URLs.
            val uri = "${DeepLinkRouter.SCHEME}://${action.destination.replace(':', '/')}"
            if (DeepLinkRouter.resolve(uri) != null) {
                if (visible.context.attemptId.isNotBlank()) destination = uri
                else { open = false; onNavigate(uri) }
            }
        }
        destination?.let { uri ->
            AlertDialog(
                onDismissRequest = { destination = null },
                title = { Text(stringResource(R.string.assistant_leave_title)) },
                text = { Text(stringResource(R.string.assistant_leave_body)) },
                confirmButton = { TextButton(onClick = {
                    scope.launch {
                        try {
                            val current = registry.current?.context
                            if (current?.screen in setOf("exam", "challenge")) app.assistant.repository.abandon(current!!.attemptId)
                            destination = null; open = false; onNavigate(uri)
                        } catch (cancel: CancellationException) { throw cancel }
                        catch (_: Exception) { app.assistant.error("assistant_network"); destination = null }
                    }
                }) { Text(stringResource(R.string.assistant_continue)) } },
                dismissButton = { TextButton(onClick = { destination = null }) { Text(stringResource(R.string.assistant_stay)) } },
            )
        }
    }
}

@Composable
private fun AssistantButton(onClick: () -> Unit, modifier: Modifier = Modifier) {
    val label = stringResource(R.string.assistant_open)
    FloatingActionButton(onClick, modifier.size(56.dp).semantics { contentDescription = label },
        shape = CircleShape, containerColor = PompColors.Cinnabar, contentColor = PompColors.Paper) {
        Text("AI", style = MaterialTheme.typography.titleMedium)
    }
}

/** Remembered across launches so the learner only parks the button once. */
private object AssistantFabPosition {
    private const val PREFERENCES = "hsk-assistant-fab"
    private const val KEY_X = "x"
    private const val KEY_Y = "y"

    fun load(context: android.content.Context): Pair<Float, Float>? = runCatching {
        val prefs = context.getSharedPreferences(PREFERENCES, android.content.Context.MODE_PRIVATE)
        if (!prefs.contains(KEY_X) || !prefs.contains(KEY_Y)) return null
        prefs.getFloat(KEY_X, 1f) to prefs.getFloat(KEY_Y, .6f)
    }.getOrNull()

    fun save(context: android.content.Context, x: Float, y: Float) {
        runCatching {
            context.getSharedPreferences(PREFERENCES, android.content.Context.MODE_PRIVATE)
                .edit().putFloat(KEY_X, x).putFloat(KEY_Y, y).apply()
        }
    }
}

@Composable
private fun DraggableAssistantButton(onClick: () -> Unit, areaWidth: Dp, areaHeight: Dp, bottomBar: Boolean) {
    val context = LocalContext.current
    val density = LocalDensity.current
    val size = 56.dp
    val margin = 16.dp
    with(density) {
        val width = areaWidth.toPx()
        val height = areaHeight.toPx()
        if (width <= 0f || height <= 0f) return
        val button = size.toPx()
        val edge = margin.toPx()
        // Never let it rest on top of a bottom bar or the gesture area.
        val floor = height - button - edge - (if (bottomBar) 72.dp.toPx() else 0f) -
            WindowInsets.navigationBars.getBottom(density).toFloat()
        val maxX = (width - button - edge).coerceAtLeast(edge)
        val maxY = floor.coerceAtLeast(edge)
        val start = remember(width, height, bottomBar) {
            val saved = AssistantFabPosition.load(context)
            if (saved == null) Offset(maxX, (height * .58f).coerceIn(edge, maxY))
            else Offset((saved.first * width).coerceIn(edge, maxX), (saved.second * height).coerceIn(edge, maxY))
        }
        var position by remember(start) { mutableStateOf(start) }
        var dragging by remember { mutableStateOf(false) }
        val glide = spring<Float>(dampingRatio = .72f, stiffness = 520f)
        val x by animateFloatAsState(position.x, if (dragging) snap() else glide, label = "assistant-fab-x")
        val y by animateFloatAsState(position.y, if (dragging) snap() else glide, label = "assistant-fab-y")
        AssistantButton(
            onClick = onClick,
            modifier = Modifier
                .offset { IntOffset(x.roundToInt(), y.roundToInt()) }
                .pointerInput(width, height, bottomBar) {
                    detectDragGestures(
                        onDragStart = { dragging = true },
                        onDrag = { change, drag ->
                            change.consume()
                            position = Offset(
                                (position.x + drag.x).coerceIn(edge, maxX),
                                (position.y + drag.y).coerceIn(edge, maxY),
                            )
                        },
                        onDragEnd = {
                            dragging = false
                            // Magnetic sides keep it off the middle of a lesson card.
                            val settled = Offset(if (position.x + button / 2f < width / 2f) edge else maxX, position.y)
                            position = settled
                            AssistantFabPosition.save(context, settled.x / width, settled.y / height)
                        },
                        onDragCancel = { dragging = false },
                    )
                },
        )
    }
}

/** Sheets are separate windows; give them their own entry, using the same chat/controller. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AssistantModalBottomSheet(
    onDismissRequest: () -> Unit,
    modifier: Modifier = Modifier,
    sheetState: SheetState = rememberModalBottomSheetState(),
    containerColor: Color = PompColors.PaperRaised.copy(
        alpha = if (PompColors.IsDark) 0.92f else 0.86f,
    ),
    content: @Composable ColumnScope.() -> Unit,
) {
    ModalBottomSheet(
        onDismissRequest = onDismissRequest,
        modifier = modifier,
        sheetState = sheetState,
        containerColor = containerColor,
        scrimColor = PompColors.Overlay.copy(alpha = if (PompColors.IsDark) 0.42f else 0.28f),
        tonalElevation = 0.dp,
        shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp),
        dragHandle = { AssistantDragHandle() },
    ) {
        content()
        val binding = LocalAssistant.current
        val state = binding?.controller?.state?.collectAsStateWithLifecycle()?.value
        if (state?.enabled == true) Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.End) {
            AssistantButton(onClick = binding.open)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
private fun AssistantChat(app: HskAiApplication, screen: ScreenContext, onClose: () -> Unit, onAction: (AssistantAction) -> Unit) {
    val state by app.assistant.state.collectAsStateWithLifecycle()
    var expanded by rememberSaveable { mutableStateOf(false) }
    var includeContext by rememberSaveable { mutableStateOf(true) }
    var inspect by remember { mutableStateOf(false) }
    var history by remember { mutableStateOf(false) }
    var recording by remember { mutableStateOf(false) }
    var preparing by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current
    var player by remember { mutableStateOf<MediaPlayer?>(null) }
    var previewFile by remember { mutableStateOf<File?>(null) }
    fun stopPreview() { player?.release(); player = null; previewFile?.delete(); previewFile = null }
    fun startRecording() {
        if (app.voiceRecorder.isRecording) { app.assistant.error("assistant_mic_busy"); return }
        try { app.voiceRecorder.start(); recording = true }
        catch (_: Exception) { app.assistant.error("assistant_microphone") }
    }
    fun finishRecording() {
        if (!recording || preparing) return
        preparing = true
        scope.launch {
            try { app.assistant.media(app.voiceRecorder.stop().dataUrl, "voice") }
            catch (cancel: CancellationException) { throw cancel }
            catch (_: Exception) { app.assistant.error("assistant_no_speech") }
            finally { recording = false; preparing = false }
        }
    }
    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { allowed ->
        if (allowed) startRecording() else app.assistant.error("assistant_microphone")
    }
    val photo = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        if (uri != null) scope.launch {
            preparing = true
            try {
                val data = withContext(Dispatchers.IO) {
                    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                    context.contentResolver.openInputStream(uri)?.use {
                        BitmapFactory.decodeStream(it, null, bounds)
                    }
                    require(bounds.outWidth > 0 && bounds.outHeight > 0)
                    require(bounds.outWidth.toLong() * bounds.outHeight.toLong() <= 24_000_000L)
                    var sample = 1
                    while (maxOf(bounds.outWidth / sample, bounds.outHeight / sample) > 2048) sample *= 2
                    val bitmap = context.contentResolver.openInputStream(uri)?.use {
                        BitmapFactory.decodeStream(it, null, BitmapFactory.Options().apply { inSampleSize = sample })
                    } ?: error("image_decode_failed")
                    val scaled = if (maxOf(bitmap.width, bitmap.height) > 2048) {
                        val scale = 2048f / maxOf(bitmap.width, bitmap.height)
                        android.graphics.Bitmap.createScaledBitmap(
                            bitmap,
                            (bitmap.width * scale).toInt().coerceAtLeast(1),
                            (bitmap.height * scale).toInt().coerceAtLeast(1),
                            true,
                        ).also { bitmap.recycle() }
                    } else {
                        bitmap
                    }
                    // Shrink until the encoded photo clears the request budget on slow links.
                    var quality = 88
                    var bytes = ByteArrayOutputStream().also { scaled.compress(android.graphics.Bitmap.CompressFormat.JPEG, quality, it) }.toByteArray()
                    while (bytes.size > MAX_PHOTO_BYTES && quality > 45) {
                        quality -= 12
                        bytes = ByteArrayOutputStream().also { scaled.compress(android.graphics.Bitmap.CompressFormat.JPEG, quality, it) }.toByteArray()
                    }
                    scaled.recycle()
                    require(bytes.size <= MAX_PHOTO_BYTES)
                    "data:image/jpeg;base64," + Base64.encodeToString(bytes, Base64.NO_WRAP)
                }
                app.assistant.media(data, "image")
            } catch (cancel: CancellationException) { throw cancel }
            catch (_: Exception) { app.assistant.error("assistant_media_invalid") }
            finally { preparing = false }
        }
    }
    val latestRecording by rememberUpdatedState(recording)
    DisposableEffect(lifecycle) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_STOP) {
                if (latestRecording) { app.voiceRecorder.cancel(); recording = false }
                stopPreview()
            }
        }
        lifecycle.lifecycle.addObserver(observer)
        onDispose {
            lifecycle.lifecycle.removeObserver(observer)
            if (latestRecording) app.voiceRecorder.cancel()
            stopPreview()
        }
    }
    LaunchedEffect(recording) { if (recording) { delay(60_000); finishRecording() } }
    val list = rememberLazyListState()
    LaunchedEffect(state.turns.lastOrNull(), state.busy, history) {
        if (!history && state.turns.isNotEmpty()) list.animateScrollToItem(maxOf(0, list.layoutInfo.totalItemsCount - 1))
    }
    val canSend = !state.busy && !state.loading && !recording && !preparing && (state.draft.isNotBlank() || state.media.isNotBlank())
    ModalBottomSheet(
        onDismissRequest = onClose,
        // Full screen must still stop below the clock and the camera cutout.
        modifier = Modifier.statusBarsPadding(),
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        containerColor = PompColors.PaperRaised.copy(
            alpha = if (PompColors.IsDark) 0.92f else 0.86f,
        ),
        scrimColor = PompColors.Overlay.copy(alpha = if (PompColors.IsDark) 0.42f else 0.28f),
        tonalElevation = 0.dp,
        shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp),
        // A real handle is what makes the swipe-down-to-close gesture reachable.
        dragHandle = { AssistantDragHandle() },
    ) {
        Column(
            Modifier.fillMaxWidth()
                .fillMaxHeight(if (expanded) 1f else .94f)
                .navigationBarsPadding()
                .imePadding(),
        ) {
            Row(Modifier.fillMaxWidth().padding(horizontal = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = { history = !history; inspect = false; if (history) app.assistant.conversations() }) {
                    Icon(Icons.Default.History, stringResource(R.string.assistant_history),
                        tint = if (history) PompColors.Cinnabar else PompColors.InkSecondary)
                }
                AssistantAvatar(30.dp)
                Spacer(Modifier.width(8.dp))
                Text("HSK AI", style = MaterialTheme.typography.titleMedium, color = PompColors.Ink, modifier = Modifier.weight(1f))
                IconButton(onClick = { app.assistant.selectConversation(); history = false }, enabled = !state.busy && !state.loading) {
                    Icon(Icons.Default.Add, stringResource(R.string.assistant_new), tint = PompColors.InkSecondary)
                }
                IconButton(onClick = { expanded = !expanded }) {
                    Icon(if (expanded) Icons.Default.FullscreenExit else Icons.Default.Fullscreen,
                        stringResource(R.string.assistant_expand), tint = PompColors.InkSecondary)
                }
                IconButton(onClick = onClose) {
                    Icon(Icons.Default.Close, stringResource(R.string.assistant_close), tint = PompColors.InkSecondary)
                }
            }
            if (!history) {
                Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 2.dp), verticalAlignment = Alignment.CenterVertically) {
                    AssistantChip(
                        text = if (includeContext) screen.title.ifBlank { stringResource(R.string.assistant_general) } else stringResource(R.string.assistant_general),
                        onClick = { includeContext = !includeContext },
                        selected = includeContext,
                        maxLines = 1,
                        modifier = Modifier.weight(1f, fill = false).semantics { contentDescription = context.getString(R.string.assistant_context) },
                        icon = {
                            Icon(if (includeContext) Icons.Default.Check else Icons.Default.RemoveCircleOutline, null,
                                Modifier.size(15.dp), tint = if (includeContext) PompColors.Cinnabar else PompColors.InkSecondary)
                        },
                    )
                    if (screen.details.isNotBlank()) IconButton(onClick = { inspect = !inspect }, modifier = Modifier.size(36.dp)) {
                        Icon(Icons.Default.Info, null, Modifier.size(17.dp),
                            tint = if (inspect) PompColors.Cinnabar else PompColors.InkDisabled)
                    }
                }
                if (inspect) HskGlassSurface(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
                    shape = RoundedCornerShape(14.dp),
                    shadowElevation = 4.dp,
                ) {
                    Text(screen.details.ifBlank { screen.title },
                        Modifier.heightIn(max = 132.dp).verticalScroll(rememberScrollState()).padding(12.dp),
                        style = MaterialTheme.typography.bodySmall, color = PompColors.InkSecondary)
                }
            }
            if (state.loading) LinearProgressIndicator(Modifier.fillMaxWidth().padding(top = 4.dp), color = PompColors.Cinnabar, trackColor = PompColors.Divider)
            Box(Modifier.weight(1f).fillMaxWidth()) {
                if (history) AssistantConversations(
                    items = state.conversations,
                    currentId = state.conversationId,
                    enabled = !state.busy && !state.loading,
                    onSelect = { app.assistant.selectConversation(it); history = false },
                    onNew = { app.assistant.selectConversation(); history = false },
                ) else LazyColumn(
                    Modifier.fillMaxSize(), state = list,
                    verticalArrangement = Arrangement.spacedBy(14.dp),
                    contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 10.dp, bottom = 14.dp),
                ) {
                    if (state.nextCursor.isNotBlank()) item {
                        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                            AssistantChip(stringResource(R.string.assistant_older), onClick = app.assistant::older)
                        }
                    }
                    if (state.turns.isEmpty() && !state.loading) item {
                        Column(
                            Modifier.fillMaxWidth().padding(top = 22.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(14.dp),
                        ) {
                            AssistantAvatar(52.dp)
                            Text(stringResource(R.string.assistant_intro), style = MaterialTheme.typography.titleMedium,
                                color = PompColors.Ink, textAlign = TextAlign.Center)
                            FlowRow(
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                val suggestions = if (screen.screen in setOf("exam", "challenge")) listOf(R.string.assistant_how)
                                    else listOf(R.string.assistant_simple, R.string.assistant_example, R.string.assistant_mistake)
                                suggestions.forEach { label ->
                                    val text = stringResource(label)
                                    AssistantChip(text, onClick = { app.assistant.edit(text) })
                                }
                            }
                        }
                    }
                    items(state.turns, key = { it.clientMessageId }) { turn ->
                        Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            AssistantUserBubble(turn)
                            when {
                                turn.text.isNotBlank() -> AssistantAnswerBubble(turn, onAction)
                                turn.status == "processing" -> AssistantAnswerFrame {
                                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                        AssistantTypingDots()
                                        Text(stringResource(when (turn.phase) {
                                            "transcribing" -> R.string.assistant_transcribing
                                            "analyzing" -> R.string.assistant_analyzing
                                            else -> R.string.assistant_answering
                                        }), style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary)
                                    }
                                }
                                turn.status == "failed" -> AssistantAnswerFrame {
                                    Text(assistantError(turn.error), style = MaterialTheme.typography.bodyMedium, color = PompColors.CinnabarDark)
                                }
                            }
                        }
                    }
                }
            }
            if (state.error.isNotBlank()) Surface(
                color = PompColors.CinnabarSoft, shape = RoundedCornerShape(14.dp),
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
            ) {
                Row(Modifier.padding(start = 12.dp, end = 4.dp, top = 4.dp, bottom = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(assistantError(state.error), Modifier.weight(1f), style = MaterialTheme.typography.bodySmall, color = PompColors.CinnabarDark)
                    // A queued question that never resolves must not lock the chat.
                    if (state.queued) TextButton(onClick = app.assistant::discard, enabled = !state.busy) {
                        Text(stringResource(R.string.assistant_cancel), color = PompColors.InkSecondary)
                    }
                    TextButton(onClick = app.assistant::retry, enabled = !state.busy) {
                        Text(stringResource(R.string.assistant_retry), color = PompColors.Cinnabar)
                    }
                }
            }
            if (state.media.isNotBlank()) Row(
                Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                if (state.mediaKind == "image") {
                    val bitmap = remember(state.media) { runCatching {
                        val bytes = Base64.decode(state.media.substringAfter(','), Base64.DEFAULT)
                        BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                    }.getOrNull() }
                    if (bitmap != null) Image(bitmap.asImageBitmap(), stringResource(R.string.assistant_photo),
                        Modifier.size(46.dp).clip(RoundedCornerShape(12.dp)), contentScale = ContentScale.Crop)
                    Text(stringResource(R.string.assistant_photo), Modifier.weight(1f),
                        style = MaterialTheme.typography.bodySmall, color = PompColors.InkSecondary, maxLines = 1, overflow = TextOverflow.Ellipsis)
                } else {
                    AssistantChip(stringResource(R.string.assistant_listen), onClick = {
                        stopPreview()
                        runCatching {
                            val file = File.createTempFile("assistant-preview-", ".m4a", context.cacheDir)
                            previewFile = file
                            file.writeBytes(Base64.decode(state.media.substringAfter(','), Base64.DEFAULT))
                            player = MediaPlayer().apply { setDataSource(file.path); prepare(); start(); setOnCompletionListener { stopPreview() } }
                        }.onFailure { stopPreview(); app.assistant.error("assistant_no_speech") }
                    }, icon = { Icon(Icons.Default.PlayArrow, null, Modifier.size(16.dp), tint = PompColors.Cinnabar) })
                    Spacer(Modifier.weight(1f))
                }
                IconButton(onClick = { stopPreview(); app.assistant.media("", "text") }, enabled = !state.busy, modifier = Modifier.size(34.dp)) {
                    Icon(Icons.Default.Close, stringResource(R.string.assistant_remove), Modifier.size(17.dp), tint = PompColors.InkSecondary)
                }
            }
            if (recording) Row(
                Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                AssistantTypingDots()
                Spacer(Modifier.width(10.dp))
                Text(stringResource(R.string.assistant_recording), Modifier.weight(1f),
                    style = MaterialTheme.typography.bodySmall, color = PompColors.InkSecondary)
                TextButton(onClick = { app.voiceRecorder.cancel(); recording = false }) {
                    Text(stringResource(R.string.assistant_cancel), color = PompColors.InkSecondary)
                }
                TextButton(onClick = ::finishRecording) { Text(stringResource(R.string.assistant_stop), color = PompColors.Cinnabar) }
            }
            Row(
                Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, top = 4.dp, bottom = 10.dp),
                verticalAlignment = Alignment.Bottom,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                HskGlassSurface(
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(24.dp),
                    shadowElevation = 4.dp,
                ) {
                    Row(Modifier.padding(horizontal = 4.dp), verticalAlignment = Alignment.Bottom) {
                        IconButton(
                            onClick = { photo.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)) },
                            enabled = !state.busy && !recording && !preparing, modifier = Modifier.size(44.dp),
                        ) { Icon(Icons.Default.AddPhotoAlternate, stringResource(R.string.assistant_photo), Modifier.size(21.dp), tint = PompColors.InkSecondary) }
                        Box(Modifier.weight(1f).padding(vertical = 12.dp), contentAlignment = Alignment.CenterStart) {
                            if (state.draft.isEmpty()) Text(stringResource(R.string.assistant_hint),
                                style = MaterialTheme.typography.bodyLarge, color = PompColors.InkDisabled,
                                maxLines = 1, overflow = TextOverflow.Ellipsis)
                            BasicTextField(
                                value = state.draft,
                                onValueChange = app.assistant::edit,
                                enabled = !state.busy && !recording,
                                textStyle = MaterialTheme.typography.bodyLarge.copy(color = PompColors.Ink),
                                cursorBrush = SolidColor(PompColors.Cinnabar),
                                maxLines = 5,
                                modifier = Modifier.fillMaxWidth(),
                            )
                        }
                        IconButton(
                            onClick = {
                                if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) startRecording()
                                else permission.launch(Manifest.permission.RECORD_AUDIO)
                            },
                            enabled = !state.busy && !recording && !preparing, modifier = Modifier.size(44.dp),
                        ) { Icon(Icons.Default.Mic, stringResource(R.string.assistant_voice), Modifier.size(21.dp), tint = PompColors.InkSecondary) }
                    }
                }
                Surface(
                    onClick = { stopPreview(); app.assistant.send(if (includeContext) screen else ScreenContext()) },
                    enabled = canSend, shape = CircleShape,
                    color = if (canSend) PompColors.Cinnabar else PompColors.Divider,
                    modifier = Modifier.size(46.dp),
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        if (state.busy || preparing) HskBrandLoader(compact = true)
                        else Icon(Icons.AutoMirrored.Filled.Send, stringResource(R.string.assistant_send), Modifier.size(19.dp),
                            tint = if (canSend) PompColors.Paper else PompColors.InkDisabled)
                    }
                }
            }
        }
    }
}

/** Keep the encoded photo comfortably inside the server request budget. */
private const val MAX_PHOTO_BYTES = 3 * 1024 * 1024

@Composable
private fun AssistantDragHandle() {
    Box(Modifier.fillMaxWidth().padding(top = 12.dp, bottom = 6.dp), contentAlignment = Alignment.Center) {
        Box(Modifier.size(width = 38.dp, height = 4.dp).clip(CircleShape).background(PompColors.Divider))
    }
}

@Composable
private fun AssistantAvatar(size: Dp) {
    Box(
        Modifier.size(size).clip(CircleShape).background(PompColors.Cinnabar),
        contentAlignment = Alignment.Center,
    ) {
        Text("AI", color = PompColors.Paper, style = MaterialTheme.typography.labelLarge)
    }
}

@Composable
private fun AssistantChip(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    selected: Boolean = false,
    enabled: Boolean = true,
    maxLines: Int = 2,
    icon: (@Composable () -> Unit)? = null,
) {
    Surface(
        onClick = onClick,
        enabled = enabled,
        shape = RoundedCornerShape(999.dp),
        color = if (selected) PompColors.CinnabarSoft else PompColors.PaperRaised,
        contentColor = if (selected) PompColors.CinnabarDark else PompColors.Ink,
        border = BorderStroke(1.dp, if (selected) PompColors.Cinnabar.copy(alpha = .4f) else PompColors.Divider),
        modifier = modifier,
    ) {
        Row(
            Modifier.padding(horizontal = 13.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            icon?.invoke()
            Text(text, style = MaterialTheme.typography.labelLarge, maxLines = maxLines, overflow = TextOverflow.Ellipsis)
        }
    }
}

@Composable
private fun bubbleMaxWidth(): Dp = (LocalConfiguration.current.screenWidthDp * .8f).dp

@Composable
private fun AssistantUserBubble(turn: AssistantTurn) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
        Surface(
            color = PompColors.CinnabarSoft,
            contentColor = PompColors.Ink,
            shape = RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp, bottomEnd = 6.dp, bottomStart = 20.dp),
            modifier = Modifier.widthIn(max = bubbleMaxWidth()),
        ) {
            Column(Modifier.padding(horizontal = 14.dp, vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                if (turn.context.title.isNotBlank()) Text(turn.context.title,
                    style = MaterialTheme.typography.labelSmall, color = PompColors.InkSecondary,
                    maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(turn.userText.ifBlank {
                    if (turn.kind == "voice") stringResource(R.string.assistant_voice) else stringResource(R.string.assistant_photo)
                }, style = MaterialTheme.typography.bodyLarge)
                if (turn.transcript.isNotBlank()) Text(turn.transcript,
                    style = MaterialTheme.typography.bodySmall, color = PompColors.InkSecondary)
            }
        }
    }
}

/** Left-aligned answer slot: avatar plus a card, shared by text, typing and error states. */
@Composable
private fun AssistantAnswerFrame(content: @Composable ColumnScope.() -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
        AssistantAvatar(28.dp)
        Spacer(Modifier.width(8.dp))
        HskGlassSurface(
            modifier = Modifier.widthIn(max = bubbleMaxWidth()),
            shape = RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp, bottomEnd = 20.dp, bottomStart = 6.dp),
            shadowElevation = 4.dp,
        ) {
            Column(Modifier.padding(horizontal = 14.dp, vertical = 11.dp), verticalArrangement = Arrangement.spacedBy(10.dp), content = content)
        }
    }
}

@Composable
private fun AssistantAnswerBubble(turn: AssistantTurn, onAction: (AssistantAction) -> Unit) {
    AssistantAnswerFrame {
        Text(turn.text, style = MaterialTheme.typography.bodyLarge, color = PompColors.Ink)
        turn.sources.forEach { source ->
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                Icon(Icons.AutoMirrored.Filled.MenuBook, null, Modifier.size(13.dp), tint = PompColors.InkDisabled)
                Text(source.label, style = MaterialTheme.typography.labelSmall, color = PompColors.InkSecondary)
            }
        }
        turn.actions.forEach { action ->
            AssistantChip(action.label, onClick = { onAction(action) }, selected = true,
                icon = { Icon(Icons.AutoMirrored.Filled.Send, null, Modifier.size(14.dp), tint = PompColors.Cinnabar) })
        }
        if (turn.status == "failed" && turn.error.isNotBlank()) Text(assistantError(turn.error),
            style = MaterialTheme.typography.bodySmall, color = PompColors.CinnabarDark)
    }
}

@Composable
private fun AssistantTypingDots() {
    val transition = rememberInfiniteTransition(label = "assistant-typing")
    Row(horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.CenterVertically) {
        repeat(3) { index ->
            val alpha by transition.animateFloat(
                initialValue = .22f,
                targetValue = 1f,
                animationSpec = infiniteRepeatable(tween(560, delayMillis = index * 150), RepeatMode.Reverse),
                label = "assistant-dot-$index",
            )
            Box(Modifier.size(7.dp).clip(CircleShape).background(PompColors.Cinnabar.copy(alpha = alpha)))
        }
    }
}

/** Saved chats, the way learners already expect them from other assistants. */
@Composable
private fun AssistantConversations(
    items: List<AssistantConversation>,
    currentId: String,
    enabled: Boolean,
    onSelect: (String) -> Unit,
    onNew: () -> Unit,
) {
    LazyColumn(
        Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(8.dp),
        contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 10.dp, bottom = 14.dp),
    ) {
        item {
            Surface(
                onClick = onNew,
                enabled = enabled,
                shape = RoundedCornerShape(16.dp),
                color = PompColors.CinnabarSoft,
                contentColor = PompColors.CinnabarDark,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Icon(Icons.Default.Add, null, Modifier.size(19.dp), tint = PompColors.Cinnabar)
                    Text(stringResource(R.string.assistant_new), style = MaterialTheme.typography.titleMedium)
                }
            }
        }
        if (items.isEmpty()) item {
            Text(stringResource(R.string.assistant_no_conversations),
                Modifier.fillMaxWidth().padding(top = 24.dp),
                style = MaterialTheme.typography.bodyMedium, color = PompColors.InkSecondary, textAlign = TextAlign.Center)
        }
        items(items, key = { it.id }) { conversation ->
            val active = conversation.id == currentId
            Surface(
                onClick = { onSelect(conversation.id) },
                enabled = enabled,
                shape = RoundedCornerShape(16.dp),
                color = PompColors.PaperRaised,
                contentColor = PompColors.Ink,
                border = BorderStroke(if (active) 2.dp else 1.dp, if (active) PompColors.Cinnabar else PompColors.Divider),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Icon(Icons.Default.ChatBubbleOutline, null, Modifier.size(17.dp),
                        tint = if (active) PompColors.Cinnabar else PompColors.InkDisabled)
                    Text(conversation.title, Modifier.weight(1f), style = MaterialTheme.typography.bodyLarge,
                        maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
            }
        }
    }
}

@Composable private fun assistantError(code: String): String = stringResource(when (code) {
    "assistant_microphone" -> R.string.assistant_mic_denied
    "assistant_mic_busy" -> R.string.assistant_mic_busy
    "assistant_no_speech" -> R.string.assistant_no_speech
    "assistant_media_invalid" -> R.string.assistant_bad_photo
    "assistant_timeout" -> R.string.assistant_timeout
    "free_feature_limit_reached", "daily_limit_reached", "ai_budget_exhausted", "subscription_required" -> R.string.assistant_limit
    else -> R.string.assistant_network
})
