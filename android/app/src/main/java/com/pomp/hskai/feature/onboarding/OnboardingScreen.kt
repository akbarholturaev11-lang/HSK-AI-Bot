package com.pomp.hskai.feature.onboarding

import android.animation.ValueAnimator
import android.os.Build
import android.view.HapticFeedbackConstants
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.keyframes
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.progressBarRangeInfo
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.zIndex
import com.pomp.hskai.core.design.PompColors

/**
 * Native port of `app/static/course_v3_onboarding.html`.
 *
 * The Mini App remains the visual/product source of truth. This composable owns
 * presentation only; server completion is deliberately injected through
 * callbacks so Android cannot create a second course-rules implementation.
 */
@Immutable
data class OnboardingUiState(
    val step: Int = 0,
    val selectedLevel: String = "beginner",
    val selectedGoal: String = "hsk_exam",
    val submitting: Boolean = false,
    val error: Boolean = false,
)

@Immutable
data class OnboardingCopy(
    val hello: String,
    val boot: String,
    val askLevel: String,
    val levelHint: String,
    val start: String,
    val continueLabel: String,
    val firstLesson: String,
    val retry: String,
    val askGoal: String,
    val goalHint: String,
    val welcomeNote: String,
    val levelNote: String,
    val goalNote: String,
    val back: String,
    val saving: String,
    val saveError: String,
    val beginner: String,
    val beginnerSub: String,
    val selected: String,
) {
    companion object {
        fun forLanguage(language: String): OnboardingCopy = when (language.lowercase()) {
            "uz" -> OnboardingCopy(
                hello = "Salom! Men Li ustozman.",
                boot = "Xitoy tilini qadamma-qadam o'rganing. O'zingizga mos darajadan boshlang.",
                askLevel = "Xitoy tilini qanchalik bilasiz?",
                levelHint = "HSK — xitoy tilini bilish darajalari.",
                start = "Boshlash",
                continueLabel = "Davom etish",
                firstLesson = "Birinchi darsni boshlash",
                retry = "Qayta urinib ko'rish",
                askGoal = "Xitoy tili sizga nima uchun kerak?",
                goalHint = "Kunlik rejangiz shu maqsadga mos bo'ladi.",
                welcomeNote = "2 ta qisqa savol. Keyin — birinchi dars.",
                levelNote = "O'zingizga mos darajani tanlang.",
                goalNote = "Tayyor. Endi birinchi darsingizga o'tamiz.",
                back = "Orqaga",
                saving = "Saqlanmoqda…",
                saveError = "Tanlov saqlanmadi. Internetni tekshirib, qayta urinib ko'ring.",
                beginner = "Noldan boshlayman",
                beginnerSub = "Avval hanzi, pinyin va tonlar",
                selected = "Darajangiz",
            )
            "tg", "tj" -> OnboardingCopy(
                hello = "Салом! Ман устод Ли ҳастам.",
                boot = "Забони чинӣ — қадам ба қадам. Аз сатҳи мувофиқ оғоз кунед.",
                askLevel = "Забони чиниро то чӣ андоза медонед?",
                levelHint = "HSK — сатҳҳои дониши забони чинӣ аст.",
                start = "Оғоз",
                continueLabel = "Идома",
                firstLesson = "Оғози дарси аввал",
                retry = "Боз кӯшиш кунед",
                askGoal = "Забони чинӣ ба шумо барои чӣ лозим аст?",
                goalHint = "Нақшаи рӯзонаи шумо ба ин мақсад мувофиқ мешавад.",
                welcomeNote = "2 саволи кӯтоҳ. Баъд — дарси аввал.",
                levelNote = "Сатҳи мувофиқро интихоб кунед.",
                goalNote = "Тайёр. Акнун ба дарси аввал мегузарем.",
                back = "Бозгашт",
                saving = "Сабт мешавад…",
                saveError = "Интихоб сабт нашуд. Интернетро санҷида, боз кӯшиш кунед.",
                beginner = "Аз сифр оғоз мекунам",
                beginnerSub = "Аввал ханзӣ, пинйин ва оҳангҳо",
                selected = "Сатҳи шумо",
            )
            else -> OnboardingCopy(
                hello = "Привет! Я учитель Ли.",
                boot = "Китайский — шаг за шагом. Начните с того, что уже знаете.",
                askLevel = "Сколько китайского вы уже знаете?",
                levelHint = "HSK — это уровни знания китайского языка.",
                start = "Начать",
                continueLabel = "Продолжить",
                firstLesson = "Начать первый урок",
                retry = "Попробовать снова",
                askGoal = "Зачем вам китайский?",
                goalHint = "Подберём акцент в вашем плане на день.",
                welcomeNote = "Всего 2 вопроса — и к первому уроку.",
                levelNote = "Выберите свой уровень — я помогу начать.",
                goalNote = "Всё готово. Перейдём к вашему первому уроку.",
                back = "Назад",
                saving = "Сохраняем…",
                saveError = "Не удалось сохранить выбор. Проверьте соединение и попробуйте снова.",
                beginner = "Начинаю с нуля",
                beginnerSub = "Сначала ханцзы, пиньинь и тоны",
                selected = "Ваш уровень",
            )
        }
    }
}

private data class LevelOption(val key: String, val title: String, val subtitle: String)
private data class GoalOption(
    val key: String,
    val titles: Map<String, String>,
    val subtitles: Map<String, String>,
    val icon: OnboardingIconKind,
)

private val stageEaseOut = CubicBezierEasing(0f, 0f, 0.58f, 1f)
private val cssEase = CubicBezierEasing(0.25f, 0.1f, 0.25f, 1f)

private val goals = listOf(
    GoalOption(
        "hsk_exam",
        mapOf("uz" to "HSK imtihonini topshirish", "ru" to "Сдать HSK", "tg" to "Супоридани HSK"),
        mapOf("uz" to "Ko'proq test va xatolar ustida ish", "ru" to "Больше тестов и разбора ошибок", "tg" to "Бештар тест ва кор бар хатоҳо"),
        OnboardingIconKind.HskExam,
    ),
    GoalOption(
        "daily_communication",
        mapOf("uz" to "Kundalik muloqot", "ru" to "Общаться в жизни", "tg" to "Муоширати ҳаррӯза"),
        mapOf("uz" to "Ko'proq gapirish va talaffuz", "ru" to "Больше речи и произношения", "tg" to "Бештар сухан ва талаффуз"),
        OnboardingIconKind.DailyCommunication,
    ),
    GoalOption(
        "travel",
        mapOf("uz" to "Sayohat", "ru" to "Путешествия", "tg" to "Сафар"),
        mapOf("uz" to "Yo'ldagi holatlar va so'zlar", "ru" to "Живые ситуации и слова в дороге", "tg" to "Ҳолатҳо ва калимаҳои роҳ"),
        OnboardingIconKind.Travel,
    ),
    GoalOption(
        "work_china",
        mapOf("uz" to "Ish uchun xitoy tili", "ru" to "Работа с Китаем", "tg" to "Забони чинӣ барои кор"),
        mapOf("uz" to "Ishchan, hurmatli nutq", "ru" to "Вежливая рабочая речь", "tg" to "Сухани кории боэҳтиром"),
        OnboardingIconKind.WorkChina,
    ),
    GoalOption(
        "study_china",
        mapOf("uz" to "Xitoyda o'qish", "ru" to "Учёба в Китае", "tg" to "Таҳсил дар Чин"),
        mapOf("uz" to "Kursga va so'z boyligiga urg'u", "ru" to "Упор на курс и словарный запас", "tg" to "Таъкид ба курс ва луғат"),
        OnboardingIconKind.StudyChina,
    ),
)

@Composable
fun OnboardingScreen(
    language: String,
    state: OnboardingUiState,
    onLevelSelected: (String) -> Unit,
    onGoalSelected: (String) -> Unit,
    onBack: () -> Unit,
    onNext: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val copy = OnboardingCopy.forLanguage(language)
    val view = LocalView.current
    val configuration = LocalConfiguration.current
    val layoutSpec = remember(configuration.screenWidthDp, configuration.screenHeightDp) {
        OnboardingLayoutSpec.resolve(
            widthDp = configuration.screenWidthDp,
            heightDp = configuration.screenHeightDp,
        )
    }
    val motionEnabled = remember {
        Build.VERSION.SDK_INT < Build.VERSION_CODES.O || ValueAnimator.areAnimatorsEnabled()
    }
    var reactionKey by remember(state.step) { mutableIntStateOf(0) }
    var stageEntered by remember(state.step, motionEnabled) { mutableStateOf(!motionEnabled) }
    val stageAlpha by animateFloatAsState(
        targetValue = if (stageEntered) 1f else 0f,
        animationSpec = tween(
            durationMillis = if (motionEnabled) 240 else 0,
            easing = stageEaseOut,
        ),
        label = "onboarding-stage-alpha",
    )
    val stageOffset by animateFloatAsState(
        targetValue = if (stageEntered) 0f else 6f,
        animationSpec = tween(
            durationMillis = if (motionEnabled) 240 else 0,
            easing = stageEaseOut,
        ),
        label = "onboarding-stage-offset",
    )
    LaunchedEffect(state.step, motionEnabled) {
        stageEntered = true
    }
    val selectionFeedback: () -> Unit = {
        view.performHapticFeedback(HapticFeedbackConstants.CLOCK_TICK)
        reactionKey += 1
    }
    Surface(color = PompColors.Paper, modifier = modifier.fillMaxSize()) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.TopCenter) {
            Column(
                modifier = Modifier
                    .fillMaxHeight()
                    .fillMaxWidth()
                    .widthIn(max = 520.dp)
                    .windowInsetsPadding(WindowInsets.safeDrawing),
            ) {
                if (state.step > 0) {
                    OnboardingTopBar(
                        step = state.step,
                        backLabel = copy.back,
                        onBack = onBack,
                        disabled = state.submitting,
                        motionEnabled = motionEnabled,
                        layoutSpec = layoutSpec,
                    )
                }

                Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth()
                        .graphicsLayer {
                            alpha = stageAlpha
                            translationY = stageOffset.dp.toPx()
                        },
                ) {
                    key(state.step) {
                        when (state.step) {
                            0 -> WelcomeStep(
                                copy = copy,
                                motionEnabled = motionEnabled,
                                layoutSpec = layoutSpec,
                            )
                            1 -> ChoiceStep(
                                question = copy.askLevel,
                                helper = copy.levelHint,
                                reactionKey = reactionKey,
                                motionEnabled = motionEnabled,
                                layoutSpec = layoutSpec,
                            ) {
                                LevelChoices(
                                    language = language,
                                    copy = copy,
                                    selected = state.selectedLevel,
                                    enabled = !state.submitting,
                                    motionEnabled = motionEnabled,
                                    layoutSpec = layoutSpec,
                                    onSelected = { key ->
                                        onLevelSelected(key)
                                        selectionFeedback()
                                    },
                                )
                            }
                            else -> ChoiceStep(
                                question = copy.askGoal,
                                helper = copy.goalHint,
                                reactionKey = reactionKey,
                                motionEnabled = motionEnabled,
                                layoutSpec = layoutSpec,
                            ) {
                                SelectedLevelSummary(copy, state.selectedLevel)
                                GoalChoices(
                                    language = language,
                                    selected = state.selectedGoal,
                                    enabled = !state.submitting,
                                    motionEnabled = motionEnabled,
                                    layoutSpec = layoutSpec,
                                    onSelected = { key ->
                                        onGoalSelected(key)
                                        selectionFeedback()
                                    },
                                )
                            }
                        }
                    }
                }

                OnboardingFooter(
                    copy = copy,
                    state = state,
                    onNext = onNext,
                    motionEnabled = motionEnabled,
                    layoutSpec = layoutSpec,
                )
            }
        }
    }
}

@Composable
private fun OnboardingTopBar(
    step: Int,
    backLabel: String,
    onBack: () -> Unit,
    disabled: Boolean,
    motionEnabled: Boolean,
    layoutSpec: OnboardingLayoutSpec,
) {
    val progress by animateFloatAsState(
        targetValue = step / 2f,
        animationSpec = tween(
            durationMillis = if (motionEnabled) 300 else 0,
            easing = cssEase,
        ),
        label = "onboarding-progress",
    )
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(
                start = layoutSpec.topHorizontalPadding.dp,
                end = layoutSpec.topHorizontalPadding.dp,
                top = 14.dp,
                bottom = 4.dp,
            ),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier
                .size(44.dp)
                .clip(RoundedCornerShape(12.dp))
                .clickable(enabled = !disabled, role = Role.Button, onClick = onBack)
                .semantics { contentDescription = backLabel },
            contentAlignment = Alignment.Center,
        ) {
            MiniAppOnboardingIcon(
                kind = OnboardingIconKind.Back,
                tint = PompColors.InkSecondary,
            )
        }
        Spacer(Modifier.width(layoutSpec.topGap.dp))
        Box(
            modifier = Modifier
                .weight(1f)
                .height(8.dp)
                .clip(RoundedCornerShape(20.dp))
                .background(PompColors.Divider)
                .semantics {
                    progressBarRangeInfo = androidx.compose.ui.semantics.ProgressBarRangeInfo(
                        current = step.toFloat(),
                        range = 0f..2f,
                        steps = 1,
                    )
                },
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(progress)
                    .height(8.dp)
                    .background(PompColors.Cinnabar),
            )
        }
        Spacer(Modifier.width(layoutSpec.topGap.dp))
        Text(
            "$step / 2",
            color = PompColors.InkSecondary,
            fontSize = 12.sp,
            fontWeight = FontWeight.Medium,
        )
    }
}

@Composable
private fun WelcomeStep(
    copy: OnboardingCopy,
    motionEnabled: Boolean,
    layoutSpec: OnboardingLayoutSpec,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(
                start = layoutSpec.welcomeHorizontalPadding.dp,
                end = layoutSpec.welcomeHorizontalPadding.dp,
                top = layoutSpec.welcomeTopPadding.dp,
                bottom = layoutSpec.welcomeBottomPadding.dp,
            ),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        SpeechBubble(text = copy.hello, centeredTail = true, large = false)
        Spacer(Modifier.height(layoutSpec.welcomeBubbleBottomMargin.dp))
        Box(
            Modifier.size(
                layoutSpec.welcomePandaWidth.dp,
                layoutSpec.welcomePandaHeight.dp,
            ),
            contentAlignment = Alignment.Center,
        ) {
            OnboardingPandaMascot(
                motionEnabled = motionEnabled,
                modifier = Modifier.fillMaxSize(),
            )
        }
        Spacer(Modifier.height(layoutSpec.welcomePandaBottomMargin.dp))
        Text(
            "HSK AI",
            color = PompColors.Cinnabar,
            fontSize = layoutSpec.welcomeTitleSize.sp,
            lineHeight = (layoutSpec.welcomeTitleSize * 1.15f).sp,
            fontWeight = FontWeight.SemiBold,
            letterSpacing = (-1).sp,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(14.dp))
        Text(
            copy.boot,
            color = PompColors.InkSecondary,
            style = MaterialTheme.typography.bodyLarge.copy(
                fontSize = layoutSpec.welcomeBodySize.sp,
                lineHeight = (layoutSpec.welcomeBodySize * 1.65f).sp,
            ),
            textAlign = TextAlign.Center,
            modifier = Modifier.widthIn(max = 330.dp),
        )
    }
}

@Composable
private fun ChoiceStep(
    question: String,
    helper: String,
    reactionKey: Int,
    motionEnabled: Boolean,
    layoutSpec: OnboardingLayoutSpec,
    choices: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(
                    start = layoutSpec.guideHorizontalPadding.dp,
                    end = layoutSpec.guideHorizontalPadding.dp,
                    top = layoutSpec.guideTopPadding.dp,
                    bottom = layoutSpec.guideBottomPadding.dp,
                ),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                Modifier.size(
                    layoutSpec.guidePandaWidth.dp,
                    layoutSpec.guidePandaHeight.dp,
                ),
                contentAlignment = Alignment.Center,
            ) {
                OnboardingPandaMascot(
                    reactionKey = reactionKey,
                    motionEnabled = motionEnabled,
                    modifier = Modifier.fillMaxSize(),
                )
            }
            Spacer(Modifier.width(layoutSpec.guideGap.dp))
            Box(Modifier.weight(1f)) {
                SpeechBubble(
                    text = question,
                    centeredTail = false,
                    large = true,
                    largeFontSize = layoutSpec.questionFontSize,
                    compactPadding = layoutSpec.compactWidth,
                )
            }
        }
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(
                    start = layoutSpec.horizontalPadding.dp,
                    end = layoutSpec.horizontalPadding.dp,
                    bottom = 16.dp,
                ),
        ) {
            Text(
                helper,
                color = PompColors.InkSecondary,
                fontSize = 13.sp,
                lineHeight = 20.sp,
                modifier = Modifier.padding(bottom = 17.dp),
            )
            choices()
        }
    }
}

@Composable
private fun SpeechBubble(
    text: String,
    centeredTail: Boolean,
    large: Boolean,
    largeFontSize: Int = 21,
    compactPadding: Boolean = false,
) {
    Box {
        Surface(
            color = PompColors.PaperRaised,
            shape = RoundedCornerShape(if (large) 18.dp else 16.dp),
            border = BorderStroke(1.dp, PompColors.Divider),
            modifier = Modifier.zIndex(1f),
        ) {
            Text(
                text,
                color = PompColors.Ink,
                fontSize = if (large) largeFontSize.sp else 17.sp,
                lineHeight = if (large) (largeFontSize * 1.35f).sp else 25.sp,
                letterSpacing = if (large) (-0.35).sp else 0.sp,
                fontWeight = if (large) FontWeight.SemiBold else FontWeight.Medium,
                modifier = Modifier.padding(
                    horizontal = if (large) {
                        if (compactPadding) 14.dp else 18.dp
                    } else {
                        22.dp
                    },
                    vertical = if (large) {
                        if (compactPadding) 14.dp else 17.dp
                    } else {
                        14.dp
                    },
                ),
            )
        }
        MiniAppBubbleTail(
            centered = centeredTail,
            modifier = Modifier
                .align(if (centeredTail) Alignment.BottomCenter else Alignment.CenterStart)
                .zIndex(0f),
        )
    }
}

@Composable
private fun LevelChoices(
    language: String,
    copy: OnboardingCopy,
    selected: String,
    enabled: Boolean,
    motionEnabled: Boolean,
    layoutSpec: OnboardingLayoutSpec,
    onSelected: (String) -> Unit,
) {
    val lang = canonicalLanguage(language)
    val descriptions = when (lang) {
        "uz" -> listOf("Biroz xitoycha bilaman", "Asosiy suhbat", "Kundalik muloqot", "Erkin muloqot")
        "tg" -> listOf("Каме забони чинӣ медонам", "Муоширати асосӣ", "Муоширати ҳаррӯза", "Муоширати озод")
        else -> listOf("Уже немного знаю китайский", "Базовое общение", "Повседневное общение", "Свободное общение")
    }
    val levels = listOf(
        LevelOption("beginner", copy.beginner, copy.beginnerSub),
        LevelOption("hsk1", "HSK 1", descriptions[0]),
        LevelOption("hsk2", "HSK 2", descriptions[1]),
        LevelOption("hsk3", "HSK 3", descriptions[2]),
        LevelOption("hsk4", "HSK 4", descriptions[3]),
    )
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        levels.forEachIndexed { index, option ->
            ChoiceCard(
                selected = selected == option.key,
                enabled = enabled,
                motionEnabled = motionEnabled,
                layoutSpec = layoutSpec,
                title = option.title,
                subtitle = option.subtitle,
                leading = { LevelBars(active = index) },
                onClick = { onSelected(option.key) },
            )
        }
    }
}

@Composable
private fun LevelBars(active: Int) {
    Row(
        modifier = Modifier.width(42.dp).height(30.dp),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.Bottom,
    ) {
        repeat(5) { index ->
            Box(
                Modifier
                    .padding(horizontal = 1.5.dp)
                    .width(5.dp)
                    .height((9 + index * 5).dp)
                    .clip(RoundedCornerShape(3.dp))
                    .background(if (index <= active) PompColors.Cinnabar else PompColors.Divider),
            )
        }
    }
}

@Composable
private fun GoalChoices(
    language: String,
    selected: String,
    enabled: Boolean,
    motionEnabled: Boolean,
    layoutSpec: OnboardingLayoutSpec,
    onSelected: (String) -> Unit,
) {
    val lang = canonicalLanguage(language)
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        goals.forEach { goal ->
            ChoiceCard(
                selected = selected == goal.key,
                enabled = enabled,
                motionEnabled = motionEnabled,
                layoutSpec = layoutSpec,
                title = goal.titles[lang] ?: goal.titles.getValue("ru"),
                subtitle = goal.subtitles[lang] ?: goal.subtitles.getValue("ru"),
                leading = {
                    Box(Modifier.size(36.dp), contentAlignment = Alignment.Center) {
                        MiniAppOnboardingIcon(
                            kind = goal.icon,
                            tint = if (selected == goal.key) PompColors.CinnabarDark else PompColors.InkSecondary,
                            size = 25.dp,
                            strokeWidth = 1.6f,
                        )
                    }
                },
                onClick = { onSelected(goal.key) },
            )
        }
    }
}

@Composable
private fun ChoiceCard(
    selected: Boolean,
    enabled: Boolean,
    motionEnabled: Boolean,
    layoutSpec: OnboardingLayoutSpec,
    title: String,
    subtitle: String,
    leading: @Composable () -> Unit,
    onClick: () -> Unit,
) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val cardScale by animateFloatAsState(
        targetValue = if (pressed && enabled) 0.99f else 1f,
        animationSpec = tween(durationMillis = if (motionEnabled) 150 else 0),
        label = "onboarding-choice-press",
    )
    val checkScale = remember { Animatable(1f) }
    LaunchedEffect(selected, motionEnabled) {
        if (selected && motionEnabled) {
            checkScale.snapTo(0.65f)
            checkScale.animateTo(
                targetValue = 1f,
                animationSpec = keyframes {
                    durationMillis = 250
                    0.65f at 0
                    1.14f at 162
                    1f at 250
                },
            )
        } else {
            checkScale.snapTo(1f)
        }
    }
    Surface(
        color = if (selected) Color(0xFFFFF3EF) else PompColors.PaperRaised,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, if (selected) PompColors.Cinnabar else PompColors.Divider),
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 72.dp)
            .graphicsLayer {
                scaleX = cardScale
                scaleY = cardScale
            }
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                enabled = enabled,
                role = Role.RadioButton,
                onClick = onClick,
            ),
    ) {
        Row(
            modifier = Modifier.padding(layoutSpec.cardPadding.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(Modifier.size(42.dp), contentAlignment = Alignment.Center) { leading() }
            Spacer(Modifier.width(layoutSpec.cardGap.dp))
            Column(Modifier.weight(1f)) {
                Text(
                    title,
                    color = if (selected) PompColors.CinnabarDark else PompColors.Ink,
                    fontSize = 15.sp,
                    lineHeight = 21.sp,
                    fontWeight = FontWeight.Medium,
                )
                Spacer(Modifier.height(4.dp))
                Text(subtitle, color = PompColors.InkSecondary, fontSize = 12.sp, lineHeight = 17.sp)
            }
            Spacer(Modifier.width(10.dp))
            Surface(
                modifier = Modifier
                    .size(20.dp)
                    .graphicsLayer {
                        scaleX = if (selected) checkScale.value else 1f
                        scaleY = if (selected) checkScale.value else 1f
                    },
                shape = CircleShape,
                color = if (selected) PompColors.Cinnabar else Color.Transparent,
                border = BorderStroke(1.dp, if (selected) PompColors.Cinnabar else PompColors.Divider),
            ) {
                if (selected) {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        MiniAppOnboardingIcon(
                            kind = OnboardingIconKind.Check,
                            tint = Color.White,
                            size = 14.dp,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun SelectedLevelSummary(copy: OnboardingCopy, level: String) {
    val title = when (level) {
        "beginner" -> copy.beginner
        "hsk1" -> "HSK 1"
        "hsk2" -> "HSK 2"
        "hsk3" -> "HSK 3"
        "hsk4" -> "HSK 4"
        else -> level.uppercase()
    }
    Row(
        modifier = Modifier.fillMaxWidth().padding(bottom = 17.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        MiniAppOnboardingIcon(
            kind = OnboardingIconKind.Check,
            tint = PompColors.Jade,
            size = 16.dp,
        )
        Spacer(Modifier.width(7.dp))
        Text(
            "${copy.selected}: $title",
            color = PompColors.InkSecondary,
            fontSize = 12.sp,
            lineHeight = 18.sp,
        )
    }
}

@Composable
private fun OnboardingFooter(
    copy: OnboardingCopy,
    state: OnboardingUiState,
    onNext: () -> Unit,
    motionEnabled: Boolean,
    layoutSpec: OnboardingLayoutSpec,
) {
    val label = when {
        state.submitting -> copy.saving
        state.error -> copy.retry
        state.step == 0 -> copy.start
        state.step == 1 -> copy.continueLabel
        else -> copy.firstLesson
    }
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val pressOffset by animateFloatAsState(
        targetValue = if (pressed && !state.submitting) 2f else 0f,
        animationSpec = tween(durationMillis = if (motionEnabled) 150 else 0),
        label = "onboarding-cta-press",
    )
    val buttonAlpha = if (state.submitting) 0.65f else 1f
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(PompColors.Paper),
    ) {
        Box(Modifier.fillMaxWidth().height(1.dp).background(PompColors.Divider))
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(
                    start = layoutSpec.footerHorizontalPadding.dp,
                    end = layoutSpec.footerHorizontalPadding.dp,
                    top = layoutSpec.footerTopPadding.dp,
                    bottom = layoutSpec.footerBottomPadding.dp,
                ),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            if (state.step == 0) {
                Text(
                    copy.welcomeNote,
                    color = PompColors.InkSecondary,
                    fontSize = 12.sp,
                    lineHeight = 18.sp,
                    textAlign = TextAlign.Center,
                )
                Spacer(Modifier.height(12.dp))
            }
            if (state.error) {
                Text(
                    copy.saveError,
                    color = PompColors.CinnabarDark,
                    fontSize = 13.sp,
                    lineHeight = 19.sp,
                    textAlign = TextAlign.Center,
                )
                Spacer(Modifier.height(12.dp))
            }
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(54.dp),
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(2.dp)
                        .align(Alignment.BottomCenter)
                        .graphicsLayer {
                            translationY = 2.dp.toPx()
                            alpha = buttonAlpha
                        }
                        .background(
                            if (pressed && !state.submitting) Color.Transparent else PompColors.CinnabarDark,
                            RoundedCornerShape(bottomStart = 13.dp, bottomEnd = 13.dp),
                        ),
                )
                Surface(
                    color = PompColors.Cinnabar,
                    shape = RoundedCornerShape(13.dp),
                    shadowElevation = 0.dp,
                    modifier = Modifier
                        .fillMaxSize()
                        .graphicsLayer {
                            translationY = pressOffset.dp.toPx()
                            alpha = buttonAlpha
                        }
                        .clickable(
                            interactionSource = interactionSource,
                            indication = null,
                            enabled = !state.submitting,
                            role = Role.Button,
                            onClick = onNext,
                        ),
                ) {
                    Row(
                        modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(label, color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                        if (!state.submitting && state.step > 0) {
                            Spacer(Modifier.width(10.dp))
                            MiniAppOnboardingIcon(
                                kind = OnboardingIconKind.Arrow,
                                tint = Color.White,
                            )
                        }
                    }
                }
            }
        }
    }
}

private fun canonicalLanguage(language: String): String = when (language.lowercase()) {
    "uz" -> "uz"
    "tg", "tj" -> "tg"
    else -> "ru"
}
