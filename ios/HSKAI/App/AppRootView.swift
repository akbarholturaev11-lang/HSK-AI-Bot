import SwiftUI

struct AppRootView: View {
    @StateObject private var model: AppModel

    init(environment: AppEnvironment) {
        _model = StateObject(wrappedValue: AppModel(environment: environment))
    }

    var body: some View {
        Group {
            switch model.phase {
            case .launching:
                LaunchView()
            case .signedOut:
                LinkScreen(model: model)
            case .onboarding(let account):
                OnboardingScreen(model: model, account: account)
            case .main(let account):
                MainShellView(
                    account: account,
                    courseModel: model.courseViewModel,
                    dictionaryModel: model.dictionaryViewModel,
                    practiceModel: model.practiceViewModel,
                    mistakesModel: model.mistakesViewModel,
                    examModel: model.examViewModel,
                    wordDrillModel: model.wordDrillViewModel,
                    pronunciationDrillModel: model.pronunciationDrillViewModel,
                    ratingModel: model.ratingViewModel,
                    subscriptionModel: model.subscriptionViewModel,
                    challengeModel: model.challengeViewModel,
                    reminderManager: model.reminderManager
                ) {
                    Task { await model.logout() }
                }
            case .bootstrapFailed:
                BootstrapFailureView {
                    Task { await model.retryBootstrap() }
                }
            }
        }
        .task {
            await model.restoreSession()
        }
    }
}

private struct LaunchView: View {
    @State private var pulse = false

    var body: some View {
        ZStack {
            HSKGlassBackdrop()

            VStack(spacing: 16) {
                ZStack {
                    Circle()
                        .fill(.ultraThinMaterial)
                        .frame(width: 100, height: 100)
                        .overlay(Circle().stroke(Color.white.opacity(0.54), lineWidth: 1))
                        .shadow(color: HSKColors.cinnabar.opacity(0.18), radius: 24, y: 10)

                    Text("HSK")
                        .font(.system(size: 26, weight: .bold, design: .rounded))
                        .foregroundStyle(HSKColors.cinnabarDark)
                }
                .scaleEffect(pulse ? 1.03 : 0.97)
                .shadow(
                    color: HSKColors.cinnabar.opacity(pulse ? 0.22 : 0.10),
                    radius: pulse ? 22 : 10
                )

                Text("HSK AI")
                    .font(.title2.bold())
                    .foregroundStyle(HSKColors.ink)

                ProgressView()
                    .tint(HSKColors.cinnabar)
            }
        }
        .onAppear {
            withAnimation(.easeInOut(duration: 1.15).repeatForever(autoreverses: true)) {
                pulse = true
            }
        }
    }
}

private struct BootstrapFailureView: View {
    let retry: () -> Void

    var body: some View {
        ZStack {
            HSKGlassBackdrop()

            HSKGlassCard(cornerRadius: 28, padding: 22, tint: HSKColors.flame) {
                VStack(spacing: 18) {
                    Image(systemName: "wifi.exclamationmark")
                        .font(.system(size: 36))
                        .foregroundStyle(HSKColors.flame)

                    Text("error_network")
                        .multilineTextAlignment(.center)
                        .foregroundStyle(HSKColors.inkSecondary)

                    Button("action_retry", action: retry)
                        .buttonStyle(HSKPrimaryButtonStyle())
                }
            }
            .padding(24)
        }
    }
}

#Preview {
    AppRootView(environment: .production)
}
