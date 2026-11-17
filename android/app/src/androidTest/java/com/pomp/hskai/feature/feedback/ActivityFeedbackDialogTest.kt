package com.pomp.hskai.feature.feedback

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import org.junit.Rule
import org.junit.Test
import org.junit.Assert.assertEquals

class ActivityFeedbackDialogTest {
    @get:Rule val compose = createComposeRule()
    @Test fun canonicalPaidQuestionHasOneHeadingAndNativeAnswer() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        var answer=""
        val prompt=ActivityFeedbackPrompt(7,paid=true,choices=FeedbackChoices(paid=listOf(FeedbackOption("useful","Useful"))))
        compose.setContent { PompHskAiTheme { ActivityFeedbackDialog(ActivityFeedbackState(prompt=prompt),
            onAnswer={answer=it},onNext={},onBack={},onClose={}) } }
        compose.onAllNodesWithText(context.getString(R.string.hsk_course_pwa_feedback_paid_q)).assertCountEquals(1)
        compose.onNodeWithText("Useful").performClick()
        assertEquals("useful",answer)
        compose.onNodeWithText(context.getString(R.string.hsk_course_pwa_feedback_liked_q)).assertDoesNotExist()
    }
    @Test fun requiredCommentDoesNotRepeatTheHeadingAsFieldLabel() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val prompt=ActivityFeedbackPrompt(8,choices=FeedbackChoices(liked=listOf(FeedbackOption("other","Other"))))
        compose.setContent { PompHskAiTheme { ActivityFeedbackDialog(ActivityFeedbackState(prompt=prompt,
            draft=mapOf("liked_code" to "other"),step=1),onAnswer={},onNext={},onBack={},onClose={}) } }
        compose.onAllNodesWithText(context.getString(R.string.hsk_course_pwa_feedback_detail_q)).assertCountEquals(1)
        compose.onNodeWithContentDescription(context.getString(R.string.hsk_course_pwa_feedback_detail_q)).assertIsDisplayed()
    }
}
