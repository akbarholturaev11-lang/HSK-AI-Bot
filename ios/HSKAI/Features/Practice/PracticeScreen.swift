import SwiftUI

struct PracticeScreen: View {
    @ObservedObject var model: PracticeViewModel
    @ObservedObject var mistakesModel: MistakesViewModel
    @ObservedObject var examModel: ExamViewModel
    @ObservedObject var wordDrillModel: WordDrillViewModel
    @ObservedObject var pronunciationDrillModel: PronunciationDrillViewModel
    @ObservedObject var voiceModel: VoiceViewModel
    let launchRequest: IOSPracticeLaunch?
    let onLaunchRequestConsumed: () -> Void
    let account: LinkedAccount

    @State private var showingMistakes = false
    @State private var showingExams = false
    @State private var showingRecognition = false
    @State private var showingPronunciation = false
    @State private var showingVoice = false

    var body: some View {
        NavigationStack {
            ZStack {
                HSKGlassBackdrop()

                switch model.phase {
                case .home:
                    home
                case .loading:
                    ProgressView()
                        .tint(HSKColors.cinnabar)
                        .controlSize(.large)
                case .session, .completing:
                    session
                case .result:
                    result
                }
            }
            .navigationTitle("tab_practice")
            .navigationBarTitleDisplayMode(.inline)
        }
        .fullScreenCover(isPresented: $showingMistakes) {
            MistakesScreen(
                model: mistakesModel,
                onClose: { showingMistakes = false }
            )
        }
        .fullScreenCover(isPresented: $showingExams) {
            ExamScreen(
                model: examModel,
                account: account,
                onClose: { showingExams = false }
            )
        }
        .fullScreenCover(isPresented: $showingRecognition, onDismiss: {
            wordDrillModel.reset()
        }) {
            WordDrillScreen(
                model: wordDrillModel,
                account: account,
                onClose: { showingRecognition = false }
            )
        }
        .onChange(of: launchRequest) { _, request in
            guard let request else { return }
            switch request {
            case .mistakes: showingMistakes = true
            case .exams: showingExams = true
            case .recognition: showingRecognition = true
            case .pronunciation: showingPronunciation = true
            case .voice: showingVoice = true
            }
            onLaunchRequestConsumed()
        }
        .fullScreenCover(isPresented: $showingVoice, onDismiss: { voiceModel.reset() }) { VoiceScreen(model: voiceModel, account: account, onClose: { showingVoice = false }) }
        .fullScreenCover(isPresented: $showingPronunciation, onDismiss: {
            pronunciationDrillModel.reset()
        }) {
            PronunciationDrillScreen(
                model: pronunciationDrillModel,
                account: account,
                onClose: { showingPronunciation = false }
            )
        }
    }

    private var home: some View {
        ScrollView(showsIndicators: false) {
            VStack(spacing: 16) {
                HSKGlassCard(cornerRadius: 30, padding: 24, tint: HSKColors.auroraBlue) {
                    VStack(spacing: 12) {
                        ZStack {
                            Circle()
                                .fill(HSKColors.auroraBlue.opacity(0.16))
                                .frame(width: 76, height: 76)
                            Image(systemName: "brain.head.profile")
                                .font(.system(size: 34, weight: .semibold))
                                .foregroundStyle(HSKColors.cinnabarDark)
                        }

                        Text("practice_title")
                            .font(.title2.bold())
                            .foregroundStyle(HSKColors.ink)

                        Text("practice_intro")
                            .font(.body)
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
                        .padding(.horizontal, 8)
                }

                Button {
                    Task {
                        await model.startPlacement(
                            level: account.level,
                            language: account.language
                        )
                    }
                } label: {
                    HSKGlassCard(cornerRadius: 24, padding: 18, tint: HSKColors.cinnabar) {
                        HStack(spacing: 14) {
                            ZStack {
                                Circle()
                                    .fill(HSKColors.cinnabar.opacity(0.14))
                                    .frame(width: 54, height: 54)
                                Text("测")
                                    .font(.title2.bold())
                                    .foregroundStyle(HSKColors.cinnabarDark)
                            }

                            VStack(alignment: .leading, spacing: 5) {
                                Text("practice_placement_title")
                                    .font(.headline)
                                    .foregroundStyle(HSKColors.ink)
                                Text("practice_placement_body")
                                    .font(.caption)
                                    .foregroundStyle(HSKColors.inkSecondary)
                                    .multilineTextAlignment(.leading)
                            }

                            Spacer()

                            Image(systemName: "chevron.right")
                                .font(.subheadline.weight(.bold))
                                .foregroundStyle(HSKColors.inkSecondary)
                        }
                    }
                }
                .buttonStyle(.plain)

                Button {
                    showingExams = true
                } label: {
                    HSKGlassCard(
                        cornerRadius: 24,
                        padding: 18,
                        tint: HSKColors.auroraMint
                    ) {
                        HStack(spacing: 14) {
                            ZStack {
                                Circle()
                                    .fill(HSKColors.jade.opacity(0.14))
                                    .frame(width: 54, height: 54)
                                Image(systemName: "checkmark.seal.fill")
                                    .font(.title3)
                                    .foregroundStyle(HSKColors.jade)
                            }

                            VStack(alignment: .leading, spacing: 5) {
                                Text("exam_center_title")
                                    .font(.headline)
                                    .foregroundStyle(HSKColors.ink)
                                Text("exam_center_row_body")
                                    .font(.caption)
                                    .foregroundStyle(HSKColors.inkSecondary)
                                    .multilineTextAlignment(.leading)
                            }

                            Spacer()

                            Image(systemName: "chevron.right")
                                .font(.caption.bold())
                                .foregroundStyle(HSKColors.inkSecondary)
                        }
                    }
                }
                .buttonStyle(.plain)

                HSKGlassCard(cornerRadius: 24, padding: 18) {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("practice_more_title")
                            .font(.headline)
                            .foregroundStyle(HSKColors.ink)

                        Button { showingVoice = true } label: {
                            HStack(spacing: 12) {
                                Image(systemName: "waveform.circle.fill").foregroundStyle(HSKColors.cinnabarDark).frame(width: 28)
                                Text("voice_title").font(.subheadline.weight(.semibold)).foregroundStyle(HSKColors.ink)
                                Spacer(); Image(systemName: "chevron.right").font(.caption.weight(.bold)).foregroundStyle(HSKColors.inkSecondary)
                            }.padding(.vertical, 7)
                        }.buttonStyle(.plain)
                        Button {
                            showingRecognition = true
                        } label: {
                            HStack(spacing: 12) {
                                Image(systemName: "eye.fill")
                                    .foregroundStyle(HSKColors.cinnabarDark)
                                    .frame(width: 28)
                                Text("practice_recognition_title")
                                    .font(.subheadline.weight(.semibold))
                                    .foregroundStyle(HSKColors.ink)
                                Spacer()
                                Image(systemName: "chevron.right")
                                    .font(.caption.weight(.bold))
                                    .foregroundStyle(HSKColors.inkSecondary)
                            }
                            .padding(.vertical, 7)
                        }
                        .buttonStyle(.plain)
                        Button {
                            showingPronunciation = true
                        } label: {
                            HStack(spacing: 12) {
                                Image(systemName: "mic.fill")
                                    .foregroundStyle(HSKColors.jade)
                                    .frame(width: 28)
                                Text("practice_pronunciation_title")
                                    .font(.subheadline.weight(.semibold))
                                    .foregroundStyle(HSKColors.ink)
                                Spacer()
                                Image(systemName: "chevron.right")
                                    .font(.caption.weight(.bold))
                                    .foregroundStyle(HSKColors.inkSecondary)
                            }
                            .padding(.vertical, 7)
                        }
                        .buttonStyle(.plain)
                        Button {
                            showingMistakes = true
                        } label: {
                            HStack(spacing: 12) {
                                Image(systemName: "exclamationmark.triangle.fill")
                                    .foregroundStyle(HSKColors.flame)
                                    .frame(width: 28)
                                Text("practice_mistakes_title")
                                    .font(.subheadline.weight(.semibold))
                                    .foregroundStyle(HSKColors.ink)
                                Spacer()
                                Image(systemName: "chevron.right")
                                    .font(.caption.weight(.bold))
                                    .foregroundStyle(HSKColors.inkSecondary)
                            }
                            .padding(.vertical, 7)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 14)
        }
    }

    private var session: some View {
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
                    questionCard(question)
                        .padding(.horizontal, 20)
                        .padding(.top, 22)
                        .padding(.bottom, 24)
                }
            }

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
                    if model.phase == .completing {
                        ProgressView().tint(.white)
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
            .overlay(alignment: .top) {
                Rectangle()
                    .fill(Color.white.opacity(0.28))
                    .frame(height: 0.7)
            }
        }
    }

    private func questionCard(_ question: IOSPracticeQuestion) -> some View {
        VStack(spacing: 16) {
            HSKGlassCard(cornerRadius: 30, padding: 22, tint: HSKColors.auroraMint) {
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

                    if !question.pinyin.isEmpty {
                        Text(question.pinyin)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(HSKColors.cinnabarDark)
                    }
                }
                .frame(maxWidth: .infinity)
            }

            VStack(spacing: 10) {
                ForEach(question.options.indices, id: \.self) { index in
                    practiceOption(
                        question.options[index],
                        index: index
                    )
                }
            }
        }
    }

    private func practiceOption(_ text: String, index: Int) -> some View {
        let selected = model.selectedIndex == index

        return Button {
            model.select(index)
        } label: {
            HStack(spacing: 12) {
                Text(String(UnicodeScalar(65 + index)!))
                    .font(.caption.weight(.bold))
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
                        selected ? HSKColors.cinnabar : HSKColors.inkSecondary.opacity(0.45)
                    )
            }
            .padding(15)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 19))
            .overlay(
                RoundedRectangle(cornerRadius: 19)
                    .fill(selected ? HSKColors.cinnabar.opacity(0.08) : Color.clear)
            )
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
                    tint: result.percent >= 70 ? HSKColors.jade : HSKColors.flame
                ) {
                    VStack(spacing: 15) {
                        ZStack {
                            Circle()
                                .fill(
                                    (result.percent >= 70 ? HSKColors.jade : HSKColors.flame)
                                        .opacity(0.14)
                                )
                                .frame(width: 90, height: 90)

                            Text("\(result.percent)%")
                                .font(.title2.bold().monospacedDigit())
                                .foregroundStyle(
                                    result.percent >= 70 ? HSKColors.jade : HSKColors.flame
                                )
                        }

                        Text("practice_result_title")
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

                        if !result.recommendation.isEmpty {
                            Text(result.recommendation)
                                .font(.subheadline)
                                .foregroundStyle(HSKColors.inkSecondary)
                                .multilineTextAlignment(.center)
                        }

                        ForEach(result.wrongItems.prefix(4)) { item in
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
                            model.reset()
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

    private func pendingRow(
        icon: String,
        title: LocalizedStringKey
    ) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundStyle(HSKColors.inkSecondary)
                .frame(width: 28)
            Text(title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(HSKColors.inkSecondary)
            Spacer()
            Text("practice_next_stage")
                .font(.caption)
                .foregroundStyle(HSKColors.inkSecondary.opacity(0.72))
        }
        .padding(.vertical, 6)
    }
}
