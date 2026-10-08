package com.pomp.hskai.feature.course

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.keyframes
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.wrapContentSize
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Diamond
import androidx.compose.material.icons.filled.LocalFireDepartment
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.LockOpen
import androidx.compose.material.icons.filled.TrackChanges
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringArrayResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskSceneSurface
import com.pomp.hskai.core.design.components.HskSectionTitle
import com.pomp.hskai.core.design.components.HskBrandLoader
import com.pomp.hskai.core.design.components.Hsk30BooksHeader
import com.pomp.hskai.core.design.components.HskGlassButton
import com.pomp.hskai.core.design.components.HskGlassSurface
import com.pomp.hskai.core.design.components.HskPrimaryButton
import com.pomp.hskai.core.navigation.LocalMainBottomInset
import com.pomp.hskai.data.api.AndroidHintDto
import com.pomp.hskai.feature.assistant.AssistantScreen
import com.pomp.hskai.feature.assistant.courseAssistantContext
import com.pomp.hskai.feature.hint.SectionHint
import com.pomp.hskai.feature.lesson.LessonCharacter
import com.pomp.hskai.feature.lesson.LessonCharacterMood
import com.pomp.hskai.feature.lesson.LessonCharacterReaction
import com.pomp.hskai.feature.lesson.LessonCharacterStage
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.domain.model.CourseLesson
import com.pomp.hskai.domain.model.CourseMap
import com.pomp.hskai.domain.model.CourseMilestone
import com.pomp.hskai.domain.model.CourseUnit
import com.pomp.hskai.domain.model.LessonAccess
import com.pomp.hskai.domain.model.LessonStatus
import com.pomp.hskai.domain.model.TodayTask
import com.pomp.hskai.feature.limit.LimitGate
import com.pomp.hskai.feature.limit.SectionLimitOverlay
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/** Native rendering of the Mini App course shell. Mini App is source of truth. */
@Composable
fun CourseScreen(
    state: CourseUiState,
    dailyGoal: Int,
    limit: LimitGate,
    hints: List<AndroidHintDto> = emptyList(),
    onDismissHint: (String) -> Unit = {},
    onLesson: (CourseLesson) -> Unit,
    /** A lesson not reached yet: the host offers the Mini App's skip test. */
    onLockedLesson: (CourseLesson) -> Unit = {},
    onTodayTask: (TodayTask) -> Unit,
    onOpenGoal: () -> Unit,
    onOpenChest: () -> Unit,
    onChestRewardConsumed: () -> Unit,
    onUnlockAnimationConsumed: () -> Unit = {},
    onSwitchTrack: (String, String?) -> Unit = { _, _ -> },
    onHsk30PromoShown: () -> Unit = {},
    onDismissHsk30Promo: () -> Unit = {},
    hsk30PromoAllowed: Boolean = true,
    onUnlockHsk30: () -> Unit = {},
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
) {
    AssistantScreen(courseAssistantContext(state), bottomBar = true)
    val map = state.map
    var pendingTrackSwitch by remember { mutableStateOf<Pair<String, String?>?>(null) }
    // The limit window belongs to the map, not to the lesson host: the Mini App
    // answers a spent allowance where the learner tapped, without loading a
    // lesson it already knows it will refuse.
    var limitedLesson by remember(map?.lessonLimit) { mutableStateOf<CourseLesson?>(null) }
    val promoAllowed = hsk30PromoAllowed && pendingTrackSwitch == null &&
        limitedLesson == null && state.chestRewardXp == null &&
        !state.isSwitchingTrack && !state.isOpeningChest
    val hsk30PromoEligible = !state.isStale && map?.hsk30?.promo?.eligible == true
    LaunchedEffect(hsk30PromoEligible, state.isRefreshing, promoAllowed) {
        if (hsk30PromoEligible && !state.isRefreshing && promoAllowed) onHsk30PromoShown()
    }
    Box(modifier = modifier.fillMaxSize()) {
        HskSceneSurface(modifier = Modifier.fillMaxSize()) {
            when {
                state.isLoading && map == null -> Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) { HskBrandLoader() }

                map == null -> CourseErrorBlock(
                    messageRes = state.error?.messageRes ?: R.string.error_unknown,
                    onRetry = onRetry,
                )

                else -> {
                    val rows = remember(map) { map.toRows() }
                    val listState = rememberLazyListState()
                    val viewportHeight = listState.layoutInfo.viewportSize.height
                    val foundationVisible = map.level.equals("hsk1", ignoreCase = true) && map.foundation != null
                    val foundationMustComeFirst = foundationVisible && map.foundation?.mustComeFirst == true

                    LaunchedEffect(
                        map.currentLesson?.order,
                        viewportHeight,
                        foundationVisible,
                        foundationMustComeFirst,
                    ) {
                        if (foundationMustComeFirst) {
                            listState.scrollToItem(0)
                            return@LaunchedEffect
                        }
                        val rowIndex = rows.indexOfFirst {
                            it is CourseRow.Path &&
                                (it.item as? PathItem.Lesson)?.lesson?.isCurrent == true
                        }
                        if (rowIndex >= 0 && viewportHeight > 0) {
                            listState.scrollToItem(
                                index = rowIndex + if (foundationVisible) 1 else 0,
                                scrollOffset = -(viewportHeight * 0.42f).roundToInt(),
                            )
                        }
                    }

                    Column(Modifier.fillMaxSize()) {
                        CourseHeader(
                            map = map,
                            dailyGoal = dailyGoal,
                            onOpenGoal = onOpenGoal,
                            hints = hints,
                            onDismissHint = onDismissHint,
                            isSwitchingTrack = state.isSwitchingTrack,
                            onSwitchTrack = { targetTrack, targetLevel ->
                                pendingTrackSwitch = targetTrack to targetLevel
                            },
                        )
                        if (!foundationMustComeFirst) {
                            map.today?.takeIf { it.tasks.isNotEmpty() }?.let { today ->
                                TodayPlanCard(today = today, onTask = onTodayTask)
                            }
                        }
                        if (state.isStale) StaleBanner()

                        LazyColumn(
                            state = listState,
                            modifier = Modifier.fillMaxWidth().weight(1f),
                            contentPadding = androidx.compose.foundation.layout.PaddingValues(
                                top = 8.dp,
                                // The tab bar floats over the list now, so the
                                // last lesson needs this to clear it.
                                bottom = 8.dp + LocalMainBottomInset.current,
                            ),
                        ) {
                            if (foundationVisible) {
                                item {
                                    map.foundation?.let { FoundationEntry(it) }
                                }
                            }
                            items(rows) { row ->
                                when (row) {
                                    is CourseRow.Unit -> UnitHeader(row.unit)
                                    is CourseRow.Path -> PathRow(
                                        row = row,
                                        chestReady = map.progress.rewardChest?.ready == true,
                                        isOpeningChest = state.isOpeningChest,
                                        isStale = state.isStale,
                                        unlockedLessonOrder = state.unlockedLessonOrder,
                                        onUnlockAnimationConsumed = onUnlockAnimationConsumed,
                                        onLesson = onLesson,
                                        onLimitedLesson = {
                                            val hsk30 = map.hsk30
                                            if (hsk30?.activeTrack == "hsk30" && !hsk30.access.allowed) {
                                                onUnlockHsk30()
                                            } else {
                                                limitedLesson = it
                                            }
                                        },
                                        onLockedLesson = onLockedLesson,
                                        onOpenChest = onOpenChest,
                                    )
                                }
                            }
                            item { Spacer(Modifier.height(14.dp)) }
                        }
                    }
                }
            }
        }

        if (limitedLesson != null) {
            SectionLimitOverlay(
                sectionTitle = stringResource(R.string.nav_course),
                sourceKey = "course_limit",
                limit = limit,
                reason = map?.lessonLimit?.limitText
                    ?: stringResource(R.string.limit_lesson_reason),
                // The server says when the allowance reopens; the hour is
                // never worked out here.
                resetAt = map?.lessonLimit?.resetAt,
                onClose = { limitedLesson = null },
            )
        }

        state.chestRewardXp?.let { reward ->
            RewardChestOverlay(
                rewardXp = reward,
                onContinue = onChestRewardConsumed,
            )
        }

        val hsk30 = map?.hsk30
        val hsk30Locked = hsk30 != null &&
            hsk30.activeTrack == "hsk30" &&
            hsk30.access.featureEnabled &&
            !hsk30.access.allowed

        if (hsk30Locked && hsk30 != null) {
            Hsk30LockedEntryDialog(
                hsk30 = hsk30,
                onUnlock = onUnlockHsk30,
                onBackToHsk20 = { onSwitchTrack("hsk20", null) },
            )
        }

        if (!hsk30Locked && state.hsk30PromoVisible && hsk30 != null && promoAllowed) {
            Hsk30PromoDialog(
                hsk30 = hsk30,
                onDismiss = onDismissHsk30Promo,
                onContinue = {
                    onDismissHsk30Promo()
                    pendingTrackSwitch = "hsk30" to null
                },
            )
        }

        if (!hsk30Locked) {
            pendingTrackSwitch?.let { (targetTrack, targetLevel) ->
                if (targetTrack == "hsk30" && hsk30 != null) {
                    Hsk30LevelChoiceDialog(
                        levels = hsk30.liveLevels,
                        isNew = hsk30.newBadge.isNew,
                        onDismiss = { pendingTrackSwitch = null },
                        onChoose = { level ->
                            pendingTrackSwitch = null
                            onSwitchTrack("hsk30", level)
                        },
                    )
                } else {
                    val targetLabel = "HSK 2.0"
                    AlertDialog(
                        onDismissRequest = { pendingTrackSwitch = null },
                        title = {
                            Text(
                                stringResource(R.string.profile_course_version_confirm_title, targetLabel),
                                fontWeight = FontWeight.SemiBold,
                            )
                        },
                        text = {
                            Text(
                                stringResource(R.string.profile_course_version_confirm_body),
                                color = PompColors.InkSecondary,
                            )
                        },
                        confirmButton = {
                            Button(
                                onClick = {
                                    pendingTrackSwitch = null
                                    onSwitchTrack(targetTrack, targetLevel)
                                },
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = PompColors.Cinnabar,
                                    contentColor = PompColors.OnCinnabar,
                                ),
                            ) {
                                Text(stringResource(R.string.action_continue))
                            }
                        },
                        dismissButton = {
                            TextButton(onClick = { pendingTrackSwitch = null }) {
                                Text(stringResource(R.string.action_cancel), color = PompColors.InkSecondary)
                            }
                        },
                        containerColor = PompColors.PaperRaised,
                    )
                }
            }
        }

    }
}

@Composable
private fun Hsk30BookDialog(
    isNew: Boolean,
    onDismiss: () -> Unit,
    dismissible: Boolean = true,
    content: @Composable ColumnScope.() -> Unit,
) {
    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(
            usePlatformDefaultWidth = false,
            dismissOnBackPress = dismissible,
            dismissOnClickOutside = dismissible,
        ),
    ) {
        BoxWithConstraints(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Surface(
                modifier = Modifier
                    .padding(horizontal = 20.dp)
                    .widthIn(max = 380.dp)
                    .fillMaxWidth()
                    .heightIn(max = maxHeight * 0.94f),
                shape = RoundedCornerShape(26.dp),
                color = PompColors.Paper,
                shadowElevation = 18.dp,
            ) {
                Column(
                    modifier = Modifier
                        .verticalScroll(rememberScrollState())
                        .padding(start = 22.dp, end = 22.dp, top = 22.dp, bottom = 14.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Hsk30BooksHeader(isNew = isNew, modifier = Modifier.fillMaxWidth())
                    Spacer(Modifier.height(16.dp))
                    content()
                }
            }
        }
    }
}

@Composable
private fun Hsk30BookTitle(title: String, body: String) {
    Text(
        title,
        color = PompColors.Ink,
        fontSize = 25.sp,
        lineHeight = 30.sp,
        fontWeight = FontWeight.Bold,
        textAlign = TextAlign.Center,
    )
    Spacer(Modifier.height(9.dp))
    Text(
        body,
        color = PompColors.InkSecondary,
        fontSize = 15.sp,
        lineHeight = 22.sp,
        textAlign = TextAlign.Center,
    )
}

@Composable
private fun Hsk30BookPrice(price: String) {
    Spacer(Modifier.height(20.dp))
    Box(Modifier.fillMaxWidth().height(1.dp).background(PompColors.Divider))
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Column(Modifier.weight(1f)) {
            Text(
                stringResource(R.string.hsk30_access_permanent),
                color = PompColors.Ink,
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                stringResource(R.string.hsk30_access_one_time),
                color = PompColors.InkSecondary,
                fontSize = 12.sp,
            )
        }
        Text(
            price,
            color = PompColors.Ink,
            fontSize = if (price.length > 10) 22.sp else 29.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
private fun Hsk30BookPrimary(label: String, enabled: Boolean = true, onClick: () -> Unit) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp),
        shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = PompColors.Cinnabar,
            contentColor = PompColors.OnCinnabar,
        ),
    ) {
        Text(
            label,
            fontSize = 16.sp,
            lineHeight = 21.sp,
            fontWeight = FontWeight.SemiBold,
            textAlign = TextAlign.Center,
            modifier = Modifier.weight(1f, fill = false),
        )
        Spacer(Modifier.width(12.dp))
        Text("→", fontSize = 23.sp)
    }
}

@Composable
private fun Hsk30BookSecondary(label: String, onClick: () -> Unit) {
    Spacer(Modifier.height(8.dp))
    TextButton(onClick = onClick, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
        Text(
            label,
            color = PompColors.InkSecondary,
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold,
            textAlign = TextAlign.Center,
        )
    }
}

@Composable
private fun Hsk30LockedEntryDialog(
    hsk30: com.pomp.hskai.domain.model.CourseHsk30,
    onUnlock: () -> Unit,
    onBackToHsk20: () -> Unit,
) {
    Hsk30BookDialog(isNew = hsk30.newBadge.isNew, onDismiss = {}, dismissible = false) {
        Hsk30BookTitle(
            title = stringResource(
                if (hsk30.access.paymentRejected) R.string.hsk30_payment_rejected_title
                else R.string.hsk30_access_required_title,
            ),
            body = stringResource(
                if (hsk30.access.paymentRejected) R.string.hsk30_payment_rejected_body
                else R.string.hsk30_access_required_body,
            ),
        )
        if (hsk30.priceDisplay.isNotBlank()) {
            Hsk30BookPrice(hsk30.priceDisplay)
        } else {
            Spacer(Modifier.height(20.dp))
        }
        Hsk30BookPrimary(
            label = stringResource(R.string.hsk30_access_unlock_button),
            enabled = hsk30.paymentEnabled && hsk30.priceDisplay.isNotBlank(),
            onClick = onUnlock,
        )
        Hsk30BookSecondary(stringResource(R.string.hsk30_access_back_hsk20), onBackToHsk20)
    }
}

@Composable
private fun Hsk30LevelChoiceDialog(
    levels: List<String>,
    isNew: Boolean,
    onDismiss: () -> Unit,
    onChoose: (String) -> Unit,
) {
    val selectable = levels
        .filter { Regex("^nhsk[1-3]$").matches(it.lowercase()) }
        .distinct()
    Hsk30BookDialog(isNew = isNew, onDismiss = onDismiss) {
        Hsk30BookTitle(
            title = stringResource(R.string.hsk30_level_picker_title),
            body = stringResource(R.string.hsk30_level_picker_body),
        )
        Spacer(Modifier.height(16.dp))
        selectable.forEach { level ->
            val band = Regex("^nhsk([1-3])$").find(level.lowercase())
                ?.groupValues?.getOrNull(1)
                ?: level
            Hsk30BookPrimary(
                label = "HSK $band" + if (isNew) " · NEW" else "",
                onClick = { onChoose(level) },
            )
            Spacer(Modifier.height(8.dp))
        }
        Hsk30BookSecondary(stringResource(R.string.action_cancel), onDismiss)
    }
}

@Composable
private fun Hsk30PromoDialog(
    hsk30: com.pomp.hskai.domain.model.CourseHsk30,
    onDismiss: () -> Unit,
    onContinue: () -> Unit,
) {
    val hasAccess = hsk30.access.allowed &&
        (hsk30.access.paidAccess || hsk30.access.permanentlyUnlocked || hsk30.access.provisionalAccess)
    Hsk30BookDialog(isNew = hsk30.newBadge.isNew, onDismiss = onDismiss) {
        Hsk30BookTitle(
            title = stringResource(if (hasAccess) R.string.hsk30_promo_switch else R.string.hsk30_promo_title),
            body = stringResource(
                if (hasAccess) R.string.hsk30_promo_body_unlocked else R.string.hsk30_access_required_body,
            ),
        )
        if (!hasAccess && hsk30.priceDisplay.isNotBlank()) {
            Hsk30BookPrice(hsk30.priceDisplay)
        } else {
            Spacer(Modifier.height(20.dp))
        }
        Hsk30BookPrimary(stringResource(R.string.hsk30_promo_switch), onClick = onContinue)
        Hsk30BookSecondary(stringResource(R.string.hsk30_promo_stay), onDismiss)
    }
}

private fun courseLevelLabel(level: String): String {
    val normalized = level.lowercase().trim()
    val nhsk = Regex("^nhsk([1-3])$").find(normalized)?.groupValues?.get(1)
    if (nhsk != null) return "HSK $nhsk"
    val number = normalized.removePrefix("hsk").toIntOrNull()
    return if (number != null) "HSK $number" else level.uppercase()
}

@Composable
private fun CourseHeader(
    map: CourseMap,
    dailyGoal: Int,
    onOpenGoal: () -> Unit,
    hints: List<AndroidHintDto>,
    onDismissHint: (String) -> Unit,
    isSwitchingTrack: Boolean,
    onSwitchTrack: (String, String?) -> Unit,
) {
    val hsk30 = map.hsk30
    val activeTrack = hsk30?.activeTrack
        ?: if (map.level.startsWith("nhsk", ignoreCase = true)) "hsk30" else "hsk20"
    val targetTrack = if (activeTrack == "hsk30") "hsk20" else "hsk30"
    val canSwitchTrack = hsk30 != null && (
        targetTrack == "hsk20" ||
            (hsk30.access.featureEnabled && hsk30.liveLevels.isNotEmpty())
        )
    val switchVersionAction = stringResource(R.string.course_switch_version)
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(start = 16.dp, end = 16.dp, top = 14.dp, bottom = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            HskSectionTitle(
                text = courseLevelLabel(map.level),
                modifier = if (canSwitchTrack) {
                    Modifier.clickable(
                        enabled = !isSwitchingTrack,
                        role = Role.Button,
                        onClickLabel = switchVersionAction,
                    ) {
                        onSwitchTrack(targetTrack, null)
                    }
                } else Modifier,
            )
            if (map.level.startsWith("nhsk", ignoreCase = true)) {
                Spacer(Modifier.width(5.dp))
                Text(
                    text = "NEW",
                    color = PompColors.CinnabarDark,
                    fontSize = 8.sp,
                    lineHeight = 10.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier
                        .background(PompColors.CinnabarSoft, RoundedCornerShape(5.dp))
                        .padding(horizontal = 4.dp, vertical = 2.dp),
                )
            }
        }
        Spacer(Modifier.width(8.dp))
        SectionHint(hints = hints, section = "course", onDismiss = onDismissHint)
        Spacer(Modifier.weight(1f))
        StatChip(
            Icons.Filled.LocalFireDepartment,
            PompColors.CinnabarInk,
            map.progress.streak.toString(),
            stringResource(R.string.today_streak),
        )
        Spacer(Modifier.width(8.dp))
        StatChip(
            Icons.Filled.Diamond,
            PompColors.GoldInk,
            map.progress.xp.toString(),
            stringResource(R.string.today_xp),
        )
        Spacer(Modifier.width(8.dp))
        GoalRing(map.progress.dailyXp, dailyGoal, onOpenGoal)
    }
}

@Composable
private fun StatChip(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    tint: Color,
    value: String,
    label: String,
) {
    Row(
        modifier = Modifier
            .padding(horizontal = 4.dp, vertical = 4.dp)
            .semantics { contentDescription = "$label: $value" },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(16.dp))
        Spacer(Modifier.width(5.dp))
        Text(
            value,
            style = MaterialTheme.typography.labelLarge.copy(
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium,
                letterSpacing = 0.sp,
            ),
            color = tint,
        )
    }
}

@Composable
fun GoalRing(
    dailyXp: Int,
    dailyGoal: Int,
    onClick: () -> Unit,
    size: Dp = 40.dp,
) {
    val goal = dailyGoal.coerceAtLeast(1)
    val fraction = (dailyXp.toFloat() / goal).coerceIn(0f, 1f)
    val complete = fraction >= 1f
    val description = stringResource(R.string.course_goal_progress, dailyXp, goal)
    Box(
        modifier = Modifier
            .size(size)
            .clip(CircleShape)
            .clickable(onClick = onClick)
            .semantics { contentDescription = description },
        contentAlignment = Alignment.Center,
    ) {
        Canvas(Modifier.fillMaxSize()) {
            val stroke = 5.dp.toPx()
            val inset = stroke / 2
            val arcSize = Size(this.size.width - stroke, this.size.height - stroke)
            drawArc(
                PompColors.Divider,
                0f,
                360f,
                false,
                Offset(inset, inset),
                arcSize,
                style = Stroke(stroke),
            )
            if (fraction > 0f) {
                drawArc(
                    if (complete) PompColors.Gold else PompColors.Cinnabar,
                    -90f,
                    360f * fraction,
                    false,
                    Offset(inset, inset),
                    arcSize,
                    style = Stroke(stroke, cap = StrokeCap.Round),
                )
            }
        }
        Icon(
            if (complete) Icons.Filled.Check else Icons.Filled.TrackChanges,
            contentDescription = null,
            tint = if (complete) PompColors.Gold else PompColors.Cinnabar,
            modifier = Modifier.size(size * 0.42f),
        )
    }
}

@Composable
private fun StaleBanner() {
    Surface(
        color = PompColors.GoldSoft,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
    ) {
        Text(
            stringResource(R.string.today_stale),
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.Ink,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
        )
    }
}

@Composable
private fun UnitHeader(unit: CourseUnit) {
    val shape = RoundedCornerShape(14.dp)
    val foreground = if (unit.isLocked) PompColors.InkSecondary else PompColors.Paper
    val bannerModifier = Modifier
        .fillMaxWidth()
        .padding(start = 16.dp, end = 16.dp, top = 8.dp)
        .then(
            if (unit.isLocked) Modifier else Modifier.background(
                brush = Brush.linearGradient(
                    colors = listOf(PompColors.Cinnabar, PompColors.CinnabarDark),
                ),
                shape = shape,
            )
        )
    if (unit.isLocked) {
        HskGlassSurface(
            modifier = bannerModifier,
            shape = shape,
            shadowElevation = 5.dp,
        ) {
            UnitHeaderBody(unit = unit, foreground = foreground)
        }
    } else {
        Surface(
            color = Color.Transparent,
            shape = shape,
            modifier = bannerModifier,
        ) {
            UnitHeaderBody(unit = unit, foreground = foreground)
        }
    }
}

@Composable
private fun UnitHeaderBody(unit: CourseUnit, foreground: Color) {
    Row(
        modifier = Modifier.padding(horizontal = 14.dp, vertical = 11.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = unit.title.ifBlank { unit.number.toString() },
            style = MaterialTheme.typography.titleMedium.copy(
                fontSize = 15.sp,
                lineHeight = 20.sp,
                fontWeight = FontWeight.SemiBold,
            ),
            color = foreground,
            modifier = Modifier.weight(1f),
            maxLines = 2,
        )
        MiniAppNodeIcon(
            kind = if (unit.isLocked) CourseNodeIconKind.Lock else CourseNodeIconKind.Book2,
            tint = foreground.copy(alpha = 0.85f),
            size = 18.dp,
        )
    }
}

private val NODE_SIZE = 64.dp
private val CURRENT_RING_SIZE = 76.dp

/** Bitta o'lchov — [COURSE_PATH_ROW_HEIGHT_DP] bilan bir xil bo'lishi shart. */
private val PATH_ROW_HEIGHT = COURSE_PATH_ROW_HEIGHT_DP.dp
private val PATH_SWING = COURSE_PATH_SWING_DP.dp

private fun pathOffset(unitIndex: Int, nodeIndex: Int): Dp =
    coursePathOffsetDp(unitIndex, nodeIndex).dp

private fun courseNodeLabel(value: String): String =
    if (value.length > 10) value.take(9) + "…" else value

@Composable
private fun PathRow(
    row: CourseRow.Path,
    chestReady: Boolean,
    isOpeningChest: Boolean,
    isStale: Boolean,
    unlockedLessonOrder: Int?,
    onUnlockAnimationConsumed: () -> Unit,
    onLesson: (CourseLesson) -> Unit,
    /** A lesson the spent daily allowance is holding shut. */
    onLimitedLesson: (CourseLesson) -> Unit,
    /** A lesson not reached yet — the Mini App offers a skip test here. */
    onLockedLesson: (CourseLesson) -> Unit,
    onOpenChest: () -> Unit,
) {
    val offsetX = pathOffset(row.unitIndex, row.nodeIndex)
    val pandaPrompts = stringArrayResource(R.array.course_panda_prompts)
    val pandaPrompt = row.pandaPromptIndex?.let { pandaPrompts[it % pandaPrompts.size] }
    val chestDescription = stringResource(R.string.course_chest_cd)

    Box(
        modifier = Modifier.fillMaxWidth().height(PATH_ROW_HEIGHT),
        // TopCenter, Center EMAS. Tugun qatorning tepasida turishi shart:
        // yo'lakcha uning markazini qatorning tepasidan 38dp pastda deb
        // hisoblaydi, va ustun markazlashtirilsa tugun yuqoriga surilib
        // yo'lakcha uning yonidan o'tib ketadi.
        contentAlignment = Alignment.TopCenter,
    ) {
        if (row.nodeCount >= 2) PathTrailSlice(row)

        if (pandaPrompt != null) {
            val onLeft = offsetX.value >= 0f
            PathPanda(
                text = pandaPrompt,
                leftBubble = onLeft,
                animationDelayMillis = (row.nodeIndex % 4) * 400,
                modifier = Modifier
                    .align(if (onLeft) Alignment.CenterStart else Alignment.CenterEnd)
                    .padding(start = if (onLeft) 8.dp else 0.dp, end = if (onLeft) 0.dp else 8.dp),
            )
        }

        Column(
            // Tugun markazi `COURSE_NODE_CENTER_DP` ga to'g'ri keladi,
            // shuning uchun yo'lakcha aynan shu nuqtadan o'tadi.
            modifier = Modifier.offset(x = offsetX, y = COURSE_NODE_TOP_GAP_DP.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Box(modifier = Modifier.size(CURRENT_RING_SIZE), contentAlignment = Alignment.Center) {
                when (val item = row.item) {
                    is PathItem.Lesson -> {
                        val lesson = item.lesson
                        // Every node answers a tap, the way the Mini App's
                        // `openLessonSheet` does. Which answer depends on why
                        // the lesson is shut: a spent allowance opens the limit
                        // window, a lesson not reached yet offers the skip
                        // test. A node that silently does nothing reads as a
                        // broken app, which is what it was.
                        val lessonDescription = lesson.stateLabel()
                        Box(
                            modifier = Modifier
                                .size(CURRENT_RING_SIZE)
                                .clickable {
                                    when (lesson.access) {
                                        LessonAccess.Open,
                                        LessonAccess.HalfPreview,
                                        -> onLesson(lesson)
                                        // Progress styling and access are
                                        // independent: current still pulses,
                                        // while a spent allowance opens this window.
                                        LessonAccess.PremiumLocked -> onLimitedLesson(lesson)
                                        LessonAccess.NotReached -> onLockedLesson(lesson)
                                    }
                                }
                                .semantics { contentDescription = lessonDescription },
                            contentAlignment = Alignment.Center,
                        ) {
                            UnlockingLessonNode(
                                lesson = lesson,
                                active = unlockedLessonOrder == lesson.order,
                                onFinished = onUnlockAnimationConsumed,
                            )
                        }
                    }

                    PathItem.Chest -> {
                        val clickable = chestReady && !isStale && !isOpeningChest
                        Box(
                            modifier = Modifier
                                .size(CURRENT_RING_SIZE)
                                .then(if (clickable) Modifier.clickable(onClick = onOpenChest) else Modifier)
                                .semantics { contentDescription = chestDescription },
                            contentAlignment = Alignment.Center,
                        ) {
                            ChestNodeFace(isOpeningChest)
                        }
                    }

                    is PathItem.Boss -> BossNodeFace()
                }
            }

            when (val item = row.item) {
                is PathItem.Lesson -> {
                    val lesson = item.lesson
                    Text(
                        text = courseNodeLabel(lesson.hanziPreview),
                        style = MaterialTheme.typography.labelMedium
                            .copy(fontSize = 12.sp, lineHeight = 15.sp),
                        color = if (lesson.status == LessonStatus.LOCKED) {
                            PompColors.InkDisabled
                        } else {
                            PompColors.InkSecondary
                        },
                        fontWeight = FontWeight.Medium,
                        maxLines = 1,
                        textAlign = TextAlign.Center,
                    )
                    Text(
                        text = if (lesson.isCheckpoint) {
                            stringResource(R.string.course_checkpoint)
                        } else {
                            stringResource(R.string.course_part_label, lesson.part)
                        },
                        style = MaterialTheme.typography.labelSmall
                            .copy(fontSize = 10.sp, lineHeight = 13.sp),
                        color = PompColors.InkDisabled,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                    )
                }

                PathItem.Chest -> Unit
                is PathItem.Boss -> Text(
                    text = item.milestone.title.substringBefore(' ').ifBlank { item.milestone.title },
                    style = MaterialTheme.typography.labelMedium
                        .copy(fontSize = 12.sp, lineHeight = 15.sp),
                    color = PompColors.InkDisabled,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                )
            }
        }
    }
}

/**
 * Bu qatorga to'g'ri keladigan yo'lakcha bo'lagi.
 *
 * Qo'shnilarning gorizontal siljishi shu yerda hisoblanadi — chiziq
 * tugunlarni bog'lashi uchun u ularning joylashuvidan chiqishi kerak, aks
 * holda ikkalasi mustaqil ravishda "taxminan" bir joyga chiziladi.
 */
@Composable
private fun PathTrailSlice(row: CourseRow.Path) {
    val previousX = if (row.nodeIndex > 0) {
        coursePathOffsetDp(row.unitIndex, row.nodeIndex - 1)
    } else {
        null
    }
    val nextX = if (row.nodeIndex < row.nodeCount - 1) {
        coursePathOffsetDp(row.unitIndex, row.nodeIndex + 1)
    } else {
        null
    }
    Box(modifier = Modifier.fillMaxSize().clipToBounds()) {
        ContinuousCourseTrail(
            previousXDp = previousX,
            currentXDp = coursePathOffsetDp(row.unitIndex, row.nodeIndex),
            nextXDp = nextX,
            modifier = Modifier.fillMaxSize(),
        )
    }
}

@Composable
private fun UnlockingLessonNode(
    lesson: CourseLesson,
    active: Boolean,
    onFinished: () -> Unit,
) {
    if (!active) {
        LessonNodeFace(lesson)
        return
    }

    val haptics = LocalHapticFeedback.current
    val density = LocalDensity.current
    val nodeScale = remember(lesson.order) { Animatable(.78f) }
    val ringScale = remember(lesson.order) { Animatable(.60f) }
    val ringAlpha = remember(lesson.order) { Animatable(0f) }
    val lockScale = remember(lesson.order) { Animatable(.45f) }
    val lockAlpha = remember(lesson.order) { Animatable(0f) }
    val lockY = remember(lesson.order) { Animatable(0f) }

    LaunchedEffect(lesson.order) {
        delay(260)
        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
        coroutineScope {
            launch {
                nodeScale.animateTo(
                    1f,
                    keyframes {
                        durationMillis = 1050
                        .78f at 0
                        1.18f at 368
                        .96f at 651
                        1f at 1050
                    },
                )
            }
            launch {
                ringAlpha.animateTo(
                    0f,
                    keyframes {
                        durationMillis = 1100
                        0f at 0
                        1f at 330
                        0f at 1100
                    },
                )
            }
            launch {
                ringScale.animateTo(
                    1.65f,
                    keyframes {
                        durationMillis = 1100
                        .60f at 0
                        .88f at 330
                        1.65f at 1100
                    },
                )
            }
            launch {
                lockAlpha.animateTo(
                    0f,
                    keyframes {
                        durationMillis = 900
                        0f at 0
                        1f at 342
                        1f at 702
                        0f at 900
                    },
                )
            }
            launch {
                lockScale.animateTo(
                    .82f,
                    keyframes {
                        durationMillis = 900
                        .45f at 0
                        1.14f at 342
                        .98f at 702
                        .82f at 900
                    },
                )
            }
            launch {
                lockY.animateTo(
                    -36f,
                    keyframes {
                        durationMillis = 900
                        0f at 0
                        -10f at 342
                        -22f at 702
                        -36f at 900
                    },
                )
            }
        }
        onFinished()
    }

    Box(modifier = Modifier.size(CURRENT_RING_SIZE), contentAlignment = Alignment.Center) {
        Canvas(
            modifier = Modifier
                .size(NODE_SIZE + 16.dp)
                .graphicsLayer {
                    scaleX = ringScale.value
                    scaleY = ringScale.value
                    alpha = ringAlpha.value
                },
        ) {
            drawCircle(
                color = PompColors.Gold,
                radius = size.minDimension / 2f,
                style = Stroke(width = 3.dp.toPx()),
            )
        }
        Box(
            modifier = Modifier.graphicsLayer {
                scaleX = nodeScale.value
                scaleY = nodeScale.value
            },
        ) {
            LessonNodeFace(lesson)
        }
        Surface(
            shape = CircleShape,
            color = PompColors.Gold,
            modifier = Modifier
                .size(42.dp)
                .graphicsLayer {
                    alpha = lockAlpha.value
                    scaleX = lockScale.value
                    scaleY = lockScale.value
                    translationY = with(density) { lockY.value.dp.toPx() }
                    rotationZ = -16f * (1f - lockAlpha.value)
                },
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = Icons.Filled.LockOpen,
                    contentDescription = null,
                    tint = Color(0xFF3A2C08),
                    modifier = Modifier.size(21.dp),
                )
            }
        }
        LessonCharacterStage(
            character = LessonCharacter.Dragon,
            mood = LessonCharacterMood.Celebrate,
            reaction = LessonCharacterReaction.Celebrate,
            reactionKey = lesson.order,
            modifier = Modifier
                .size(76.dp)
                .offset(x = 70.dp, y = (-4).dp),
        )
    }
}

@Composable
private fun LessonNodeFace(lesson: CourseLesson) {
    val current = lesson.isCurrent
    val checkpoint = lesson.isCheckpoint
    val (background, depth, content, contentColor, border) = when {
        lesson.status == LessonStatus.DONE -> NodeStyle(
            PompColors.Jade,
            PompColors.DoneDepth,
            NodeContent.Done,
            PompColors.Paper,
            null,
        )
        current -> NodeStyle(
            PompColors.Cinnabar,
            PompColors.CinnabarDark,
            if (checkpoint) NodeContent.Checkpoint else NodeContent.Glyph,
            PompColors.OnCinnabar,
            null,
        )
        lesson.access.isPremiumLocked || lesson.access == LessonAccess.NotReached -> NodeStyle(
            PompColors.Divider,
            PompColors.LockedDepth,
            if (checkpoint) NodeContent.Checkpoint else NodeContent.Locked,
            PompColors.InkDisabled,
            null,
        )
        checkpoint -> NodeStyle(
            PompColors.CinnabarSoft,
            PompColors.BossDepth,
            NodeContent.Checkpoint,
            PompColors.Cinnabar,
            BorderStroke(2.dp, PompColors.Cinnabar),
        )
        else -> NodeStyle(
            PompColors.Cinnabar,
            PompColors.CinnabarDark,
            NodeContent.Glyph,
            PompColors.OnCinnabar,
            null,
        )
    }

    Box(modifier = Modifier.size(CURRENT_RING_SIZE), contentAlignment = Alignment.Center) {
        if (current) {
            Surface(
                color = Color.Transparent,
                shape = CircleShape,
                border = BorderStroke(2.dp, PompColors.CinnabarInk.copy(alpha = 0.48f)),
                modifier = Modifier.size(NODE_SIZE + 10.dp),
            ) {}
        }
        Box(Modifier.size(NODE_SIZE).offset(y = 4.dp).background(depth, CircleShape))
        Surface(
            color = background,
            shape = CircleShape,
            border = border,
            modifier = Modifier.size(NODE_SIZE),
        ) {
            Box(contentAlignment = Alignment.Center) {
                when (content) {
                    NodeContent.Done -> MiniAppLessonNodeIcon(
                        kind = CourseNodeIconKind.Check,
                        tint = contentColor,
                    )
                    NodeContent.Locked -> MiniAppLessonNodeIcon(
                        kind = CourseNodeIconKind.Lock,
                        tint = contentColor,
                    )
                    NodeContent.Checkpoint -> MiniAppLessonNodeIcon(
                        kind = CourseNodeIconKind.Flag,
                        tint = contentColor,
                    )
                    NodeContent.Glyph -> Text(
                        text = "学",
                        style = PompTextStyles.hanziSmall.copy(fontSize = 19.sp),
                        color = contentColor,
                    )
                }
            }
        }
    }
}

@Composable
private fun ChestNodeFace(opening: Boolean) {
    Box(modifier = Modifier.size(CURRENT_RING_SIZE), contentAlignment = Alignment.Center) {
        Box(
            Modifier
                .size(NODE_SIZE)
                .offset(y = 4.dp)
                .background(PompColors.ChestDepth, CircleShape),
        )
        Surface(
            color = PompColors.GoldSoft,
            shape = CircleShape,
            border = BorderStroke(2.dp, PompColors.Gold),
            modifier = Modifier.size(NODE_SIZE),
        ) {
            Box(contentAlignment = Alignment.Center) {
                if (opening) {
                    HskBrandLoader(compact = true)
                } else {
                    MiniAppLessonNodeIcon(
                        kind = CourseNodeIconKind.Gift,
                        tint = PompColors.Gold,
                    )
                }
            }
        }
    }
}

@Composable
private fun BossNodeFace() {
    Box(modifier = Modifier.size(CURRENT_RING_SIZE), contentAlignment = Alignment.Center) {
        Box(
            Modifier
                .size(NODE_SIZE)
                .offset(y = 4.dp)
                .background(PompColors.BossDepth, CircleShape),
        )
        Surface(
            color = PompColors.CinnabarSoft,
            shape = CircleShape,
            border = BorderStroke(2.dp, PompColors.Cinnabar),
            modifier = Modifier.size(NODE_SIZE),
        ) {
            Box(contentAlignment = Alignment.Center) {
                MiniAppLessonNodeIcon(
                    kind = CourseNodeIconKind.Star,
                    tint = PompColors.Cinnabar,
                )
            }
        }
    }
}

@Composable
private fun ChestGlyph(modifier: Modifier = Modifier) {
    Canvas(modifier) {
        val stroke = 2.dp.toPx()
        drawRoundRect(
            color = PompColors.Gold,
            topLeft = Offset(size.width * 0.08f, size.height * 0.30f),
            size = Size(size.width * 0.84f, size.height * 0.58f),
            cornerRadius = androidx.compose.ui.geometry.CornerRadius(5.dp.toPx()),
            style = Stroke(stroke),
        )
        drawRoundRect(
            color = PompColors.Gold,
            topLeft = Offset(size.width * 0.12f, size.height * 0.18f),
            size = Size(size.width * 0.76f, size.height * 0.28f),
            cornerRadius = androidx.compose.ui.geometry.CornerRadius(5.dp.toPx()),
            style = Stroke(stroke),
        )
        drawLine(
            color = PompColors.Gold,
            start = Offset(size.width * 0.50f, size.height * 0.32f),
            end = Offset(size.width * 0.50f, size.height * 0.84f),
            strokeWidth = stroke,
        )
        drawCircle(
            color = PompColors.Gold,
            radius = 2.5.dp.toPx(),
            center = Offset(size.width * 0.50f, size.height * 0.58f),
        )
    }
}

@Composable
private fun PathPanda(
    text: String,
    leftBubble: Boolean,
    animationDelayMillis: Int,
    modifier: Modifier = Modifier,
) {
    val bubbleFill = if (PompColors.IsDark) {
        PompColors.PaperRaised.copy(alpha = 0.88f)
    } else {
        Color.White.copy(alpha = 0.72f)
    }
    Box(modifier = modifier.size(72.dp), contentAlignment = Alignment.Center) {
        CoursePandaMascot(
            modifier = Modifier.size(72.dp),
            animationDelayMillis = animationDelayMillis,
        )
        Box(
            modifier = Modifier
                .align(if (leftBubble) Alignment.TopStart else Alignment.TopEnd)
                .offset(y = (-28).dp),
        ) {
            HskGlassSurface(
                shape = RoundedCornerShape(14.dp),
                shadowElevation = 4.dp,
            ) {
                Text(
                    text = text,
                    style = MaterialTheme.typography.labelSmall.copy(
                        fontSize = 11.sp,
                        lineHeight = 11.sp,
                        fontWeight = FontWeight.Medium,
                    ),
                    color = PompColors.Ink,
                    modifier = Modifier.padding(horizontal = 11.dp, vertical = 6.dp),
                    maxLines = 1,
                )
            }
            Canvas(
                modifier = Modifier
                    .size(8.dp)
                    .align(if (leftBubble) Alignment.BottomStart else Alignment.BottomEnd)
                    .offset(
                        x = if (leftBubble) 20.dp else (-20).dp,
                        y = 4.dp,
                    ),
            ) {
                val path = Path().apply {
                    moveTo(size.width / 2f, size.height)
                    lineTo(0f, size.height / 2f)
                    lineTo(size.width / 2f, 0f)
                    lineTo(size.width, size.height / 2f)
                    close()
                }
                drawPath(path, color = bubbleFill)
                drawLine(
                    PompColors.Divider,
                    Offset(size.width / 2f, size.height),
                    Offset(size.width, size.height / 2f),
                    strokeWidth = 1.dp.toPx(),
                )
                drawLine(
                    PompColors.Divider,
                    Offset(size.width, size.height / 2f),
                    Offset(size.width / 2f, 0f),
                    strokeWidth = 1.dp.toPx(),
                )
            }
        }
    }
}

@Composable
private fun RewardChestOverlay(rewardXp: Int, onContinue: () -> Unit) {
    Surface(
        color = PompColors.Overlay.copy(alpha = 0.56f),
        modifier = Modifier.fillMaxSize(),
    ) {
        Box(contentAlignment = Alignment.Center) {
            HskGlassSurface(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 28.dp),
                shape = RoundedCornerShape(22.dp),
                shadowElevation = 16.dp,
            ) {
                Column(
                    modifier = Modifier.padding(horizontal = 22.dp, vertical = 24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    CoursePandaMascot(mood = PandaMood.Celebrate, modifier = Modifier.size(104.dp))
                    Spacer(Modifier.height(6.dp))
                    ChestGlyph(Modifier.size(58.dp))
                    Spacer(Modifier.height(12.dp))
                    Text(
                        text = stringResource(R.string.course_chest_reward, rewardXp),
                        style = MaterialTheme.typography.headlineSmall,
                        color = PompColors.Gold,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(Modifier.height(18.dp))
                    HskPrimaryButton(
                        text = stringResource(R.string.action_continue),
                        onClick = onContinue,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }
        }
    }
}

@Composable
private fun CourseErrorBlock(messageRes: Int, onRetry: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            stringResource(messageRes),
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(16.dp))
        HskGlassButton(
            text = stringResource(R.string.action_retry),
            onClick = onRetry,
        )
    }
}

@Composable
private fun CourseLesson.stateLabel(): String = when (access) {
    LessonAccess.Open -> stringResource(R.string.course_part_label, part)
    LessonAccess.HalfPreview -> stringResource(R.string.today_reason_preview)
    LessonAccess.PremiumLocked -> stringResource(R.string.today_reason_premium)
    LessonAccess.NotReached -> stringResource(R.string.today_reason_not_reached)
}

private data class NodeStyle(
    val background: Color,
    val depth: Color,
    val content: NodeContent,
    val contentColor: Color,
    val border: BorderStroke?,
)

private enum class NodeContent { Done, Locked, Checkpoint, Glyph }

private sealed interface PathItem {
    data class Lesson(val lesson: CourseLesson) : PathItem
    data object Chest : PathItem
    data class Boss(val milestone: CourseMilestone) : PathItem
}

private sealed interface CourseRow {
    data class Unit(val unit: CourseUnit) : CourseRow
    data class Path(
        val item: PathItem,
        val unitIndex: Int,
        val nodeIndex: Int,
        val previousNodeIndex: Int?,
        val pandaPromptIndex: Int?,
        val nodeCount: Int,
    ) : CourseRow
}

private fun CourseMap.toRows(): List<CourseRow> = buildList {
    var mascotCount = 0
    units.forEachIndexed { unitIndex, unit ->
        add(CourseRow.Unit(unit))
        val nodes = unit.lessons
            .map { lesson -> PathItem.Lesson(lesson) as PathItem }
            .toMutableList()
        if (!unit.isLocked && unit.milestone != null) {
            nodes.add(minOf(3, nodes.size), PathItem.Chest)
            nodes.add(PathItem.Boss(unit.milestone))
        }
        nodes.forEachIndexed { nodeIndex, item ->
            val pandaPrompt = if (
                item is PathItem.Lesson &&
                !item.lesson.isCurrent &&
                nodeIndex % 5 == 2
            ) {
                mascotCount++ % 4
            } else {
                null
            }
            add(
                CourseRow.Path(
                    item = item,
                    unitIndex = unitIndex,
                    nodeIndex = nodeIndex,
                    previousNodeIndex = if (nodeIndex > 0) nodeIndex - 1 else null,
                    pandaPromptIndex = pandaPrompt,
                    nodeCount = nodes.size,
                )
            )
        }
    }
}
