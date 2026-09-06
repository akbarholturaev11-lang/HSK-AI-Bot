package com.pomp.hskai.feature.foundation

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.enableEdgeToEdge
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.MainActivity
import com.pomp.hskai.core.auth.AuthState
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompHskAiTheme

/** Full-screen native Starter 0 flow. Not exported; only the course map can open it. */
class FoundationActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val app = application as HskAiApplication
        setContent {
            PompHskAiTheme {
                FoundationActivityContent(
                    app = app,
                    onClose = ::finish,
                    onCompleted = ::returnToFreshCourse,
                )
            }
        }
    }

    private fun returnToFreshCourse() {
        startActivity(
            Intent(this, MainActivity::class.java).addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK,
            )
        )
        finish()
    }
}

@Composable
private fun FoundationActivityContent(
    app: HskAiApplication,
    onClose: () -> Unit,
    onCompleted: () -> Unit,
) {
    val auth by app.authRepository.state.collectAsStateWithLifecycle()
    when (val current = auth) {
        is AuthState.Authenticated -> {
            val model: FoundationViewModel = viewModel(
                factory = FoundationViewModel.Factory(
                    repository = app.courseRepository,
                    audioPlayer = app.lessonAudioPlayer,
                    language = current.account.language,
                )
            )
            val state by model.state.collectAsStateWithLifecycle()
            LaunchedEffect(state.completed) {
                if (state.completed) onCompleted()
            }
            FoundationScreen(
                state = state,
                onChoose = model::choose,
                onAddBuilderToken = model::addBuilderToken,
                onUndoBuilderToken = model::undoBuilderToken,
                onSubmitBuilder = model::submitBuilder,
                onMarkSpoken = model::markSpoken,
                onPlayAudio = model::playAudio,
                onAdvance = model::advance,
                onRetry = {
                    if (state.cards.isEmpty()) model.load() else model.retrySave()
                },
                onClose = onClose,
            )
        }
        else -> Surface(Modifier.fillMaxSize(), color = PompColors.Paper) {
            Box(contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = PompColors.Cinnabar)
            }
        }
    }
}
