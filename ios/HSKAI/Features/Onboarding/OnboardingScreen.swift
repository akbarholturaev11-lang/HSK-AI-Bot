import SwiftUI

struct OnboardingScreen: View {
    @ObservedObject var model: AppModel
    let account: LinkedAccount

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
            HSKColors.paper.ignoresSafeArea()
            VStack(spacing: 0) {
                if model.onboarding.step > 0 {
                    topBar
                }

                ScrollView {
                    content
                        .frame(maxWidth: 520)
                        .padding(.horizontal, 24)
                        .padding(.top, model.onboarding.step == 0 ? 42 : 24)
                        .padding(.bottom, 24)
                }

                footer
            }
        }
    }

    @ViewBuilder
    private var content: some View {
        switch model.onboarding.step {
        case 0:
            VStack(spacing: 20) {
                Text("你好")
                    .font(.system(size: 68, weight: .bold, design: .rounded))
                    .foregroundStyle(HSKColors.cinnabar)

                Text("onboarding_hello")
                    .font(.title2.bold())
                    .foregroundStyle(HSKColors.ink)
                    .multilineTextAlignment(.center)

                Text("onboarding_intro")
                    .font(.body)
                    .foregroundStyle(HSKColors.inkSecondary)
                    .multilineTextAlignment(.center)
                    .lineSpacing(5)
            }
            .padding(.top, 54)

        case 1:
            choiceHeader(
                title: "onboarding_ask_level",
                subtitle: "onboarding_level_hint"
            )

            VStack(spacing: 11) {
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
            choiceHeader(
                title: "onboarding_ask_goal",
                subtitle: "onboarding_goal_hint"
            )

            VStack(spacing: 11) {
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
        HStack(spacing: 14) {
            Button {
                model.onboardingBack()
            } label: {
                Image(systemName: "chevron.left")
                    .font(.headline)
                    .foregroundStyle(HSKColors.inkSecondary)
                    .frame(width: 44, height: 44)
            }

            GeometryReader { proxy in
                ZStack(alignment: .leading) {
                    Capsule().fill(HSKColors.divider)
                    Capsule()
                        .fill(HSKColors.cinnabar)
                        .frame(
                            width: proxy.size.width *
                                CGFloat(model.onboarding.step) / 2
                        )
                }
            }
            .frame(height: 8)

            Text("\(model.onboarding.step) / 2")
                .font(.caption.weight(.semibold))
                .foregroundStyle(HSKColors.inkSecondary)
        }
        .padding(.horizontal, 18)
        .padding(.top, 8)
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
                    ProgressView()
                        .tint(.white)
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
        .padding(.horizontal, 24)
        .padding(.vertical, 16)
        .background(HSKColors.paper)
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
                Image(systemName: systemImage)
                    .font(.title3)
                    .foregroundStyle(selected ? HSKColors.cinnabar : HSKColors.inkSecondary)
                    .frame(width: 34)

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
                    .foregroundStyle(selected ? HSKColors.cinnabar : HSKColors.divider)
            }
            .padding(16)
            .frame(maxWidth: .infinity)
            .background(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .fill(selected ? HSKColors.cinnabarSoft : HSKColors.paperRaised)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .stroke(
                        selected ? HSKColors.cinnabar : HSKColors.divider,
                        lineWidth: selected ? 1.5 : 1
                    )
            )
        }
        .buttonStyle(.plain)
    }
}
