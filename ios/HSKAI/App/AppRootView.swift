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
            case .authenticated(let account):
                AuthenticatedPlaceholder(account: account)
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
    var body: some View {
        ZStack {
            HSKColors.paper.ignoresSafeArea()

            VStack(spacing: 14) {
                Text("HSK AI")
                    .font(.title.bold())
                    .foregroundStyle(HSKColors.ink)

                ProgressView()
                    .tint(HSKColors.cinnabar)
                    .controlSize(.regular)
            }
        }
    }
}

private struct AuthenticatedPlaceholder: View {
    let account: LinkedAccount

    var body: some View {
        ZStack {
            HSKColors.paper.ignoresSafeArea()

            VStack(spacing: 12) {
                Image(systemName: "checkmark.seal.fill")
                    .font(.system(size: 44))
                    .foregroundStyle(HSKColors.jade)

                Text("link_success")
                    .font(.title2.bold())
                    .foregroundStyle(HSKColors.ink)

                Text(account.displayName)
                    .font(.body)
                    .foregroundStyle(HSKColors.inkSecondary)
            }
            .padding(24)
        }
    }
}

private struct BootstrapFailureView: View {
    let retry: () -> Void

    var body: some View {
        ZStack {
            HSKColors.paper.ignoresSafeArea()

            VStack(spacing: 18) {
                Text("error_network")
                    .multilineTextAlignment(.center)
                    .foregroundStyle(HSKColors.inkSecondary)

                Button("action_retry", action: retry)
                    .buttonStyle(HSKPrimaryButtonStyle())
            }
            .padding(24)
        }
    }
}

#Preview {
    AppRootView(environment: .production)
}
