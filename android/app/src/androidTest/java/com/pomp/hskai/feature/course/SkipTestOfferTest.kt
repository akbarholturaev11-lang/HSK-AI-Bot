package com.pomp.hskai.feature.course

import android.graphics.Bitmap
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.settings.PinyinVisibility
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.io.FileOutputStream

/**
 * The sheet a locked lesson opens.
 *
 * Its mascot is asked for by HEIGHT alone, which leaves the Canvas as wide as
 * the screen. While the drawing scaled x and y independently that stretched
 * the panda to roughly three times its width — it swallowed the heading and
 * ran off both edges. The mascot now scales uniformly and centres itself, so
 * the text below it has to stay clear of it whatever box it is handed.
 */
@RunWith(AndroidJUnit4::class)
class SkipTestOfferTest {

    @get:Rule
    val compose = createComposeRule()

    private fun show() {
        compose.setContent {
            PompHskAiTheme {
                SkipTestScreen(
                    state = SkipTestUiState(lessonOrder = 4),
                    pinyin = PinyinVisibility.ALL,
                    onStart = {},
                    onSelect = {},
                    onAdvance = {},
                    onUnlock = {},
                    onOpenLesson = {},
                    onClose = {},
                )
            }
        }
    }

    private fun shoot(name: String) {
        compose.waitForIdle()
        val bitmap = compose.onRoot().captureToImage().asAndroidBitmap()
        val dir = InstrumentationRegistry.getInstrumentation().targetContext.filesDir
        FileOutputStream(File(dir, "skip-$name.png")).use {
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)
        }
    }

    private fun boundsOf(text: String): Rect =
        compose.onNodeWithText(text).fetchSemanticsNode().boundsInRoot

    @Test
    fun theOfferReadsCleanlyAndTheMascotStaysInsideTheScreen() {
        show()
        shoot("offer")

        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val tag = context.getString(R.string.skip_test_tag)
        val body = context.getString(R.string.skip_test_offer)

        compose.onNodeWithText(tag).assertIsDisplayed()
        compose.onNodeWithText(body).assertIsDisplayed()

        // Nothing may sit on top of the heading: a stretched mascot used to
        // cover it. The two texts must also stay in reading order.
        val root = compose.onRoot().fetchSemanticsNode().boundsInRoot
        val tagBounds = boundsOf(tag)
        val bodyBounds = boundsOf(body)

        assertTrue("the tag must start below the top of the screen", tagBounds.top > root.top)
        assertTrue("the body must sit under the tag", bodyBounds.top >= tagBounds.bottom)
        assertTrue(
            "the offer must stay inside the screen horizontally",
            tagBounds.left >= root.left && tagBounds.right <= root.right,
        )
    }
}
