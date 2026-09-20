import SwiftUI

struct OnboardingScreen: View {
    @ObservedObject var model: AppModel
    let account: LinkedAccount
    @State private var appeared = false

    private let levelOptions = [
        ("beginner", "onboarding_level_beginner", "onboarding_level_beginner_sub"),
        ("hsk1", "HSK 1", "onboarding_level_hsk1_sub"),
        ("hsk2", "HSK 2", "onboarding_level_hsk2_sub"),
        ("hsk3", "HSK 3", "onboarding_level_hsk3_sub"),
        ("hsk4", "HSK 4", "onboarding_level_hsk4_sub"),
    ]

    private let goalOptions = [
        ("hsk_exam", "onboarding_goal_hsk", "checkmark.seal"),
        ("daily_communication", "onboarding_goal_daily", "bubble.left.and.bubble.right"),
        ("travel", "onboarding_goal_travel", "airplane"),
        ("work_china", "onboarding_goal_work", "briefcase"),
        ("study_china", "onboarding_goal_study", "graduationcap"),
    ]

    var body: some View {
        ZStack {
            HSKGlassBackdrop()

            VStack(spacing: 0) {
                if model.onboarding.step > 0 {
                    topBar
                }

                ScrollView(showsIndicators: false) {
                    content
                        .frame(maxWidth: 560)
                        .padding(.horizontal, 20)
                        .padding(.top, model.onboarding.step == 0 ? 34 : 22)
                        .padding(.bottom, 30)
                        .id(model.onboarding.step)
                        .transition(.asymmetric(
                            insertion: .move(edge: .trailing).combined(with: .opacity),
                            removal: .move(edge: .leading).combined(with: .opacity)
                        ))
                }

                footer
            }
        }
        .animation(.spring(response: 0.42, dampingFraction: 0.86), value: model.onboarding.step)
        .onAppear {
            withAnimation(.easeOut(duration: 0.4)) { appeared = true }
        }
    }

    @ViewBuilder
    private var content: some View {
        switch model.onboarding.step {
        case 0:
            VStack(spacing: 18) {
                ZStack {
                    Circle()
                        .fill(.ultraThinMaterial)
                        .frame(width: 132, height: 132)
                        .overlay(Circle().stroke(Color.white.opacity(0.58), lineWidth: 1))
                        .shadow(color: HSKColors.cinnabar.opacity(0.16), radius: 24, y: 10)

                    Text("你好")
                        .font(.system(size: 54, weight: .bold, design: .rounded))
                        .foregroundStyle(
                            LinearGradient(
                                colors: [HSKColors.cinnabar, HSKColors.cinnabarDark],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                }
                .scaleEffect(appeared ? 1 : 0.90)

                Text("onboarding_hello")
                    .font(.title2.bold())
                    .foregroundStyle(HSKColors.ink)
                    .multilineTextAlignment(.center)

                Text("onboarding_intro")
                    .font(.body)
                    .foregroundStyle(HSKColors.inkSecondary)
                    .multilineTextAlignment(.center)
                    .lineSpacing(5)
                    .padding(.horizontal, 12)

                HSKGlassPill {
                    Label("HSK AI", systemImage: "sparkles")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(HSKColors.cinnabarDark)
                }
                .padding(.top, 4)
            }
            .padding(.top, 46)

        case 1:
            choiceHeader(title: "onboarding_ask_level", subtitle: "onboarding_level_hint")

            VStack(spacing: 12) {
                ForEach(levelOptions, id: \.0) { option in
                    SelectionCard(
                        title: LocalizedStringKey(option.1),
                        subtitle: LocalizedStringKey(option.2),
                        selected: model.onboarding.selectedLevel == option.0,
                        systemImage: option.0 == "beginner" ? "sparkles" : "character.book.closed"
                    ) {
                        model.selectOnboardingLevel(option.0)
                    }
                }
            }
            .padding(.top, 20)

        default:
            choiceHeader(title: "onboarding_ask_goal", subtitle: "onboarding_goal_hint")

            VStack(spacing: 12) {
                ForEach(goalOptions, id: \.0) { option in
                    SelectionCard(
                        title: LocalizedStringKey(option.1),
                        subtitle: nil,
                        selected: model.onboarding.selectedGoal == option.0,
                        systemImage: option.2
                    ) {
                        model.selectOnboardingGoal(option.0)
                    }
                }
            }
            .padding(.top, 20)
        }
    }

    private func choiceHeader(
        title: LocalizedStringKey,
        subtitle: LocalizedStringKey
    ) -> some View {
        VStack(spacing: 8) {
            Text(title)
                .font(.title2.bold())
                .foregroundStyle(HSKColors.ink)
                .multilineTextAlignment(.center)
            Text(subtitle)
                .font(.subheadline)
                .foregroundStyle(HSKColors.inkSecondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
    }

    private var topBar: some View {
        HStack(spacing: 13) {
            Button {
                model.onboardingBack()
            } label: {
                Image(systemName: "chevron.left")
                    .font(.headline)
                    .foregroundStyle(HSKColors.ink)
            }
            .buttonStyle(HSKGlassIconButtonStyle())

            GeometryReader { proxy in
                ZStack(alignment: .leading) {
                    Capsule().fill(.ultraThinMaterial)
                    Capsule()
                        .fill(
                            LinearGradient(
                                colors: [HSKColors.cinnabar, HSKColors.cinnabarDark],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(
                            width: proxy.size.width *
                                CGFloat(model.onboarding.step) / 2
                        )
                }
                .overlay(Capsule().stroke(Color.white.opacity(0.42), lineWidth: 0.7))
            }
            .frame(height: 9)

            HSKGlassPill {
                Text("\(model.onboarding.step) / 2")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(HSKColors.inkSecondary)
            }
        }
        .padding(.horizontal, 18)
        .padding(.top, 10)
        .padding(.bottom, 4)
    }

    private var footer: some View {
        VStack(spacing: 10) {
            if let errorKey = model.onboarding.errorKey {
                Text(LocalizedStringKey(errorKey))
                    .font(.footnote)
                    .foregroundStyle(HSKColors.flame)
                    .multilineTextAlignment(.center)
            }

            Button {
                Task { await model.onboardingNext(account: account) }
            } label: {
                if model.onboarding.isSubmitting {
                    ProgressView().tint(.white)
                } else {
                    Text(
                        model.onboarding.step == 0
                            ? "onboarding_start"
                            : model.onboarding.step == 2
                                ? "onboarding_first_lesson"
                                : "action_continue"
                    )
                }
            }
            .buttonStyle(HSKPrimaryButtonStyle())
            .disabled(model.onboarding.isSubmitting)
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
}

private struct SelectionCard: View {
    let title: LocalizedStringKey
    let subtitle: LocalizedStringKey?
    let selected: Bool
    let systemImage: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 14) {
                ZStack {
                    Circle()
                        .fill(selected ? HSKColors.cinnabar.opacity(0.16) : Color.white.opacity(0.14))
                        .frame(width: 42, height: 42)
                    Image(systemName: systemImage)
                        .font(.headline)
                        .foregroundStyle(selected ? HSKColors.cinnabarDark : HSKColors.inkSecondary)
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text(title)
                        .font(.headline)
                        .foregroundStyle(HSKColors.ink)
                    if let subtitle {
                        Text(subtitle)
                            .font(.caption)
                            .foregroundStyle(HSKColors.inkSecondary)
                            .multilineTextAlignment(.leading)
                    }
                }

                Spacer()

                Image(systemName: selected ? "checkmark.circle.fill" : "circle")
                    .font(.title3)
                    .foregroundStyle(selected ? HSKColors.cinnabar : HSKColors.inkSecondary.opacity(0.42))
            }
            .padding(15)
            .frame(maxWidth: .infinity)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .fill(selected ? HSKColors.cinnabar.opacity(0.08) : Color.clear)
            }
            .overlay {
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .stroke(
                        selected
                            ? HSKColors.cinnabar.opacity(0.58)
                            : Color.white.opacity(0.48),
                        lineWidth: selected ? 1.2 : 0.8
                    )
            }
            .shadow(
                color: selected
                    ? HSKColors.cinnabar.opacity(0.12)
                    : Color.black.opacity(0.07),
                radius: selected ? 16 : 10,
                y: 6
            )
        }
        .buttonStyle(.plain)
        .scaleEffect(selected ? 1.01 : 1)
        .animation(.spring(response: 0.28, dampingFraction: 0.78), value: selected)
    }
}
