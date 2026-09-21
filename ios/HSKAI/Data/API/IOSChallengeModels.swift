import Foundation

struct IOSChallengeList: Decodable, Sendable {
    let ok: Bool
    let pendingCount: Int
    let activeCount: Int
    let items: [IOSChallenge]
}
struct IOSChallenge: Decodable, Sendable, Identifiable {
    let id: Int
    let status: String
    let viewerRole: String
    let viewerDone: Bool
    let opponentDone: Bool
    let otherUser: IOSChallengeUser
    let challengerScore: Int?
    let opponentScore: Int?
    let winnerRole: String?
}
struct IOSChallengeUser: Decodable, Sendable { let name: String; let username: String }
struct IOSChallengeAction: Decodable, Sendable { let ok: Bool; let error: String?; let notificationSent: Bool? }
struct IOSChallengeStart: Decodable, Sendable { let ok: Bool; let session: IOSChallengeSession }
struct IOSChallengeSession: Decodable, Sendable { let id: String; let challengeId: Int; let questions: [IOSChallengeQuestion] }
struct IOSChallengeQuestion: Decodable, Sendable, Identifiable { let id: String; let prompt: String; let sentence: String; let audioText: String; let options: [String] }
struct IOSChallengeCreate: Encodable { let opponentRef: String; let level: String; let language: String }
struct IOSChallengeRespond: Encodable { let action: String }
struct IOSChallengeAnswer: Encodable { let questionId: String; let selectedIndex: Int }
struct IOSChallengeSubmit: Encodable { let answers: [IOSChallengeAnswer]; let durationSeconds: Int }
