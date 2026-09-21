import SwiftUI

struct ProfileScreen: View {
    let account: LinkedAccount
    @ObservedObject var courseModel: CourseViewModel
    @ObservedObject var subscriptionModel: SubscriptionViewModel
    let onLogout: () -> Void

    var body: some View {
        NavigationStack {
            ZStack {
                HSKGlassBackdrop()
                ScrollView(showsIndicators: false) {
                    VStack(spacing: 14) {
                        HSKGlassCard(cornerRadius: 32, padding: 24, tint: HSKColors.auroraBlue) {
                            VStack(spacing: 12) {
                                Circle()
                                    .fill(.ultraThinMaterial)
                                    .frame(width: 86, height: 86)
                                    .overlay(
                                        Text(String(account.displayName.prefix(1)).uppercased())
                                            .font(.system(size: 34, weight: .bold))
                                            .foregroundStyle(HSKColors.cinnabarDark)
                                    )
                                    .overlay(Circle().stroke(Color.white.opacity(0.58), lineWidth: 1))
                                Text(account.displayName)
                                    .font(.title2.bold())
                                    .foregroundStyle(HSKColors.ink)
                                HStack(spacing: 8) {
                                    pill(account.level.uppercased())
                                    pill(account.isPaid ? "profile_pro" : "profile_free")
                                }
                            }
                            .frame(maxWidth: .infinity)
                        }

                        if let progress = courseModel.map?.progress {
                            HSKGlassCard(cornerRadius: 24, padding: 18, tint: HSKColors.auroraMint) {
                                VStack(spacing: 14) {
                                    row("bolt.fill", "profile_xp", "\(progress.xp)")
                                    Divider().opacity(0.35)
                                    row("flame.fill", "profile_streak", "\(progress.streak)")
                                    Divider().opacity(0.35)
                                    row("checkmark.seal.fill", "profile_lessons", "\(progress.completed)")
                                    Divider().opacity(0.35)
                                    row("trophy.fill", "profile_league", progress.league.capitalized)
                                }
                            }
                        }

                        HSKGlassCard(cornerRadius: 24, padding: 18, tint: HSKColors.auroraBlue) {
                            VStack(alignment: .leading, spacing: 12) {
                                Label("subscription_title", systemImage: "sparkles")
                                    .font(.headline)
                                    .foregroundStyle(HSKColors.ink)
                                if subscriptionModel.isLoading && subscriptionModel.overview == nil {
                                    ProgressView().tint(HSKColors.cinnabar)
                                } else {
                                    Text(subscriptionModel.overview?.status ?? account.accessState)
                                        .font(.title3.bold())
                                        .foregroundStyle(HSKColors.cinnabarDark)
                                    if subscriptionModel.trial?.available == true && subscriptionModel.trial?.active != true {
                                        Button("subscription_start_trial") {
                                            Task { await subscriptionModel.startTrial() }
                                        }
                                        .buttonStyle(HSKGlassSecondaryButtonStyle())
                                    }
                                    if let errorKey = subscriptionModel.errorKey {
                                        Text(LocalizedStringKey(errorKey))
                                            .font(.footnote)
                                            .foregroundStyle(HSKColors.flame)
                                    }
                                }
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                        }

                        HSKGlassCard(cornerRadius: 24, padding: 18) {
                            VStack(spacing: 14) {
                                row("globe", "profile_language", account.language.uppercased())
                                Divider().opacity(0.35)
                                row("graduationcap.fill", "profile_level", account.level.uppercased())
                                Divider().opacity(0.35)
                                row("checkmark.shield.fill", "profile_access", account.accessState)
                            }
                        }

                        Button(role: .destructive, action: onLogout) {
                            Label("logout", systemImage: "rectangle.portrait.and.arrow.right")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(HSKGlassSecondaryButtonStyle())
                    }
                    .padding(16)
                    .padding(.bottom, 28)
                }
            }
            .navigationTitle("tab_profile")
            .navigationBarTitleDisplayMode(.inline)
        }
        .task { if subscriptionModel.overview == nil { await subscriptionModel.load() } }
    }

    private func pill(_ key: String) -> some View {
        HSKGlassPill {
            Text(LocalizedStringKey(key))
                .font(.caption.bold())
                .foregroundStyle(HSKColors.inkSecondary)
        }
    }

    private func row(_ icon: String, _ title: LocalizedStringKey, _ value: String) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundStyle(HSKColors.cinnabarDark)
                .frame(width: 24)
            Text(title).foregroundStyle(HSKColors.ink)
            Spacer()
            Text(value).font(.subheadline.weight(.semibold)).foregroundStyle(HSKColors.inkSecondary)
        }
    }
}
