import SwiftUI

struct MainShellView: View {
    let account: LinkedAccount
    @ObservedObject var courseModel: CourseViewModel
    @ObservedObject var dictionaryModel: DictionaryViewModel
    @ObservedObject var practiceModel: PracticeViewModel
    @ObservedObject var mistakesModel: MistakesViewModel
    @ObservedObject var examModel: ExamViewModel
    @ObservedObject var wordDrillModel: WordDrillViewModel
    @ObservedObject var pronunciationDrillModel: PronunciationDrillViewModel
    @ObservedObject var ratingModel: RatingViewModel
    @ObservedObject var subscriptionModel: SubscriptionViewModel
    @ObservedObject var reminderManager: StudyReminderManager
    let onLogout: () -> Void
    @State private var selection: IOSDeepLinkDestination = .course

    var body: some View {
        TabView(selection: $selection) {
            CourseScreen(model: courseModel, account: account)
                .tabItem { Label("tab_course", systemImage: "map.fill") }
                .tag(IOSDeepLinkDestination.course)

            PracticeScreen(
                model: practiceModel,
                mistakesModel: mistakesModel,
                examModel: examModel,
                wordDrillModel: wordDrillModel,
                pronunciationDrillModel: pronunciationDrillModel,
                account: account
            )
                .tabItem { Label("tab_practice", systemImage: "brain.head.profile") }
                .tag(IOSDeepLinkDestination.practice)

            DictionaryScreen(model: dictionaryModel)
                .tabItem { Label("tab_dictionary", systemImage: "character.book.closed.fill") }
                .tag(IOSDeepLinkDestination.dictionary)

            RatingScreen(model: ratingModel)
                .tabItem { Label("tab_rating", systemImage: "trophy.fill") }
                .tag(IOSDeepLinkDestination.rating)

            ProfileScreen(account: account, courseModel: courseModel, subscriptionModel: subscriptionModel, reminderManager: reminderManager, onLogout: onLogout)
                .tabItem { Label("tab_profile", systemImage: "person.crop.circle.fill") }
                .tag(IOSDeepLinkDestination.profile)
        }
        .tint(HSKColors.cinnabar)
        .toolbarBackground(.ultraThinMaterial, for: .tabBar)
        .toolbarBackground(.visible, for: .tabBar)
        .onOpenURL { url in
            if let destination = IOSDeepLinkRouter.destination(for: url) {
                selection = destination
            }
        }
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
