package com.pomp.hskai.feature.course

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChatBubbleOutline
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.Flight
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.WorkOutline
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.core.design.PompColors

/**
 * Native equivalent of Mini App's existing `.opt-row` progressive setup sheet.
 *
 * The order is intentionally server/Mini-App owned: goal -> time -> focus.
 * Only one question is visible at a time.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StudySetupSheet(
    language: String,
    state: StudySetupUiState,
    onDismiss: () -> Unit,
    onGoal: (String) -> Unit,
    onTime: (Int) -> Unit,
    onFocus: (String) -> Unit,
) {
    if (!state.visible) return
    val copy = StudySetupCopy.forLanguage(language)
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = PompColors.PaperRaised,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(start = 20.dp, end = 20.dp, bottom = 28.dp),
        ) {
            val title = when (state.stage) {
                StudySetupStage.GOAL -> copy.goalQuestion
                StudySetupStage.TIME -> copy.timeQuestion
                StudySetupStage.FOCUS -> copy.focusQuestion
            }
            val subtitle = when (state.stage) {
                StudySetupStage.GOAL -> copy.goalSubtitle
                StudySetupStage.TIME -> copy.timeSubtitle
                StudySetupStage.FOCUS -> copy.focusSubtitle
            }
            Text(
                text = title,
                color = PompColors.Ink,
                fontSize = 18.sp,
                lineHeight = 24.sp,
                fontWeight = FontWeight.SemiBold,
            )
            Spacer(Modifier.height(5.dp))
            Text(
                text = subtitle,
                color = PompColors.InkSecondary,
                fontSize = 13.sp,
                lineHeight = 19.sp,
            )
            Spacer(Modifier.height(16.dp))

            when (state.stage) {
                StudySetupStage.GOAL -> GoalRows(
                    copy = copy,
                    selected = state.setup?.goal.orEmpty(),
                    enabled = !state.saving,
                    onPick = onGoal,
                )
                StudySetupStage.TIME -> TimeRows(
                    copy = copy,
                    selected = state.setup?.dailyMinutes ?: 10,
                    enabled = !state.saving,
                    onPick = onTime,
                )
                StudySetupStage.FOCUS -> FocusRows(
                    copy = copy,
                    enabled = !state.saving,
                    onPick = onFocus,
                )
            }

            if (state.saving) {
                Spacer(Modifier.height(14.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    CircularProgressIndicator(
                        color = PompColors.Cinnabar,
                        strokeWidth = 2.dp,
                        modifier = Modifier.size(18.dp),
                    )
                    Spacer(Modifier.size(9.dp))
                    Text(copy.saving, color = PompColors.InkSecondary, fontSize = 13.sp)
                }
            } else if (state.error != null) {
                Spacer(Modifier.height(14.dp))
                Text(
                    text = copy.saveError,
                    color = PompColors.CinnabarDark,
                    fontSize = 13.sp,
                    lineHeight = 19.sp,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

@Composable
private fun GoalRows(
    copy: StudySetupCopy,
    selected: String,
    enabled: Boolean,
    onPick: (String) -> Unit,
) {
    val options = listOf(
        SetupOption("hsk_exam", copy.goals.getValue("hsk_exam"), Icons.Filled.EmojiEvents),
        SetupOption("daily_communication", copy.goals.getValue("daily_communication"), Icons.Filled.ChatBubbleOutline),
        SetupOption("travel", copy.goals.getValue("travel"), Icons.Filled.Flight),
        SetupOption("work_china", copy.goals.getValue("work_china"), Icons.Filled.WorkOutline),
        SetupOption("study_china", copy.goals.getValue("study_china"), Icons.Filled.School),
    )
    SetupRows(options, selected, enabled) { onPick(it) }
}

@Composable
private fun TimeRows(
    copy: StudySetupCopy,
    selected: Int,
    enabled: Boolean,
    onPick: (Int) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
        listOf(5, 10, 15, 20, 30).forEach { minutes ->
            SetupRow(
                title = "$minutes ${copy.minuteUnit}",
                selected = minutes == selected,
                enabled = enabled,
                icon = null,
                onClick = { onPick(minutes) },
            )
        }
    }
}

@Composable
private fun FocusRows(
    copy: StudySetupCopy,
    enabled: Boolean,
    onPick: (String) -> Unit,
) {
    val options = listOf(
        SetupOption("speaking", copy.focus.getValue("speaking"), Icons.Filled.ChatBubbleOutline),
        SetupOption("listening", copy.focus.getValue("listening"), null),
        SetupOption("vocabulary", copy.focus.getValue("vocabulary"), null),
        SetupOption("grammar", copy.focus.getValue("grammar"), null),
        SetupOption("none", copy.focus.getValue("none"), null),
    )
    SetupRows(options, selected = "", enabled = enabled) { onPick(it) }
}

@Composable
private fun SetupRows(
    options: List<SetupOption>,
    selected: String,
    enabled: Boolean,
    onPick: (String) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
        options.forEach { option ->
            SetupRow(
                title = option.title,
                selected = option.key == selected,
                enabled = enabled,
                icon = option.icon,
                onClick = { onPick(option.key) },
            )
        }
    }
}

@Composable
private fun SetupRow(
    title: String,
    selected: Boolean,
    enabled: Boolean,
    icon: ImageVector?,
    onClick: () -> Unit,
) {
    Surface(
        color = if (selected) PompColors.CinnabarSoft else PompColors.PaperRaised,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, if (selected) PompColors.Cinnabar else PompColors.Divider),
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 54.dp)
            .clickable(enabled = enabled, onClick = onClick),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 15.dp, vertical = 13.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (icon != null) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = if (selected) PompColors.CinnabarDark else PompColors.InkSecondary,
                    modifier = Modifier.size(22.dp),
                )
                Spacer(Modifier.size(12.dp))
            }
            Text(
                text = title,
                color = if (selected) PompColors.CinnabarDark else PompColors.Ink,
                fontSize = 15.sp,
                lineHeight = 21.sp,
                fontWeight = FontWeight.Medium,
                modifier = Modifier.weight(1f),
            )
            if (selected) {
                Icon(
                    imageVector = Icons.Filled.Check,
                    contentDescription = null,
                    tint = PompColors.Cinnabar,
                    modifier = Modifier.size(20.dp),
                )
            }
        }
    }
}

private data class SetupOption(
    val key: String,
    val title: String,
    val icon: ImageVector?,
)

private data class StudySetupCopy(
    val goalQuestion: String,
    val goalSubtitle: String,
    val goals: Map<String, String>,
    val timeQuestion: String,
    val timeSubtitle: String,
    val focusQuestion: String,
    val focusSubtitle: String,
    val minuteUnit: String,
    val saving: String,
    val saveError: String,
    val focus: Map<String, String>,
) {
    companion object {
        fun forLanguage(language: String): StudySetupCopy = when (language.lowercase()) {
            "uz" -> StudySetupCopy(
                goalQuestion = "Xitoy tili sizga nima uchun kerak?",
                goalSubtitle = "Kunlik rejangiz shunga qarab tuziladi.",
                goals = mapOf(
                    "hsk_exam" to "HSK imtihonini topshirish",
                    "daily_communication" to "Kundalik muloqot",
                    "travel" to "Sayohat",
                    "work_china" to "Ish uchun xitoy tili",
                    "study_china" to "Xitoyda o'qish",
                ),
                timeQuestion = "Kuniga necha daqiqa vaqtingiz bor?",
                timeSubtitle = "Kunlik reja uzunligi shunga bog'liq.",
                focusQuestion = "Nimaga ko'proq urg'u beraylik?",
                focusSubtitle = "Bu — reja uchun ishora. Xatolarni tizim o'zi topadi.",
                minuteUnit = "daq",
                saving = "Saqlanmoqda…",
                saveError = "Tanlov saqlanmadi. Qayta urinib ko'ring.",
                focus = mapOf(
                    "speaking" to "Gapirish",
                    "listening" to "Tinglash",
                    "vocabulary" to "So'z va ieroglif",
                    "grammar" to "Grammatika",
                    "none" to "Farqi yo'q",
                ),
            )
            "tg", "tj" -> StudySetupCopy(
                goalQuestion = "Забони чинӣ ба шумо барои чӣ лозим аст?",
                goalSubtitle = "Нақшаи рӯзонаи шумо аз ин вобаста аст.",
                goals = mapOf(
                    "hsk_exam" to "Супоридани HSK",
                    "daily_communication" to "Муоширати ҳаррӯза",
                    "travel" to "Сафар",
                    "work_china" to "Кор бо Чин",
                    "study_china" to "Таҳсил дар Чин",
                ),
                timeQuestion = "Дар як рӯз чанд дақиқа вақт доред?",
                timeSubtitle = "Дарозии нақшаи рӯзона аз ин вобаста аст.",
                focusQuestion = "Ба чӣ бештар таъкид кунем?",
                focusSubtitle = "Ин ишора барои нақша аст. Хатоҳоро система худаш меёбад.",
                minuteUnit = "дақ",
                saving = "Сабт мешавад…",
                saveError = "Интихоб сабт нашуд. Боз кӯшиш кунед.",
                focus = mapOf(
                    "speaking" to "Гуфтугӯ",
                    "listening" to "Шунидан",
                    "vocabulary" to "Калима ва ҳарф",
                    "grammar" to "Грамматика",
                    "none" to "Фарқ надорад",
                ),
            )
            else -> StudySetupCopy(
                goalQuestion = "Зачем вам китайский?",
                goalSubtitle = "От этого зависит, что будет в плане на день.",
                goals = mapOf(
                    "hsk_exam" to "Сдать HSK",
                    "daily_communication" to "Общаться в жизни",
                    "travel" to "Путешествия",
                    "work_china" to "Работа с Китаем",
                    "study_china" to "Учёба в Китае",
                ),
                timeQuestion = "Сколько минут в день у вас есть?",
                timeSubtitle = "От этого зависит длина плана на день.",
                focusQuestion = "На чём сделать упор?",
                focusSubtitle = "Это подсказка для плана. Ошибки система найдёт сама.",
                minuteUnit = "мин",
                saving = "Сохраняем…",
                saveError = "Не удалось сохранить выбор. Попробуйте ещё раз.",
                focus = mapOf(
                    "speaking" to "Разговор",
                    "listening" to "Аудирование",
                    "vocabulary" to "Слова и иероглифы",
                    "grammar" to "Грамматика",
                    "none" to "Без разницы",
                ),
            )
        }
    }
}
