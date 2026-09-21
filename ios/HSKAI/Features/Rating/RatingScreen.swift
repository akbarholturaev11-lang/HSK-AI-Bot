import SwiftUI

struct RatingScreen: View {
    @ObservedObject var model: RatingViewModel

    var body: some View {
        NavigationStack {
            ZStack {
                HSKGlassBackdrop()
                if let rating = model.rating {
                    ScrollView(showsIndicators: false) {
                        VStack(spacing: 14) {
                            HSKGlassCard(cornerRadius: 30, padding: 22, tint: HSKColors.auroraMint) {
                                HStack(spacing: 18) {
                                    Image(systemName: "trophy.fill")
                                        .font(.system(size: 34))
                                        .foregroundStyle(HSKColors.cinnabarDark)
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(rating.league.isEmpty ? "rating_league" : rating.league.capitalized)
                                            .font(.title2.bold())
                                            .foregroundStyle(HSKColors.ink)
                                        Text(String(format: NSLocalizedString("rating_rank_format", comment: ""), rating.rank, rating.leagueSize))
                                            .foregroundStyle(HSKColors.inkSecondary)
                                    }
                                    Spacer()
                                }
                            }

                            HStack(spacing: 10) {
                                stat("flame.fill", value: rating.weeklyXp, label: "rating_weekly_xp")
                                stat("bolt.fill", value: rating.dailyXp, label: "rating_daily_xp")
                                stat("calendar", value: rating.streak, label: "rating_streak")
                            }

                            if let referral = model.referral {
                                HSKGlassCard(cornerRadius: 24, padding: 18, tint: HSKColors.auroraBlue) {
                                    VStack(alignment: .leading, spacing: 12) {
                                        Label("referral_title", systemImage: "person.2.badge.plus")
                                            .font(.headline)
                                            .foregroundStyle(HSKColors.ink)
                                        Text(String(format: NSLocalizedString("referral_progress_format", comment: ""), referral.activated, referral.trialRequired))
                                            .font(.subheadline)
                                            .foregroundStyle(HSKColors.inkSecondary)
                                        ProgressView(value: Double(referral.activated), total: Double(max(1, referral.trialRequired)))
                                            .tint(HSKColors.jade)
                                        if !referral.link.isEmpty {
                                            ShareLink(item: referral.link) {
                                                Label("referral_share", systemImage: "square.and.arrow.up")
                                                    .frame(maxWidth: .infinity)
                                            }
                                            .buttonStyle(HSKGlassSecondaryButtonStyle())
                                        }
                                    }
                                }
                            }

                            VStack(spacing: 10) {
                                ForEach(rating.leaderboard) { entry in
                                    HSKGlassCard(
                                        cornerRadius: 20,
                                        padding: 14,
                                        tint: entry.isCurrentUser ? HSKColors.auroraBlue : nil
                                    ) {
                                        HStack(spacing: 12) {
                                            Text("#\(entry.rank)")
                                                .font(.headline.monospacedDigit())
                                                .foregroundStyle(HSKColors.cinnabarDark)
                                                .frame(width: 42, alignment: .leading)
                                            Circle()
                                                .fill(.ultraThinMaterial)
                                                .frame(width: 40, height: 40)
                                                .overlay(
                                                    Text(String(entry.name.prefix(1)).uppercased())
                                                        .font(.headline)
                                                        .foregroundStyle(HSKColors.ink)
                                                )
                                            VStack(alignment: .leading, spacing: 3) {
                                                Text(entry.name.isEmpty ? entry.username : entry.name)
                                                    .font(.headline)
                                                    .foregroundStyle(HSKColors.ink)
                                                Text(entry.courseLevel.uppercased())
                                                    .font(.caption)
                                                    .foregroundStyle(HSKColors.inkSecondary)
                                            }
                                            Spacer()
                                            Text("\(entry.xp) XP")
                                                .font(.subheadline.monospacedDigit().weight(.bold))
                                                .foregroundStyle(HSKColors.ink)
                                        }
                                    }
                                }
                            }
                        }
                        .padding(16)
                        .padding(.bottom, 28)
                    }
                    .refreshable { await model.load() }
                } else if model.isLoading {
                    ProgressView().tint(HSKColors.cinnabar).controlSize(.large)
                } else {
                    HSKGlassCard(cornerRadius: 26, padding: 22, tint: HSKColors.flame) {
                        VStack(spacing: 12) {
                            Text("rating_load_error").foregroundStyle(HSKColors.inkSecondary)
                            Button("action_retry") { Task { await model.load() } }
                                .buttonStyle(HSKGlassSecondaryButtonStyle())
                        }
                    }
                    .padding(24)
                }
            }
            .navigationTitle("tab_rating")
            .navigationBarTitleDisplayMode(.inline)
        }
        .task { if model.rating == nil { await model.load() } }
    }

    private func stat(_ icon: String, value: Int, label: LocalizedStringKey) -> some View {
        HSKGlassCard(cornerRadius: 20, padding: 12) {
            VStack(spacing: 5) {
                Image(systemName: icon).foregroundStyle(HSKColors.cinnabarDark)
                Text("\(value)").font(.headline.monospacedDigit()).foregroundStyle(HSKColors.ink)
                Text(label).font(.caption2).foregroundStyle(HSKColors.inkSecondary).lineLimit(1)
            }
            .frame(maxWidth: .infinity)
        }
    }
}
