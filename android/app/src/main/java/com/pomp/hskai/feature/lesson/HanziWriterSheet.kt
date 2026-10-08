package com.pomp.hskai.feature.lesson

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.IconButton
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.SkipNext
import androidx.compose.material.icons.filled.SkipPrevious
import androidx.compose.material3.Icon
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.core.hanzi.CharacterStrokes
import com.pomp.hskai.core.hanzi.StrokeAnimation
import com.pomp.hskai.feature.assistant.AssistantScreen
import com.pomp.hskai.feature.assistant.ScreenContext
import com.pomp.hskai.feature.assistant.AssistantModalBottomSheet as ModalBottomSheet

/**
 * How a character is written, stroke by stroke.
 *
 * The Mini App puts a pencil beside the lesson and plays the strokes in
 * order; a learner who has only ever seen the finished character does not
 * know where it starts. The data is the same hanzi-writer set the Mini App
 * uses, fetched through our own origin because the app talks to one host.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun HanziWriterSheet(
    hanzi: String,
    pinyin: String,
    meaning: String,
    /** The characters of [hanzi] the sheet can write, in order. */
    characters: List<String>,
    /** Which of [characters] is on screen. */
    index: Int,
    strokes: CharacterStrokes?,
    isLoading: Boolean,
    onShowCharacter: (Int) -> Unit,
    onDismiss: () -> Unit,
) {
    val current = characters.getOrNull(index) ?: hanzi
    var playing by remember(index, current) { mutableStateOf(true) }
    var replayKey by remember(index, current) { mutableIntStateOf(0) }
    var finished by remember(index, current) { mutableStateOf(false) }
    var completedStrokes by remember(index, current) { mutableIntStateOf(0) }
    var manualStrokeCount by remember(index, current) { mutableStateOf<Int?>(null) }
    val strokeCount = strokes?.size ?: 0
    AssistantScreen(
        ScreenContext(
            screen = "writing",
            title = hanzi,
            details = "Writing sheet: $hanzi · $pinyin · $meaning. Strokes loaded: ${strokes?.size ?: 0}.",
            materialRef = hanzi,
            answerState = if (isLoading) "loading" else "viewing",
        ),
        bottomBar = false,
        priority = 100,
    )
    val sheetState = rememberModalBottomSheetState()
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = PompColors.PaperRaised,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp)
                .padding(bottom = 28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            if (pinyin.isNotBlank()) {
                Text(
                    text = pinyin,
                    style = PompTextStyles.pinyin.copy(fontSize = 17.sp),
                    fontWeight = FontWeight.Medium,
                    color = PompColors.CinnabarDark,
                )
            }
            if (meaning.isNotBlank()) {
                Text(
                    text = meaning,
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                    textAlign = TextAlign.Center,
                )
            }
            Spacer(Modifier.height(14.dp))

            // A listening card hands the sheet the whole sentence that was
            // said. Stroke data belongs to one character, so the sentence is
            // written a character at a time rather than drawn on top of
            // itself — which is what one box for the lot produced.
            if (characters.size > 1) {
                Text(
                    text = stringResource(R.string.lesson_writer_position, index + 1, characters.size),
                    style = MaterialTheme.typography.labelLarge,
                    color = PompColors.InkSecondary,
                )
                Spacer(Modifier.height(10.dp))
            }

            Surface(
                color = PompColors.Paper,
                shape = RoundedCornerShape(18.dp),
                border = BorderStroke(1.dp, PompColors.Divider),
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(1f),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    when {
                        isLoading -> CircularProgressIndicator(color = PompColors.Cinnabar)

                        // Without the outlines the character is still shown —
                        // the learner loses the animation, not the word.
                        strokes == null || strokes.isEmpty() -> Text(
                            text = current,
                            style = PompTextStyles.hanziLarge.copy(fontSize = 128.sp),
                            color = PompColors.Ink,
                        )

                        else -> StrokeAnimation(
                            strokes = strokes,
                            replayKey = replayKey,
                            isPlaying = playing,
                            visibleStrokeCount = manualStrokeCount,
                            onStrokeComplete = { completedStrokes = it },
                            onAnimationFinished = { finished = true; playing = false },
                        )
                    }
                }
            }

            Spacer(Modifier.height(14.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(24.dp, Alignment.CenterHorizontally),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(
                    onClick = {
                        if (completedStrokes > 0) {
                            val step = (completedStrokes - 1).coerceAtLeast(0)
                            playing = false
                            manualStrokeCount = step
                            completedStrokes = step
                            finished = false
                        } else if (index > 0) {
                            onShowCharacter(index - 1)
                        }
                    },
                    enabled = !isLoading && (completedStrokes > 0 || index > 0),
                ) {
                    Icon(Icons.Filled.SkipPrevious, contentDescription = stringResource(if (completedStrokes == 0) R.string.lesson_writer_previous else R.string.writer_previous_stroke))
                }
                IconButton(
                    onClick = {
                        if (playing) {
                            playing = false
                        } else {
                            if (finished) {
                                replayKey++
                                completedStrokes = 0
                                finished = false
                            }
                            manualStrokeCount = null
                            playing = true
                        }
                    },
                    enabled = !isLoading && strokes?.isNotEmpty() == true,
                ) {
                    Icon(
                        if (playing) Icons.Filled.Pause else Icons.Filled.PlayArrow,
                        contentDescription = stringResource(
                            if (playing) R.string.writer_pause else R.string.writer_resume
                        ),
                        tint = PompColors.CinnabarDark,
                    )
                }
                IconButton(
                    onClick = {
                        if (completedStrokes < strokeCount) {
                            val step = completedStrokes + 1
                            playing = false
                            manualStrokeCount = step
                            completedStrokes = step
                            finished = step == strokeCount
                        } else if (index < characters.lastIndex) {
                            onShowCharacter(index + 1)
                        }
                    },
                    enabled = !isLoading && (completedStrokes < strokeCount || index < characters.lastIndex),
                ) {
                    Icon(Icons.Filled.SkipNext, contentDescription = stringResource(if (completedStrokes >= strokeCount) R.string.lesson_writer_next else R.string.writer_next_stroke))
                }
            }
        }
    }
}

