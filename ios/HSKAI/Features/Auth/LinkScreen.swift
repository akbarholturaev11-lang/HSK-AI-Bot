import SwiftUI
import UIKit

struct LinkScreen: View {
    @ObservedObject var model: AppModel
    @Environment(\.openURL) private var openURL

    var body: some View {
        ZStack {
            HSKColors.paper.ignoresSafeArea()

            ScrollView {
                VStack(spacing: 0) {
                    Spacer(minLength: 34)

                    Text("HSK AI")
                        .font(.headline)
                        .foregroundStyle(HSKColors.cinnabarDark)

                    Text("auth_welcome_title")
                        .font(.system(size: 34, weight: .bold, design: .rounded))
                        .foregroundStyle(HSKColors.ink)
                        .multilineTextAlignment(.center)
                        .padding(.top, 12)

                    Text("auth_single_subtitle")
                        .font(.body)
                        .foregroundStyle(HSKColors.inkSecondary)
                        .multilineTextAlignment(.center)
                        .padding(.top, 9)

                    authCard
                        .padding(.top, 28)

                    Spacer(minLength: 30)
                }
                .padding(.horizontal, 24)
            }
        }
    }

    @ViewBuilder
    private var authCard: some View {
        VStack(spacing: 18) {
            if model.link.isRequesting {
                ProgressView()
                    .tint(HSKColors.cinnabar)
                    .controlSize(.large)
                    .frame(minHeight: 180)
            } else if model.link.displayCode.isEmpty || model.link.isExpired {
                if let errorKey = model.link.errorKey {
                    Text(LocalizedStringKey(errorKey))
                        .font(.subheadline)
                        .foregroundStyle(HSKColors.flame)
                        .multilineTextAlignment(.center)
                } else if model.link.isExpired {
                    Text("link_expired")
                        .font(.subheadline)
                        .foregroundStyle(HSKColors.flame)
                        .multilineTextAlignment(.center)
                }

                Button(
                    model.link.isExpired || model.link.errorKey != nil
                        ? LocalizedStringKey("link_new_code")
                        : LocalizedStringKey("action_continue")
                ) {
                    Task { await model.requestLink() }
                }
                .buttonStyle(HSKPrimaryButtonStyle())
            } else {
                codeBlock
            }
        }
        .padding(22)
        .frame(maxWidth: .infinity)
        .background(
            RoundedRectangle(cornerRadius: 28, style: .continuous)
                .fill(HSKColors.paperRaised)
                .shadow(color: Color.black.opacity(0.08), radius: 20, y: 8)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 28, style: .continuous)
                .stroke(HSKColors.divider.opacity(0.7), lineWidth: 1)
        )
    }

    private var codeBlock: some View {
        VStack(spacing: 14) {
            Text("link_code_label")
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(HSKColors.inkSecondary)

            Text(model.link.displayCode)
                .font(.system(size: 30, weight: .bold, design: .monospaced))
                .tracking(3)
                .foregroundStyle(HSKColors.cinnabarDark)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 17)
                .background(
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .fill(HSKColors.cinnabarSoft)
                )
                .textSelection(.enabled)

            Text("link_code_instruction")
                .font(.footnote)
                .foregroundStyle(HSKColors.inkSecondary)
                .multilineTextAlignment(.center)

            Button("auth_login") {
                if let url = model.link.botDeepLink {
                    openURL(url)
                }
            }
            .buttonStyle(HSKPrimaryButtonStyle())
            .padding(.top, 5)

            Button("auth_register") {
                if let url = model.link.botDeepLink {
                    openURL(url)
                }
            }
            .font(.headline)
            .foregroundStyle(HSKColors.cinnabarDark)
            .frame(minHeight: 44)

            Button {
                UIPasteboard.general.string = model.link.displayCode
            } label: {
                Label("copy_code", systemImage: "doc.on.doc")
                    .font(.subheadline.weight(.semibold))
            }
            .foregroundStyle(HSKColors.cinnabarDark)
            .frame(minHeight: 44)

            if model.link.isWaitingForApproval {
                Divider()
                    .overlay(HSKColors.divider)

                HStack(spacing: 10) {
                    ProgressView()
                        .tint(HSKColors.cinnabar)

                    Text("link_waiting")
                        .font(.subheadline)
                        .foregroundStyle(HSKColors.inkSecondary)
                }

                Text(
                    String(
                        format: NSLocalizedString("link_expires_in", comment: ""),
                        Self.formatRemaining(model.link.secondsRemaining)
                    )
                )
                .font(.footnote)
                .foregroundStyle(HSKColors.inkSecondary)
            }

            Text("link_security_note")
                .font(.footnote)
                .foregroundStyle(HSKColors.inkSecondary)
                .multilineTextAlignment(.center)
                .padding(.top, 2)
        }
    }

    static func formatRemaining(_ totalSeconds: Int) -> String {
        let safe = max(0, totalSeconds)
        return String(format: "%d:%02d", safe / 60, safe % 60)
    }
}
