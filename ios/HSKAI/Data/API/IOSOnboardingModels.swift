import Foundation

struct IOSOnboardingProfile: Decodable, Sendable {
    let goal: String
    let dailyMinutes: Int
    let startMode: String
    let timezoneOffsetMinutes: Int
}

struct IOSOnboardingStatus: Decodable, Sendable {
    let ok: Bool
    let completed: Bool
    let level: String
    let profile: IOSOnboardingProfile
}

struct IOSOnboardingRequest: Encodable, Sendable {
    let level: String
    let goal: String
    let dailyMinutes: Int
    let startMode: String
    let language: String
    let timezoneOffsetMinutes: Int
    let activationVariant: String
}

struct IOSOnboardingComplete: Decodable, Sendable {
    let ok: Bool
    let profile: IOSOnboardingProfile?
    let level: String
    let lesson: Int?
    let tab: String
    let placement: Bool
    let reviewOnly: Bool
    let foundationRequired: Bool
    let error: String?
}
