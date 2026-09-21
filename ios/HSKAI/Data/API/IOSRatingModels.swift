import Foundation

struct IOSRatingResponse: Decodable, Sendable, Equatable {
    let ok: Bool
    let rank: Int
    let league: String
    let leagueSize: Int
    let weeklyXp: Int
    let dailyXp: Int
    let streak: Int
    let weeklyResetSeconds: Int
    let leaderboard: [IOSRatingEntry]
}

struct IOSRatingEntry: Decodable, Sendable, Equatable, Identifiable {
    let challengeRef: String
    let rank: Int
    let name: String
    let username: String
    let xp: Int
    let courseLevel: String
    let isPaid: Bool
    let isCurrentUser: Bool

    var id: String { challengeRef.isEmpty ? "\(rank):\(name):\(username)" : challengeRef }
}

struct IOSReferralResponse: Decodable, Sendable, Equatable {
    let ok: Bool
    let code: String
    let link: String
    let invited: Int
    let activated: Int
    let trialProgress: Int
    let trialRequired: Int
    let items: [IOSReferralItem]
}

struct IOSReferralItem: Decodable, Sendable, Equatable, Identifiable {
    let name: String
    let status: String
    let joinedAt: String
    let activatedAt: String
    let courseLevel: String
    let completedLessons: Int
    let isPaid: Bool

    var id: String { "\(name):\(joinedAt):\(courseLevel)" }
}
