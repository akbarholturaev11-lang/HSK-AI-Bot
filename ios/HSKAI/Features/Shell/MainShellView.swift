import SwiftUI

struct MainShellView: View {
    let account: LinkedAccount
    let onLogout: () -> Void

    var body: some View {
        TabView {
            ShellPlaceholder(
                titleKey: "tab_course",
                systemImage: "map.fill"
            )
            .tabItem { Label("tab_course", systemImage: "map.fill") }

            ShellPlaceholder(
                titleKey: "tab_practice",
                systemImage: "brain.head.profile"
            )
            .tabItem { Label("tab_practice", systemImage: "brain.head.profile") }

            ShellPlaceholder(
                titleKey: "tab_dictionary",
                systemImage: "character.book.closed.fill"
            )
            .tabItem { Label("tab_dictionary", systemImage: "character.book.closed.fill") }

            ShellPlaceholder(
                titleKey: "tab_rating",
                systemImage: "trophy.fill"
            )
            .tabItem { Label("tab_rating", systemImage: "trophy.fill") }

            ProfileShellPlaceholder(account: account, onLogout: onLogout)
                .tabItem { Label("tab_profile", systemImage: "person.crop.circle.fill") }
        }
        .tint(HSKColors.cinnabar)
    }
}

private struct ShellPlaceholder: View {
    let titleKey: LocalizedStringKey
    let systemImage: String

    var body: some View {
        NavigationStack {
            ZStack {
                HSKColors.paper.ignoresSafeArea()
                VStack(spacing: 12) {
                    Image(systemName: systemImage)
                        .font(.system(size: 40))
                        .foregroundStyle(HSKColors.cinnabar)
                    Text(titleKey)
                        .font(.title2.bold())
                        .foregroundStyle(HSKColors.ink)
                }
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
                HSKColors.paper.ignoresSafeArea()
                VStack(spacing: 12) {
                    Image(systemName: "person.crop.circle.fill")
                        .font(.system(size: 48))
                        .foregroundStyle(HSKColors.cinnabar)
                    Text(account.displayName)
                        .font(.title2.bold())
                        .foregroundStyle(HSKColors.ink)
                    Text(account.level.uppercased())
                        .font(.subheadline)
                        .foregroundStyle(HSKColors.inkSecondary)
                    Button("profile_logout", action: onLogout)
                        .padding(.top, 10)
                        .foregroundStyle(HSKColors.cinnabarDark)
                }
                .padding(24)
            }
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}
