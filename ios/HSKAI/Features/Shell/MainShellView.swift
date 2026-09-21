import SwiftUI

struct MainShellView: View {
    let account: LinkedAccount
    @ObservedObject var courseModel: CourseViewModel
    @ObservedObject var practiceModel: PracticeViewModel
    @ObservedObject var mistakesModel: MistakesViewModel
    @ObservedObject var examModel: ExamViewModel
    let onLogout: () -> Void

    var body: some View {
        TabView {
            CourseScreen(model: courseModel, account: account)
                .tabItem { Label("tab_course", systemImage: "map.fill") }

            PracticeScreen(
                model: practiceModel,
                mistakesModel: mistakesModel,
                examModel: examModel,
                account: account
            )
                .tabItem { Label("tab_practice", systemImage: "brain.head.profile") }

            ShellPlaceholder(titleKey: "tab_dictionary", systemImage: "character.book.closed.fill")
                .tabItem { Label("tab_dictionary", systemImage: "character.book.closed.fill") }

            ShellPlaceholder(titleKey: "tab_rating", systemImage: "trophy.fill")
                .tabItem { Label("tab_rating", systemImage: "trophy.fill") }

            ProfileShellPlaceholder(account: account, onLogout: onLogout)
                .tabItem { Label("tab_profile", systemImage: "person.crop.circle.fill") }
        }
        .tint(HSKColors.cinnabar)
        .toolbarBackground(.ultraThinMaterial, for: .tabBar)
        .toolbarBackground(.visible, for: .tabBar)
    }
}

private struct ShellPlaceholder: View {
    let titleKey: LocalizedStringKey
    let systemImage: String

    var body: some View {
        NavigationStack {
            ZStack {
                HSKGlassBackdrop()

                HSKGlassCard(cornerRadius: 28, padding: 28, tint: HSKColors.cinnabar) {
                    VStack(spacing: 14) {
                        ZStack {
                            Circle()
                                .fill(HSKColors.cinnabar.opacity(0.12))
                                .frame(width: 74, height: 74)
                            Image(systemName: systemImage)
                                .font(.system(size: 34, weight: .semibold))
                                .foregroundStyle(HSKColors.cinnabar)
                        }

                        Text(titleKey)
                            .font(.title2.bold())
                            .foregroundStyle(HSKColors.ink)
                    }
                }
                .padding(26)
            }
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

private struct ProfileShellPlaceholder: View {
    let account: LinkedAccount
    let onLogout: () -> Void

    var body: some View {
        NavigationStack {
            ZStack {
                HSKGlassBackdrop()

                HSKGlassCard(cornerRadius: 30, padding: 24, tint: HSKColors.cinnabar) {
                    VStack(spacing: 13) {
                        ZStack {
                            Circle()
                                .fill(.thinMaterial)
                                .frame(width: 92, height: 92)
                                .overlay(Circle().stroke(Color.white.opacity(0.54), lineWidth: 1))

                            Image(systemName: "person.crop.circle.fill")
                                .font(.system(size: 58))
                                .foregroundStyle(HSKColors.cinnabar)
                        }

                        Text(account.displayName)
                            .font(.title2.bold())
                            .foregroundStyle(HSKColors.ink)

                        HSKGlassPill {
                            Text(account.level.uppercased())
                                .font(.caption.weight(.bold))
                                .foregroundStyle(HSKColors.inkSecondary)
                        }

                        Button("profile_logout", action: onLogout)
                            .buttonStyle(HSKGlassSecondaryButtonStyle())
                            .padding(.top, 8)
                    }
                }
                .padding(24)
            }
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}
