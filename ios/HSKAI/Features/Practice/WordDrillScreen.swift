import SwiftUI

struct WordDrillScreen: View {
    @ObservedObject var model: WordDrillViewModel
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
                    questionBody
                case .finished:
                    summary
                case .idle:
                    emptyState
                }
            }
        }
        .task {
            if model.phase == .idle && !model.limitReached && model.errorKey == nil {
                await model.startRecognition(level: account.level, language: account.language)
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

    private var questionBody: some View {
        VStack(spacing: 16) {
            if let question = model.current {
                Text("drill_recognition_prompt")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(HSKColors.inkSecondary)

                HSKGlassCard(cornerRadius: 28, padding: 22, tint: HSKColors.auroraBlue) {
                    VStack(spacing: 7) {
                        Text(question.pinyin)
                            .font(.title3.weight(.semibold))
                            .foregroundStyle(HSKColors.cinnabarDark)
                        Text(question.meaning)
                            .font(.title3.weight(.semibold))
                            .foregroundStyle(HSKColors.ink)
                            .multilineTextAlignment(.center)
                        if question.isReview {
                            HSKGlassPill {
                                Text("drill_review_word")
                                    .font(.caption.bold())
                                    .foregroundStyle(HSKColors.inkSecondary)
                            }
                        }
                    }
                    .frame(maxWidth: .infinity)
                }

                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                    ForEach(question.options, id: \.self) { option in
                        optionButton(option, question: question)
                    }
                }

                Spacer()

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
                            if !model.wasCorrect {
                                Text("\(question.hanzi) · \(question.pinyin)")
                                    .foregroundStyle(HSKColors.inkSecondary)
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

    private func optionButton(_ option: String, question: IOSDrillQuestion) -> some View {
        let right = model.answered && option == question.hanzi
        let wrong = model.answered && option == model.selected && option != question.hanzi
        let tint: Color? = right ? HSKColors.jade : (wrong ? HSKColors.flame : nil)

        return Button {
            model.choose(option)
        } label: {
            Text(option)
                .font(.system(size: 36, weight: .semibold, design: .rounded))
                .foregroundStyle(tint ?? HSKColors.ink)
                .frame(maxWidth: .infinity, minHeight: 82)
                .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 20))
                .overlay(
                    RoundedRectangle(cornerRadius: 20)
                        .fill((tint ?? Color.clear).opacity(tint == nil ? 0 : 0.10))
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 20)
                        .stroke(tint?.opacity(0.75) ?? Color.white.opacity(0.42), lineWidth: right || wrong ? 1.4 : 0.8)
                )
        }
        .buttonStyle(.plain)
        .disabled(model.answered)
    }

    private var summary: some View {
        VStack(spacing: 18) {
            Spacer()
            HSKGlassCard(cornerRadius: 32, padding: 26, tint: HSKColors.jade) {
                VStack(spacing: 12) {
                    Image(systemName: "eye.fill")
                        .font(.system(size: 36))
                        .foregroundStyle(HSKColors.cinnabarDark)
                    Text("drill_complete_title")
                        .font(.title2.bold())
                        .foregroundStyle(HSKColors.ink)
                    Text("\(model.correctCount) / \(model.questions.count)")
                        .font(.title3.monospacedDigit().weight(.bold))
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
        VStack(spacing: 14) {
            Spacer()
            HSKGlassCard(cornerRadius: 26, padding: 20, tint: HSKColors.flame) {
                VStack(spacing: 12) {
                    Text(model.limitReached ? "drill_limit_reached" : "drill_load_error")
                        .foregroundStyle(HSKColors.inkSecondary)
                        .multilineTextAlignment(.center)
                    if !model.limitReached {
                        Button("action_retry") {
                            Task { await model.startRecognition(level: account.level, language: account.language) }
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
