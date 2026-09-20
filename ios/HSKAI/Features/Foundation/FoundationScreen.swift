import SwiftUI

struct FoundationScreen: View {
    @ObservedObject var model: FoundationViewModel
    let required: Bool
    let onCompleted: () -> Void
    let onClose: () -> Void

    var body: some View {
        ZStack {
            HSKGlassBackdrop()

            if model.isLoading {
                ProgressView()
                    .tint(HSKColors.cinnabar)
                    .controlSize(.large)
            } else if let card = model.currentCard {
                VStack(spacing: 0) {
                    topBar

                    ScrollView(showsIndicators: false) {
                        VStack(spacing: 18) {
                            stepPill
                            cardBody(card)
                        }
                        .padding(.horizontal, 20)
                        .padding(.top, 18)
                        .padding(.bottom, 26)
                        .id(model.cardIndex)
                        .transition(.asymmetric(
                            insertion: .move(edge: .trailing).combined(with: .opacity),
                            removal: .move(edge: .leading).combined(with: .opacity)
                        ))
                    }

                    footer(card)
                }
            } else {
                failure
            }
        }
        .animation(.spring(response: 0.42, dampingFraction: 0.86), value: model.cardIndex)
        .task {
            if model.cards.isEmpty {
                await model.load()
            }
        }
        .onChange(of: model.isCompleted) { completed in
            if completed { onCompleted() }
        }
    }

    private var topBar: some View {
        HStack(spacing: 12) {
            if required {
                Color.clear.frame(width: 44, height: 44)
            } else {
                Button(action: onClose) {
                    Image(systemName: "xmark")
                        .font(.subheadline.weight(.bold))
                        .foregroundStyle(HSKColors.ink)
                }
                .buttonStyle(HSKGlassIconButtonStyle())
            }

            ProgressView(value: model.progress)
                .tint(HSKColors.cinnabar)
                .background(.ultraThinMaterial, in: Capsule())
                .clipShape(Capsule())

            HSKGlassPill {
                Text("\(min(model.cardIndex + 1, max(model.cards.count, 1)))/\(max(model.cards.count, 1))")
                    .font(.caption.monospacedDigit().weight(.semibold))
                    .foregroundStyle(HSKColors.inkSecondary)
            }
        }
        .padding(.horizontal, 16)
        .padding(.top, 10)
    }

    private var stepPill: some View {
        HSKGlassPill {
            HStack(spacing: 7) {
                Image(systemName: "sparkles")
                    .foregroundStyle(HSKColors.cinnabar)
                Text("foundation_step")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(HSKColors.inkSecondary)
            }
        }
    }

    @ViewBuilder
    private func cardBody(_ card: FoundationCard) -> some View {
        switch card {
        case .info(let info):
            infoCard(info)
        case .choice(let choice):
            choiceCard(choice)
        case .builder(let builder):
            builderCard(builder)
        case .speak(let speak):
            speakCard(speak)
        case .result(let result):
            resultCard(result)
        case .unsupported:
            HSKGlassCard(cornerRadius: 28, padding: 22) {
                VStack(spacing: 12) {
                    Image(systemName: "questionmark.square.dashed")
                        .font(.system(size: 34))
                        .foregroundStyle(HSKColors.inkSecondary)
                    Text("foundation_unknown_card")
                        .foregroundStyle(HSKColors.inkSecondary)
                }
                .frame(maxWidth: .infinity)
            }
        }
    }

    private func infoCard(_ card: FoundationInfoCard) -> some View {
        HSKGlassCard(cornerRadius: 30, padding: 22, tint: HSKColors.cinnabar) {
            VStack(spacing: 16) {
                if !card.title.isEmpty {
                    Text(card.title)
                        .font(.title2.bold())
                        .foregroundStyle(HSKColors.ink)
                        .multilineTextAlignment(.center)
                }

                if !card.text.isEmpty {
                    Text(card.text)
                        .font(.body)
                        .foregroundStyle(HSKColors.inkSecondary)
                        .multilineTextAlignment(.center)
                        .lineSpacing(5)
                }

                ForEach(Array(card.examples.enumerated()), id: \.offset) { _, example in
                    exampleView(example, playable: true)
                }

                if !card.audioText.isEmpty {
                    Button {
                        model.playCurrentAudio()
                    } label: {
                        Label("foundation_listen", systemImage: "speaker.wave.2.fill")
                    }
                    .buttonStyle(HSKGlassSecondaryButtonStyle())
                }

                if !card.naturalPinyin.isEmpty {
                    HSKGlassPill {
                        Text(card.naturalPinyin)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(HSKColors.cinnabarDark)
                    }
                }
            }
        }
    }

    private func choiceCard(_ card: FoundationChoiceCard) -> some View {
        VStack(spacing: 16) {
            HSKGlassCard(cornerRadius: 30, padding: 22, tint: HSKColors.cinnabar) {
                VStack(spacing: 12) {
                    Text(card.title)
                        .font(.title2.bold())
                        .foregroundStyle(HSKColors.ink)
                        .multilineTextAlignment(.center)

                    Text(card.prompt)
                        .font(.body)
                        .foregroundStyle(HSKColors.inkSecondary)
                        .multilineTextAlignment(.center)

                    if !card.audioText.isEmpty {
                        Button {
                            model.playCurrentAudio()
                        } label: {
                            Image(systemName: "speaker.wave.2.fill")
                                .font(.title3)
                                .foregroundStyle(HSKColors.cinnabarDark)
                        }
                        .buttonStyle(HSKGlassIconButtonStyle())
                    }
                }
            }

            VStack(spacing: 11) {
                ForEach(card.options.indices, id: \.self) { index in
                    choiceOption(
                        card.options[index],
                        index: index,
                        correctIndex: card.correctIndex
                    )
                }
            }

            if let correct = model.answerCorrect {
                feedback(correct: correct, text: card.explanation)
                    .transition(.scale(scale: 0.96).combined(with: .opacity))
            }
        }
    }

    private func builderCard(_ card: FoundationBuilderCard) -> some View {
        VStack(spacing: 16) {
            HSKGlassCard(cornerRadius: 30, padding: 22, tint: HSKColors.cinnabar) {
                VStack(spacing: 10) {
                    Text(card.title)
                        .font(.title2.bold())
                        .foregroundStyle(HSKColors.ink)
                    Text(card.prompt)
                        .font(.body)
                        .foregroundStyle(HSKColors.inkSecondary)
                        .multilineTextAlignment(.center)
                }
                .frame(maxWidth: .infinity)
            }

            HSKGlassCard(cornerRadius: 24, padding: 16) {
                HStack(spacing: 10) {
                    if model.builderTokens.isEmpty {
                        Text("foundation_builder_hint")
                            .font(.subheadline)
                            .foregroundStyle(HSKColors.inkSecondary)
                            .frame(maxWidth: .infinity, minHeight: 50)
                    } else {
                        ForEach(Array(model.builderTokens.enumerated()), id: \.offset) { _, token in
                            tokenButton(token) {
                                model.undoBuilderToken()
                            }
                        }
                        Spacer()
                    }
                }
                .frame(maxWidth: .infinity)
            }

            HStack(spacing: 12) {
                ForEach(Array(card.tokens.enumerated()), id: \.offset) { _, token in
                    tokenButton(token) {
                        model.addBuilderToken(token)
                    }
                }
            }
            .frame(maxWidth: .infinity)

            Button("foundation_check") {
                model.submitBuilder()
            }
            .buttonStyle(HSKGlassSecondaryButtonStyle())
            .disabled(model.builderTokens.count != card.answerTokens.count)

            if let correct = model.answerCorrect {
                feedback(correct: correct, text: card.explanation)
            }
        }
    }

    private func speakCard(_ card: FoundationSpeakCard) -> some View {
        HSKGlassCard(cornerRadius: 30, padding: 22, tint: HSKColors.jade) {
            VStack(spacing: 16) {
                Image(systemName: "waveform.circle.fill")
                    .font(.system(size: 48))
                    .symbolRenderingMode(.hierarchical)
                    .foregroundStyle(HSKColors.jade)

                Text(card.title)
                    .font(.title2.bold())
                    .foregroundStyle(HSKColors.ink)
                    .multilineTextAlignment(.center)

                Text(card.text)
                    .foregroundStyle(HSKColors.inkSecondary)
                    .multilineTextAlignment(.center)

                if let example = card.example {
                    exampleView(example, playable: true)
                }

                Button {
                    model.playCurrentAudio()
                } label: {
                    Label("foundation_listen", systemImage: "speaker.wave.2.fill")
                }
                .buttonStyle(HSKGlassSecondaryButtonStyle())

                Text("foundation_speaking_optional")
                    .font(.footnote)
                    .foregroundStyle(HSKColors.inkSecondary)
                    .multilineTextAlignment(.center)
            }
        }
    }

    private func resultCard(_ card: FoundationInfoCard) -> some View {
        HSKGlassCard(cornerRadius: 30, padding: 24, tint: HSKColors.jade) {
            VStack(spacing: 16) {
                ZStack {
                    Circle()
                        .fill(HSKColors.jade.opacity(0.15))
                        .frame(width: 86, height: 86)
                    Image(systemName: model.canFinish ? "checkmark.seal.fill" : "lock.fill")
                        .font(.system(size: 40))
                        .foregroundStyle(model.canFinish ? HSKColors.jade : HSKColors.flame)
                }

                Text(card.title)
                    .font(.title2.bold())
                    .foregroundStyle(HSKColors.ink)
                    .multilineTextAlignment(.center)

                Text(card.text)
                    .foregroundStyle(HSKColors.inkSecondary)
                    .multilineTextAlignment(.center)

                HSKGlassPill {
                    Text("\(model.masteredObjectives.count)/\(model.requiredObjectives.count)")
                        .font(.headline.monospacedDigit())
                        .foregroundStyle(HSKColors.ink)
                }
            }
            .frame(maxWidth: .infinity)
        }
    }

    private func exampleView(_ example: FoundationExample, playable: Bool) -> some View {
        HStack(spacing: 14) {
            VStack(alignment: .leading, spacing: 4) {
                Text(example.hanzi)
                    .font(.system(size: 34, weight: .semibold, design: .rounded))
                    .foregroundStyle(HSKColors.ink)
                Text(example.pinyin)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(HSKColors.cinnabarDark)
                Text(example.translation)
                    .font(.subheadline)
                    .foregroundStyle(HSKColors.inkSecondary)
            }

            Spacer()

            if playable, !example.hanzi.isEmpty {
                Button {
                    model.play(example.hanzi)
                } label: {
                    Image(systemName: "speaker.wave.2.fill")
                        .foregroundStyle(HSKColors.cinnabarDark)
                }
                .buttonStyle(HSKGlassIconButtonStyle())
            }
        }
        .padding(14)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .stroke(Color.white.opacity(0.44), lineWidth: 0.8)
        )
    }

    private func choiceOption(
        _ text: String,
        index: Int,
        correctIndex: Int
    ) -> some View {
        let selected = model.selectedChoice == index
        let correct = selected && model.answerCorrect == true
        let wrong = selected && model.answerCorrect == false

        let fillColor: Color
        let strokeColor: Color
        let shadowColor: Color

        if correct {
            fillColor = HSKColors.jade.opacity(0.12)
            strokeColor = HSKColors.jade.opacity(0.70)
            shadowColor = HSKColors.jade.opacity(0.12)
        } else if wrong {
            fillColor = HSKColors.flame.opacity(0.12)
            strokeColor = HSKColors.flame.opacity(0.70)
            shadowColor = HSKColors.flame.opacity(0.12)
        } else if selected {
            fillColor = HSKColors.cinnabar.opacity(0.08)
            strokeColor = HSKColors.cinnabar.opacity(0.58)
            shadowColor = Color.black.opacity(0.06)
        } else {
            fillColor = .clear
            strokeColor = Color.white.opacity(0.44)
            shadowColor = Color.black.opacity(0.06)
        }

        return Button {
            model.choose(index)
        } label: {
            HStack(spacing: 12) {
                Text(text)
                    .font(.body.weight(.medium))
                    .foregroundStyle(HSKColors.ink)
                    .frame(maxWidth: .infinity, alignment: .leading)

                if selected {
                    Image(systemName: correct ? "checkmark.circle.fill" : "xmark.circle.fill")
                        .foregroundStyle(correct ? HSKColors.jade : HSKColors.flame)
                }
            }
            .padding(16)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 19, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 19, style: .continuous)
                    .fill(fillColor)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 19, style: .continuous)
                    .stroke(strokeColor, lineWidth: selected ? 1.2 : 0.8)
            )
            .shadow(color: shadowColor, radius: 12, y: 6)
        }
        .buttonStyle(.plain)
        .disabled(model.answerCorrect == true)
        .scaleEffect(selected ? 1.01 : 1)
        .animation(.spring(response: 0.28, dampingFraction: 0.78), value: selected)
    }

    private func tokenButton(_ token: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(token)
                .font(.system(size: 25, weight: .semibold, design: .rounded))
                .foregroundStyle(HSKColors.ink)
                .frame(minWidth: 54, minHeight: 54)
                .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .stroke(Color.white.opacity(0.52), lineWidth: 0.8)
                )
                .shadow(color: Color.black.opacity(0.07), radius: 9, y: 5)
        }
        .buttonStyle(.plain)
    }

    private func feedback(correct: Bool, text: String) -> some View {
        HStack(spacing: 10) {
            Image(systemName: correct ? "checkmark.circle.fill" : "xmark.circle.fill")
                .foregroundStyle(correct ? HSKColors.jade : HSKColors.flame)
            Text(text)
                .font(.subheadline)
                .foregroundStyle(HSKColors.ink)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(14)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill((correct ? HSKColors.jade : HSKColors.flame).opacity(0.09))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .stroke((correct ? HSKColors.jade : HSKColors.flame).opacity(0.36), lineWidth: 0.9)
        )
    }

    private func footer(_ card: FoundationCard) -> some View {
        VStack(spacing: 9) {
            if let errorKey = model.errorKey {
                Text(LocalizedStringKey(errorKey))
                    .font(.footnote)
                    .foregroundStyle(HSKColors.flame)
                    .multilineTextAlignment(.center)
            }

            Button {
                Task { await model.advance() }
            } label: {
                if model.isSaving {
                    ProgressView().tint(.white)
                } else {
                    Text("action_continue")
                }
            }
            .buttonStyle(HSKPrimaryButtonStyle())
            .disabled(!canAdvance(card))
        }
        .padding(.horizontal, 20)
        .padding(.top, 12)
        .padding(.bottom, 10)
        .background(.ultraThinMaterial)
        .overlay(alignment: .top) {
            Rectangle()
                .fill(Color.white.opacity(0.28))
                .frame(height: 0.7)
        }
    }

    private func canAdvance(_ card: FoundationCard) -> Bool {
        if model.isSaving { return false }
        switch card {
        case .choice, .builder:
            return model.answerCorrect == true
        case .result:
            return model.canFinish
        default:
            return true
        }
    }

    private var failure: some View {
        HSKGlassCard(cornerRadius: 28, padding: 22, tint: HSKColors.flame) {
            VStack(spacing: 16) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.system(size: 34))
                    .foregroundStyle(HSKColors.flame)

                Text(LocalizedStringKey(model.errorKey ?? "foundation_load_error"))
                    .foregroundStyle(HSKColors.inkSecondary)
                    .multilineTextAlignment(.center)

                Button("action_retry") {
                    Task { await model.load() }
                }
                .buttonStyle(HSKPrimaryButtonStyle())
            }
        }
        .padding(24)
    }
}
