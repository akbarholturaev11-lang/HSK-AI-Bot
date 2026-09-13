package com.pomp.hskai.feature.assistant

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import android.media.MediaPlayer
import android.util.Base64
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.DialogProperties
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.R
import com.pomp.hskai.core.auth.AuthState
import com.pomp.hskai.core.design.PompColors
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
        Box(Modifier.fillMaxSize()) {
            // A dedicated shelf in inner screens keeps the FAB away from answer/next controls.
            Box(Modifier.fillMaxSize().padding(bottom = if (availableOnScreen && visible?.bottomBar == false) 80.dp else 0.dp)) { content() }
            if (availableOnScreen && !open) AssistantButton(
                onClick = binding.open,
                modifier = Modifier.align(Alignment.BottomEnd).padding(end = 16.dp, bottom = if (visible?.bottomBar == true) 110.dp else 16.dp).navigationBarsPadding(),
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

/** Sheets are separate windows; give them their own entry, using the same chat/controller. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AssistantModalBottomSheet(
    onDismissRequest: () -> Unit,
    modifier: Modifier = Modifier,
    sheetState: SheetState = rememberModalBottomSheetState(),
    containerColor: Color = PompColors.Paper,
    content: @Composable ColumnScope.() -> Unit,
) {
    ModalBottomSheet(onDismissRequest, modifier, sheetState = sheetState, containerColor = containerColor) {
        content()
        val binding = LocalAssistant.current
        val state = binding?.controller?.state?.collectAsStateWithLifecycle()?.value
        if (state?.enabled == true) Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.End) {
            AssistantButton(onClick = binding.open)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
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
                    val stream = ByteArrayOutputStream()
                    scaled.compress(android.graphics.Bitmap.CompressFormat.JPEG, 88, stream)
                    scaled.recycle()
                    require(stream.size() <= 5 * 1024 * 1024)
                    "data:image/jpeg;base64," + Base64.encodeToString(stream.toByteArray(), Base64.NO_WRAP)
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
    LaunchedEffect(state.turns.lastOrNull(), state.busy) { if (state.turns.isNotEmpty()) list.animateScrollToItem(state.turns.lastIndex) }
    ModalBottomSheet(
        onDismissRequest = onClose,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        containerColor = PompColors.Paper,
        dragHandle = null,
    ) {
        Column(Modifier.fillMaxWidth().height((LocalConfiguration.current.screenHeightDp * if (expanded) 1f else .8f).dp).imePadding().padding(horizontal = 16.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text("HSK AI", style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f))
                IconButton(onClick = { history = !history }) { Icon(Icons.Default.History, stringResource(R.string.assistant_history)) }
                IconButton(onClick = { app.assistant.selectConversation(); history = false }, enabled = !state.busy && !state.loading) { Icon(Icons.Default.Add, stringResource(R.string.assistant_new)) }
                IconButton(onClick = { expanded = !expanded }) { Icon(if (expanded) Icons.Default.FullscreenExit else Icons.Default.Fullscreen, stringResource(R.string.assistant_expand)) }
                IconButton(onClick = onClose) { Icon(Icons.Default.Close, stringResource(R.string.assistant_close)) }
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(if (includeContext) screen.title else stringResource(R.string.assistant_general), Modifier.weight(1f).clickable { inspect = !inspect }, maxLines = 2, style = MaterialTheme.typography.labelLarge, color = PompColors.InkSecondary)
                Switch(checked = includeContext, onCheckedChange = { includeContext = it }, modifier = Modifier.semantics { contentDescription = context.getString(R.string.assistant_context) })
            }
            if (inspect) LazyColumn(Modifier.heightIn(max = 160.dp)) { item { Text(screen.details.ifBlank { screen.title }, style = MaterialTheme.typography.bodySmall) } }
            if (history) LazyColumn(Modifier.heightIn(max = 180.dp)) {
                items(state.conversations, key = { it.id }) { conversation ->
                    TextButton(onClick = { app.assistant.selectConversation(conversation.id); history = false }, enabled = !state.busy) { Text(conversation.title) }
                }
            }
            if (state.loading) LinearProgressIndicator(Modifier.fillMaxWidth(), color = PompColors.Cinnabar)
            LazyColumn(Modifier.weight(1f).fillMaxWidth(), state = list, verticalArrangement = Arrangement.spacedBy(12.dp), contentPadding = PaddingValues(vertical = 12.dp)) {
                if (state.nextCursor.isNotBlank()) item { TextButton(onClick = app.assistant::older) { Text(stringResource(R.string.assistant_older)) } }
                if (state.turns.isEmpty() && !state.loading) item {
                    Text(stringResource(R.string.assistant_intro), style = MaterialTheme.typography.bodyLarge)
                    val suggestions = if (screen.screen in setOf("exam", "challenge")) listOf(R.string.assistant_how) else listOf(R.string.assistant_simple, R.string.assistant_example, R.string.assistant_mistake)
                    suggestions.forEach { label ->
                        val text = stringResource(label)
                        TextButton(onClick = { app.assistant.edit(text) }) { Text(text) }
                    }
                }
                items(state.turns, key = { it.clientMessageId }) { turn ->
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Surface(color = PompColors.CinnabarSoft, shape = MaterialTheme.shapes.large, modifier = Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(12.dp)) {
                                if (turn.context.title.isNotBlank()) Text(turn.context.title, style = MaterialTheme.typography.labelSmall, color = PompColors.InkSecondary)
                                Text(turn.userText.ifBlank { if (turn.kind == "voice") stringResource(R.string.assistant_voice) else stringResource(R.string.assistant_photo) })
                                if (turn.transcript.isNotBlank()) Text(turn.transcript, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                        if (turn.text.isNotBlank()) Text(turn.text, color = PompColors.Ink)
                        turn.sources.forEach { Text(it.label, style = MaterialTheme.typography.labelSmall, color = PompColors.InkSecondary) }
                        turn.actions.forEach { action -> OutlinedButton(onClick = { onAction(action) }) { Text(action.label) } }
                        if (turn.status == "processing") Text(stringResource(when (turn.phase) {
                            "transcribing" -> R.string.assistant_transcribing
                            "analyzing" -> R.string.assistant_analyzing
                            else -> R.string.assistant_answering
                        }), color = PompColors.InkSecondary)
                        if (turn.status == "failed") Text(assistantError(turn.error), color = PompColors.CinnabarDark)
                    }
                }
            }
            if (state.error.isNotBlank()) Row(verticalAlignment = Alignment.CenterVertically) {
                Text(assistantError(state.error), Modifier.weight(1f), style = MaterialTheme.typography.bodySmall, color = PompColors.CinnabarDark)
                TextButton(onClick = app.assistant::retry, enabled = !state.busy) { Text(stringResource(R.string.assistant_retry)) }
            }
            if (state.media.isNotBlank()) Row(verticalAlignment = Alignment.CenterVertically) {
                if (state.mediaKind == "image") {
                    val bitmap = remember(state.media) { runCatching {
                        val bytes = Base64.decode(state.media.substringAfter(','), Base64.DEFAULT)
                        android.graphics.BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                    }.getOrNull() }
                    if (bitmap != null) Image(bitmap.asImageBitmap(), stringResource(R.string.assistant_photo), Modifier.size(56.dp))
                } else TextButton(onClick = {
                    stopPreview()
                    runCatching {
                        val file = File.createTempFile("assistant-preview-", ".m4a", context.cacheDir)
                        previewFile = file
                        file.writeBytes(Base64.decode(state.media.substringAfter(','), Base64.DEFAULT))
                        player = MediaPlayer().apply { setDataSource(file.path); prepare(); start(); setOnCompletionListener { stopPreview() } }
                    }.onFailure { stopPreview(); app.assistant.error("assistant_no_speech") }
                }) { Text(stringResource(R.string.assistant_listen)) }
                IconButton(onClick = { stopPreview(); app.assistant.media("", "text") }, enabled = !state.busy) { Icon(Icons.Default.Close, stringResource(R.string.assistant_remove)) }
            }
            if (recording) Row(verticalAlignment = Alignment.CenterVertically) {
                Text(stringResource(R.string.assistant_recording), Modifier.weight(1f))
                TextButton(onClick = { app.voiceRecorder.cancel(); recording = false }) { Text(stringResource(R.string.assistant_cancel)) }
                TextButton(onClick = ::finishRecording) { Text(stringResource(R.string.assistant_stop)) }
            }
            OutlinedTextField(value = state.draft, onValueChange = app.assistant::edit, modifier = Modifier.fillMaxWidth(), maxLines = 4,
                placeholder = { Text(stringResource(R.string.assistant_hint)) }, enabled = !state.busy && !recording)
            Row(Modifier.fillMaxWidth().navigationBarsPadding(), verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = { photo.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)) }, enabled = !state.busy && !recording && !preparing) { Icon(Icons.Default.AddPhotoAlternate, stringResource(R.string.assistant_photo)) }
                IconButton(onClick = {
                    if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) startRecording()
                    else permission.launch(Manifest.permission.RECORD_AUDIO)
                }, enabled = !state.busy && !recording && !preparing) { Icon(Icons.Default.Mic, stringResource(R.string.assistant_voice)) }
                Spacer(Modifier.weight(1f))
                if (state.busy || preparing) Text(stringResource(R.string.assistant_sending), style = MaterialTheme.typography.labelSmall)
                IconButton(onClick = { stopPreview(); app.assistant.send(if (includeContext) screen else ScreenContext()) }, enabled = !state.busy && !state.loading && !recording && !preparing && (state.draft.isNotBlank() || state.media.isNotBlank())) { Icon(Icons.AutoMirrored.Filled.Send, stringResource(R.string.assistant_send), tint = PompColors.Cinnabar) }
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
