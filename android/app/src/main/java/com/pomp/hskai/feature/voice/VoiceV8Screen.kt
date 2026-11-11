package com.pomp.hskai.feature.voice

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.provider.Settings
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.AnimationSpec
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.Easing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.snap
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.isImeVisible
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.requiredSize
import androidx.compose.foundation.layout.requiredWidth
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.animation.core.withInfiniteAnimationFrameMillis
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.BlurredEdgeTreatment
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.BlendMode
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.ColorMatrix
import androidx.compose.ui.graphics.CompositingStrategy
import androidx.compose.ui.graphics.LinearGradientShader
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.Shader
import androidx.compose.ui.graphics.ShaderBrush
import androidx.compose.ui.graphics.Shadow
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.addOutline
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.layout
import androidx.compose.ui.layout.boundsInRoot
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.onClick
import androidx.compose.ui.semantics.onLongClick
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.semantics.toggleableState
import androidx.compose.ui.state.ToggleableState
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Constraints
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.min
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.core.view.WindowCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.R
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.feature.assistant.AssistantHidden
import com.pomp.hskai.feature.feedback.BugReportDialog
import com.pomp.hskai.feature.limit.LimitGate
import com.pomp.hskai.feature.limit.SectionLimitOverlay
import java.nio.ByteBuffer
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.pow
import kotlin.math.roundToInt
import kotlin.math.sign
import kotlin.math.sin
import kotlin.math.sqrt
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/*
 * AI Voice V8 — the native counterpart of app/static/iphone-pwa-voice.html,
 * which carries HSK_AI_Voice_Integrated_V8.html 1:1. Sizes are the reference's
 * CSS pixels as dp; easings are its cubic-bezier curves. Logic stays in
 * VoiceViewModel (Android voice API, Live socket, limits).
 */

/** The nine V8 topics and the backend partner each one talks to. */
internal enum class VoiceV8Topic(
    val id: String,
    val role: String,
    val titleRes: Int,
    val zh: String,
    val py: String,
    val glyph: String,
    val photoRes: Int,
) {
    FREE("free", "friend", R.string.hsk_course_voice_v8_topic_free, "自由聊天", "Zìyóu liáotiān", "聊", R.drawable.voice_v8_free),
    DAILY("daily", "roommate", R.string.hsk_course_voice_v8_topic_daily, "日常生活", "Rìcháng shēnghuó", "日", R.drawable.voice_v8_daily),
    SHOPPING("shopping", "seller", R.string.hsk_course_voice_v8_topic_shopping, "购物", "Gòuwù", "买", R.drawable.voice_v8_shopping),
    FOOD("food", "seller", R.string.hsk_course_voice_v8_topic_food, "在餐厅点餐", "Zài cāntīng diǎncān", "餐", R.drawable.voice_v8_food),
    TRAVEL("travel", "friend", R.string.hsk_course_voice_v8_topic_travel, "旅行问路", "Lǚxíng wènlù", "旅", R.drawable.voice_v8_travel),
    SCHOOL("school", "classmate", R.string.hsk_course_voice_v8_topic_school, "学校生活", "Xuéxiào shēnghuó", "学", R.drawable.voice_v8_school),
    FRIENDS("friends", "friend", R.string.hsk_course_voice_v8_topic_friends, "认识新朋友", "Rènshi xīn péngyou", "友", R.drawable.voice_v8_friends),
    WORK("work", "manager_wang", R.string.hsk_course_voice_v8_topic_work, "工作和生意", "Gōngzuò hé shēngyi", "商", R.drawable.voice_v8_work),
    HSK("hsk", "teacher_li", R.string.hsk_course_voice_v8_topic_hsk, "HSK口语练习", "HSK kǒuyǔ liànxí", "考", R.drawable.voice_v8_hsk);

    companion object {
        fun of(id: String?): VoiceV8Topic = entries.firstOrNull { it.id == id } ?: FREE

        /** Same entry rule as the PWA course: the HSK teacher opens the HSK topic. */
        fun forRole(role: String?): VoiceV8Topic = if (role == "teacher_li") HSK else FREE
    }
}

/** The V8 settings sheet; defaults match the PWA's stored switches. */
data class VoiceV8Prefs(
    val pinyin: Boolean = false,
    val translation: Boolean = true,
    val backdrop: Boolean = true,
)

/** What the V8 screen asks of VoiceViewModel. */
class VoiceV8Actions(
    val startFromMicrophone: (liveAllowed: Boolean) -> Unit,
    val startWithText: (String) -> Unit,
    val toggleRecording: () -> Unit,
    val sendText: (String) -> Unit,
    val endSession: () -> Unit,
    val changeTopic: (role: String) -> Unit,
    val selectRole: (String) -> Unit,
    val cancelRecording: () -> Unit,
    val restart: () -> Unit,
    val exit: () -> Unit,
)

internal enum class VoiceV8Status(val textRes: Int, val urgent: Boolean = false) {
    Connect(R.string.hsk_course_voice_v8_status_connect),
    Slow(R.string.hsk_course_voice_v8_status_slow, urgent = true),
    Reconnect(R.string.hsk_course_voice_v8_status_reconnect),
    Offline(R.string.hsk_course_voice_v8_status_offline, urgent = true),
    Mic(R.string.hsk_course_voice_v8_status_mic, urgent = true),
    Fail(R.string.hsk_course_voice_v8_status_fail, urgent = true),
    Login(R.string.hsk_course_voice_v8_status_login, urgent = true),
    Ready(R.string.hsk_course_voice_v8_status_ready),
    Listening(R.string.hsk_course_voice_v8_status_listening),
    Speaking(R.string.hsk_course_voice_v8_status_speaking),
    Thinking(R.string.hsk_course_voice_v8_status_thinking),
    Recording(R.string.hsk_course_voice_v8_status_recording),
    Turn(R.string.hsk_course_voice_v8_status_turn),
    End(R.string.hsk_course_voice_v8_status_end),
}

internal data class VoiceV8StatusLine(val status: VoiceV8Status, val messageRes: Int? = null)

internal val VOICE_V8_TOO_SHORT_CODES = setOf("TRANSCRIPTION_EMPTY", "EMPTY_AUDIO", "LIVE_TURN_EMPTY")

internal fun voiceV8QuotaExhausted(state: VoiceUiState): Boolean {
    val status = state.status ?: return false
    return !status.isPaid && state.remainingLimit == 0
}

/** The line under the orb: the PWA's `setState()` states, derived from the ViewModel. */
internal fun voiceV8Status(state: VoiceUiState, micDenied: Boolean, ended: Boolean): VoiceV8StatusLine {
    val noQuota = VoiceV8StatusLine(VoiceV8Status.Fail, R.string.hsk_course_voice_v8_no_quota)
    if (ended) return VoiceV8StatusLine(VoiceV8Status.End)
    if (micDenied) return VoiceV8StatusLine(VoiceV8Status.Mic)
    when (val error = state.error) {
        null -> Unit
        ApiError.Offline -> return VoiceV8StatusLine(VoiceV8Status.Offline)
        ApiError.Timeout -> return VoiceV8StatusLine(VoiceV8Status.Slow)
        ApiError.SessionExpired -> return VoiceV8StatusLine(VoiceV8Status.Login)
        is ApiError.LimitReached -> return noQuota
        is ApiError.Server -> if (error.code !in VOICE_V8_TOO_SHORT_CODES) {
            return VoiceV8StatusLine(VoiceV8Status.Fail)
        }
        else -> return VoiceV8StatusLine(VoiceV8Status.Fail)
    }
    if (state.status == null) {
        return VoiceV8StatusLine(if (state.isLoading) VoiceV8Status.Connect else VoiceV8Status.Fail)
    }
    if (state.isStarting || (state.isLoading && !state.hasSession)) return VoiceV8StatusLine(VoiceV8Status.Connect)
    if (!state.hasSession) {
        return if (voiceV8QuotaExhausted(state)) noQuota else VoiceV8StatusLine(VoiceV8Status.Ready)
    }
    val status = if (state.isLive) {
        when {
            state.isLiveConnecting ->
                if (state.isLiveReconnecting) VoiceV8Status.Reconnect else VoiceV8Status.Connect
            !state.isLiveConnected -> VoiceV8Status.Ready
            state.isSending -> VoiceV8Status.Thinking
            state.isAiSpeaking -> VoiceV8Status.Speaking
            state.isLiveMuted -> VoiceV8Status.Ready
            else -> VoiceV8Status.Listening
        }
    } else {
        when {
            state.isRecording -> VoiceV8Status.Recording
            state.isSending -> VoiceV8Status.Thinking
            state.isReplyPlaying -> VoiceV8Status.Speaking
            state.turnCount == 0 && !state.usedTurnFallback -> VoiceV8Status.Ready
            else -> VoiceV8Status.Turn
        }
    }
    return VoiceV8StatusLine(status)
}

/** One `.msg` of the transcript; a correction belongs under the learner's line. */
internal data class VoiceV8Message(
    val user: Boolean,
    val text: String,
    val pinyin: String = "",
    val translation: String = "",
    val correction: String = "",
    val source: VoiceLine? = null,
)

internal fun voiceV8Messages(lines: List<VoiceLine>): List<VoiceV8Message> {
    val out = ArrayList<VoiceV8Message>(lines.size)
    for (line in lines) {
        if (line.speaker == VoiceSpeaker.USER) {
            if (line.text.isNotBlank()) out += VoiceV8Message(user = true, text = line.text)
            continue
        }
        val fix = line.correction.orEmpty().trim()
        val previous = out.lastOrNull()
        if (fix.isNotEmpty() && previous != null && previous.user && previous.correction.isEmpty()) {
            out[out.lastIndex] = previous.copy(correction = fix)
        }
        val han = line.hanzi.ifBlank { line.text }
        if (han.isBlank()) continue
        out += VoiceV8Message(
            user = false,
            text = han,
            pinyin = line.pinyin.trim(),
            translation = (if (line.hanzi.isBlank()) "" else line.translation.ifBlank { line.text }).trim(),
            source = line,
        )
    }
    return out
}

private enum class V8Layer { Topics, Settings, Plus }

private val Red = Color(0xFFE04A40)
private val EaseOrb = CubicBezierEasing(0.23f, 1f, 0.32f, 1f)
private val EaseSpring = CubicBezierEasing(0.2f, 1.19f, 0.32f, 1f)
private val EaseDrawer = CubicBezierEasing(0.22f, 1f, 0.36f, 1f)
private val EaseRelease = CubicBezierEasing(0.18f, 1.22f, 0.26f, 1f)
private val EaseRebound = CubicBezierEasing(0.22f, 0.89f, 0.25f, 1f)
private val EaseCss = CubicBezierEasing(0.25f, 0.1f, 0.25f, 1f)
private val EaseInOut = CubicBezierEasing(0.42f, 0f, 0.58f, 1f)

private const val MAX_CHARS = 200

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun VoiceV8Screen(
    state: VoiceUiState,
    topicId: String,
    onTopicSelected: (String) -> Unit,
    prefs: VoiceV8Prefs,
    onPrefsChange: (VoiceV8Prefs) -> Unit,
    limit: LimitGate,
    actions: VoiceV8Actions,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val density = LocalDensity.current
    val focusManager = LocalFocusManager.current
    val reduced = remember {
        Settings.Global.getFloat(context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f
    }
    val topic = VoiceV8Topic.of(topicId)
    val latestState by rememberUpdatedState(state)
    val latestActions by rememberUpdatedState(actions)

    var chat by rememberSaveable { mutableStateOf(false) }
    var endedLocally by rememberSaveable { mutableStateOf(false) }
    var micDenied by rememberSaveable { mutableStateOf(false) }
    var layer by rememberSaveable { mutableStateOf<V8Layer?>(null) }
    var endModal by rememberSaveable { mutableStateOf(false) }
    var limitOpen by rememberSaveable { mutableStateOf(false) }
    var prompt by rememberSaveable { mutableStateOf("") }
    var promptFocused by remember { mutableStateOf(false) }
    var lastSubmitted by remember { mutableStateOf<String?>(null) }
    var toast by remember { mutableStateOf<Int?>(null) }
    var toastSerial by remember { mutableLongStateOf(0L) }
    var reportedAnswer by remember { mutableStateOf<Pair<String, VoiceLine>?>(null) }
    val promptFocus = remember { FocusRequester() }

    val ended = endedLocally || state.result != null
    val typing = promptFocused && !ended
    val busy = state.isStarting || state.isSending
    val statusLine = voiceV8Status(state, micDenied, ended)
    val messages = remember(state.lines) { voiceV8Messages(state.lines) }

    fun showToast(res: Int) {
        toast = res
        toastSerial++
    }

    AssistantHidden()

    // Opening the screen talks to the topic's partner.
    LaunchedEffect(topic) { if (!latestState.hasSession) latestActions.selectRole(topic.role) }

    // Dark system bars over the black call surface; restored on leave.
    val view = LocalView.current
    DisposableEffect(view) {
        val window = view.context.findActivity()?.window
        val controller = window?.let { WindowCompat.getInsetsController(it, view) }
        val lightStatus = controller?.isAppearanceLightStatusBars
        val lightNav = controller?.isAppearanceLightNavigationBars
        controller?.isAppearanceLightStatusBars = false
        controller?.isAppearanceLightNavigationBars = false
        onDispose {
            lightStatus?.let { controller.isAppearanceLightStatusBars = it }
            lightNav?.let { controller.isAppearanceLightNavigationBars = it }
        }
    }

    // A hidden app ends a Live call and drops an unfinished recording.
    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event != Lifecycle.Event.ON_STOP) return@LifecycleEventObserver
            val current = latestState
            if (current.isLive && current.hasSession) {
                layer = null
                endModal = false
                endedLocally = true
                latestActions.endSession()
            } else if (current.isRecording) {
                latestActions.cancelRecording()
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    LaunchedEffect(toastSerial) {
        if (toast != null) {
            delay(2_600)
            toast = null
        }
    }
    LaunchedEffect(state.error) {
        val error = state.error ?: return@LaunchedEffect
        lastSubmitted?.let { if (prompt.isEmpty()) prompt = it }
        lastSubmitted = null
        when {
            error is ApiError.LimitReached -> limitOpen = true
            error is ApiError.Server && error.code in VOICE_V8_TOO_SHORT_CODES ->
                showToast(R.string.hsk_course_course_voice_inline_too_short)
        }
    }
    LaunchedEffect(state.turnCount) { lastSubmitted = null }

    // A soft keyboard closed with Back leaves the field; the footer settles.
    val imeVisible = WindowInsets.isImeVisible
    var imeSeen by remember { mutableStateOf(false) }
    LaunchedEffect(imeVisible, promptFocused) {
        if (imeVisible && promptFocused) imeSeen = true
        if (!imeVisible && imeSeen) {
            imeSeen = false
            if (promptFocused) focusManager.clearFocus()
        }
    }

    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        micDenied = !granted
        if (!granted) return@rememberLauncherForActivityResult
        val current = latestState
        when {
            current.hasSession ->
                if (!current.isLive && !current.isRecording && current.canAnswer) latestActions.toggleRecording()
            !current.isStarting -> latestActions.startFromMicrophone(current.status?.liveAvailable == true)
        }
    }

    fun micGranted(): Boolean =
        ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) ==
            PackageManager.PERMISSION_GRANTED

    fun closeLayers() {
        endModal = false
        layer = null
    }

    fun recordingAction() {
        if (ended) return
        val current = latestState
        if (current.hasSession) {
            if (!current.isLive && busy) return
            // A conversation opened by text has not asked for the microphone yet.
            if (!current.isLive && !current.isRecording && !micGranted()) {
                permission.launch(Manifest.permission.RECORD_AUDIO)
                return
            }
            latestActions.toggleRecording()
            return
        }
        if (busy) return
        if (voiceV8QuotaExhausted(current)) {
            limitOpen = true
            return
        }
        if (micGranted()) {
            micDenied = false
            latestActions.startFromMicrophone(current.status?.liveAvailable == true)
        } else {
            permission.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    fun submit() {
        val value = prompt.trim()
        if (value.isEmpty() || busy || ended) return
        if (value.length > MAX_CHARS) {
            showToast(R.string.hsk_course_voice_v8_max_chars)
            return
        }
        val current = latestState
        if (!current.hasSession && voiceV8QuotaExhausted(current)) {
            limitOpen = true
            return
        }
        prompt = ""
        lastSubmitted = value
        focusManager.clearFocus()
        chat = true
        if (current.hasSession) latestActions.sendText(value) else latestActions.startWithText(value)
    }

    fun finish() {
        closeLayers()
        focusManager.clearFocus()
        endedLocally = true
        latestActions.endSession()
    }

    fun selectTopic(next: VoiceV8Topic) {
        if (busy || next == topic) return
        layer = null
        onTopicSelected(next.id)
        latestActions.changeTopic(next.role)
        endedLocally = false
        micDenied = false
        chat = false
        showToast(R.string.hsk_course_voice_v8_topic_changed)
    }

    BackHandler {
        when {
            limitOpen -> Unit
            endModal -> endModal = false
            layer != null -> layer = null
            promptFocused -> focusManager.clearFocus()
            else -> latestActions.exit()
        }
    }

    // --- geometry ---------------------------------------------------------
    val safeTop = with(density) { WindowInsets.statusBars.getTop(this).toDp() }
    val navBottom = with(density) { WindowInsets.navigationBars.getBottom(this).toDp() }
    val imeBottom = with(density) { WindowInsets.ime.getBottom(this).toDp() }
    val keyboard = imeBottom > navBottom
    val safeBottom = if (keyboard) 0.dp else navBottom

    Box(modifier.fillMaxSize().background(Color.Black)) {
        BoxWithConstraints(
            Modifier
                .fillMaxSize()
                .padding(bottom = if (keyboard) imeBottom else 0.dp),
        ) {
            val framed = maxWidth >= 480.dp
            val appWidth = if (framed) 430.dp else maxWidth
            val appHeight = if (framed) min(900.dp, maxHeight * 0.96f) else maxHeight
            Box(
                Modifier
                    .align(Alignment.Center)
                    .size(appWidth, appHeight)
                    .then(
                        if (framed) Modifier
                            .clip(RoundedCornerShape(44.dp))
                            .border(1.dp, Color(0xFF262626), RoundedCornerShape(44.dp))
                        else Modifier.clip(RoundedCornerShape(0.dp)),
                    )
                    .background(Color.Black),
            ) {
                V8App(
                    width = appWidth,
                    height = appHeight,
                    safeTop = if (framed) 0.dp else safeTop,
                    safeBottom = if (framed) 0.dp else safeBottom,
                    reduced = reduced,
                    state = state,
                    topic = topic,
                    prefs = prefs,
                    chat = chat,
                    typing = typing,
                    ended = ended,
                    busy = busy,
                    statusLine = statusLine,
                    toast = toast,
                    messages = messages,
                    layer = layer,
                    endModal = endModal,
                    prompt = prompt,
                    promptFocus = promptFocus,
                    onPromptChange = { prompt = it.take(400) },
                    onPromptFocus = { focused ->
                        promptFocused = focused
                        if (focused) chat = true
                    },
                    onChat = { chat = it },
                    onLayer = { next ->
                        if (next == V8Layer.Topics || next == V8Layer.Plus) focusManager.clearFocus()
                        layer = next
                    },
                    onEndModal = { endModal = it },
                    onSubmit = ::submit,
                    onExample = { text ->
                        layer = null
                        prompt = text
                        submit()
                    },
                    onMic = ::recordingAction,
                    onFinish = ::finish,
                    onRestart = {
                        if (!busy) {
                            endedLocally = false
                            micDenied = false
                            chat = false
                            prompt = ""
                            latestActions.restart()
                        }
                    },
                    onTopic = ::selectTopic,
                    onPrefsChange = onPrefsChange,
                    onReport = { line -> reportedAnswer = state.sessionId.orEmpty() to line },
                )
            }
        }

        if (limitOpen) {
            SectionLimitOverlay(
                sectionTitle = stringResource(R.string.nav_ai),
                sourceKey = "voice_limit",
                limit = limit,
                reason = state.status?.limitStatus?.limitText ?: stringResource(R.string.limit_voice_reason),
                resetAt = state.status?.resetAt,
                onClose = {
                    limitOpen = false
                    // PWA inline Pro bridge: closing the offer unpaid leaves Voice.
                    if (latestState.status?.isPaid != true) latestActions.exit()
                },
            )
        }
    }

    reportedAnswer?.let { (sessionId, line) ->
        BugReportDialog(
            repository = (context.applicationContext as HskAiApplication).featureRepository,
            screenshot = null,
            screen = "ai_voice",
            initialDescription = context.getString(
                R.string.assistant_report_prefill,
                sessionId.take(80),
                listOf(line.hanzi, line.pinyin, line.text, line.translation, line.correction.orEmpty())
                    .filter { it.isNotBlank() }.distinct().joinToString("\n").take(350),
            ),
            onDismiss = { reportedAnswer = null },
        )
    }
}

@Composable
private fun V8App(
    width: Dp,
    height: Dp,
    safeTop: Dp,
    safeBottom: Dp,
    reduced: Boolean,
    state: VoiceUiState,
    topic: VoiceV8Topic,
    prefs: VoiceV8Prefs,
    chat: Boolean,
    typing: Boolean,
    ended: Boolean,
    busy: Boolean,
    statusLine: VoiceV8StatusLine,
    toast: Int?,
    messages: List<VoiceV8Message>,
    layer: V8Layer?,
    endModal: Boolean,
    prompt: String,
    promptFocus: FocusRequester,
    onPromptChange: (String) -> Unit,
    onPromptFocus: (Boolean) -> Unit,
    onChat: (Boolean) -> Unit,
    onLayer: (V8Layer?) -> Unit,
    onEndModal: (Boolean) -> Unit,
    onSubmit: () -> Unit,
    onExample: (String) -> Unit,
    onMic: () -> Unit,
    onFinish: () -> Unit,
    onRestart: () -> Unit,
    onTopic: (VoiceV8Topic) -> Unit,
    onPrefsChange: (VoiceV8Prefs) -> Unit,
    onReport: (VoiceLine) -> Unit,
) {
    val narrow = width <= 380.dp
    val drawerFraction = if (narrow) 0.83f else 0.8f
    val drawerOpen = layer == V8Layer.Topics
    val drawer by animateFloatAsState(if (drawerOpen) 1f else 0f, spec(reduced, 400, EaseDrawer), label = "drawer")

    Box(Modifier.fillMaxSize()) {
        // #voiceScreen: everything the side drawer pushes aside.
        Box(
            Modifier
                .fillMaxSize()
                .graphicsLayer {
                    transformOrigin = TransformOrigin(0f, 0.5f)
                    translationX = width.toPx() * drawerFraction * drawer
                    val scale = 1f - 0.033f * drawer
                    scaleX = scale
                    scaleY = scale
                    shape = RoundedCornerShape(topStart = 26.dp * drawer, bottomStart = 26.dp * drawer)
                    clip = drawer > 0f
                }
                .drawWithContent {
                    drawContent()
                    if (drawer > 0f) drawRect(Color.Black.copy(alpha = 0.43f * drawer))
                }
                .background(Color.Black),
        ) {
            V8Backdrop(topic = topic, visible = prefs.backdrop && !chat && !typing, chat = chat || typing, reduced = reduced)
            V8VoiceSurface(
                width = width, height = height, safeTop = safeTop, safeBottom = safeBottom, reduced = reduced,
                state = state, chat = chat, typing = typing, ended = ended, busy = busy,
                statusLine = statusLine, toast = toast, messages = messages, prefs = prefs,
                prompt = prompt, promptFocus = promptFocus, onPromptChange = onPromptChange,
                onPromptFocus = onPromptFocus, onChat = onChat, onLayer = onLayer, onEndModal = onEndModal,
                onSubmit = onSubmit, onMic = onMic, onReport = onReport,
            )
        }

        V8TopicsDrawer(
            open = drawerOpen, progress = drawer, widthFraction = drawerFraction, narrow = narrow,
            safeTop = safeTop, safeBottom = safeBottom, reduced = reduced, current = topic,
            onSelect = onTopic, onClose = { onLayer(null) },
        )
        V8Sheet(
            open = layer == V8Layer.Settings, reduced = reduced, safeBottom = safeBottom,
            maxHeight = min(height * 0.79f, 520.dp), onDismiss = { onLayer(null) },
        ) {
            V8SheetHead(R.string.hsk_course_voice_v8_settings_title, R.string.hsk_course_voice_v8_settings_close) { onLayer(null) }
            V8SettingRow(R.string.hsk_course_voice_v8_settings_pinyin, prefs.pinyin, last = false) {
                onPrefsChange(prefs.copy(pinyin = !prefs.pinyin))
            }
            V8SettingRow(R.string.hsk_course_voice_v8_settings_translation, prefs.translation, last = false) {
                onPrefsChange(prefs.copy(translation = !prefs.translation))
            }
            V8SettingRow(R.string.hsk_course_voice_v8_settings_backdrop, prefs.backdrop, last = true) {
                onPrefsChange(prefs.copy(backdrop = !prefs.backdrop))
            }
        }
        V8Sheet(
            open = layer == V8Layer.Plus, reduced = reduced, safeBottom = safeBottom,
            maxHeight = null, onDismiss = { onLayer(null) },
        ) {
            V8SheetHead(R.string.hsk_course_voice_v8_examples_title, R.string.hsk_course_voice_v8_examples_close) { onLayer(null) }
            val examples = listOf(
                R.string.hsk_course_voice_v8_example1_label to R.string.hsk_course_voice_v8_example1_text,
                R.string.hsk_course_voice_v8_example2_label to R.string.hsk_course_voice_v8_example2_text,
                R.string.hsk_course_voice_v8_example3_label to R.string.hsk_course_voice_v8_example3_text,
                R.string.hsk_course_voice_v8_example4_label to R.string.hsk_course_voice_v8_example4_text,
            ).map { (label, text) -> stringResource(label) to stringResource(text) }
            Column(
                Modifier.padding(top = 24.dp, bottom = 4.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                examples.chunked(2).forEach { pair ->
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        pair.forEach { (label, text) ->
                            V8ExampleButton(label, Modifier.weight(1f)) { onExample(text) }
                        }
                    }
                }
            }
        }

        if (ended) V8Restart(onRestart)
        if (endModal) V8EndModal(onCancel = { onEndModal(false) }, onConfirm = onFinish)
    }
}

// --- #voiceScreen content ----------------------------------------------------

@Composable
private fun V8VoiceSurface(
    width: Dp,
    height: Dp,
    safeTop: Dp,
    safeBottom: Dp,
    reduced: Boolean,
    state: VoiceUiState,
    chat: Boolean,
    typing: Boolean,
    ended: Boolean,
    busy: Boolean,
    statusLine: VoiceV8StatusLine,
    toast: Int?,
    messages: List<VoiceV8Message>,
    prefs: VoiceV8Prefs,
    prompt: String,
    promptFocus: FocusRequester,
    onPromptChange: (String) -> Unit,
    onPromptFocus: (Boolean) -> Unit,
    onChat: (Boolean) -> Unit,
    onLayer: (V8Layer?) -> Unit,
    onEndModal: (Boolean) -> Unit,
    onSubmit: () -> Unit,
    onMic: () -> Unit,
    onReport: (VoiceLine) -> Unit,
) {
    val latestChat by rememberUpdatedState(chat)
    var dialogueBounds by remember { mutableStateOf(Rect.Zero) }
    var orbBounds by remember { mutableStateOf(Rect.Zero) }

    Box(
        Modifier
            .fillMaxSize()
            // Vertical swipe anywhere outside controls: down opens, up hides the chat.
            .pointerInput(ended) {
                if (ended) return@pointerInput
                awaitEachGesture {
                    val down = awaitFirstDown(requireUnconsumed = false, pass = PointerEventPass.Final)
                    if (down.isConsumed) return@awaitEachGesture
                    val inDialogue = latestChat && dialogueBounds.contains(down.position)
                    if (inDialogue || orbBounds.contains(down.position)) return@awaitEachGesture
                    var last = down.position
                    while (true) {
                        val event = awaitPointerEvent(PointerEventPass.Final)
                        val change = event.changes.firstOrNull { it.id == down.id } ?: break
                        last = change.position
                        if (!change.pressed) break
                    }
                    val dy = last.y - down.position.y
                    val dx = last.x - down.position.x
                    if (abs(dy) > 90.dp.toPx() && abs(dy) > abs(dx) * 1.4f) onChat(dy > 0)
                }
            },
    ) {
        if (!ended) {
            V8TopBar(safeTop = safeTop, onTopics = { onLayer(V8Layer.Topics) }, onSettings = { onLayer(V8Layer.Settings) })
            V8Dialogue(
                messages = messages, prefs = prefs, chat = chat, typing = typing, reduced = reduced,
                top = 85.dp + safeTop,
                bottom = (if (typing) 161.dp else 212.dp) + safeBottom,
                onBounds = { dialogueBounds = it },
                onReport = onReport,
            )
        }

        val orbSize by animateDpAsState(
            when {
                typing -> 62.dp
                chat -> 80.dp
                else -> 173.dp
            },
            spec(reduced, 660, EaseOrb), label = "orbSize",
        )
        val orbCenter by animateDpAsState(
            when {
                typing -> height - 123.dp - safeBottom
                chat -> height - 133.dp - safeBottom
                else -> height * 0.452f
            },
            spec(reduced, 660, EaseOrb), label = "orbCenter",
        )
        val active = statusLine.status == VoiceV8Status.Speaking || statusLine.status == VoiceV8Status.Listening
        V8Orb(
            size = orbSize,
            centerX = width / 2,
            centerY = orbCenter,
            small = chat || typing,
            typing = typing,
            ended = ended,
            active = active,
            reduced = reduced,
            statusText = toast?.let { stringResource(it) }
                ?: stringResource(statusLine.messageRes ?: statusLine.status.textRes),
            statusUrgent = toast == null && statusLine.status.urgent,
            statusSize = when {
                typing -> 11.sp
                chat -> 12.sp
                else -> 14.sp
            },
            statusGap = when {
                typing -> 4.dp
                chat -> 7.dp
                else -> 17.dp
            },
            statusMaxWidth = if (chat) min(350.dp, width * 0.92f) else min(340.dp, width * 0.94f),
            onBounds = { orbBounds = it },
            onChat = onChat,
            isChat = chat,
        )

        if (!ended) {
            V8Footer(
                safeBottom = safeBottom,
                width = width,
                typing = typing,
                reduced = reduced,
                state = state,
                busy = busy,
                prompt = prompt,
                promptFocus = promptFocus,
                onPromptChange = onPromptChange,
                onPromptFocus = onPromptFocus,
                onPlus = { onLayer(V8Layer.Plus) },
                onMic = onMic,
                onClose = { onEndModal(true) },
                onSubmit = onSubmit,
            )
        }
    }
}

@Composable
private fun V8TopBar(safeTop: Dp, onTopics: () -> Unit, onSettings: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(top = 10.dp + safeTop, start = 17.dp, end = 17.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        V8CircleButton(
            size = 49.dp,
            label = stringResource(R.string.hsk_course_voice_v8_topics_open),
            onClick = onTopics,
        ) { V8Glyph(V8Icon.History, 25.dp, Color.White) }
        V8CircleButton(
            size = 49.dp,
            label = stringResource(R.string.hsk_course_course_voice_inline_settings),
            onClick = onSettings,
        ) { V8Glyph(V8Icon.Settings, 25.dp, Color.White) }
    }
}

@Composable
private fun V8Dialogue(
    messages: List<VoiceV8Message>,
    prefs: VoiceV8Prefs,
    chat: Boolean,
    typing: Boolean,
    reduced: Boolean,
    top: Dp,
    bottom: Dp,
    onBounds: (Rect) -> Unit,
    onReport: (VoiceLine) -> Unit,
) {
    val shown = chat || typing
    val alpha by animateFloatAsState(if (shown) 1f else 0f, spec(reduced, 300, EaseCss), label = "dialogueAlpha")
    val shift by animateFloatAsState(if (shown) 0f else -13f, spec(reduced, 350, EaseCss), label = "dialogueShift")
    val list = rememberLazyListState()
    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            delay(30)
            list.animateScrollToItem(messages.lastIndex)
        }
    }
    LaunchedEffect(chat) {
        if (chat && messages.isNotEmpty()) {
            delay(180)
            list.scrollToItem(messages.lastIndex)
        }
    }
    // Prompt focus (PWA `scrollBottom`): keep the latest line in view while
    // the keyboard shrinks the transcript.
    val lastIndex by rememberUpdatedState(messages.lastIndex)
    LaunchedEffect(typing) {
        if (!typing) return@LaunchedEffect
        snapshotFlow { list.layoutInfo.viewportSize.height }.collect {
            if (lastIndex >= 0) list.scrollToItem(lastIndex)
        }
    }
    val label = stringResource(R.string.hsk_course_voice_v8_dialogue_label)
    LazyColumn(
        state = list,
        userScrollEnabled = shown,
        modifier = Modifier
            .fillMaxSize()
            .padding(top = top, bottom = bottom)
            .onGloballyPositioned { onBounds(it.boundsInRoot()) }
            .graphicsLayer {
                this.alpha = alpha
                translationY = shift * density
                compositingStrategy = CompositingStrategy.Offscreen
            }
            .drawWithContent {
                drawContent()
                if (chat) {
                    drawRect(
                        Brush.verticalGradient(
                            0f to Color.Transparent, 0.09f to Color.Black,
                            0.97f to Color.Black, 1f to Color.Transparent,
                        ),
                        blendMode = BlendMode.DstIn,
                    )
                }
            }
            // `pointer-events:none` and out of the reading order while hidden.
            .then(
                if (shown) Modifier.semantics { contentDescription = label; liveRegion = LiveRegionMode.Polite }
                else Modifier.clearAndSetSemantics {},
            ),
        contentPadding = PaddingValues(start = 18.dp, end = 18.dp, top = 7.dp, bottom = 10.dp),
        verticalArrangement = Arrangement.spacedBy(30.dp),
    ) {
        itemsIndexed(messages) { _, message ->
            V8MessageView(message, prefs, interactive = shown, onReport = onReport)
        }
    }
}

@Composable
private fun V8MessageView(
    message: VoiceV8Message,
    prefs: VoiceV8Prefs,
    interactive: Boolean,
    onReport: (VoiceLine) -> Unit,
) {
    val body = TextStyle(fontSize = 18.sp, lineHeight = 27.9.sp, letterSpacing = (-0.1).sp, color = Color.White)
    val sub = TextStyle(fontSize = 14.sp, lineHeight = 19.9.sp)
    val content: @Composable ColumnScope.() -> Unit = {
        Text(message.text.take(2000), style = body, fontWeight = FontWeight.Medium)
        if (prefs.pinyin && message.pinyin.isNotEmpty()) {
            Text(message.pinyin, style = sub, color = Color(0xFFC2C2C2), modifier = Modifier.padding(top = 4.dp))
        }
        if (prefs.translation && message.translation.isNotEmpty()) {
            Text(message.translation, style = sub, color = Color(0xFFDDDDDD), modifier = Modifier.padding(top = 4.dp))
        }
        if (message.correction.isNotEmpty()) {
            Text("✓ " + message.correction, style = sub, color = Color(0xFFDDDDDD), modifier = Modifier.padding(top = 4.dp))
        }
    }
    if (message.user) {
        BoxWithConstraints(Modifier.fillMaxWidth(), contentAlignment = Alignment.CenterEnd) {
            Column(
                Modifier
                    .widthIn(max = maxWidth * 0.85f)
                    .clip(RoundedCornerShape(23.dp))
                    .background(Color(0xFF7D2925))
                    .padding(horizontal = 17.dp, vertical = 13.dp),
                content = content,
            )
        }
    } else {
        // AI content stays reportable (Play AI-content policy) without
        // changing the V8 look: a long press opens the report action.
        var menu by remember(message) { mutableStateOf(false) }
        val reportLabel = stringResource(R.string.assistant_report_answer)
        val source = message.source?.takeIf { interactive }
        Box {
            Column(
                Modifier
                    .fillMaxWidth()
                    .then(
                        if (source == null) Modifier else Modifier
                            .pointerInput(source) { detectTapGestures(onLongPress = { menu = true }) }
                            .semantics { onLongClick(reportLabel) { menu = true; true } },
                    ),
                content = content,
            )
            if (source != null) {
                DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                    DropdownMenuItem(
                        text = { Text(reportLabel) },
                        onClick = {
                            menu = false
                            onReport(source)
                        },
                    )
                }
            }
        }
    }
}

// --- the orb -------------------------------------------------------------------

private val ORB_SPRING_FRAMES = listOf(
    0.37f to (1.08f to 0.93f),
    0.64f to (0.975f to 1.045f),
    0.83f to (1.015f to 0.98f),
    1f to (1f to 1f),
)

@Composable
private fun V8Orb(
    size: Dp,
    centerX: Dp,
    centerY: Dp,
    small: Boolean,
    typing: Boolean,
    ended: Boolean,
    active: Boolean,
    reduced: Boolean,
    statusText: String,
    statusUrgent: Boolean,
    statusSize: TextUnit,
    statusGap: Dp,
    statusMaxWidth: Dp,
    isChat: Boolean,
    onBounds: (Rect) -> Unit,
    onChat: (Boolean) -> Unit,
) {
    val scope = rememberCoroutineScope()
    val latestChat by rememberUpdatedState(isChat)
    val displacement = remember { Animatable(0f) }
    var dragging by remember { mutableStateOf(false) }
    var stretchX by remember { mutableFloatStateOf(1f) }
    var stretchY by remember { mutableFloatStateOf(1f) }
    var reboundFrom by remember { mutableStateOf(1f to 1f) }
    val rebound = remember { Animatable(1f) }

    val float = rememberInfiniteTransition(label = "orbFloat")
    val floatPhase by float.animateFloat(
        0f, 1f,
        infiniteRepeatable(tween(1_700, easing = EaseInOut), RepeatMode.Reverse),
        label = "orbFloatPhase",
    )

    val renderer = remember { VoiceV8OrbRenderer() }
    DisposableEffect(renderer) { onDispose { renderer.release() } }
    var clock by remember { mutableFloatStateOf(1.2f) }
    LaunchedEffect(reduced) {
        if (reduced) return@LaunchedEffect
        var last = 0L
        while (true) {
            withInfiniteAnimationFrameMillis { ms ->
                // The reference redraws every 32 ms.
                if (ms - last >= 32) {
                    last = ms
                    clock = ms * 0.00083f
                }
            }
        }
    }

    val orbLabel = stringResource(R.string.hsk_course_voice_v8_orb_label)
    // #orb: the gesture target stays put; its content carries the drag offset.
    Box(
        Modifier
            .offset { IntOffset((centerX - size / 2).roundToPx(), (centerY - size / 2).roundToPx()) }
            .size(size)
            .onGloballyPositioned { onBounds(it.boundsInRoot()) }
            .semantics {
                contentDescription = orbLabel
                role = Role.Button
                onClick { onChat(!latestChat); true }
            }
            .pointerInput(ended, reduced) {
                if (ended) return@pointerInput
                awaitEachGesture {
                    val down = awaitFirstDown()
                    down.consume()
                    scope.launch {
                        displacement.stop()
                        displacement.snapTo(0f)
                        rebound.snapTo(1f)
                    }
                    dragging = true
                    stretchX = 1f
                    stretchY = 1f
                    var dy = 0f
                    var released = false
                    var upTime = down.uptimeMillis
                    while (true) {
                        val event = awaitPointerEvent()
                        val change = event.changes.firstOrNull { it.id == down.id } ?: break
                        if (!change.pressed) {
                            released = true
                            upTime = change.uptimeMillis
                            break
                        }
                        change.consume()
                        dy = (change.position.y - down.position.y) / density
                        if (abs(dy) < 3f) continue
                        val amount = kotlin.math.min(abs(dy), 175f)
                        val shift = sign(dy) * kotlin.math.min(75f, amount.pow(0.82f) * 0.72f)
                        scope.launch { displacement.snapTo(shift) }
                        stretchX = 1f - amount * 0.00085f
                        stretchY = 1f + amount * 0.00165f
                    }
                    dragging = false
                    val from = stretchX to stretchY
                    stretchX = 1f
                    stretchY = 1f
                    scope.launch { displacement.animateTo(0f, spec(reduced, 470, EaseRelease)) }
                    if (!reduced && abs(dy) >= 3f) {
                        reboundFrom = from
                        scope.launch {
                            rebound.snapTo(0f)
                            rebound.animateTo(1f, tween(580, easing = LinearEasing))
                        }
                    }
                    if (released) {
                        val dt = upTime - down.uptimeMillis
                        when {
                            dy > 55f -> onChat(true)
                            dy < -55f -> onChat(false)
                            abs(dy) < 12f && dt < 460 && latestChat -> onChat(false)
                        }
                    }
                }
            },
    ) {
        Box(
            Modifier
                .fillMaxSize()
                .graphicsLayer {
                    translationY = displacement.value * density
                    alpha = when {
                        ended -> 0f
                        typing -> 0.82f
                        else -> 1f
                    }
                    // CSS opacity: per draw, never an offscreen layer that would
                    // cut the halo and the status line at the orb's own box.
                    compositingStrategy = CompositingStrategy.ModulateAlpha
                },
        ) {
            // #orb::before — a soft cinnabar halo behind the sphere.
            Box(
                Modifier
                    .fillMaxSize()
                    .graphicsLayer { scaleX = 1.3f; scaleY = 1.3f }
                    .blur(10.dp, BlurredEdgeTreatment.Unbounded)
                    .clip(CircleShape)
                    .background(
                        ellipseBrush(
                            0.5f, 0.56f,
                            listOf(Color(233, 101, 81, (0.16f * 255).roundToInt()), Color(233, 101, 81, 0)),
                            listOf(0f, 0.68f),
                        ),
                    ),
            )
            Canvas(
                Modifier
                    .fillMaxSize()
                    .graphicsLayer {
                        var sx = 1f
                        var sy = 1f
                        var ty = 0f
                        when {
                            reduced -> Unit
                            dragging -> {
                                sx = stretchX
                                sy = stretchY
                            }
                            rebound.isRunning -> {
                                val p = rebound.value
                                var startP = 0f
                                var start = reboundFrom
                                for ((endP, end) in ORB_SPRING_FRAMES) {
                                    if (p <= endP) {
                                        val local = EaseRebound.transform(((p - startP) / (endP - startP)).coerceIn(0f, 1f))
                                        sx = start.first + (end.first - start.first) * local
                                        sy = start.second + (end.second - start.second) * local
                                        break
                                    }
                                    startP = endP
                                    start = end
                                }
                            }
                            small -> ty = -3f * floatPhase
                            else -> {
                                ty = -6f * floatPhase
                                sx = 1f + 0.018f * floatPhase
                                sy = sx
                            }
                        }
                        scaleX = sx
                        scaleY = sy
                        translationY = ty * density
                    },
            ) {
                val t = if (reduced) 1.2f else clock
                drawIntoCanvas { canvas ->
                    renderer.draw(canvas.nativeCanvas, this.size.width, density, t, if (active) 1.16f else 1f)
                }
            }
            if (!ended) V8OrbStatus(statusText, statusUrgent, statusSize, statusGap, statusMaxWidth, reduced)
        }
    }
}

/** #orbStatus: centred under the orb at `top: calc(100% + gap)`. */
@Composable
private fun V8OrbStatus(
    text: String,
    urgent: Boolean,
    fontSize: TextUnit,
    gap: Dp,
    maxWidth: Dp,
    reduced: Boolean,
) {
    val visible = text.isNotEmpty()
    val alpha by animateFloatAsState(if (visible) 1f else 0f, spec(reduced, 220, EaseCss), label = "statusAlpha")
    val shift by animateFloatAsState(if (visible) 0f else -4f, spec(reduced, 220, EaseCss), label = "statusShift")
    val shadow = with(LocalDensity.current) { Shadow(Color.Black, Offset(0f, 1.dp.toPx()), 2.dp.toPx()) }
    Text(
        text = text,
        modifier = Modifier
            .layout { measurable, constraints ->
                val parentWidth = constraints.maxWidth
                val parentHeight = constraints.maxHeight
                val placeable = measurable.measure(Constraints(maxWidth = maxWidth.roundToPx()))
                layout(parentWidth, parentHeight) {
                    placeable.place((parentWidth - placeable.width) / 2, parentHeight + gap.roundToPx())
                }
            }
            .graphicsLayer {
                this.alpha = alpha
                translationY = shift * density
            }
            .semantics { liveRegion = LiveRegionMode.Polite },
        style = TextStyle(
            fontSize = fontSize,
            fontWeight = FontWeight.Medium,
            lineHeight = fontSize * 1.3f,
            color = if (urgent) Color(0xFFD9B4AE) else Color(0xFFAAAAAA),
            textAlign = TextAlign.Center,
            shadow = shadow,
        ),
    )
}

// --- footer ----------------------------------------------------------------------

@Composable
private fun V8Footer(
    safeBottom: Dp,
    width: Dp,
    typing: Boolean,
    reduced: Boolean,
    state: VoiceUiState,
    busy: Boolean,
    prompt: String,
    promptFocus: FocusRequester,
    onPromptChange: (String) -> Unit,
    onPromptFocus: (Boolean) -> Unit,
    onPlus: () -> Unit,
    onMic: () -> Unit,
    onClose: () -> Unit,
    onSubmit: () -> Unit,
) {
    val tiny = width <= 350.dp
    val springMs = 390
    val side by animateDpAsState(
        if (typing) (if (tiny) 8.dp else 12.dp) else (if (tiny) 14.dp else 20.dp),
        spec(reduced, springMs, EaseSpring), label = "footerSide",
    )
    val barHeight by animateDpAsState(if (typing) 50.dp else 44.dp, spec(reduced, springMs, EaseSpring), label = "footerHeight")
    val lift by animateDpAsState(if (typing) 12.dp else 15.dp, spec(reduced, springMs, EaseSpring), label = "footerBottom")
    val gap by animateDpAsState(if (typing) (if (tiny) 6.dp else 8.dp) else 6.dp, spec(reduced, springMs, EaseSpring), label = "footerGap")
    val plusWidth by animateDpAsState(if (typing) 33.dp else 29.dp, spec(reduced, 360, EaseSpring), label = "plusWidth")
    val padStart by animateDpAsState(if (typing) 7.dp else 6.dp, spec(reduced, springMs, EaseSpring), label = "composerStart")
    val padEnd by animateDpAsState(if (typing) 9.dp else 7.dp, spec(reduced, springMs, EaseSpring), label = "composerEnd")

    val micOn = if (state.isLive) state.isLiveConnected && !state.isLiveMuted else state.isRecording
    val micDisabled = state.isLive && state.isLiveConnected && state.isLiveMuted
    val micLabel = stringResource(
        when {
            micDisabled -> R.string.hsk_course_voice_v8_mic_disabled
            micOn -> R.string.hsk_course_voice_v8_mic_off
            else -> R.string.hsk_course_voice_v8_mic_on
        },
    )
    val ready = prompt.isNotBlank()

    Box(Modifier.fillMaxSize()) {
        Row(
            Modifier
                .align(Alignment.BottomCenter)
                .padding(start = side, end = side, bottom = lift + safeBottom)
                .fillMaxWidth()
                .height(barHeight),
            horizontalArrangement = Arrangement.spacedBy(gap),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // .composer
            Row(
                Modifier
                    .weight(1f)
                    .fillMaxHeight()
                    .clip(RoundedCornerShape(30.dp))
                    .background(Brush.verticalGradient(listOf(Color(0xFF292929), Color(0xFF212121))))
                    .border(1.dp, Color(0xFF434343), RoundedCornerShape(30.dp))
                    .insetTopHighlight(0.09f, RoundedCornerShape(30.dp))
                    .padding(start = padStart, end = padEnd),
                horizontalArrangement = Arrangement.spacedBy(4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                val plusLabel = stringResource(R.string.hsk_course_voice_v8_examples_title)
                Box(
                    Modifier
                        .size(plusWidth, 34.dp)
                        .clickable(
                            interactionSource = remember { MutableInteractionSource() },
                            indication = null,
                            role = Role.Button,
                            onClickLabel = plusLabel,
                            onClick = onPlus,
                        )
                        .semantics { contentDescription = plusLabel },
                    contentAlignment = Alignment.Center,
                ) { V8Glyph(V8Icon.Plus, 22.dp, Color.White) }
                val promptLabel = stringResource(R.string.hsk_course_voice_v8_prompt_label)
                BasicTextField(
                    value = prompt,
                    onValueChange = onPromptChange,
                    singleLine = true,
                    textStyle = TextStyle(fontSize = 16.sp, color = Color.White),
                    cursorBrush = SolidColor(Color.White),
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                    keyboardActions = KeyboardActions(onSend = { onSubmit() }),
                    modifier = Modifier
                        .weight(1f)
                        .padding(horizontal = 2.dp)
                        .focusRequester(promptFocus)
                        .onFocusChanged { onPromptFocus(it.isFocused) }
                        .semantics { contentDescription = promptLabel },
                    decorationBox = { field ->
                        Box(contentAlignment = Alignment.CenterStart) {
                            if (prompt.isEmpty()) {
                                Text(
                                    stringResource(R.string.hsk_course_voice_v8_ask),
                                    style = TextStyle(fontSize = 16.sp, color = Color(0xFF828282)),
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                            field()
                        }
                    },
                )
            }
            // #micmuted
            V8CircleButton(
                size = barHeight,
                label = micLabel,
                pressed = micOn && !micDisabled,
                dimmed = false,
                onClick = onMic,
            ) { V8Glyph(if (micOn && !micDisabled) V8Icon.Mic else V8Icon.MicMuted, 22.dp, Color.White) }
            if (!typing) {
                // #close
                V8CircleButton(
                    size = barHeight,
                    label = stringResource(R.string.hsk_course_voice_v8_end_label),
                    background = Brush.linearGradient(listOf(Color.White, Color.White)),
                    borderColor = Color.White,
                    highlight = false,
                    onClick = onClose,
                ) { V8Glyph(V8Icon.Close, 24.dp, Color.Black) }
            } else {
                // #send
                val enabled = ready && !busy
                val sendLabel = stringResource(R.string.hsk_course_voice_v8_send_label)
                Box(
                    Modifier
                        .size(barHeight)
                        .graphicsLayer { alpha = if (enabled) 1f else 0.8f }
                        .clip(CircleShape)
                        .background(if (enabled) Red else Color(0xFF39393B))
                        .border(1.dp, if (enabled) Red else Color(0xFF555555), CircleShape)
                        .clickable(
                            enabled = enabled,
                            interactionSource = remember { MutableInteractionSource() },
                            indication = null,
                            role = Role.Button,
                            onClick = onSubmit,
                        )
                        .semantics { contentDescription = sendLabel },
                    contentAlignment = Alignment.Center,
                ) { V8Glyph(V8Icon.Send, 25.dp, if (enabled) Color.White else Color(0xFFAAAAAA)) }
            }
        }
    }
}

@Composable
private fun V8CircleButton(
    size: Dp,
    label: String,
    onClick: () -> Unit,
    pressed: Boolean? = null,
    dimmed: Boolean = false,
    background: Brush = cssAngleBrush(140f, listOf(Color(0xFF303030), Color(0xFF171717))),
    borderColor: Color = Color(0xFF3A3A3A),
    highlight: Boolean = true,
    content: @Composable () -> Unit,
) {
    Box(
        Modifier
            .size(size)
            .graphicsLayer { alpha = if (dimmed) 0.48f else 1f }
            .clip(CircleShape)
            .background(background)
            .border(1.dp, borderColor, CircleShape)
            .then(if (highlight) Modifier.insetTopHighlight(0.1f, CircleShape) else Modifier)
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null,
                role = Role.Button,
                onClick = onClick,
            )
            .semantics {
                contentDescription = label
                if (pressed != null) {
                    toggleableState = if (pressed) ToggleableState.On else ToggleableState.Off
                }
            },
        contentAlignment = Alignment.Center,
    ) { content() }
}

// --- backdrop --------------------------------------------------------------------

@Composable
private fun V8Backdrop(topic: VoiceV8Topic, visible: Boolean, chat: Boolean, reduced: Boolean) {
    val context = LocalContext.current
    val image = remember(topic) { blurredTopicPhoto(context, topic.photoRes)?.asImageBitmap() }
    val alpha by animateFloatAsState(if (visible) 0.81f else 0f, spec(reduced, 580, EaseDrawer), label = "backdropAlpha")
    val scale by animateFloatAsState(
        when {
            visible -> 1f
            chat -> 1.1f
            else -> 1.08f
        },
        spec(reduced, 800, EaseDrawer), label = "backdropScale",
    )
    val mediaScale by animateFloatAsState(
        when {
            visible -> 1.08f
            chat -> 1.16f
            else -> 1.14f
        },
        spec(reduced, 820, EaseDrawer), label = "mediaScale",
    )
    val mediaAlpha by animateFloatAsState(if (chat) 0.18f else 0.95f, spec(reduced, 580, EaseCss), label = "mediaAlpha")
    val filter = remember {
        val saturate = ColorMatrix().apply { setToSaturation(1.1f) }
        ColorFilter.colorMatrix(ColorMatrix().apply { setToScale(0.78f, 0.78f, 0.78f, 1f); timesAssign(saturate) })
    }
    if (alpha <= 0f) return
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val w = maxWidth
        val h = maxHeight
        // #topicBackdrop: inset -4% (a required size larger than the box is centred).
        Box(
            Modifier
                .requiredSize(w * 1.08f, h * 1.08f)
                .graphicsLayer {
                    this.alpha = alpha
                    scaleX = scale
                    scaleY = scale
                },
        ) {
            if (image != null) {
                // #topicBackdropMedia: inset -7%, cover.
                Image(
                    bitmap = image,
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    colorFilter = filter,
                    modifier = Modifier
                        .requiredSize(w * 1.08f * 1.14f, h * 1.08f * 1.14f)
                        .graphicsLayer {
                            this.alpha = mediaAlpha
                            scaleX = mediaScale
                            scaleY = mediaScale
                        },
                )
            } else {
                Box(Modifier.fillMaxSize().background(cssAngleBrush(135f, listOf(Color(0xFF2F2321), Color(0xFF101010)))))
            }
            // #topicBackdropWash
            Box(
                Modifier
                    .fillMaxSize()
                    .graphicsLayer { this.alpha = 0.92f }
                    .background(
                        ellipseBrush(
                            0.48f, 0.34f,
                            listOf(Color(255, 252, 242, (0.13f * 255).roundToInt()), Color(255, 252, 242, 0)),
                            listOf(0f, 0.43f),
                        ),
                    )
                    .background(
                        ellipseBrush(
                            0.58f, 0.49f,
                            listOf(Color(248, 170, 134, (0.06f * 255).roundToInt()), Color(248, 170, 134, 0)),
                            listOf(0f, 0.46f),
                        ),
                    )
                    .background(
                        Brush.verticalGradient(
                            0f to Color(6, 7, 9, (0.06f * 255).roundToInt()),
                            0.46f to Color(7, 7, 9, (0.29f * 255).roundToInt()),
                            0.75f to Color(1, 2, 4, (0.60f * 255).roundToInt()),
                            1f to Color(0, 0, 0, (0.80f * 255).roundToInt()),
                        ),
                    ),
            )
        }
    }
}

/** The 180×156 scene photo with `blur(13px)` already applied at its own scale. */
private fun blurredTopicPhoto(context: Context, res: Int): Bitmap? {
    val source = BitmapFactory.decodeResource(context.resources, res) ?: return null
    val bitmap = source.copy(Bitmap.Config.ARGB_8888, true)
    if (bitmap !== source) source.recycle()
    val w = bitmap.width
    val h = bitmap.height
    val bytes = ByteArray(w * h * 4)
    val buffer = ByteBuffer.wrap(bytes)
    bitmap.copyPixelsToBuffer(buffer)
    val a = IntArray(bytes.size) { bytes[it].toInt() and 0xFF }
    val b = IntArray(bytes.size)
    // σ ≈ 2 source pixels: the photo is shown ~7× larger than its pixels.
    repeat(3) {
        clampBoxPass(a, b, w, h, 2, horizontal = true)
        clampBoxPass(b, a, w, h, 2, horizontal = false)
    }
    for (i in bytes.indices) bytes[i] = a[i].toByte()
    buffer.rewind()
    bitmap.copyPixelsFromBuffer(buffer)
    return bitmap
}

private fun clampBoxPass(input: IntArray, output: IntArray, w: Int, h: Int, radius: Int, horizontal: Boolean) {
    val lines = if (horizontal) h else w
    val length = if (horizontal) w else h
    val window = radius * 2 + 1
    for (line in 0 until lines) {
        for (channel in 0 until 4) {
            fun at(pos: Int): Int {
                val p = pos.coerceIn(0, length - 1)
                return input[(if (horizontal) line * w + p else p * w + line) * 4 + channel]
            }
            var sum = 0
            for (k in -radius..radius) sum += at(k)
            for (pos in 0 until length) {
                output[(if (horizontal) line * w + pos else pos * w + line) * 4 + channel] = sum / window
                sum += at(pos + radius + 1) - at(pos - radius)
            }
        }
    }
}

// --- topics drawer ----------------------------------------------------------------

@Composable
private fun V8TopicsDrawer(
    open: Boolean,
    progress: Float,
    widthFraction: Float,
    narrow: Boolean,
    safeTop: Dp,
    safeBottom: Dp,
    reduced: Boolean,
    current: VoiceV8Topic,
    onSelect: (VoiceV8Topic) -> Unit,
    onClose: () -> Unit,
) {
    val fade by animateFloatAsState(if (open) 1f else 0f, spec(reduced, 250, EaseCss), label = "topicsFade")
    if (!open && fade <= 0f && progress <= 0f) return
    Box(
        Modifier
            .fillMaxSize()
            .graphicsLayer { alpha = fade },
    ) {
        Box(
            Modifier
                .fillMaxSize()
                .background(Color.Black.copy(alpha = 0.42f))
                .clickable(
                    enabled = open,
                    interactionSource = remember { MutableInteractionSource() },
                    indication = null,
                    onClick = onClose,
                ),
        )
        val shape = RoundedCornerShape(topEnd = 24.dp, bottomEnd = 24.dp)
        Column(
            Modifier
                .fillMaxHeight()
                .fillMaxWidth(widthFraction)
                .graphicsLayer { translationX = -size.width * 1.04f * (1f - progress) }
                .shadow(24.dp, shape, ambientColor = Color.Black, spotColor = Color.Black)
                .clip(shape)
                .background(Color(0xFF101011))
                .clickable(interactionSource = remember { MutableInteractionSource() }, indication = null) {}
                .padding(top = 19.dp + safeTop, bottom = 15.dp + safeBottom),
        ) {
            Row(
                Modifier.fillMaxWidth().padding(start = 20.dp, end = 20.dp, top = 8.dp, bottom = 13.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Row {
                    val brand = TextStyle(fontSize = 25.sp, fontWeight = FontWeight(720), letterSpacing = (-1.25).sp)
                    Text("HSK ", style = brand, color = Color.White)
                    Text("AI", style = brand, color = Color(0xFFF16D5B))
                }
                V8DismissX(stringResource(R.string.hsk_course_voice_v8_menu_close), onClose)
            }
            Column(
                Modifier
                    .weight(1f)
                    .verticalScroll(rememberScrollState())
                    .padding(start = 12.dp, end = 12.dp, bottom = 10.dp),
            ) {
                Text(
                    stringResource(R.string.hsk_course_voice_v8_topics_title),
                    style = TextStyle(fontSize = 21.sp, fontWeight = FontWeight(650), letterSpacing = (-0.4).sp),
                    color = Color.White,
                    modifier = Modifier.padding(start = 8.dp, end = 8.dp, top = 9.dp, bottom = 24.dp),
                )
                V8Caption(stringResource(R.string.hsk_course_voice_v8_topics_current))
                Row(
                    Modifier
                        .padding(start = 1.dp, end = 1.dp, bottom = 15.dp)
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(17.dp))
                        .background(Color(0xFF29201F))
                        .border(1.dp, Color(0xFF5C3531), RoundedCornerShape(17.dp))
                        .padding(horizontal = 10.dp, vertical = 9.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    V8TopicPhoto(current, narrow)
                    Column(Modifier.weight(1f)) {
                        Text(
                            stringResource(current.titleRes),
                            style = TextStyle(fontSize = 14.sp, lineHeight = 18.2.sp, fontWeight = FontWeight(620)),
                            color = Color.White,
                        )
                        Text(
                            current.zh + " · " + current.py,
                            style = TextStyle(fontSize = 11.sp),
                            color = Color(0xFFBB9E9A),
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.padding(top = 4.dp),
                        )
                    }
                    Box(
                        Modifier
                            .size(7.dp)
                            .shadow(4.dp, CircleShape, ambientColor = Color(0xFFE46A5C), spotColor = Color(0xFFE46A5C))
                            .background(Color(0xFFE46A5C), CircleShape),
                    )
                }
                V8Caption(stringResource(R.string.hsk_course_voice_v8_topics_other))
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    VoiceV8Topic.entries.filter { it != current }.forEach { item ->
                        V8TopicChoice(item, narrow) { onSelect(item) }
                    }
                }
            }
            Row(
                Modifier
                    .fillMaxWidth()
                    .drawBehind { drawLine(Color(0xFF242427), Offset.Zero, Offset(size.width, 0f), 1.dp.toPx()) }
                    .padding(start = 21.dp, end = 21.dp, top = 14.dp, bottom = 5.dp + safeBottom),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text("HSK AI", fontSize = 11.sp, fontWeight = FontWeight(650), color = Color(0xFFD0D0D0))
                Text(stringResource(R.string.hsk_course_voice_v8_drawer_footer), fontSize = 11.sp, color = Color(0xFF8A8A8A))
            }
        }
    }
}

@Composable
private fun V8Caption(text: String) {
    Text(
        text,
        style = TextStyle(fontSize = 10.sp, fontWeight = FontWeight(730), letterSpacing = 1.15.sp),
        color = Color(0xFF79797B),
        modifier = Modifier.padding(start = 8.dp, end = 8.dp, top = 11.dp, bottom = 9.dp),
    )
}

@Composable
private fun V8TopicChoice(topic: VoiceV8Topic, narrow: Boolean, onClick: () -> Unit) {
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    Row(
        Modifier
            .fillMaxWidth()
            .heightIn(min = if (narrow) 68.dp else 79.dp)
            .clip(RoundedCornerShape(14.dp))
            .background(if (pressed) Color(0xFF303030) else Color.Transparent)
            .clickable(interactionSource = interaction, indication = null, role = Role.Button, onClick = onClick)
            .padding(horizontal = 8.dp, vertical = 7.dp),
        horizontalArrangement = Arrangement.spacedBy(11.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        V8TopicPhoto(topic, narrow)
        Column(Modifier.weight(1f)) {
            Text(
                stringResource(topic.titleRes),
                style = TextStyle(fontSize = if (narrow) 13.sp else 14.sp, lineHeight = 18.5.sp, fontWeight = FontWeight(610)),
                color = Color.White,
            )
            Text(
                topic.zh + " · " + topic.py,
                style = TextStyle(fontSize = 11.sp),
                color = Color(0xFF949498),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.padding(top = 5.dp),
            )
        }
        Text("›", fontSize = 17.sp, color = Color(0xFF7A7A7C))
    }
}

@Composable
private fun V8TopicPhoto(topic: VoiceV8Topic, narrow: Boolean) {
    val filter = remember {
        val saturate = ColorMatrix().apply { setToSaturation(0.85f) }
        ColorFilter.colorMatrix(ColorMatrix().apply { setToScale(0.82f, 0.82f, 0.82f, 1f); timesAssign(saturate) })
    }
    Box(
        Modifier
            .size(if (narrow) 55.dp else 66.dp, if (narrow) 54.dp else 62.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(cssAngleBrush(135f, listOf(Color(0xFF4D3833), Color(0xFF292222)))),
        contentAlignment = Alignment.Center,
    ) {
        Text(topic.glyph, fontSize = 23.sp, color = Color(0xFFFFDFCE))
        Image(
            painter = painterResource(topic.photoRes),
            contentDescription = null,
            contentScale = ContentScale.Crop,
            colorFilter = filter,
            modifier = Modifier.fillMaxSize(),
        )
        Box(Modifier.fillMaxSize().border(1.dp, Color(0x10FFFFFF), RoundedCornerShape(12.dp)))
    }
}

// --- sheets ------------------------------------------------------------------------

@Composable
private fun V8Sheet(
    open: Boolean,
    reduced: Boolean,
    safeBottom: Dp,
    maxHeight: Dp?,
    onDismiss: () -> Unit,
    content: @Composable ColumnScope.() -> Unit,
) {
    val fade by animateFloatAsState(if (open) 1f else 0f, spec(reduced, 250, EaseCss), label = "sheetFade")
    val slide by animateFloatAsState(if (open) 1f else 0f, spec(reduced, 350, EaseDrawer), label = "sheetSlide")
    if (!open && fade <= 0f && slide <= 0f) return
    Box(Modifier.fillMaxSize().graphicsLayer { alpha = fade }) {
        Box(
            Modifier
                .fillMaxSize()
                .background(Color.Black.copy(alpha = 0.5f))
                .clickable(
                    enabled = open,
                    interactionSource = remember { MutableInteractionSource() },
                    indication = null,
                    onClick = onDismiss,
                ),
        )
        val shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp)
        Column(
            Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .then(if (maxHeight != null) Modifier.heightIn(max = maxHeight) else Modifier)
                .graphicsLayer { translationY = size.height * (1f - slide) }
                .shadow(28.dp, shape, ambientColor = Color.Black, spotColor = Color.Black)
                .clip(shape)
                .background(Color(0xFF242425))
                .border(1.dp, Color(0xFF383839), shape)
                .clickable(interactionSource = remember { MutableInteractionSource() }, indication = null) {}
                .padding(start = 21.dp, end = 21.dp, top = 13.dp, bottom = 26.dp + safeBottom),
        ) {
            Box(
                Modifier
                    .align(Alignment.CenterHorizontally)
                    .padding(bottom = 11.dp)
                    .size(37.dp, 4.dp)
                    .background(Color(0xFF6B6B6B), RoundedCornerShape(5.dp)),
            )
            content()
        }
    }
}

@Composable
private fun V8SheetHead(titleRes: Int, closeRes: Int, onClose: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 9.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            stringResource(titleRes),
            style = TextStyle(fontSize = 19.sp, fontWeight = FontWeight(650), letterSpacing = (-0.2).sp),
            color = Color.White,
            modifier = Modifier.weight(1f),
        )
        Spacer(Modifier.width(12.dp))
        V8DismissX(stringResource(closeRes), onClose)
    }
}

@Composable
private fun V8SettingRow(labelRes: Int, on: Boolean, last: Boolean, onToggle: () -> Unit) {
    val label = stringResource(labelRes)
    val knob by animateDpAsState(if (on) 20.dp else 3.dp, tween(200, easing = EaseCss), label = "knob")
    Row(
        Modifier
            .fillMaxWidth()
            .then(
                if (last) Modifier else Modifier.drawBehind {
                    drawLine(Color(0xFF3B3B3B), Offset(0f, size.height), Offset(size.width, size.height), 1.dp.toPx())
                },
            )
            .padding(vertical = 19.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label, fontSize = 15.sp, color = Color.White, modifier = Modifier.weight(1f))
        Box(
            Modifier
                .size(43.dp, 26.dp)
                .clip(RoundedCornerShape(22.dp))
                .background(if (on) Red else Color(0xFF555555))
                .clickable(
                    interactionSource = remember { MutableInteractionSource() },
                    indication = null,
                    role = Role.Switch,
                    onClick = onToggle,
                )
                .semantics {
                    contentDescription = label
                    toggleableState = if (on) ToggleableState.On else ToggleableState.Off
                    stateDescription = if (on) "on" else "off"
                },
        ) {
            Box(
                Modifier
                    .offset(x = knob, y = 3.dp)
                    .size(20.dp)
                    .background(Color.White, CircleShape),
            )
        }
    }
}

@Composable
private fun V8ExampleButton(label: String, modifier: Modifier, onClick: () -> Unit) {
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    Box(
        modifier
            .heightIn(min = 52.dp)
            .clip(RoundedCornerShape(17.dp))
            .background(if (pressed) Color(0xFF5F2C28) else Color(0xFF38383A))
            .border(1.dp, Color(0xFF565659), RoundedCornerShape(17.dp))
            .clickable(interactionSource = interaction, indication = null, role = Role.Button, onClick = onClick)
            .padding(horizontal = 8.dp, vertical = 10.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(label, fontSize = 14.sp, lineHeight = 18.2.sp, color = Color.White, textAlign = TextAlign.Center)
    }
}

@Composable
private fun V8DismissX(label: String, onClick: () -> Unit) {
    Box(
        Modifier
            .size(34.dp)
            .clip(CircleShape)
            .background(Color(0xFF303033))
            .border(1.dp, Color(0xFF444444), CircleShape)
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null,
                role = Role.Button,
                onClick = onClick,
            )
            .semantics { contentDescription = label },
        contentAlignment = Alignment.Center,
    ) { V8Glyph(V8Icon.Dismiss, 16.dp, Color.White) }
}

// --- end dialog and ended state -------------------------------------------------

@Composable
private fun V8EndModal(onCancel: () -> Unit, onConfirm: () -> Unit) {
    Box(
        Modifier
            .fillMaxSize()
            .background(Color(0xBB000000))
            .clickable(interactionSource = remember { MutableInteractionSource() }, indication = null) {}
            .padding(20.dp),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            Modifier
                .widthIn(max = 330.dp)
                .fillMaxWidth()
                .clip(RoundedCornerShape(24.dp))
                .background(Color(0xFF202020))
                .border(1.dp, Color(0xFF393939), RoundedCornerShape(24.dp))
                .padding(22.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(Modifier.height(19.dp))
            Text(
                stringResource(R.string.hsk_course_voice_v8_end_title),
                fontSize = 19.sp, fontWeight = FontWeight(620), color = Color.White, textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(19.dp))
            Text(
                stringResource(R.string.hsk_course_voice_v8_end_body),
                fontSize = 14.sp, color = Color(0xFFAAAAAA), textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(20.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                V8ModalButton(stringResource(R.string.hsk_course_voice_v8_end_cancel), Color(0xFF333333), Modifier.weight(1f), onCancel)
                V8ModalButton(stringResource(R.string.hsk_course_voice_v8_end_confirm), Red, Modifier.weight(1f), onConfirm)
            }
        }
    }
}

@Composable
private fun V8ModalButton(text: String, color: Color, modifier: Modifier, onClick: () -> Unit) {
    Box(
        modifier
            .height(44.dp)
            .clip(RoundedCornerShape(14.dp))
            .background(color)
            .clickable(role = Role.Button, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) { Text(text, fontSize = 16.sp, color = Color.White) }
}

@Composable
private fun V8Restart(onRestart: () -> Unit) {
    Column(
        Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(22.dp, Alignment.CenterVertically),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(stringResource(R.string.hsk_course_voice_v8_status_end), fontSize = 16.sp, color = Color(0xFFAAAAAA))
        Box(
            Modifier
                .clip(RoundedCornerShape(24.dp))
                .background(Red)
                .clickable(role = Role.Button, onClick = onRestart)
                .padding(horizontal = 22.dp, vertical = 14.dp),
        ) { Text(stringResource(R.string.hsk_course_voice_v8_restart), fontSize = 16.sp, color = Color.White) }
    }
}

// --- icons (the reference's inline SVGs on a 24-unit view box) ------------------

private enum class V8Icon(val paths: List<String>, val stroke: Float) {
    History(listOf("M4 7h16M4 16h10"), 2.4f),
    Settings(listOf("M3 7h18M3 17h18"), 2.4f),
    Plus(listOf("M12 2v20M2 12h20"), 2.3f),
    Mic(listOf("M9 5a3 3 0 0 1 6 0v6a3 3 0 0 1-6 0z", "M5 10a7 7 0 0 0 14 0M12 17v5M8 22h8"), 2.4f),
    MicMuted(
        listOf("M10 9v2.2c0 1 .5 1.7 1.1 2.1M14 8V5a2 2 0 0 0-4 0v1M7 12c.2 2.7 2.2 4.6 5 4.6 1 0 1.8-.2 2.5-.7M17 12c0 .6-.1 1.1-.3 1.6M12 17v4m-4 0h8M2 2l20 20"),
        2.4f,
    ),
    Close(listOf("M4 4l16 16M20 4 4 20"), 2.4f),
    Send(listOf("m12 19 0-14M6 11l6-6 6 6"), 2.3f),
    Dismiss(listOf("M5 5l14 14M19 5 5 19"), 2.5f),
}

@Composable
private fun V8Glyph(icon: V8Icon, size: Dp, color: Color) {
    val paths = remember(icon) { icon.paths.map { PathParser().parsePathString(it).toPath() } }
    Canvas(Modifier.size(size)) {
        val unit = this.size.width / 24f
        withTransform({ scale(unit, unit, pivot = Offset.Zero) }) {
            val stroke = Stroke(width = icon.stroke, cap = StrokeCap.Round, join = StrokeJoin.Round)
            paths.forEach { drawPath(it, color, style = stroke) }
            if (icon == V8Icon.Settings) drawSettingsKnobs(color, stroke)
        }
    }
}

private fun DrawScope.drawSettingsKnobs(color: Color, stroke: Stroke) {
    listOf(Offset(9f, 7f), Offset(16f, 17f)).forEach { center ->
        drawCircle(Color(0xFF252525), radius = 3f, center = center)
        drawCircle(color, radius = 3f, center = center, style = stroke)
    }
}

// --- helpers -------------------------------------------------------------------------

private fun <T> spec(reduced: Boolean, ms: Int, easing: Easing): AnimationSpec<T> =
    if (reduced) snap() else tween(ms, easing = easing)

/** CSS `linear-gradient(<angle>deg, …)` on any box. */
private fun cssAngleBrush(angle: Float, colors: List<Color>): Brush = object : ShaderBrush() {
    override fun createShader(size: Size): Shader {
        val rad = Math.toRadians(angle.toDouble())
        val dx = sin(rad).toFloat()
        val dy = -cos(rad).toFloat()
        val half = (abs(size.width * dx) + abs(size.height * dy)) / 2f
        val c = Offset(size.width / 2f, size.height / 2f)
        return LinearGradientShader(c - Offset(dx * half, dy * half), c + Offset(dx * half, dy * half), colors)
    }
}

/** CSS `radial-gradient(ellipse at x% y%, …)` (farthest-corner ellipse). */
private fun ellipseBrush(cx: Float, cy: Float, colors: List<Color>, stops: List<Float>): Brush = object : ShaderBrush() {
    override fun createShader(size: Size): Shader {
        val x = size.width * cx
        val y = size.height * cy
        val rx = max(x, size.width - x) * sqrt(2f)
        val ry = max(y, size.height - y) * sqrt(2f)
        return android.graphics.RadialGradient(
            x, y, max(rx, 1f), colors.map { it.toArgb() }.toIntArray(), stops.toFloatArray(),
            android.graphics.Shader.TileMode.CLAMP,
        ).apply { setLocalMatrix(android.graphics.Matrix().apply { setScale(1f, ry / max(rx, 1f), x, y) }) }
    }
}

/** CSS `box-shadow: inset 0 1px 0 rgba(255,255,255,a)` inside a 1px border. */
private fun Modifier.insetTopHighlight(alpha: Float, shape: androidx.compose.ui.graphics.Shape): Modifier =
    drawWithContent {
        drawContent()
        val border = 1.dp.toPx()
        val inner = Size(size.width - border * 2, size.height - border * 2)
        if (inner.minDimension <= 0f) return@drawWithContent
        val outline = shape.createOutline(inner, layoutDirection, this)
        val box = Path().apply { addOutline(outline); translate(Offset(border, border)) }
        val shifted = Path().apply { addOutline(outline); translate(Offset(border, border + 1.dp.toPx())) }
        val crescent = Path().apply { op(box, shifted, androidx.compose.ui.graphics.PathOperation.Difference) }
        drawPath(crescent, Color.White.copy(alpha = alpha))
    }

private tailrec fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.findActivity()
    else -> null
}
