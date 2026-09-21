import SwiftUI

struct PronunciationDrillScreen: View {
    @ObservedObject var model: PronunciationDrillViewModel
    let account: LinkedAccount
    let onClose: () -> Void

    var body: some View {
        ZStack {
            HSKGlassBackdrop()
            VStack(spacing: 0) {
                topBar
                switch model.phase {
                case .loading:
                    Spacer()
                    ProgressView().tint(HSKColors.cinnabar).controlSize(.large)
                    Spacer()
                case .running:
                    drill
                case .finished:
                    summary
                case .idle:
                    emptyState
                }
            }
        }
        .task {
            if model.phase == .idle && !model.limitReached && model.errorKey == nil {
                await model.start(level: account.level, language: account.language)
            }
        }
    }

    private var topBar: some View {
        HStack(spacing: 12) {
            Button(action: onClose) {
                Image(systemName: "xmark")
                    .font(.subheadline.weight(.bold))
                    .foregroundStyle(HSKColors.ink)
            }
            .buttonStyle(HSKGlassIconButtonStyle())

            ProgressView(value: model.progress)
                .tint(HSKColors.cinnabar)
                .background(.ultraThinMaterial, in: Capsule())
                .clipShape(Capsule())
        }
        .padding(.horizontal, 16)
        .padding(.top, 12)
    }

    private var drill: some View {
        VStack(spacing: 16) {
            if let question = model.current {
                Text("drill_pronunciation_prompt")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(HSKColors.inkSecondary)

                HSKGlassCard(cornerRadius: 30, padding: 24, tint: HSKColors.auroraMint) {
                    VStack(spacing: 10) {
                        Text(question.hanzi)
                            .font(.system(size: 62, weight: .semibold, design: .rounded))
                            .foregroundStyle(HSKColors.ink)
                        Text(question.pinyin)
                            .font(.title3.weight(.semibold))
                            .foregroundStyle(HSKColors.cinnabarDark)
                        Text(question.meaning)
                            .font(.headline)
                            .foregroundStyle(HSKColors.inkSecondary)
                        Button {
                            model.playCurrent()
                        } label: {
                            Label("foundation_listen", systemImage: "speaker.wave.2.fill")
                        }
                        .buttonStyle(HSKGlassSecondaryButtonStyle())
                    }
                    .frame(maxWidth: .infinity)
                }

                Spacer()

                Button {
                    Task { await model.speak() }
                } label: {
                    ZStack {
                        Circle()
                            .fill(.ultraThinMaterial)
                            .frame(width: 94, height: 94)
                            .overlay(
                                Circle().fill(
                                    (model.isRecording ? HSKColors.flame : HSKColors.cinnabar)
                                        .opacity(0.88)
                                )
                            )
                            .overlay(Circle().stroke(Color.white.opacity(0.62), lineWidth: 1))
                            .shadow(color: HSKColors.cinnabar.opacity(0.22), radius: 20, y: 10)
                        Image(systemName: model.isRecording ? "waveform" : "mic.fill")
                            .font(.system(size: 34, weight: .semibold))
                            .foregroundStyle(.white)
                    }
                }
                .buttonStyle(.plain)
                .disabled(model.isRecording || model.isScoring || model.answered)

                Text(model.isRecording ? "pronunciation_listening" :
                        (model.isScoring ? "pronunciation_checking" : "pronunciation_tap_mic"))
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(HSKColors.inkSecondary)

                if !model.answered {
                    Button("pronunciation_skip") {
                        Task { await model.skip() }
                    }
                    .buttonStyle(HSKGlassSecondaryButtonStyle())
                    .disabled(model.isRecording || model.isScoring)
                }

                if let errorKey = model.errorKey {
                    Text(LocalizedStringKey(errorKey))
                        .font(.footnote)
                        .foregroundStyle(HSKColors.flame)
                        .multilineTextAlignment(.center)
                }

                if model.answered {
                    HSKGlassCard(
                        cornerRadius: 22,
                        padding: 15,
                        tint: model.wasCorrect ? HSKColors.jade : HSKColors.flame
                    ) {
                        VStack(spacing: 10) {
                            Text(model.wasCorrect ? "lesson_correct" : "lesson_wrong")
                                .font(.headline)
                                .foregroundStyle(model.wasCorrect ? HSKColors.jade : HSKColors.flame)
                            if let score = model.spokenScore {
                                Text("\(score)%")
                                    .font(.title2.monospacedDigit().bold())
                                    .foregroundStyle(HSKColors.ink)
                            }
                            Button("lesson_next") {
                                Task { await model.advance() }
                            }
                            .buttonStyle(HSKPrimaryButtonStyle())
                        }
                    }
                }
            }
        }
        .padding(.horizontal, 18)
        .padding(.top, 18)
        .padding(.bottom, 16)
    }

    private var summary: some View {
        VStack {
            Spacer()
            HSKGlassCard(cornerRadius: 32, padding: 26, tint: HSKColors.jade) {
                VStack(spacing: 12) {
                    Image(systemName: "waveform.badge.mic")
                        .font(.system(size: 38))
                        .foregroundStyle(HSKColors.cinnabarDark)
                    Text("drill_pronunciation_complete")
                        .font(.title2.bold())
                        .foregroundStyle(HSKColors.ink)
                    Text("\(model.correctCount) / \(model.questions.count)")
                        .font(.title3.monospacedDigit().bold())
                        .foregroundStyle(HSKColors.inkSecondary)
                    Button("action_done", action: onClose)
                        .buttonStyle(HSKPrimaryButtonStyle())
                }
                .frame(maxWidth: .infinity)
            }
            .padding(24)
            Spacer()
        }
    }

    private var emptyState: some View {
        VStack {
            Spacer()
            HSKGlassCard(cornerRadius: 26, padding: 20, tint: HSKColors.flame) {
                VStack(spacing: 12) {
                    Text(model.limitReached ? "drill_limit_reached" : "drill_load_error")
                        .foregroundStyle(HSKColors.inkSecondary)
                        .multilineTextAlignment(.center)
                    if !model.limitReached {
                        Button("action_retry") {
                            Task { await model.start(level: account.level, language: account.language) }
                        }
                        .buttonStyle(HSKGlassSecondaryButtonStyle())
                    }
                    Button("action_close", action: onClose)
                        .buttonStyle(HSKGlassSecondaryButtonStyle())
                }
            }
            .padding(24)
            Spacer()
        }
    }
}
