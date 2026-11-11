package com.pomp.hskai.feature.feedback

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.unit.dp
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
        title = { Row { Text(stringResource(if (state.completed) R.string.bug_report_thanks_title else heading),
            modifier = Modifier.weight(1f)); IconButton(onClick = onClose, enabled = !state.busy) {
            Icon(Icons.Default.Close, contentDescription = stringResource(R.string.action_close)) } } },
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
                enabled = !state.busy && !state.draft[question?.key].isNullOrBlank()) { Text(stringResource(if (state.step == state.questions.lastIndex) R.string.bug_report_send else R.string.action_continue)) }
        },
        dismissButton = {
            if (!state.completed && state.step > 0) TextButton(onClick = onBack, enabled = !state.busy) { Text(stringResource(R.string.action_back)) }
        })
}
