import SwiftUI

struct ExamScreen: View {
    @ObservedObject var model: ExamViewModel
    let account: LinkedAccount
    let onClose: () -> Void

    var body: some View {
        ZStack {
            HSKGlassBackdrop()

            switch model.phase {
            case .center:
                center
            case .loading:
                ProgressView()
                    .tint(HSKColors.cinnabar)
                    .controlSize(.large)
            case .exam, .completing:
                exam
            case .result:
                result
            }
        }
    }

    private var center: some View {
        VStack(spacing: 0) {
            header(title: "exam_center_title")

            ScrollView(showsIndicators: false) {
                VStack(spacing: 14) {
                    HSKGlassCard(
                        cornerRadius: 30,
                        padding: 24,
                        tint: HSKColors.auroraBlue
                    ) {
                        VStack(spacing: 10) {
                            Image(systemName: "checkmark.seal.fill")
                                .font(.system(size: 40))
                                .foregroundStyle(HSKColors.cinnabarDark)

                            Text("exam_center_title")
                                .font(.title2.bold())
                                .foregroundStyle(HSKColors.ink)

                            Text("exam_center_intro")
                                .font(.subheadline)
                                .foregroundStyle(HSKColors.inkSecondary)
                                .multilineTextAlignment(.center)
                        }
                        .frame(maxWidth: .infinity)
                    }

                    if let errorKey = model.errorKey {
                        Text(LocalizedStringKey(errorKey))
                            .font(.footnote)
                            .foregroundStyle(HSKColors.flame)
                            .multilineTextAlignment(.center)
                    }

                    ForEach(model.orderedEntries(currentLevel: account.level)) { entry in
                        examEntry(entry)
                    }
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 24)
            }
        }
    }

    private func examEntry(_ entry: IOSExamEntry) -> some View {
        let current = entry.level == account.level.lowercased()

        return Button {
            Task {
                await model.start(
                    level: entry.level,
                    language: account.language
                )
            }
        } label: {
            HSKGlassCard(
                cornerRadius: 22,
                padding: 17,
                tint: current ? HSKColors.cinnabar : HSKColors.auroraMint
            ) {
                HStack(spacing: 14) {
                    ZStack {
                        Circle()
                            .fill(
                                (current ? HSKColors.cinnabar : HSKColors.jade)
                                    .opacity(0.14)
                            )
                            .frame(width: 58, height: 58)
                        Text(entry.level.uppercased())
                            .font(.caption.bold())
                            .foregroundStyle(
                                current ? HSKColors.cinnabarDark : HSKColors.jade
                            )
                    }

                    VStack(alignment: .leading, spacing: 6) {
                        HStack(spacing: 8) {
                            Text(entry.level.uppercased())
                                .font(.headline)
                                .foregroundStyle(HSKColors.ink)

                            if current {
                                HSKGlassPill {
                                    Text("exam_current_level")
                                        .font(.caption2.weight(.bold))
                                        .foregroundStyle(HSKColors.cinnabarDark)
                                }
                            }
                        }

                        Text(
                            String(
                                format: NSLocalizedString("exam_meta", comment: ""),
                                entry.questions,
                                entry.minutes
                            )
                        )
                        .font(.caption)
                        .foregroundStyle(HSKColors.inkSecondary)

                        Text(
                            entry.sections
                                .map(sectionName)
                                .joined(separator: " · ")
                        )
                        .font(.caption2)
                        .foregroundStyle(HSKColors.inkSecondary)
                    }

                    Spacer()

                    Image(systemName: "chevron.right")
                        .font(.caption.bold())
                        .foregroundStyle(HSKColors.inkSecondary)
                }
            }
        }
        .buttonStyle(.plain)
    }

    private var exam: some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                Button {
                    model.resetToCenter()
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

                if let session = model.session {
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
                        HSKGlassCard(
                            cornerRadius: 30,
                            padding: 22,
                            tint: HSKColors.auroraBlue
                        ) {
                            VStack(spacing: 12) {
                                HSKGlassPill {
                                    Text(sectionName(question.section))
                                        .font(.caption.bold())
                                        .foregroundStyle(HSKColors.cinnabarDark)
                                }

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

                                if !question.prompt.isEmpty {
                                    Text(question.prompt)
                                        .font(.title2.bold())
                                        .foregroundStyle(HSKColors.ink)
                                        .multilineTextAlignment(.center)
                                }

                                if !question.sentence.isEmpty {
                                    Text(question.sentence)
                                        .font(.system(size: 30, weight: .semibold, design: .rounded))
                                        .foregroundStyle(HSKColors.ink)
                                        .multilineTextAlignment(.center)
                                }
                            }
                            .frame(maxWidth: .infinity)
                        }

                        ForEach(question.options.indices, id: \.self) { index in
                            examOption(question.options[index], index: index)
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, 20)
                }
            }

            VStack(spacing: 8) {
                if let session = model.session {
                    Text(
                        String(
                            format: NSLocalizedString("exam_session_meta", comment: ""),
                            session.durationMin,
                            session.passScore
                        )
                    )
                    .font(.caption)
                    .foregroundStyle(HSKColors.inkSecondary)
                }

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
                    } else if let session = model.session,
                              model.questionIndex == session.questions.count - 1 {
                        Text("exam_finish")
                    } else {
                        Text("action_continue")
                    }
                }
                .buttonStyle(HSKPrimaryButtonStyle())
                .disabled(model.selectedIndex == nil || model.phase == .completing)
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 14)
            .background(.ultraThinMaterial)
        }
    }

    private func examOption(_ text: String, index: Int) -> some View {
        let selected = model.selectedIndex == index

        return Button {
            model.select(index)
        } label: {
            HStack(spacing: 12) {
                Text(String(UnicodeScalar(65 + index)!))
                    .font(.caption.bold())
                    .foregroundStyle(
                        selected ? HSKColors.cinnabarDark : HSKColors.inkSecondary
                    )
                    .frame(width: 32, height: 32)
                    .background(
                        Circle().fill(
                            selected
                                ? HSKColors.cinnabar.opacity(0.14)
                                : Color.white.opacity(0.12)
                        )
                    )

                Text(text)
                    .font(.body.weight(.semibold))
                    .foregroundStyle(HSKColors.ink)
                    .multilineTextAlignment(.leading)

                Spacer()

                Image(systemName: selected ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(
                        selected ? HSKColors.cinnabar : HSKColors.inkSecondary.opacity(0.42)
                    )
            }
            .padding(15)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 19))
            .overlay(
                RoundedRectangle(cornerRadius: 19)
                    .stroke(
                        selected
                            ? HSKColors.cinnabar.opacity(0.62)
                            : Color.white.opacity(0.44),
                        lineWidth: selected ? 1.2 : 0.8
                    )
            )
            .shadow(
                color: selected
                    ? HSKColors.cinnabar.opacity(0.12)
                    : Color.black.opacity(0.06),
                radius: 11,
                y: 5
            )
        }
        .buttonStyle(.plain)
        .disabled(model.selectedIndex != nil)
        .scaleEffect(selected ? 1.01 : 1)
        .animation(.spring(response: 0.28, dampingFraction: 0.78), value: selected)
    }

    private var result: some View {
        VStack {
            Spacer()

            if let result = model.result {
                HSKGlassCard(
                    cornerRadius: 32,
                    padding: 24,
                    tint: result.passed ? HSKColors.jade : HSKColors.flame
                ) {
                    VStack(spacing: 15) {
                        ZStack {
                            Circle()
                                .fill(
                                    (result.passed ? HSKColors.jade : HSKColors.flame)
                                        .opacity(0.14)
                                )
                                .frame(width: 92, height: 92)

                            Text("\(result.percent)%")
                                .font(.title2.bold().monospacedDigit())
                                .foregroundStyle(
                                    result.passed ? HSKColors.jade : HSKColors.flame
                                )
                        }

                        Text(
                            result.passed
                                ? LocalizedStringKey("exam_passed")
                                : LocalizedStringKey("exam_not_passed")
                        )
                        .font(.title2.bold())
                        .foregroundStyle(HSKColors.ink)

                        Text(
                            String(
                                format: NSLocalizedString("exam_result_score", comment: ""),
                                result.score,
                                result.total
                            )
                        )
                        .foregroundStyle(HSKColors.inkSecondary)

                        VStack(spacing: 8) {
                            ForEach(result.sectionScores.keys.sorted(), id: \.self) { section in
                                if let score = result.sectionScores[section],
                                   score.total > 0 {
                                    HStack {
                                        Text(sectionName(section))
                                            .font(.subheadline)
                                            .foregroundStyle(HSKColors.inkSecondary)
                                        Spacer()
                                        Text("\(score.score)/\(score.total)")
                                            .font(.subheadline.monospacedDigit().weight(.semibold))
                                            .foregroundStyle(HSKColors.ink)
                                    }
                                    .padding(12)
                                    .background(
                                        .ultraThinMaterial,
                                        in: RoundedRectangle(cornerRadius: 14)
                                    )
                                }
                            }
                        }

                        ForEach(result.wrongItems.prefix(3)) { item in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(item.question)
                                    .font(.subheadline.weight(.semibold))
                                    .foregroundStyle(HSKColors.ink)
                                Text("✓ \(item.correctAnswer)")
                                    .font(.caption)
                                    .foregroundStyle(HSKColors.jade)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(12)
                            .background(
                                .ultraThinMaterial,
                                in: RoundedRectangle(cornerRadius: 14)
                            )
                        }

                        Button("action_done") {
                            model.resetToCenter()
                        }
                        .buttonStyle(HSKPrimaryButtonStyle())
                    }
                    .frame(maxWidth: .infinity)
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

    private func sectionName(_ section: String) -> String {
        switch section.lowercased() {
        case "listening":
            return NSLocalizedString("exam_section_listening", comment: "")
        case "writing":
            return NSLocalizedString("exam_section_writing", comment: "")
        default:
            return NSLocalizedString("exam_section_reading", comment: "")
        }
    }
}
