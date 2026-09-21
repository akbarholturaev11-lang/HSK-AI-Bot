import SwiftUI

struct MistakesScreen: View {
    @ObservedObject var model: MistakesViewModel
    let onClose: () -> Void

    var body: some View {
        ZStack {
            HSKGlassBackdrop()

            switch model.phase {
            case .overview:
                overview
            case .loadingReview:
                ProgressView()
                    .tint(HSKColors.cinnabar)
                    .controlSize(.large)
            case .review, .completing:
                review
            case .result:
                result
            }
        }
        .task {
            await model.loadOverview()
        }
    }

    private var overview: some View {
        VStack(spacing: 0) {
            header(title: "mistakes_title")

            ScrollView(showsIndicators: false) {
                VStack(spacing: 14) {
                    if model.isLoadingOverview && model.overview == nil {
                        ProgressView()
                            .tint(HSKColors.cinnabar)
                            .padding(.top, 40)
                    } else if let overview = model.overview {
                        HSKGlassCard(cornerRadius: 28, padding: 22, tint: HSKColors.flame) {
                            VStack(spacing: 12) {
                                Text(String(overview.summary.total))
                                    .font(.system(size: 46, weight: .bold, design: .rounded))
                                    .foregroundStyle(HSKColors.flame)
                                Text("mistakes_active_count")
                                    .font(.subheadline)
                                    .foregroundStyle(HSKColors.inkSecondary)

                                if !overview.summary.categories.isEmpty {
                                    HStack(spacing: 8) {
                                        ForEach(
                                            overview.summary.categories
                                                .sorted { $0.value > $1.value }
                                                .prefix(3),
                                            id: \.key
                                        ) { category, count in
                                            HSKGlassPill {
                                                Text("\(category) · \(count)")
                                                    .font(.caption.weight(.semibold))
                                                    .foregroundStyle(HSKColors.ink)
                                            }
                                        }
                                    }
                                }

                                Button("mistakes_start_review") {
                                    Task { await model.startReview() }
                                }
                                .buttonStyle(HSKPrimaryButtonStyle())
                                .disabled(overview.summary.total == 0)
                            }
                            .frame(maxWidth: .infinity)
                        }

                        if let errorKey = model.errorKey {
                            Text(LocalizedStringKey(errorKey))
                                .font(.footnote)
                                .foregroundStyle(HSKColors.flame)
                                .multilineTextAlignment(.center)
                        }

                        ForEach(overview.items.prefix(60)) { item in
                            mistakeRow(item)
                        }
                    } else if let errorKey = model.errorKey {
                        HSKGlassCard(cornerRadius: 26, padding: 20, tint: HSKColors.flame) {
                            VStack(spacing: 14) {
                                Text(LocalizedStringKey(errorKey))
                                    .foregroundStyle(HSKColors.inkSecondary)
                                    .multilineTextAlignment(.center)
                                Button("action_retry") {
                                    Task { await model.loadOverview(force: true) }
                                }
                                .buttonStyle(HSKGlassSecondaryButtonStyle())
                            }
                        }
                    }
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 24)
            }
        }
    }

    private func mistakeRow(_ item: IOSMistakeItem) -> some View {
        HSKGlassCard(cornerRadius: 20, padding: 15) {
            VStack(alignment: .leading, spacing: 7) {
                HStack {
                    Text(item.category.isEmpty ? "—" : item.category)
                        .font(.caption.weight(.bold))
                        .foregroundStyle(HSKColors.cinnabarDark)
                    Spacer()
                    if item.count > 1 {
                        Text("×\(item.count)")
                            .font(.caption.monospacedDigit().weight(.semibold))
                            .foregroundStyle(HSKColors.inkSecondary)
                    }
                }

                Text(item.question)
                    .font(.headline)
                    .foregroundStyle(HSKColors.ink)

                if !item.pinyin.isEmpty {
                    Text(item.pinyin)
                        .font(.caption)
                        .foregroundStyle(HSKColors.cinnabarDark)
                }

                if let user = item.userAnswer, !user.isEmpty {
                    Text("✕ \(user)")
                        .font(.subheadline)
                        .foregroundStyle(HSKColors.flame)
                }

                Text("✓ \(item.correctAnswer)")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(HSKColors.jade)
            }
        }
    }

    private var review: some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                Button {
                    model.reset()
                } label: {
                    Image(systemName: "xmark")
                        .font(.subheadline.weight(.bold))
                        .foregroundStyle(HSKColors.ink)
                }
                .buttonStyle(HSKGlassIconButtonStyle())

                ProgressView(value: model.progress)
                    .tint(HSKColors.cinnabar)
                    .background(.ultraThinMaterial, in: Capsule())
                    .clipShape(Capsule())

                if let session = model.reviewSession {
                    HSKGlassPill {
                        Text("\(model.questionIndex + 1)/\(session.questions.count)")
                            .font(.caption.monospacedDigit().weight(.bold))
                            .foregroundStyle(HSKColors.ink)
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.top, 10)

            ScrollView(showsIndicators: false) {
                if let question = model.currentQuestion {
                    VStack(spacing: 16) {
                        HSKGlassCard(cornerRadius: 30, padding: 22, tint: HSKColors.flame) {
                            VStack(spacing: 12) {
                                if !question.audioText.isEmpty {
                                    Button {
                                        model.playCurrentAudio()
                                    } label: {
                                        Image(systemName: "speaker.wave.2.fill")
                                            .font(.title2)
                                            .foregroundStyle(HSKColors.cinnabarDark)
                                    }
                                    .buttonStyle(HSKGlassIconButtonStyle())
                                }

                                Text(question.prompt)
                                    .font(.title2.bold())
                                    .foregroundStyle(HSKColors.ink)
                                    .multilineTextAlignment(.center)

                                if !question.sentence.isEmpty {
                                    Text(question.sentence)
                                        .font(.system(size: 30, weight: .semibold, design: .rounded))
                                        .foregroundStyle(HSKColors.ink)
                                }

                                if !question.pinyin.isEmpty {
                                    Text(question.pinyin)
                                        .font(.subheadline.weight(.semibold))
                                        .foregroundStyle(HSKColors.cinnabarDark)
                                }
                            }
                            .frame(maxWidth: .infinity)
                        }

                        ForEach(question.options.indices, id: \.self) { index in
                            reviewOption(
                                question.options[index],
                                index: index
                            )
                        }

                        if let feedback = model.feedback {
                            HSKGlassCard(
                                cornerRadius: 20,
                                padding: 15,
                                tint: feedback.correct ? HSKColors.jade : HSKColors.flame
                            ) {
                                VStack(alignment: .leading, spacing: 6) {
                                    Text(
                                        feedback.correct
                                            ? LocalizedStringKey("lesson_correct")
                                            : LocalizedStringKey("lesson_wrong")
                                    )
                                    .font(.headline)
                                    .foregroundStyle(
                                        feedback.correct ? HSKColors.jade : HSKColors.flame
                                    )

                                    if !feedback.correctAnswer.isEmpty {
                                        Text("✓ \(feedback.correctAnswer)")
                                            .font(.subheadline.weight(.semibold))
                                            .foregroundStyle(HSKColors.ink)
                                    }

                                    if !feedback.explanation.isEmpty {
                                        Text(feedback.explanation)
                                            .font(.subheadline)
                                            .foregroundStyle(HSKColors.inkSecondary)
                                    }
                                }
                                .frame(maxWidth: .infinity, alignment: .leading)
                            }
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, 20)
                }
            }

            VStack(spacing: 8) {
                if let errorKey = model.errorKey {
                    Text(LocalizedStringKey(errorKey))
                        .font(.footnote)
                        .foregroundStyle(HSKColors.flame)
                }

                Button {
                    Task { await model.advance() }
                } label: {
                    if model.phase == .completing {
                        ProgressView().tint(.white)
                    } else {
                        Text("action_continue")
                    }
                }
                .buttonStyle(HSKPrimaryButtonStyle())
                .disabled(model.feedback == nil || model.phase == .completing)
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 14)
            .background(.ultraThinMaterial)
        }
    }

    private func reviewOption(_ text: String, index: Int) -> some View {
        let selected = model.selectedIndex == index
        let feedback = model.feedback
        let correct = feedback?.correctIndex == index
        let wrongSelected = selected && feedback != nil && correct == false

        return Button {
            Task { await model.answer(index) }
        } label: {
            HStack(spacing: 12) {
                Text(text)
                    .font(.body.weight(.semibold))
                    .foregroundStyle(HSKColors.ink)
                    .multilineTextAlignment(.leading)
                Spacer()
                if correct {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(HSKColors.jade)
                } else if wrongSelected {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(HSKColors.flame)
                } else {
                    Image(systemName: selected ? "circle.inset.filled" : "circle")
                        .foregroundStyle(
                            selected ? HSKColors.cinnabar : HSKColors.inkSecondary.opacity(0.4)
                        )
                }
            }
            .padding(15)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 18))
            .overlay(
                RoundedRectangle(cornerRadius: 18)
                    .stroke(
                        correct
                            ? HSKColors.jade.opacity(0.68)
                            : wrongSelected
                                ? HSKColors.flame.opacity(0.68)
                                : selected
                                    ? HSKColors.cinnabar.opacity(0.60)
                                    : Color.white.opacity(0.44),
                        lineWidth: correct || wrongSelected || selected ? 1.2 : 0.8
                    )
            )
        }
        .buttonStyle(.plain)
        .disabled(model.selectedIndex != nil)
    }

    private var result: some View {
        VStack {
            Spacer()

            if let result = model.result {
                HSKGlassCard(
                    cornerRadius: 32,
                    padding: 24,
                    tint: result.percent >= 70 ? HSKColors.jade : HSKColors.flame
                ) {
                    VStack(spacing: 15) {
                        Text("\(result.percent)%")
                            .font(.system(size: 48, weight: .bold, design: .rounded))
                            .foregroundStyle(
                                result.percent >= 70 ? HSKColors.jade : HSKColors.flame
                            )

                        Text("mistakes_review_done")
                            .font(.title2.bold())
                            .foregroundStyle(HSKColors.ink)

                        Text(
                            String(
                                format: NSLocalizedString("practice_result_score", comment: ""),
                                result.score,
                                result.total
                            )
                        )
                        .foregroundStyle(HSKColors.inkSecondary)

                        Text(
                            String(
                                format: NSLocalizedString("mistakes_remaining", comment: ""),
                                result.remaining
                            )
                        )
                        .font(.subheadline)
                        .foregroundStyle(HSKColors.inkSecondary)

                        Button("action_done") {
                            Task { await model.finishResult() }
                        }
                        .buttonStyle(HSKPrimaryButtonStyle())
                    }
                }
                .padding(24)
            }

            Spacer()
        }
    }

    private func header(title: LocalizedStringKey) -> some View {
        HStack(spacing: 12) {
            Button(action: onClose) {
                Image(systemName: "xmark")
                    .font(.subheadline.weight(.bold))
                    .foregroundStyle(HSKColors.ink)
            }
            .buttonStyle(HSKGlassIconButtonStyle())

            Text(title)
                .font(.headline)
                .foregroundStyle(HSKColors.ink)

            Spacer()
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }
}
