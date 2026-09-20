import SwiftUI

struct LessonScreen: View {
    @ObservedObject var model: LessonViewModel
    let onClose: () -> Void
    let onCompleted: () -> Void

    var body: some View {
        ZStack {
            HSKGlassBackdrop()

            if model.isLoading {
                ProgressView()
                    .tint(HSKColors.cinnabar)
                    .controlSize(.large)
            } else if model.lesson == nil {
                failureView
            } else {
                lessonBody
            }
        }
        .task {
            if model.lesson == nil {
                await model.load()
            }
        }
    }

    @ViewBuilder
    private var lessonBody: some View {
        switch model.outcome {
        case .inProgress:
            activeLesson
        case .previewEnded:
            endCard(
                icon: "lock.circle.fill",
                title: "lesson_preview_title",
                body: "lesson_preview_body",
                accent: HSKColors.flame,
                primaryTitle: "action_close",
                primary: onClose
            )
        case .completed(let summary):
            completionCard(summary)
        case .failed:
            failedCompletion
        }
    }

    private var activeLesson: some View {
        VStack(spacing: 0) {
            topBar
            stageLine

            ScrollView(showsIndicators: false) {
                if let card = model.currentCard {
                    cardView(card)
                        .padding(.horizontal, 20)
                        .padding(.top, 18)
                        .padding(.bottom, 28)
                        .id(model.cardIndex)
                        .transition(.asymmetric(
                            insertion: .move(edge: .trailing).combined(with: .opacity),
                            removal: .move(edge: .leading).combined(with: .opacity)
                        ))
                }
            }

            footer
        }
        .animation(.spring(response: 0.40, dampingFraction: 0.86), value: model.cardIndex)
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

            HSKGlassPill {
                HStack(spacing: 4) {
                    Image(systemName: "heart.fill")
                        .font(.caption)
                        .foregroundStyle(HSKColors.cinnabar)
                    Text(String(model.hearts))
                        .font(.caption.monospacedDigit().weight(.bold))
                        .foregroundStyle(HSKColors.ink)
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.top, 10)
    }

    private var stageLine: some View {
        HStack(spacing: 8) {
            Text("\(model.cardIndex + 1) / \(max(model.cards.count, 1))")
                .font(.caption2.monospacedDigit().weight(.semibold))
                .foregroundStyle(HSKColors.cinnabarDark)

            Spacer()

            Text(model.sectionTitle)
                .font(.caption.weight(.semibold))
                .foregroundStyle(HSKColors.inkSecondary)
                .lineLimit(1)
        }
        .padding(.horizontal, 20)
        .padding(.top, 10)
    }

    @ViewBuilder
    private func cardView(_ card: LessonCard) -> some View {
        switch card {
        case .word(let word):
            wordCard(word)
        case .grammar(let grammar):
            grammarCard(grammar)
        case .pronunciation(let pronunciation):
            pronunciationCard(pronunciation)
        case .choice(let choice):
            choiceCard(choice)
        case .builder(let builder):
            builderCard(builder)
        case .match(let match):
            matchCard(match)
        case .unsupported(_, let rawType):
            HSKGlassCard(cornerRadius: 28, padding: 22, tint: HSKColors.flame) {
                VStack(spacing: 13) {
                    Image(systemName: "questionmark.square.dashed")
                        .font(.system(size: 36))
                        .foregroundStyle(HSKColors.flame)
                    Text("lesson_unsupported")
                        .font(.headline)
                        .foregroundStyle(HSKColors.ink)
                    if !rawType.isEmpty {
                        Text(rawType)
                            .font(.caption.monospaced())
                            .foregroundStyle(HSKColors.inkSecondary)
                    }
                }
                .frame(maxWidth: .infinity)
            }
        }
    }

    private func wordCard(_ card: LessonWordCard) -> some View {
        HSKGlassCard(cornerRadius: 32, padding: 24, tint: HSKColors.cinnabar) {
            VStack(spacing: 15) {
                HSKGlassPill {
                    Text("lesson_new_word")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(HSKColors.cinnabarDark)
                }

                Text(card.hanzi)
                    .font(.system(size: 74, weight: .semibold, design: .rounded))
                    .foregroundStyle(HSKColors.ink)

                Text(card.pinyin)
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(HSKColors.cinnabarDark)

                Text(card.meaning)
                    .font(.title3)
                    .foregroundStyle(HSKColors.ink)
                    .multilineTextAlignment(.center)

                if !card.partOfSpeech.isEmpty {
                    Text(card.partOfSpeech)
                        .font(.caption.monospaced())
                        .foregroundStyle(HSKColors.inkSecondary)
                }

                Button {
                    model.play(card.hanzi)
                } label: {
                    Label("foundation_listen", systemImage: "speaker.wave.2.fill")
                }
                .buttonStyle(HSKGlassSecondaryButtonStyle())
            }
            .frame(maxWidth: .infinity)
        }
    }

    private func grammarCard(_ card: LessonGrammarCard) -> some View {
        VStack(spacing: 14) {
            HSKGlassCard(cornerRadius: 30, padding: 22, tint: HSKColors.auroraBlue) {
                VStack(spacing: 10) {
                    if !card.titleZh.isEmpty {
                        Text(card.titleZh)
                            .font(.system(size: 38, weight: .semibold, design: .rounded))
                            .foregroundStyle(HSKColors.cinnabarDark)
                    }

                    Text(card.title)
                        .font(.title2.bold())
                        .foregroundStyle(HSKColors.ink)
                        .multilineTextAlignment(.center)

                    Text(card.rule)
                        .font(.body)
                        .foregroundStyle(HSKColors.inkSecondary)
                        .lineSpacing(5)
                }
                .frame(maxWidth: .infinity)
            }

            ForEach(Array(card.examples.enumerated()), id: \.offset) { _, example in
                HSKGlassCard(cornerRadius: 22, padding: 16) {
                    HStack(spacing: 14) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(example.hanzi)
                                .font(.title2.bold())
                                .foregroundStyle(HSKColors.ink)
                            Text(example.pinyin)
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(HSKColors.cinnabarDark)
                            Text(example.translation)
                                .font(.subheadline)
                                .foregroundStyle(HSKColors.inkSecondary)
                        }
                        Spacer()
                        Button {
                            model.play(example.hanzi)
                        } label: {
                            Image(systemName: "speaker.wave.2.fill")
                                .foregroundStyle(HSKColors.cinnabarDark)
                        }
                        .buttonStyle(HSKGlassIconButtonStyle())
                    }
                }
            }
        }
    }

    private func pronunciationCard(_ card: LessonPronunciationCard) -> some View {
        HSKGlassCard(cornerRadius: 32, padding: 24, tint: HSKColors.jade) {
            VStack(spacing: 16) {
                Image(systemName: "waveform.circle.fill")
                    .font(.system(size: 52))
                    .symbolRenderingMode(.hierarchical)
                    .foregroundStyle(HSKColors.jade)

                Text(card.phrase)
                    .font(.system(size: 54, weight: .semibold, design: .rounded))
                    .foregroundStyle(HSKColors.ink)

                Text(card.pinyin)
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(HSKColors.cinnabarDark)

                Text(card.translation)
                    .font(.body)
                    .foregroundStyle(HSKColors.inkSecondary)
                    .multilineTextAlignment(.center)

                Button {
                    model.play(card.phrase)
                } label: {
                    Label("foundation_listen", systemImage: "speaker.wave.2.fill")
                }
                .buttonStyle(HSKGlassSecondaryButtonStyle())
            }
            .frame(maxWidth: .infinity)
        }
    }

    private func choiceCard(_ card: LessonChoiceCard) -> some View {
        VStack(spacing: 15) {
            HSKGlassCard(cornerRadius: 30, padding: 22, tint: HSKColors.cinnabar) {
                VStack(spacing: 12) {
                    if card.isReviewCard {
                        HSKGlassPill {
                            Label("lesson_review", systemImage: "arrow.clockwise")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(HSKColors.cinnabarDark)
                        }
                    }

                    if !card.title.isEmpty {
                        Text(card.title)
                            .font(.title2.bold())
                            .foregroundStyle(HSKColors.ink)
                            .multilineTextAlignment(.center)
                    }

                    if !card.prompt.isEmpty {
                        Text(card.prompt)
                            .font(.body)
                            .foregroundStyle(HSKColors.inkSecondary)
                            .multilineTextAlignment(.center)
                    }

                    if !card.sentence.isEmpty {
                        Text(card.sentence)
                            .font(.title3.weight(.semibold))
                            .foregroundStyle(HSKColors.ink)
                            .multilineTextAlignment(.center)
                            .padding(.top, 2)
                    }

                    if card.kind == .dialogCloze, !card.lines.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            ForEach(Array(card.lines.enumerated()), id: \.offset) { _, line in
                                HStack(alignment: .top, spacing: 8) {
                                    Text(line.speaker)
                                        .font(.caption.bold())
                                        .foregroundStyle(HSKColors.cinnabarDark)
                                        .frame(width: 24)
                                    Text(line.isBlank ? "____" : line.text)
                                        .font(.body.weight(.medium))
                                        .foregroundStyle(HSKColors.ink)
                                }
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(14)
                        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 18))
                    }

                    if card.kind == .listening, !card.audioText.isEmpty {
                        Button {
                            model.play(card.audioText)
                        } label: {
                            Image(systemName: "speaker.wave.3.fill")
                                .font(.title2)
                                .foregroundStyle(HSKColors.cinnabarDark)
                        }
                        .buttonStyle(HSKGlassIconButtonStyle())

                        if !card.audioPinyin.isEmpty {
                            Text(card.audioPinyin)
                                .font(.caption)
                                .foregroundStyle(HSKColors.inkSecondary)
                        }
                    }
                }
            }

            VStack(spacing: 10) {
                ForEach(card.options.indices, id: \.self) { index in
                    lessonChoiceOption(
                        card.options[index],
                        index: index
                    )
                }
            }
        }
    }

    private func builderCard(_ card: LessonBuilderCard) -> some View {
        VStack(spacing: 15) {
            HSKGlassCard(cornerRadius: 30, padding: 22, tint: HSKColors.cinnabar) {
                VStack(spacing: 10) {
                    if card.reverse {
                        Text(card.hanzi)
                            .font(.system(size: 42, weight: .semibold, design: .rounded))
                            .foregroundStyle(HSKColors.ink)
                        Text(card.pinyin)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(HSKColors.cinnabarDark)
                        Text(card.translation)
                            .font(.body)
                            .foregroundStyle(HSKColors.inkSecondary)
                    } else {
                        Text("lesson_build_sentence")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(HSKColors.cinnabarDark)
                        Text(card.prompt)
                            .font(.title3.weight(.semibold))
                            .foregroundStyle(HSKColors.ink)
                            .multilineTextAlignment(.center)
                    }
                }
                .frame(maxWidth: .infinity)
            }

            HSKGlassCard(cornerRadius: 22, padding: 15) {
                HStack(spacing: 9) {
                    if model.builderTokens.isEmpty {
                        Text("lesson_builder_hint")
                            .font(.subheadline)
                            .foregroundStyle(HSKColors.inkSecondary)
                            .frame(maxWidth: .infinity, minHeight: 54)
                    } else {
                        ForEach(Array(model.builderTokens.enumerated()), id: \.offset) { _, value in
                            token(value) { model.undoBuilderToken() }
                        }
                        Spacer()
                    }
                }
            }

            HStack(spacing: 10) {
                ForEach(Array(card.tokens.enumerated()), id: \.offset) { _, value in
                    token(value) { model.addBuilderToken(value) }
                }
            }
            .frame(maxWidth: .infinity)

            Button("lesson_check") {
                model.submitBuilder()
            }
            .buttonStyle(HSKGlassSecondaryButtonStyle())
            .disabled(
                model.answerCorrect != nil
                    || model.builderTokens.count != card.answerTokens.count
            )
        }
    }

    private func matchCard(_ card: LessonMatchCard) -> some View {
        VStack(spacing: 16) {
            HSKGlassCard(cornerRadius: 28, padding: 20, tint: HSKColors.auroraMint) {
                VStack(spacing: 8) {
                    Text("lesson_match_title")
                        .font(.title2.bold())
                        .foregroundStyle(HSKColors.ink)
                    Text("lesson_match_subtitle")
                        .font(.subheadline)
                        .foregroundStyle(HSKColors.inkSecondary)
                }
                .frame(maxWidth: .infinity)
            }

            HStack(alignment: .top, spacing: 12) {
                VStack(spacing: 10) {
                    ForEach(card.pairs.indices, id: \.self) { index in
                        matchButton(
                            text: card.pairs[index].hanzi,
                            selected: model.selectedMatchLeft == index,
                            matched: model.matchedPairIndices.contains(index)
                        ) {
                            model.selectMatchLeft(index)
                        }
                    }
                }

                VStack(spacing: 10) {
                    ForEach(Array(card.pairs.indices.reversed()), id: \.self) { index in
                        matchButton(
                            text: card.pairs[index].meaning,
                            selected: model.selectedMatchRight == index,
                            matched: model.matchedPairIndices.contains(index)
                        ) {
                            model.selectMatchRight(index)
                        }
                    }
                }
            }
        }
    }

    private func lessonChoiceOption(_ text: String, index: Int) -> some View {
        let selected = model.selectedChoice == index
        let correct = selected && model.answerCorrect == true
        let wrong = selected && model.answerCorrect == false

        let fillColor: Color
        let strokeColor: Color

        if correct {
            fillColor = HSKColors.jade.opacity(0.12)
            strokeColor = HSKColors.jade.opacity(0.70)
        } else if wrong {
            fillColor = HSKColors.flame.opacity(0.12)
            strokeColor = HSKColors.flame.opacity(0.70)
        } else if selected {
            fillColor = HSKColors.cinnabar.opacity(0.08)
            strokeColor = HSKColors.cinnabar.opacity(0.58)
        } else {
            fillColor = .clear
            strokeColor = Color.white.opacity(0.44)
        }

        return Button {
            model.answerChoice(index)
        } label: {
            HStack {
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
        }
        .buttonStyle(.plain)
        .disabled(model.answerCorrect != nil)
    }

    private func token(_ value: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(value)
                .font(.system(size: 23, weight: .semibold, design: .rounded))
                .foregroundStyle(HSKColors.ink)
                .frame(minWidth: 52, minHeight: 52)
                .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 15))
                .overlay(
                    RoundedRectangle(cornerRadius: 15)
                        .stroke(Color.white.opacity(0.50), lineWidth: 0.8)
                )
                .shadow(color: Color.black.opacity(0.07), radius: 8, y: 4)
        }
        .buttonStyle(.plain)
    }

    private func matchButton(
        text: String,
        selected: Bool,
        matched: Bool,
        action: @escaping () -> Void
    ) -> some View {
        let fillColor: Color = matched
            ? HSKColors.jade.opacity(0.12)
            : selected
                ? HSKColors.cinnabar.opacity(0.10)
                : .clear
        let strokeColor: Color = matched
            ? HSKColors.jade.opacity(0.62)
            : selected
                ? HSKColors.cinnabar.opacity(0.60)
                : Color.white.opacity(0.44)

        return Button(action: action) {
            Text(text)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(matched ? HSKColors.jade : HSKColors.ink)
                .multilineTextAlignment(.center)
                .frame(maxWidth: .infinity, minHeight: 56)
                .padding(.horizontal, 8)
                .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 17))
                .overlay(
                    RoundedRectangle(cornerRadius: 17)
                        .fill(fillColor)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 17)
                        .stroke(
                            strokeColor,
                            lineWidth: selected || matched ? 1.1 : 0.8
                        )
                )
        }
        .buttonStyle(.plain)
        .disabled(matched || model.answerCorrect != nil)
    }

    @ViewBuilder
    private var footer: some View {
        if let correct = model.answerCorrect {
            VStack(spacing: 10) {
                HStack(spacing: 10) {
                    Image(systemName: correct ? "checkmark.circle.fill" : "exclamationmark.circle.fill")
                        .font(.title3)
                        .foregroundStyle(correct ? HSKColors.jade : HSKColors.flame)

                    VStack(alignment: .leading, spacing: 3) {
                        Text(correct ? "lesson_correct" : "lesson_wrong")
                            .font(.headline)
                            .foregroundStyle(correct ? HSKColors.jade : HSKColors.flame)

                        if !model.answerExplanation.isEmpty {
                            Text(model.answerExplanation)
                                .font(.footnote)
                                .foregroundStyle(HSKColors.inkSecondary)
                                .lineLimit(3)
                        }
                    }

                    Spacer()
                }

                Button {
                    Task { await model.advance() }
                } label: {
                    if model.isSubmitting {
                        ProgressView().tint(.white)
                    } else {
                        Text("lesson_next")
                    }
                }
                .buttonStyle(HSKPrimaryButtonStyle())
            }
            .padding(.horizontal, 18)
            .padding(.top, 12)
            .padding(.bottom, 10)
            .background(.ultraThinMaterial)
            .overlay(alignment: .top) {
                Rectangle().fill(Color.white.opacity(0.28)).frame(height: 0.7)
            }
        } else if let card = model.currentCard,
                  !isGraded(card) {
            VStack {
                Button {
                    Task { await model.acknowledge() }
                } label: {
                    if model.isSubmitting {
                        ProgressView().tint(.white)
                    } else {
                        Text("lesson_next")
                    }
                }
                .buttonStyle(HSKPrimaryButtonStyle())
            }
            .padding(.horizontal, 18)
            .padding(.top, 12)
            .padding(.bottom, 10)
            .background(.ultraThinMaterial)
        }
    }

    private func isGraded(_ card: LessonCard) -> Bool {
        switch card {
        case .choice, .builder, .match:
            return true
        case .word, .grammar, .pronunciation, .unsupported:
            return false
        }
    }

    private func completionCard(_ summary: LessonViewModel.CompletionSummary) -> some View {
        endCard(
            icon: "checkmark.seal.fill",
            title: "lesson_completed_title",
            bodyText: completionText(summary),
            accent: HSKColors.jade,
            primaryTitle: "action_close"
        ) {
            onCompleted()
            onClose()
        }
    }

    private func completionText(_ summary: LessonViewModel.CompletionSummary) -> String {
        if summary.graded == 0 {
            return NSLocalizedString("lesson_completed_body", comment: "")
        }
        return String(
            format: NSLocalizedString("lesson_score_format", comment: ""),
            summary.correct,
            summary.graded
        )
    }

    private var failedCompletion: some View {
        VStack {
            endCard(
                icon: "exclamationmark.triangle.fill",
                title: "lesson_save_error",
                body: "error_network",
                accent: HSKColors.flame,
                primaryTitle: "action_retry"
            ) {
                Task { await model.retryCompletion() }
            }
        }
    }

    private var failureView: some View {
        endCard(
            icon: "wifi.exclamationmark",
            title: LocalizedStringKey(model.errorKey ?? "lesson_load_error"),
            body: "lesson_retry_body",
            accent: HSKColors.flame,
            primaryTitle: "action_retry"
        ) {
            Task { await model.load() }
        }
    }

    private func endCard(
        icon: String,
        title: LocalizedStringKey,
        body: String,
        accent: Color,
        primaryTitle: LocalizedStringKey,
        primary: @escaping () -> Void
    ) -> some View {
        endCard(
            icon: icon,
            title: title,
            bodyText: NSLocalizedString(body, comment: ""),
            accent: accent,
            primaryTitle: primaryTitle,
            primary: primary
        )
    }

    private func endCard(
        icon: String,
        title: LocalizedStringKey,
        bodyText: String,
        accent: Color,
        primaryTitle: LocalizedStringKey,
        primary: @escaping () -> Void
    ) -> some View {
        HSKGlassCard(cornerRadius: 32, padding: 24, tint: accent) {
            VStack(spacing: 16) {
                ZStack {
                    Circle()
                        .fill(accent.opacity(0.14))
                        .frame(width: 90, height: 90)
                    Image(systemName: icon)
                        .font(.system(size: 42))
                        .foregroundStyle(accent)
                }

                Text(title)
                    .font(.title2.bold())
                    .foregroundStyle(HSKColors.ink)
                    .multilineTextAlignment(.center)

                Text(bodyText)
                    .font(.body)
                    .foregroundStyle(HSKColors.inkSecondary)
                    .multilineTextAlignment(.center)

                Button(primaryTitle, action: primary)
                    .buttonStyle(HSKPrimaryButtonStyle())

                if case .failed = model.outcome {
                    Button("action_close", action: onClose)
                        .buttonStyle(HSKGlassSecondaryButtonStyle())
                }
            }
        }
        .padding(24)
    }
}
