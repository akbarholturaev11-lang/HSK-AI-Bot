package com.pomp.hskai.feature.profile

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.settings.DailyGoal
import com.pomp.hskai.feature.assistant.AssistantModalBottomSheet as ModalBottomSheet

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun LanguagePicker(
    current: AppLanguage,
    onPick: (AppLanguage) -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState()
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = PompColors.PaperRaised,
    ) {
        Column(Modifier.padding(horizontal = 20.dp, vertical = 8.dp)) {
            Text(
                text = stringResource(R.string.profile_language_picker_title),
                style = androidx.compose.material3.MaterialTheme.typography.titleMedium,
                color = PompColors.Ink,
            )
            androidx.compose.foundation.layout.Spacer(Modifier.padding(6.dp))
            AppLanguage.entries.forEach { language ->
                val selected = language == current
                Surface(
                    color = if (selected) PompColors.CinnabarSoft else PompColors.PaperRaised,
                    shape = androidx.compose.foundation.shape.RoundedCornerShape(14.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 52.dp)
                        .padding(vertical = 4.dp)
                        .clickable { onPick(language) },
                ) {
                    Text(
                        text = stringResource(language.labelRes()),
                        style = androidx.compose.material3.MaterialTheme.typography.bodyLarge,
                        color = if (selected) PompColors.CinnabarDark else PompColors.Ink,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
                    )
                }
            }
            androidx.compose.foundation.layout.Spacer(Modifier.padding(12.dp))
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun DailyGoalPicker(
    current: Int,
    onPick: (Int) -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState()
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = PompColors.PaperRaised,
    ) {
        Column(Modifier.padding(horizontal = 20.dp, vertical = 8.dp)) {
            Text(
                text = stringResource(R.string.profile_goal_picker_title),
                style = androidx.compose.material3.MaterialTheme.typography.titleMedium,
                color = PompColors.Ink,
            )
            androidx.compose.foundation.layout.Spacer(Modifier.padding(6.dp))
            DailyGoal.CHOICES.forEach { value ->
                val selected = value == current
                Surface(
                    color = if (selected) PompColors.CinnabarSoft else PompColors.PaperRaised,
                    shape = androidx.compose.foundation.shape.RoundedCornerShape(14.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 52.dp)
                        .padding(vertical = 4.dp)
                        .clickable { onPick(value) },
                ) {
                    Text(
                        text = stringResource(R.string.profile_goal_option, value),
                        style = androidx.compose.material3.MaterialTheme.typography.bodyLarge,
                        color = if (selected) PompColors.CinnabarDark else PompColors.Ink,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
                    )
                }
            }
            androidx.compose.foundation.layout.Spacer(Modifier.padding(12.dp))
        }
    }
}
