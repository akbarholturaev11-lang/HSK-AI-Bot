import SwiftUI
import UIKit

struct LinkScreen: View {
    @ObservedObject var model: AppModel
    @Environment(\.openURL) private var openURL
    @State private var appeared = false

    var body: some View {
        ZStack {
            HSKGlassBackdrop()

            ScrollView(showsIndicators: false) {
                VStack(spacing: 0) {
                    Spacer(minLength: 52)

                    HSKGlassPill {
                        HStack(spacing: 8) {
                            Image(systemName: "sparkles")
                                .font(.caption.weight(.bold))
                            Text("HSK AI")
                                .font(.subheadline.weight(.semibold))
                        }
                        .foregroundStyle(HSKColors.cinnabarDark)
                    }

                    Text("auth_welcome_title")
                        .font(.system(size: 34, weight: .bold, design: .rounded))
                        .foregroundStyle(HSKColors.ink)
                        .multilineTextAlignment(.center)
                        .padding(.top, 20)

                    Text("auth_single_subtitle")
                        .font(.body)
                        .foregroundStyle(HSKColors.inkSecondary)
                        .multilineTextAlignment(.center)
                        .lineSpacing(4)
                        .padding(.top, 10)
                        .padding(.horizontal, 8)

                    authCard
                        .padding(.top, 30)

                    Text("link_security_note")
                        .font(.footnote)
                        .foregroundStyle(HSKColors.inkSecondary)
                        .multilineTextAlignment(.center)
                        .padding(.top, 18)
                        .padding(.horizontal, 24)

                    Spacer(minLength: 34)
                }
                .padding(.horizontal, 20)
                .opacity(appeared ? 1 : 0)
                .offset(y: appeared ? 0 : 18)
            }
        }
        .onAppear {
            withAnimation(.spring(response: 0.55, dampingFraction: 0.84)) {
                appeared = true
            }
        }
    }

    @ViewBuilder
    private var authCard: some View {
        HSKGlassCard(cornerRadius: 30, padding: 22, tint: HSKColors.cinnabar) {
            VStack(spacing: 18) {
                if model.link.isRequesting {
                    VStack(spacing: 14) {
                        ProgressView()
                            .tint(HSKColors.cinnabar)
                            .controlSize(.large)
                        Text("link_waiting")
                            .font(.subheadline)
                            .foregroundStyle(HSKColors.inkSecondary)
                    }
                    .frame(minHeight: 170)
                } else if model.link.displayCode.isEmpty || model.link.isExpired {
                    Image(systemName: model.link.isExpired ? "arrow.clockwise.circle.fill" : "paperplane.circle.fill")
                        .font(.system(size: 44))
                        .symbolRenderingMode(.hierarchical)
                        .foregroundStyle(HSKColors.cinnabar)

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
        }
    }

    private var codeBlock: some View {
        VStack(spacing: 15) {
            HStack {
                Text("link_code_label")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(HSKColors.inkSecondary)
                Spacer()
                if model.link.isWaitingForApproval {
                    ProgressView()
                        .tint(HSKColors.cinnabar)
                        .scaleEffect(0.84)
                }
            }

            Text(model.link.displayCode)
                .font(.system(size: 31, weight: .bold, design: .monospaced))
                .tracking(3)
                .foregroundStyle(HSKColors.ink)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 18)
                .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 18, style: .continuous)
                        .stroke(
                            LinearGradient(
                                colors: [
                                    Color.white.opacity(0.76),
                                    HSKColors.cinnabar.opacity(0.28),
                                ],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 1
                        )
                )
                .shadow(color: HSKColors.cinnabar.opacity(0.10), radius: 14, y: 7)
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
            .padding(.top, 2)

            Button("auth_register") {
                if let url = model.link.botDeepLink {
                    openURL(url)
                }
            }
            .buttonStyle(HSKGlassSecondaryButtonStyle())

            Button {
                UIPasteboard.general.string = model.link.displayCode
            } label: {
                Label("copy_code", systemImage: "doc.on.doc")
                    .font(.subheadline.weight(.semibold))
            }
            .foregroundStyle(HSKColors.cinnabarDark)
            .frame(minHeight: 42)

            if model.link.isWaitingForApproval {
                HStack(spacing: 8) {
                    Image(systemName: "lock.shield.fill")
                        .foregroundStyle(HSKColors.jade)
                    Text("link_waiting")
                        .font(.footnote.weight(.medium))
                        .foregroundStyle(HSKColors.inkSecondary)
                    Spacer()
                    Text(
                        String(
                            format: NSLocalizedString("link_expires_in", comment: ""),
                            Self.formatRemaining(model.link.secondsRemaining)
                        )
                    )
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(HSKColors.inkSecondary)
                }
                .padding(12)
                .background(.ultraThinMaterial, in: Capsule())
                .transition(.opacity.combined(with: .scale(scale: 0.97)))
            }
        }
        .animation(.spring(response: 0.35, dampingFraction: 0.86), value: model.link.isWaitingForApproval)
    }

    static func formatRemaining(_ totalSeconds: Int) -> String {
        let safe = max(0, totalSeconds)
        return String(format: "%d:%02d", safe / 60, safe % 60)
    }
}
