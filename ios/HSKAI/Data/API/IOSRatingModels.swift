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
