import Foundation

struct IOSSubscriptionOverview: Decodable, Sendable {
    let ok: Bool?
    let status: String?
    let isPaid: Bool?
    let planType: String?
    let expiresAt: String?
    let trialActive: Bool?
    let trialEndsAt: String?
}

struct IOSTrialStatus: Decodable, Sendable {
    let ok: Bool?
    let available: Bool?
    let active: Bool?
    let started: Bool?
    let endsAt: String?
    let expiresAt: String?
    let error: String?
}
