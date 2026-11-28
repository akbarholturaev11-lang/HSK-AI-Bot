package com.pomp.hskai.feature.course

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.feature.assistant.AssistantModalBottomSheet
import com.pomp.hskai.core.design.components.HskCharacter
import com.pomp.hskai.core.design.components.HskCharacterMood
import com.pomp.hskai.core.design.components.HskCharacterStage

/** Presentation of a verified ended period. No access or billing changes. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun ProExpirySheet(onRestore: () -> Unit, onDismiss: () -> Unit, title: String? = null) {
    AssistantModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        containerColor = PompColors.PaperRaised,
        showAssistant = false,
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().verticalScroll(rememberScrollState())
                .padding(start = 24.dp, end = 24.dp, bottom = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            // Reuse the cast's concerned face, without its answer-feedback
            // reaction or the celebratory Pro halo. The period has ended.
            HskCharacterStage(
                character = HskCharacter.Panda, mood = HskCharacterMood.Wrong,
                modifier = Modifier.size(168.dp).testTag("pro-expiry-panda"),
            )
            Text(title ?: stringResource(R.string.hsk_course_pro_expiry_title),
                color = PompColors.Ink, fontSize = 23.sp, fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center)
            Text(stringResource(R.string.hsk_course_pro_expiry_body),
                color = PompColors.Ink, fontSize = 17.sp, textAlign = TextAlign.Center)
            Button(onClick = onRestore, modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp),
                colors = ButtonDefaults.buttonColors(containerColor = PompColors.Cinnabar)) {
                Text(stringResource(R.string.hsk_course_pro_expiry_restore), fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center)
            }
            TextButton(onClick = onDismiss, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                Text(stringResource(R.string.hsk_course_pro_expiry_limited),
                    color = PompColors.InkSecondary, fontWeight = FontWeight.Medium, textAlign = TextAlign.Center)
            }
        }
    }
}
