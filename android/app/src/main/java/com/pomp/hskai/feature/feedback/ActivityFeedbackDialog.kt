package com.pomp.hskai.feature.feedback

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.text.style.TextAlign
import com.pomp.hskai.R
import kotlinx.coroutines.delay

@Composable
fun ActivityFeedbackDialog(state: ActivityFeedbackState, onAnswer: (String)->Unit, onNext: ()->Unit,
    onBack: ()->Unit, onClose: ()->Unit) {
    if (state.prompt == null) return
    LaunchedEffect(state.completed) { if (state.completed) { delay(1200); onClose() } }
    val question = state.question
    val heading = when (question?.heading) {
        "paid" -> R.string.hsk_course_pwa_feedback_paid_q
        "liked" -> R.string.hsk_course_pwa_feedback_liked_q
        "disliked" -> R.string.hsk_course_pwa_feedback_disliked_q
        else -> R.string.hsk_course_pwa_feedback_detail_q
    }
    val questionText = stringResource(heading)
    AlertDialog(onDismissRequest = onClose,
        title = { Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Text(stringResource(if (state.completed) R.string.bug_report_thanks_title else heading))
            if (!state.completed && !state.prompt.paid) state.prompt.reward_hint?.takeIf { it.isNotBlank() }?.let {
                Text(it, modifier = Modifier.fillMaxWidth(), fontSize = 12.sp, lineHeight = 15.sp,
                    maxLines = 2, color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center)
            }
        } },
        text = { Column(Modifier.heightIn(max=440.dp).verticalScroll(rememberScrollState())) {
            if (!state.completed && question != null) {
                if (question.options.isEmpty()) OutlinedTextField(value = state.draft[question.key].orEmpty(), onValueChange = onAnswer,
                    enabled = !state.busy, modifier = Modifier.semantics { contentDescription = questionText })
                else question.options.forEach { option ->
                    OutlinedButton(onClick = { onAnswer(option.code) }, enabled = !state.busy,
                        modifier = Modifier.fillMaxWidth()) { Text(option.label) }
                }
                if (state.busy) LinearProgressIndicator(Modifier.fillMaxWidth())
                if (state.error) Text(stringResource(R.string.bug_report_failed), color = MaterialTheme.colorScheme.error)
            }
        } },
        confirmButton = {
            if (!state.completed && (question?.options?.isEmpty() == true || state.error)) TextButton(onClick = onNext,
                enabled = !state.busy && !state.draft[question?.key].isNullOrBlank()) { Text(stringResource(if (state.step == state.questions.lastIndex) R.string.bug_report_send else R.string.hsk_common_action_continue)) }
        },
        dismissButton = {
            if (!state.completed) Row {
                if (state.step > 0) TextButton(onClick = onBack, enabled = !state.busy) { Text(stringResource(R.string.hsk_common_action_back)) }
                TextButton(onClick = onClose, enabled = !state.busy) {
                    Text(state.prompt.dismiss_label?.takeIf { it.isNotBlank() } ?: stringResource(R.string.hsk_course_later))
                }
            }
        })
}
