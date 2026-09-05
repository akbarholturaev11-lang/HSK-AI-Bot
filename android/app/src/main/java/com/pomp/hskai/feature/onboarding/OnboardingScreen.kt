package com.pomp.hskai.feature.onboarding

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ArrowForward
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.ChatBubbleOutline
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.Flight
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.WorkOutline
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.vector.ImageVector
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
import com.pomp.hskai.feature.course.CoursePandaMascot

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
    val icon: ImageVector,
)

private val goals = listOf(
    GoalOption(
        "hsk_exam",
        mapOf("uz" to "HSK imtihonini topshirish", "ru" to "Сдать HSK", "tg" to "Супоридани HSK"),
        mapOf("uz" to "Imtihon formati va natijaga yo'naltirilgan reja", "ru" to "План с акцентом на формат и результат экзамена", "tg" to "Нақша бо тамаркуз ба формати имтиҳон"),
        Icons.Filled.EmojiEvents,
    ),
    GoalOption(
        "daily_communication",
        mapOf("uz" to "Kundalik muloqot", "ru" to "Общаться в жизни", "tg" to "Муоширати ҳаррӯза"),
        mapOf("uz" to "Ko'proq tinglash va gapirish", "ru" to "Больше живой речи и аудирования", "tg" to "Бештар шунидан ва гуфтугӯ"),
        Icons.Filled.ChatBubbleOutline,
    ),
    GoalOption(
        "travel",
        mapOf("uz" to "Sayohat", "ru" to "Путешествия", "tg" to "Саёҳат"),
        mapOf("uz" to "Yo'l, mehmonxona va kundalik vaziyatlar", "ru" to "Дорога, отель и бытовые ситуации", "tg" to "Роҳ, меҳмонхона ва ҳолатҳои рӯзмарра"),
        Icons.Filled.Flight,
    ),
    GoalOption(
        "work_china",
        mapOf("uz" to "Ish uchun xitoy tili", "ru" to "Работа с Китаем", "tg" to "Кор бо Чин"),
        mapOf("uz" to "Ish, savdo va amaliy muloqot", "ru" to "Работа, торговля и деловое общение", "tg" to "Кор, тиҷорат ва муоширати амалӣ"),
        Icons.Filled.WorkOutline,
    ),
    GoalOption(
        "study_china",
        mapOf("uz" to "Xitoyda o'qish", "ru" to "Учёба в Китае", "tg" to "Таҳсил дар Чин"),
        mapOf("uz" to "O'qish va kampus hayotiga tayyorgarlik", "ru" to "Подготовка к учёбе и жизни в кампусе", "tg" to "Омодагӣ ба таҳсил ва зиндагии донишҷӯӣ"),
        Icons.Filled.School,
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
    Surface(color = PompColors.Paper, modifier = modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .windowInsetsPadding(WindowInsets.safeDrawing),
        ) {
            if (state.step > 0) {
                OnboardingTopBar(state.step, copy.back, onBack, state.submitting)
            }

            Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
                when (state.step) {
                    0 -> WelcomeStep(copy)
                    1 -> ChoiceStep(
                        question = copy.askLevel,
                        helper = copy.levelHint,
                    ) {
                        LevelChoices(
                            language = language,
                            copy = copy,
                            selected = state.selectedLevel,
                            enabled = !state.submitting,
                            onSelected = onLevelSelected,
                        )
                    }
                    else -> ChoiceStep(
                        question = copy.askGoal,
                        helper = copy.goalHint,
                    ) {
                        SelectedLevelSummary(copy, state.selectedLevel, language)
                        GoalChoices(
                            language = language,
                            selected = state.selectedGoal,
                            enabled = !state.submitting,
                            onSelected = onGoalSelected,
                        )
                    }
                }
            }

            OnboardingFooter(copy, state, onNext)
        }
    }
}

@Composable
private fun OnboardingTopBar(step: Int, backLabel: String, onBack: () -> Unit, disabled: Boolean) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(start = 8.dp, end = 20.dp, top = 14.dp, bottom = 4.dp),
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
            Icon(Icons.Filled.ArrowBack, contentDescription = null, tint = PompColors.InkSecondary)
        }
        Spacer(Modifier.width(6.dp))
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
                    .fillMaxWidth(step / 2f)
                    .height(8.dp)
                    .background(PompColors.Cinnabar),
            )
        }
        Spacer(Modifier.width(14.dp))
        Text(
            "$step / 2",
            color = PompColors.InkSecondary,
            fontSize = 12.sp,
            fontWeight = FontWeight.Medium,
        )
    }
}

@Composable
private fun WelcomeStep(copy: OnboardingCopy) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 30.dp, vertical = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        SpeechBubble(text = copy.hello, centeredTail = true, large = false)
        Spacer(Modifier.height(24.dp))
        Box(Modifier.size(190.dp, 202.dp), contentAlignment = Alignment.Center) {
            CoursePandaMascot(
                modifier = Modifier.graphicsLayer {
                    scaleX = 2.35f
                    scaleY = 2.35f
                },
                celebrate = true,
            )
        }
        Spacer(Modifier.height(16.dp))
        Text(
            "HSK AI",
            color = PompColors.Cinnabar,
            fontSize = 38.sp,
            lineHeight = 44.sp,
            fontWeight = FontWeight.SemiBold,
            letterSpacing = (-1).sp,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(14.dp))
        Text(
            copy.boot,
            color = PompColors.InkSecondary,
            style = MaterialTheme.typography.bodyLarge.copy(fontSize = 16.sp, lineHeight = 26.sp),
            textAlign = TextAlign.Center,
            modifier = Modifier.width(330.dp),
        )
    }
}

@Composable
private fun ChoiceStep(question: String, helper: String, choices: @Composable ColumnScope.() -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(start = 24.dp, end = 24.dp, top = 22.dp, bottom = 16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(Modifier.size(90.dp, 100.dp), contentAlignment = Alignment.Center) {
                CoursePandaMascot(
                    modifier = Modifier.graphicsLayer {
                        scaleX = 1.22f
                        scaleY = 1.22f
                    },
                    celebrate = false,
                )
            }
            Spacer(Modifier.width(16.dp))
            Box(Modifier.weight(1f)) { SpeechBubble(text = question, centeredTail = false, large = true) }
        }
        Column(modifier = Modifier.fillMaxWidth().padding(start = 24.dp, end = 24.dp, bottom = 16.dp)) {
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
private fun SpeechBubble(text: String, centeredTail: Boolean, large: Boolean) {
    Box(modifier = Modifier.padding(if (centeredTail) 8.dp else 0.dp)) {
        Surface(
            color = PompColors.PaperRaised,
            shape = RoundedCornerShape(if (large) 18.dp else 16.dp),
            border = BorderStroke(1.dp, PompColors.Divider),
            modifier = Modifier.zIndex(1f),
        ) {
            Text(
                text,
                color = PompColors.Ink,
                fontSize = if (large) 21.sp else 17.sp,
                lineHeight = if (large) 28.sp else 25.sp,
                fontWeight = if (large) FontWeight.SemiBold else FontWeight.Medium,
                modifier = Modifier.padding(horizontal = if (large) 18.dp else 22.dp, vertical = if (large) 17.dp else 14.dp),
            )
        }
        Box(
            Modifier
                .size(14.dp)
                .align(if (centeredTail) Alignment.BottomCenter else Alignment.CenterStart)
                .graphicsLayer {
                    rotationZ = 45f
                    translationX = if (centeredTail) 0f else -5.dp.toPx()
                    translationY = if (centeredTail) 5.dp.toPx() else 0f
                }
                .background(PompColors.PaperRaised)
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
    onSelected: (String) -> Unit,
) {
    val lang = canonicalLanguage(language)
    val descriptions = when (lang) {
        "uz" -> listOf("Asoslardan boshlayman", "Boshlang'ich", "Oddiy kundalik mavzular", "O'rta daraja", "Murakkabroq matn va muloqot")
        "tg" -> listOf("Аз асосҳо оғоз мекунам", "Сатҳи ибтидоӣ", "Мавзӯъҳои оддии рӯзмарра", "Сатҳи миёна", "Матн ва муоширати мураккабтар")
        else -> listOf("Начну с основ", "Начальный уровень", "Простые бытовые темы", "Средний уровень", "Более сложные тексты и общение")
    }
    val levels = listOf(
        LevelOption("beginner", copy.beginner, copy.beginnerSub),
        LevelOption("hsk1", "HSK 1", descriptions[1]),
        LevelOption("hsk2", "HSK 2", descriptions[2]),
        LevelOption("hsk3", "HSK 3", descriptions[3]),
        LevelOption("hsk4", "HSK 4", descriptions[4]),
    )
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        levels.forEachIndexed { index, option ->
            ChoiceCard(
                selected = selected == option.key,
                enabled = enabled,
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
private fun GoalChoices(language: String, selected: String, enabled: Boolean, onSelected: (String) -> Unit) {
    val lang = canonicalLanguage(language)
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        goals.forEach { goal ->
            ChoiceCard(
                selected = selected == goal.key,
                enabled = enabled,
                title = goal.titles[lang] ?: goal.titles.getValue("ru"),
                subtitle = goal.subtitles[lang] ?: goal.subtitles.getValue("ru"),
                leading = {
                    Icon(
                        goal.icon,
                        contentDescription = null,
                        tint = if (selected == goal.key) PompColors.CinnabarDark else PompColors.InkSecondary,
                        modifier = Modifier.size(25.dp),
                    )
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
    title: String,
    subtitle: String,
    leading: @Composable () -> Unit,
    onClick: () -> Unit,
) {
    Surface(
        color = if (selected) Color(0xFFFFF3EF) else PompColors.PaperRaised,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, if (selected) PompColors.Cinnabar else PompColors.Divider),
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 72.dp)
            .clickable(enabled = enabled, role = Role.RadioButton, onClick = onClick),
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(Modifier.size(42.dp), contentAlignment = Alignment.Center) { leading() }
            Spacer(Modifier.width(14.dp))
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
                modifier = Modifier.size(20.dp),
                shape = CircleShape,
                color = if (selected) PompColors.Cinnabar else Color.Transparent,
                border = BorderStroke(1.dp, if (selected) PompColors.Cinnabar else PompColors.Divider),
            ) {
                if (selected) {
                    Icon(
                        Icons.Filled.Check,
                        contentDescription = null,
                        tint = Color.White,
                        modifier = Modifier.padding(3.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun SelectedLevelSummary(copy: OnboardingCopy, level: String, language: String) {
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
        Icon(Icons.Filled.Check, contentDescription = null, tint = PompColors.Jade, modifier = Modifier.size(16.dp))
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
private fun OnboardingFooter(copy: OnboardingCopy, state: OnboardingUiState, onNext: () -> Unit) {
    val note = when (state.step) {
        0 -> copy.welcomeNote
        1 -> copy.levelNote
        else -> copy.goalNote
    }
    val label = when {
        state.submitting -> copy.saving
        state.error -> copy.retry
        state.step == 0 -> copy.start
        state.step == 1 -> copy.continueLabel
        else -> copy.firstLesson
    }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(PompColors.Paper)
            .padding(start = 24.dp, end = 24.dp, top = 16.dp, bottom = 20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(Modifier.fillMaxWidth().height(1.dp).background(PompColors.Divider))
        Spacer(Modifier.height(12.dp))
        Text(note, color = PompColors.InkSecondary, fontSize = 12.sp, lineHeight = 18.sp, textAlign = TextAlign.Center)
        if (state.error) {
            Spacer(Modifier.height(8.dp))
            Text(copy.saveError, color = PompColors.CinnabarDark, fontSize = 13.sp, lineHeight = 19.sp, textAlign = TextAlign.Center)
        }
        Spacer(Modifier.height(12.dp))
        Surface(
            color = PompColors.Cinnabar,
            shape = RoundedCornerShape(13.dp),
            shadowElevation = 0.dp,
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 54.dp)
                .clickable(enabled = !state.submitting, role = Role.Button, onClick = onNext),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 14.dp),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                if (state.submitting) {
                    CircularProgressIndicator(color = Color.White, strokeWidth = 2.dp, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(10.dp))
                }
                Text(label, color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                if (!state.submitting && state.step > 0) {
                    Spacer(Modifier.width(10.dp))
                    Icon(Icons.Filled.ArrowForward, contentDescription = null, tint = Color.White, modifier = Modifier.size(20.dp))
                }
            }
        }
        Box(Modifier.fillMaxWidth().height(2.dp).background(PompColors.CinnabarDark))
    }
}

private fun canonicalLanguage(language: String): String = when (language.lowercase()) {
    "uz" -> "uz"
    "tg", "tj" -> "tg"
    else -> "ru"
}
